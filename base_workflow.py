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

    # Activity wrappers - simplifies workflow code while unifying activity invocation
    async def do_agent_resolve(self, ticket):
        resolve_result = await self._execute_activity(
            agent_resolve, ticket,
            task_queue="support",
        )
        workflow.logger.debug(f"{resolve_result}")

    async def do_assign_agent(self, ticket) -> str:
        agent = await self._execute_activity(
            assign_agent, ticket,
            task_queue="internal",
        )
        workflow.logger.debug(f"Assigned to {agent}")
        return agent

    async def do_notify_customer(self, ticket, message: str):
        await self._execute_activity(
            notify_customer, ticket, message,
            task_queue="support",
        )
        workflow.logger.debug(f"Customer notified: {message}")

    async def do_search_knowledge_base(self, ticket) -> str:
        solution = await self._execute_activity(
            search_knowledge_base, ticket,
            task_queue="support",
        )
        workflow.logger.debug(f"KB search successful: {solution}")
        return solution

    async def do_send_auto_response(self, ticket) -> str:
        auto_result = await self._execute_activity(
            send_auto_response, ticket,
            task_queue="support",
        )
        workflow.logger.debug(f"Result: {auto_result}")
        return auto_result

    async def do_escalate_to_engineering(self, ticket) -> str:
        esc_result = await self._execute_activity(
            escalate_to_engineering, ticket,
            task_queue="internal",
        )
        workflow.logger.debug(f"{esc_result}")
        return esc_result

    async def do_agent_investigate(self, ticket) -> str:
        investigation_result = await self._execute_activity(
            agent_investigate, ticket,
            task_queue="internal",
        )
        workflow.logger.debug(f"Investigation: {investigation_result}")
        return investigation_result

    async def do_notify_management(self, ticket):
        await self._execute_activity(
            notify_management, ticket,
            task_queue="support",
        )
        workflow.logger.debug(f"Notifying management about ticket ({ticket.ticket_id}) status: {ticket.status}")

    async def do_apply_urgent_fix(self, ticket) -> str:
        fix_result = await self._execute_activity(
            apply_urgent_fix, ticket,
            task_queue="engineering",
        )
        workflow.logger.debug(f"Applying urgent fix result: {fix_result}")
