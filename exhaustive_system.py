import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import aioredis
import aiomysql
from tenacity import retry, stop_after_attempt, wait_exponential


# Event sourcing infrastructure
@dataclass
class Event:
    event_id: str
    aggregate_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: float
    version: int


class EventStore:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def append_events(self, aggregate_id: str, events: List[Event], expected_version: int):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Optimistic concurrency check
                await cursor.execute(
                    "SELECT MAX(version) FROM events WHERE aggregate_id = %s",
                    (aggregate_id,)
                )
                current_version = (await cursor.fetchone())[0] or 0

                if current_version != expected_version:
                    raise ConcurrencyError(f"Expected version {expected_version}, got {current_version}")

                # Atomic event insertion
                for event in events:
                    await cursor.execute(
                        """INSERT INTO events (event_id, aggregate_id, event_type, event_data, timestamp, version)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (event.event_id, event.aggregate_id, event.event_type,
                         json.dumps(event.event_data), event.timestamp, event.version)
                    )
                await conn.commit()

    async def get_events(self, aggregate_id: str) -> List[Event]:
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM events WHERE aggregate_id = %s ORDER BY version",
                    (aggregate_id,)
                )
                rows = await cursor.fetchall()
                return [Event(**row) for row in rows]


# State management with snapshots
class TicketAggregate:
    def __init__(self):
        self.ticket_id: str = ""
        self.status: str = "new"
        self.assigned_agent: str = ""
        self.priority: str = ""
        self.version: int = 0
        self.events: List[Event] = []

    def apply_event(self, event: Event):
        if event.event_type == "TicketCreated":
            self.ticket_id = event.event_data["ticket_id"]
            self.priority = event.event_data["priority"]
        elif event.event_type == "AgentAssigned":
            self.assigned_agent = event.event_data["agent_id"]
            self.status = "assigned"
        elif event.event_type == "StatusChanged":
            self.status = event.event_data["new_status"]
        # ... handle all event types

        self.version = event.version


# Distributed lock for coordination
class DistributedLock:
    def __init__(self, redis_client, key: str, ttl: int = 30):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.lock_id = str(uuid.uuid4())

    async def acquire(self, timeout: int = 10):
        end_time = time.time() + timeout
        while time.time() < end_time:
            acquired = await self.redis.set(
                self.key, self.lock_id, nx=True, ex=self.ttl
            )
            if acquired:
                return True
            await asyncio.sleep(0.1)
        return False

    async def release(self):
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.key, self.lock_id)


# Saga orchestration
class SupportTicketSaga:
    def __init__(self, event_store, redis_client, service_registry):
        self.event_store = event_store
        self.redis = redis_client
        self.services = service_registry
        self.logger = logging.getLogger(__name__)

    async def handle_ticket_created(self, ticket_data: Dict[str, Any]):
        saga_id = str(uuid.uuid4())

        # Persist saga state
        await self.redis.hset(
            f"saga:{saga_id}",
            mapping={
                "ticket_id": ticket_data["ticket_id"],
                "status": "started",
                "current_step": "auto_response",
                "compensation_stack": json.dumps([])
            }
        )

        try:
            if ticket_data["priority"] == "low":
                await self._handle_low_priority_flow(saga_id, ticket_data)
            elif ticket_data["priority"] == "medium":
                await self._handle_medium_priority_flow(saga_id, ticket_data)
            elif ticket_data["priority"] == "high":
                await self._handle_high_priority_flow(saga_id, ticket_data)

        except Exception as e:
            await self._compensate_saga(saga_id)
            raise

    async def _handle_low_priority_flow(self, saga_id: str, ticket_data: Dict[str, Any]):
        compensation_stack = []

        try:
            # Step 1: Send auto response
            await self._update_saga_step(saga_id, "auto_response")
            auto_response_id = await self._call_with_compensation(
                self.services.automation.send_auto_response,
                (ticket_data["ticket_id"], ticket_data["customer_name"]),
                compensation_stack,
                "cancel_auto_response"
            )

            # Step 2: Search knowledge base
            await self._update_saga_step(saga_id, "knowledge_search")
            kb_result = await self._call_with_retry_and_compensation(
                self.services.automation.search_knowledge_base,
                (ticket_data["issue"],),
                compensation_stack,
                "clear_kb_cache",
                max_attempts=3
            )

            if kb_result == "solution_found":
                # Success path
                await self._update_saga_step(saga_id, "completed")
                await self._emit_event(
                    ticket_data["ticket_id"],
                    "TicketResolved",
                    {"resolution_method": "automatic", "saga_id": saga_id}
                )
            else:
                # Escalate to agent
                await self._handle_agent_escalation(saga_id, ticket_data, compensation_stack)

        except Exception as e:
            self.logger.error(f"Saga {saga_id} failed at step {await self._get_saga_step(saga_id)}: {e}")
            await self._compensate_actions(compensation_stack)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def _call_with_retry_and_compensation(self, func, args, compensation_stack, compensation_action,
                                                max_attempts=3):
        try:
            result = await func(*args)
            compensation_stack.append({
                "action": compensation_action,
                "args": args,
                "timestamp": time.time()
            })
            return result
        except Exception as e:
            self.logger.error(f"Function {func.__name__} failed: {e}")
            raise

    async def _handle_agent_escalation(self, saga_id: str, ticket_data: Dict[str, Any], compensation_stack: List):
        # Distributed lock to prevent double assignment
        lock = DistributedLock(self.redis, f"agent_assignment:{ticket_data['ticket_id']}")

        if not await lock.acquire():
            raise Exception("Could not acquire agent assignment lock")

        try:
            agent_id = await self._call_with_compensation(
                self.services.agent.assign_agent,
                (ticket_data["ticket_id"], ticket_data["priority"]),
                compensation_stack,
                "release_agent"
            )

            # Persist agent assignment with idempotency
            await self._emit_event(
                ticket_data["ticket_id"],
                "AgentAssigned",
                {"agent_id": agent_id, "saga_id": saga_id}
            )

            # Continue with investigation...

        finally:
            await lock.release()

    async def _compensate_actions(self, compensation_stack: List):
        # Execute compensations in reverse order
        for compensation in reversed(compensation_stack):
            try:
                compensation_func = getattr(self.services, compensation["action"])
                await compensation_func(*compensation["args"])
                self.logger.info(f"Compensated: {compensation['action']}")
            except Exception as e:
                self.logger.error(f"Compensation failed for {compensation['action']}: {e}")

    async def _emit_event(self, aggregate_id: str, event_type: str, event_data: Dict[str, Any]):
        event = Event(
            event_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            event_type=event_type,
            event_data=event_data,
            timestamp=time.time(),
            version=await self._get_next_version(aggregate_id)
        )
        await self.event_store.append_events(aggregate_id, [event], event.version - 1)

    async def _update_saga_step(self, saga_id: str, step: str):
        await self.redis.hset(f"saga:{saga_id}", "current_step", step)

    async def _get_saga_step(self, saga_id: str) -> str:
        return await self.redis.hget(f"saga:{saga_id}", "current_step")


# Process manager for handling timeouts
class ProcessManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def schedule_timeout(self, saga_id: str, timeout_seconds: int, timeout_action: str):
        await self.redis.zadd(
            "timeout_queue",
            {f"{saga_id}:{timeout_action}": time.time() + timeout_seconds}
        )

    async def process_timeouts(self):
        while True:
            try:
                now = time.time()
                expired = await self.redis.zrangebyscore("timeout_queue", 0, now)

                for item in expired:
                    saga_id, action = item.decode().split(":", 1)
                    await self._handle_timeout(saga_id, action)
                    await self.redis.zrem("timeout_queue", item)

                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Timeout processing error: {e}")
                await asyncio.sleep(5)


# Dead letter queue handling
class DeadLetterHandler:
    def __init__(self, event_store):
        self.event_store = event_store

    async def handle_failed_message(self, message: Dict[str, Any], error: Exception):
        dlq_event = Event(
            event_id=str(uuid.uuid4()),
            aggregate_id=message.get("aggregate_id", "system"),
            event_type="MessageFailed",
            event_data={
                "original_message": message,
                "error": str(error),
                "retry_count": message.get("retry_count", 0),
                "timestamp": time.time()
            },
            timestamp=time.time(),
            version=1
        )
        await self.event_store.append_events("system", [dlq_event], 0)


# Exception classes
class ConcurrencyError(Exception):
    pass


class SagaCompensationError(Exception):
    pass