from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from models import Ticket

with workflow.unsafe.imports_passed_through():
    from activities import (
        agent_resolve,
        assign_agent,
        notify_customer,
        notify_management,
        apply_urgent_fix,
        agent_investigate,
        send_auto_response,
        search_knowledge_base,
        escalate_to_engineering,
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

    async def _wait_if_paused(self):
        await workflow.wait_condition(lambda: not self.is_paused)

    # Activity wrappers - simplifies workflow code while unifying activity invocation
    async def do_agent_resolve(self, ticket):
        resolve_result = await _execute_activity(
            agent_resolve, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Agent investigating, ticket resolved")
        workflow.logger.info(f"{resolve_result}")
        await self._wait_if_paused()

    async def do_assign_agent(self, ticket) -> str:
        agent = await _execute_activity(
            assign_agent, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("agent assigned")
        workflow.logger.info(f"Assigned to {agent}")
        await self._wait_if_paused()
        return agent

    async def do_notify_customer(self, ticket, message: str):
        await _execute_activity(
            notify_customer, ticket, message,
            task_queue="support",
        )
        self.steps_completed.append("Customer notified")
        workflow.logger.info(f"Customer notified: {message}")
        # Don't wait for pause on the notification step

    async def do_search_knowledge_base(self, ticket) -> str:
        solution = await _execute_activity(
            search_knowledge_base, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Search KB")
        workflow.logger.info(f"KB search successful: {solution}")
        await self._wait_if_paused()
        return solution

    async def do_send_auto_response(self, ticket) -> str:
        auto_result = await _execute_activity(
            send_auto_response, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Auto-response sent")
        workflow.logger.info(f"Result: {auto_result}")
        await self._wait_if_paused()
        return auto_result

    async def do_escalate_to_engineering(self, ticket) -> str:
        esc_result = await _execute_activity(
            escalate_to_engineering, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("Escalating ticket...")
        workflow.logger.info(f"{esc_result}")
        await self._wait_if_paused()
        return esc_result

    async def do_agent_investigate(self, ticket) -> str:
        investigation_result = await _execute_activity(
            agent_investigate, ticket,
            task_queue="internal",
        )
        self.steps_completed.append("Agent investigating")
        workflow.logger.info(f"Investigation: {investigation_result}")
        await self._wait_if_paused()
        return investigation_result

    async def do_notify_management(self, ticket):
        await _execute_activity(
            notify_management, ticket,
            task_queue="support",
        )
        self.steps_completed.append("Notifying mgmt")
        workflow.logger.info(f"Notifying management about ticket ({ticket.ticket_id}) status: {ticket.status}")
        # Don't pause on notifying management

    async def do_apply_urgent_fix(self, ticket) -> str:
        fix_result = await _execute_activity(
            apply_urgent_fix, ticket,
            task_queue="engineering",
        )
        self.steps_completed.append("Applying urgent fix")
        workflow.logger.info(f"Applying urgent fix result: {fix_result}")
        await self._wait_if_paused()
        return fix_result

# TODO - for diagnosing 'TypeError - 'Task' object is not callable'
# @workflow.defn
# class SupportTicketSystem2(WorkflowBase):
#     def __init__(self):
#         super().__init__()
#
#     @workflow.run
#     async def run(self, ticket: Ticket) -> str:
#         workflow.logger.info("🚀 ISOLATED TEST")
#         return "success"

@workflow.defn
class SupportTicketSystem(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket) -> str:
        """
        Process a ticket - different paths based on priority
        """
        workflow.logger.info(f"\n{'=' * 70}\n")
        workflow.logger.info(f"Processing ticket {ticket.ticket_id}: {ticket.issue}\n")
        workflow.logger.info(f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
        workflow.logger.info(f"{'=' * 70}\n")

        # TODO This is to set the return value in the @workflow.query--I bet there's a better way to do this
        self.ticket_priority = ticket.priority

        try:
            if ticket.priority == "low":
                workflow.logger.info("🔵 Taking LOW priority path\n")
                await workflow.execute_child_workflow(
                    LowPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"low-{ticket.ticket_id}",
                )
                return "Low priority workflow started"

            elif ticket.priority == "medium":
                workflow.logger.info("🟡 Taking MEDIUM priority path\n")
                await workflow.execute_child_workflow(
                    MediumPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"medium-{ticket.ticket_id}",
                )
                return "Medium priority workflow started"

            elif ticket.priority == "high":
                workflow.logger.info("🔴 Taking HIGH priority path\n")
                await workflow.execute_child_workflow(
                    HighPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"high-{ticket.ticket_id}",
                )
                return "High priority workflow started"

            else:
                return f"Invalid priority: {ticket.priority}"

        except Exception as e:
            workflow.logger.info(f"\n❌ FAILURE: {str(e)}")
            workflow.logger.info(f"Ticket stuck in status: {ticket.status}")
            workflow.logger.info("Manual intervention required!\n")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

    @workflow.query
    def get_status(self) -> dict:
        return {
            "ticket_priority": self.ticket_priority,
            "current_step": self.steps_completed[-1] if self.steps_completed else "Initializing",
            "steps_completed": self.steps_completed,
            "current_step_number": len(self.steps_completed),
        }

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

@workflow.defn
class LowPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting low-priority workflow...")

        ticket.status = "auto_responding"
        await self.do_send_auto_response(ticket)

        try:
            ticket.status = "searching_kb"
            solution = await self.do_search_knowledge_base(ticket)
            await self.do_notify_customer(ticket, solution)

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
            return f"Resolved automatically: {ticket.ticket_id}"

        # TODO - this path seems to have problems--create test that forces failure
        # TODO - http://localhost:8080/namespaces/default/workflows/low-TEMP-001/526e76f8-d15b-4f8e-8772-f23bac38fa88/history
        # TODO - http://localhost:8080/namespaces/default/workflows/low-TEMP-001/74f936ee-41b3-4e8a-af5d-5856e550ab04/history
        except ApplicationError as e:
            # KB Search failed -- need human help
            workflow.logger.info("No solution found in knowledge base, assigning to agent...")
            await self.do_assign_agent(ticket)

            await self.do_agent_resolve(ticket)
            ticket.status = "resolved_by_agent"

            await self.do_notify_customer(ticket, "Your ticket has been resolved by our team!")

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
            return f"Resolved by agent: {ticket.ticket_id}"

@workflow.defn
class MediumPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting medium-priority workflow...")

        ticket.status = "assigning_agent"
        await self.do_assign_agent(ticket)

        ticket.status = "investigating"
        investigation_result = await self.do_agent_investigate(ticket)

        # TODO - Replace this with try/except pattern shown in "low"
        if investigation_result == "needs_escalation":
            ticket.status = "escalating"
            await self.do_escalate_to_engineering(ticket)
            ticket.status = "resolved_escalated"

            await self.do_notify_customer(ticket, "Your issue required engineering review and has been resolved!")

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after escalation!\n")
            return f"Resolved with escalation: {ticket.ticket_id}"
        else:
            ticket.status = "resolving"
            resolve_result = await self.do_agent_resolve(ticket)
            workflow.logger.info(f"Agent resolution: {resolve_result}")
            await self.do_notify_customer(ticket, "Your ticket has been resolved by agent!")

            ticket.status = "resolved medium"

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved normally!\n")
            return f"Resolved normally: {ticket.ticket_id}"

@workflow.defn
class HighPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting high-priority workflow...")
        ticket.status = "assigning_senior_agent"
        workflow.logger.info(f"Assigning to senior agent...")
        agent = await self.do_assign_agent(ticket)

        ticket.status = "escalating"
        esc_result = await self.do_escalate_to_engineering(ticket)
        workflow.logger.info(f"{esc_result}")

        ticket.status = "urgent_fix"
        fix_result = await self.do_apply_urgent_fix(ticket)
        workflow.logger.info(f"Urgent Fix result: {fix_result}")

        ticket.status = "notifying everyone"
        await self.do_notify_customer(ticket, "Engineering fixed it!")
        await self.do_notify_management(ticket)

        ticket.status = "resolved_urgent"

        workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
        return f"Resolved urgently: {ticket.ticket_id}"
