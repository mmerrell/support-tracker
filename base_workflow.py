from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import (
        agent_resolve,
        assign_agent,
        notify_customer,
        notify_management,
        escalate_to_engineering,
        apply_urgent_fix,
        agent_investigate,
        send_auto_response,
        search_knowledge_base,
    )

class WorkflowBase:
    def __init__(self):
        self.is_paused = False
        self.steps_completed = []

    @workflow.query
    async def is_paused(self):
        return self.is_paused

    @workflow.signal
    async def pause(self):
        self.is_paused = True
        workflow.logger.info("Pausing Workflow...")

    @workflow.signal
    async def resume(self):
        self.is_paused = False
        workflow.logger.info("Resuming Workflow...")

    @staticmethod
    async def _execute_activity(activity_call, *args, **kwargs):
        return await workflow.execute_activity(
            activity_call,
            args=list(args),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
            **kwargs
        )

    async def _wait_if_paused(self):
        await workflow.wait_condition(lambda: not self.is_paused)

    # Activity wrappers - simplifies workflow code while unifying activity invocation
    async def do_agent_resolve(self, ticket):
        resolve_result = await self._execute_activity(
            agent_resolve, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Agent investigating, ticket resolved")
        workflow.logger.info(f"{resolve_result}")
        await self._wait_if_paused()

    async def do_assign_agent(self, ticket) -> str:
        agent = await self._execute_activity(
            assign_agent, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("agent assigned")
        workflow.logger.info(f"Assigned to {agent}")
        await self._wait_if_paused()
        return agent

    async def do_notify_customer(self, ticket, message: str):
        await self._execute_activity(
            notify_customer, ticket, message,
            task_queue="support",
        )
        self.steps_completed.append("Customer notified")
        workflow.logger.info(f"Customer notified: {message}")
        # Don't wait for pause on the notification step

    async def do_search_knowledge_base(self, ticket) -> str:
        solution = await self._execute_activity(
            search_knowledge_base, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Search KB")
        workflow.logger.info(f"KB search successful: {solution}")
        await self._wait_if_paused()
        return solution

    async def do_send_auto_response(self, ticket) -> str:
        auto_result = await self._execute_activity(
            send_auto_response, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Auto-response sent")
        workflow.logger.info(f"Result: {auto_result}")
        await self._wait_if_paused()
        return auto_result

    async def do_escalate_to_engineering(self, ticket) -> str:
        esc_result = await self._execute_activity(
            escalate_to_engineering, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("Escalating ticket...")
        workflow.logger.info(f"{esc_result}")
        await self._wait_if_paused()
        return esc_result

    async def do_agent_investigate(self, ticket) -> str:
        investigation_result = await self._execute_activity(
            agent_investigate, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("Agent investigating")
        workflow.logger.info(f"Investigation: {investigation_result}")
        await self._wait_if_paused()
        return investigation_result

    async def do_notify_management(self, ticket):
        await self._execute_activity(
            notify_management, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Notifying mgmt")
        workflow.logger.info(f"Notifying management about ticket ({ticket.ticket_id}) status: {ticket.status}")
        # Don't pause on notifying management

    async def do_apply_urgent_fix(self, ticket) -> str:
        fix_result = await self._execute_activity(
            apply_urgent_fix, ticket,
            task_queue="engineering",
        )
        self.steps_completed.append("Applying urgent fix")
        workflow.logger.info(f"Applying urgent fix result: {fix_result}")
        await self._wait_if_paused()
        return fix_result
