import uuid
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
        self.current_step = ""

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

@workflow.defn
class SupportTicketSystem(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket) -> str:
        """
        Process a ticket - different paths based on priority
        """
        workflow.logger.info(f"\n{'=' * 70}")
        workflow.logger.info(f"Processing ticket {ticket.ticket_id}: {ticket.issue}")
        workflow.logger.info(f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}")
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
            "current_step": self.current_step,
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

        # Step 1: Auto-response
        ticket.status = "auto_responding"
        self.current_step = ticket.status
        auto_result = await _execute_activity(
            send_auto_response, ticket.ticket_id, ticket.customer_name,
            task_queue="support",
        )
        self.steps_completed.append("Auto-response sent")
        workflow.logger.info(f"Result: {auto_result}")
        await self._wait_if_paused()

        # Step 2: Search knowledge base
        ticket.status = "searching_kb"
        self.current_step = ticket.status

        try:
            solution = await _execute_activity(
                search_knowledge_base, ticket.issue,
                task_queue="support",
            )
            self.steps_completed.append("Searching KB")
            await self._wait_if_paused()

            ticket.status = "resolved_auto"
            self.current_step = ticket.status
            await _execute_activity(
                notify_customer, ticket.ticket_id, f"Your issue has been resolved! {solution}",
                task_queue="support",
            )
            self.steps_completed.append("KB success")
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
            return f"Resolved automatically: {ticket.ticket_id}"

        # TODO - this path seems to have problems--create test that forces failure
        # TODO - http://localhost:8080/namespaces/default/workflows/low-TEMP-001/526e76f8-d15b-4f8e-8772-f23bac38fa88/history
        # TODO - http://localhost:8080/namespaces/default/workflows/low-TEMP-001/74f936ee-41b3-4e8a-af5d-5856e550ab04/history
        except ApplicationError as e:
            # KB Search failed -- need human help
            workflow.logger.info("No solution found, assigning to agent...")
            agent = await _execute_activity(
                assign_agent, ticket.ticket_id, ticket.priority,
                task_queue="internal",
            )
            self.steps_completed.append("KB unsuccessful: agent assigned")
            workflow.logger.info(f"Assigned to {agent}")
            await self._wait_if_paused()

            resolve_result = await _execute_activity(
                agent_resolve, ticket.ticket_id,
                task_queue="support",
            )
            self.steps_completed.append("Agent investigating, ticket resolved")
            workflow.logger.info(f"{resolve_result}")
            ticket.status = "resolved_by_agent"
            await self._wait_if_paused()

            ticket.status = "notify_customer"
            self.current_step = ticket.status
            await _execute_activity(
                notify_customer,
                ticket.ticket_id, "Your ticket has been resolved by our team!",
                task_queue="support",
            )
            self.steps_completed.append("Agent successful")
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
            return f"Resolved by agent: {ticket.ticket_id}"

@workflow.defn
class MediumPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting medium-priority workflow...")

        # Step 1: Assign agent
        ticket.status = "assigning_agent"
        self.current_step = ticket.status
        agent = await _execute_activity(
            assign_agent, ticket.ticket_id, ticket.priority,
            task_queue="internal",
        )
        self.steps_completed.append("Agent investigating")
        workflow.logger.info(f"Assigned to {agent}")
        await self._wait_if_paused()

        # Step 2: Investigate
        ticket.status = "investigating"
        self.current_step = ticket.status
        investigation_result = await _execute_activity(
            agent_investigate, ticket.ticket_id, ticket.issue,
            task_queue="internal",
        )
        self.steps_completed.append("Agent investigating")
        workflow.logger.info(f"Investigation: {investigation_result}")
        await self._wait_if_paused()

        # TODO - Replace this with try/except pattern shown in "low"
        if investigation_result == "needs_escalation":
            # Escalate to engineering
            workflow.logger.info("Issue needs escalation...")
            ticket.status = "escalating"
            self.current_step = ticket.status
            esc_result = await _execute_activity(
                escalate_to_engineering, ticket.ticket_id, ticket.issue,
                task_queue="internal",
            )
            self.steps_completed.append("Escalating ticket")
            workflow.logger.info(f"{esc_result}")
            await self._wait_if_paused()

            ticket.status = "resolved_escalated"
            self.current_step = ticket.status
            await _execute_activity(
                notify_customer, ticket.ticket_id, "Your issue required engineering review and has been resolved!",
                task_queue="support",
            )
            self.steps_completed.append("Escalation successful")
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after escalation!\n")
            return f"Resolved with escalation: {ticket.ticket_id}"
        else:
            # Resolve normally
            ticket.status = "resolving"
            self.current_step = ticket.status
            resolve_result = await _execute_activity(
                agent_resolve, ticket.ticket_id,
                task_queue="support",
            )
            self.steps_completed.append("Agent resolving")
            workflow.logger.info(f"{resolve_result}")
            await self._wait_if_paused()

            ticket.status = "resolved_agent"
            self.current_step = ticket.status
            await _execute_activity(
                notify_customer, ticket.ticket_id, "Your ticket has been resolved!",
                task_queue="support",
            )
            self.steps_completed.append("Agent resolved")
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved normally!\n")
            return f"Resolved normally: {ticket.ticket_id}"

@workflow.defn
class HighPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting high-priority workflow...")
        # Step 1: Assign senior agent immediately
        ticket.status = "assigning_senior"
        self.current_step = ticket.status
        agent = await _execute_activity(
            assign_agent, ticket.ticket_id, ticket.priority,
            task_queue="internal",
        )
        self.steps_completed.append("Assigning sr agent")
        workflow.logger.info(f"Assigned to senior: {agent}")
        await self._wait_if_paused()

        # Step 2: Escalate immediately
        ticket.status = "escalating"
        self.current_step = ticket.status
        await self._wait_if_paused()
        esc_result = await _execute_activity(
            escalate_to_engineering, ticket.ticket_id, ticket.issue,
            task_queue="internal",
        )
        self.steps_completed.append("Escalating ticket")
        workflow.logger.info(f"{esc_result}")
        await self._wait_if_paused()

        # Step 3: Apply urgent fix
        ticket.status = "urgent_fix"
        self.current_step = ticket.status
        await self._wait_if_paused()
        fix_result = await _execute_activity(
            apply_urgent_fix,
            ticket.ticket_id,
            task_queue="engineering",
        )
        self.steps_completed.append("Applying urgent fix")
        workflow.logger.info(f"{fix_result}")
        await self._wait_if_paused()

        # Step 4: Notify everyone
        ticket.status = "notifying"
        self.current_step = ticket.status
        await self._wait_if_paused()
        await _execute_activity(
            notify_customer, ticket.ticket_id, "Engineering fixed it!",
            task_queue="support",
        )
        self.steps_completed.append("Notifying re ticket")
        workflow.logger.info(f"Customer notified")
        await self._wait_if_paused()

        await _execute_activity(
            notify_management, ticket.ticket_id, ticket.priority,
            task_queue="support",
        )
        self.steps_completed.append("Notifying mgmt")
        workflow.logger.info(f"Management notified")

        ticket.status = "resolved_urgent"
        self.current_step = ticket.status
        self.steps_completed.append("Ticket resolved")
        workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
        return f"Resolved urgently: {ticket.ticket_id}"
