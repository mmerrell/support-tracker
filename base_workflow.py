from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

WORKFLOW_TASK_QUEUE = "workflows"
ESCALATION_TASK_QUEUE = "escalation"
SUPPORT_TASK_QUEUE = "support"
ENGINEERING_TASK_QUEUE = "engineering"

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
        validate_resolution,
        release_agent
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
    async def do_agent_resolve(self, ticket) -> str:
        resolve_result = await self._execute_activity(
            agent_resolve, ticket,
            task_queue=SUPPORT_TASK_QUEUE,
        )
        workflow.logger.debug(f"{resolve_result}")
        self._status = resolve_result
        return resolve_result

    async def do_assign_agent(self, ticket) -> str:
        assignment_result = await self._execute_activity(
            assign_agent, ticket,
            task_queue=ESCALATION_TASK_QUEUE,
        )
        workflow.logger.debug(f"Assignment result: {assignment_result}")
        self._status = assignment_result
        return assignment_result

    async def do_notify_customer(self, ticket, message: str):
        await self._execute_activity(
            notify_customer, ticket, message,
            task_queue=SUPPORT_TASK_QUEUE,
        )
        workflow.logger.debug(f"Customer notified: {message}")

    async def do_search_knowledge_base(self, ticket) -> str:
        solution = await self._execute_activity(
            search_knowledge_base, ticket,
            task_queue=SUPPORT_TASK_QUEUE,
        )
        workflow.logger.debug(f"KB search successful: {solution}")
        self._status = "searching_kb"
        return solution

    async def do_send_auto_response(self, ticket) -> str:
        auto_result = await self._execute_activity(
            send_auto_response, ticket,
            task_queue=SUPPORT_TASK_QUEUE,
        )
        workflow.logger.debug(f"Result: {auto_result}")
        self._status = "auto_responding"
        return auto_result

    async def do_escalate_to_engineering(self, ticket) -> str:
        esc_result = await self._execute_activity(
            escalate_to_engineering, ticket,
            task_queue=ESCALATION_TASK_QUEUE,
        )
        workflow.logger.debug(f"{esc_result}")
        self._status = esc_result
        return esc_result

    async def do_agent_investigate(self, ticket) -> str:
        investigation_result = await self._execute_activity(
            agent_investigate, ticket,
            task_queue=ESCALATION_TASK_QUEUE,
        )
        workflow.logger.debug(f"Investigation: {investigation_result}")
        self._status = investigation_result
        return investigation_result

    async def do_notify_management(self, ticket):
        await self._execute_activity(
            notify_management, ticket,
            task_queue=SUPPORT_TASK_QUEUE,
        )
        workflow.logger.debug(f"Notifying management about ticket ({ticket.ticket_id}) status: {self._status}")

    async def do_apply_urgent_fix(self, ticket) -> str:
        fix_result = await self._execute_activity(
            apply_urgent_fix, ticket,
            task_queue=ENGINEERING_TASK_QUEUE,
        )
        workflow.logger.debug(f"Applying urgent fix result: {fix_result}")
        self._status = fix_result
        return fix_result

    async def do_validate_resolution(self, ticket) -> str:
        fix_result = await self._execute_activity(
            validate_resolution, ticket,
            task_queue=ENGINEERING_TASK_QUEUE,
        )
        workflow.logger.debug(f"Validation result: {fix_result}")
        return fix_result

    async def do_release_agent(self, agent_name: str, ticket):
        return await self._execute_activity(
            release_agent, agent_name, ticket,
            task_queue=SUPPORT_TASK_QUEUE,
        )
