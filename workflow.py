from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from models import Ticket

DEFAULT_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
)

with workflow.unsafe.imports_passed_through():
    from activities import (
        resolve_ticket,
        assign_agent,
        notify_customer,
        notify_management,
        escalate_to_engineering,
        apply_urgent_fix,
        investigate_issue,
        send_auto_response,
        search_knowledge_base,
    )

@workflow.defn
class SupportTicketSystem:
    def __init__(self):
        self.steps_completed = []
        self.ticket_priority = "Initializing"
        self.current_step = "Initializing"
        self.is_paused = False

    @workflow.run
    async def process_ticket(self, ticket: Ticket) -> str:
        """
        Process a ticket - different paths based on priority
        """
        workflow.logger.info(f"\n{'=' * 70}")
        workflow.logger.info(f"Processing ticket {ticket.ticket_id}: {ticket.issue}")
        workflow.logger.info(f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}")
        workflow.logger.info(f"{'=' * 70}\n")

        self.ticket_priority = ticket.priority

        try:
            # LOW PRIORITY PATH
            if ticket.priority == "low":
                workflow.logger.info("🔵 Taking LOW priority path\n")

                # Step 1: Auto-response
                ticket.status = "auto_responding"
                self.current_step = ticket.status
                await self._wait_if_paused()
                auto_result = await workflow.execute_activity(
                    send_auto_response,
                    args=[ticket.ticket_id, ticket.customer_name],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Auto-response sent")
                workflow.logger.info(f"Result: {auto_result}")

                # Step 2: Search knowledge base
                ticket.status = "searching_kb"
                self.current_step = ticket.status
                await self._wait_if_paused()
                kb_result = await workflow.execute_activity(
                    search_knowledge_base,
                    args=[ticket.issue],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Searching KB")
                workflow.logger.info(f"Knowledge base search: {kb_result}")

                if kb_result == "solution_found":
                    ticket.status = "resolved_auto"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    await workflow.execute_activity(
                        notify_customer,
                        args=[ticket.ticket_id, "Your issue has been resolved! Check the solution link."],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("KB success")
                    workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
                    return f"Resolved automatically: {ticket.ticket_id}"
                else:
                    # Need human help
                    workflow.logger.info("No solution found, assigning to agent...")
                    await self._wait_if_paused()
                    agent = await workflow.execute_activity(
                        assign_agent,
                        args=[ticket.ticket_id, ticket.priority],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("KB unsuccessful: agent assigned")
                    workflow.logger.info(f"Assigned to {agent}")

                    await self._wait_if_paused()
                    resolve_result = await workflow.execute_activity(
                        resolve_ticket,
                        ticket.ticket_id,
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Agent investigating")
                    workflow.logger.info(f"{resolve_result}")

                    ticket.status = "resolved_agent"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    await workflow.execute_activity(
                        notify_customer,
                        args=[ticket.ticket_id, "Your ticket has been resolved by our team!"],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Agent successful")
                    workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
                    return f"Resolved by agent: {ticket.ticket_id}"

            # MEDIUM PRIORITY PATH
            elif ticket.priority == "medium":
                workflow.logger.info("🟡 Taking MEDIUM priority path\n")

                # Step 1: Assign agent
                ticket.status = "assigning_agent"
                self.current_step = ticket.status
                await self._wait_if_paused()
                agent = await workflow.execute_activity(
                    assign_agent,
                    args=[ticket.ticket_id, ticket.priority],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Agent investigating")
                workflow.logger.info(f"Assigned to {agent}")

                # Step 2: Investigate
                ticket.status = "investigating"
                self.current_step = ticket.status
                await self._wait_if_paused()
                investigation_result = await workflow.execute_activity(
                    investigate_issue,
                    args=[ticket.ticket_id, ticket.issue],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Agent investigating")
                workflow.logger.info(f"Investigation: {investigation_result}")

                if investigation_result == "needs_escalation":
                    # Escalate to engineering
                    workflow.logger.info("Issue needs escalation...")
                    ticket.status = "escalating"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    esc_result = await workflow.execute_activity(
                        escalate_to_engineering,
                        args=[ticket.ticket_id, ticket.issue],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Escalating ticket")
                    workflow.logger.info(f"{esc_result}")

                    ticket.status = "resolved_escalated"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    await workflow.execute_activity(
                        notify_customer,
                        args=[ticket.ticket_id, "Your issue required engineering review and has been resolved!"],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Escalation successful")
                    workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after escalation!\n")
                    return f"Resolved with escalation: {ticket.ticket_id}"
                else:
                    # Resolve normally
                    ticket.status = "resolving"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    resolve_result = await workflow.execute_activity(
                        resolve_ticket,
                        ticket.ticket_id,
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Agent resolving")
                    workflow.logger.info(f"{resolve_result}")

                    ticket.status = "resolved_agent"
                    self.current_step = ticket.status
                    await self._wait_if_paused()
                    await workflow.execute_activity(
                        notify_customer,
                        args=[ticket.ticket_id, "Your ticket has been resolved!"],
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    self.steps_completed.append("Agent resolved")
                    workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved normally!\n")
                    return f"Resolved normally: {ticket.ticket_id}"

            # HIGH PRIORITY PATH
            elif ticket.priority == "high":
                workflow.logger.info("🔴 Taking HIGH priority path\n")

                # Step 1: Assign senior agent immediately
                ticket.status = "assigning_senior"
                self.current_step = ticket.status
                await self._wait_if_paused()
                agent = await workflow.execute_activity(
                    assign_agent,
                    args=[ticket.ticket_id, ticket.priority],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Assigning sr agent")
                workflow.logger.info(f"Assigned to senior: {agent}")

                # Step 2: Escalate immediately
                ticket.status = "escalating"
                self.current_step = ticket.status
                await self._wait_if_paused()
                esc_result = await workflow.execute_activity(
                    escalate_to_engineering,
                    args=[ticket.ticket_id, ticket.issue],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Escalating ticket")
                workflow.logger.info(f"{esc_result}")

                # Step 3: Apply urgent fix
                ticket.status = "urgent_fix"
                self.current_step = ticket.status
                await self._wait_if_paused()
                fix_result = await workflow.execute_activity(
                    apply_urgent_fix,
                    args=[ticket.ticket_id],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Applying urgent fix")
                workflow.logger.info(f"{fix_result}")

                # Step 4: Notify everyone
                ticket.status = "notifying"
                self.current_step = ticket.status
                await self._wait_if_paused()
                await workflow.execute_activity(
                    notify_customer,
                    args=[ticket.ticket_id, "Your ticket has been resolved with an engineering fix!"],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Notifying re ticket")
                workflow.logger.info(f"Customer notified")

                await self._wait_if_paused()
                await workflow.execute_activity(
                    notify_management,
                    args=[ticket.ticket_id, ticket.priority],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                self.steps_completed.append("Notifying mgmt")
                workflow.logger.info(f"Management notified")

                ticket.status = "resolved_urgent"
                self.current_step = ticket.status
                self.steps_completed.append("Ticket resolved")
                workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
                return f"Resolved urgently: {ticket.ticket_id}"

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

    @workflow.signal
    def pause(self):
        self.is_paused = True
        workflow.logger.info("Pausing Workflow...")

    @workflow.signal
    def resume(self):
        self.is_paused = False
        workflow.logger.info("Resuming Workflow...")

    async def _wait_if_paused(self):
        await workflow.wait_condition(lambda: not self.is_paused)