from typing import Optional, List

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError

from base_workflow import WorkflowBase
from enums import InvestigationResult, FixResult, EscalationResult
from models import Ticket

@workflow.defn
class SupportTicketSystem(WorkflowBase):
    def __init__(self):
        self._status = "new"
        self._assigned_agent: Optional[str] = None
        self._timeline: List[dict] = []
        self._escalation_count = 0
        self._resolution_attempts = 0

    @workflow.query
    def status(self) -> str:
        return self._status

    @workflow.query
    def assigned_agent(self) -> Optional[str]:
        return self._assigned_agent

    @workflow.query
    def timeline(self) -> List[dict]:
        return self._timeline

    @workflow.query
    def escalation_count(self) -> int:
        return self._escalation_count

    def _add_timeline_event(self, event: str, details: str = ""):
        self._timeline.append({
            "timestamp": workflow.now().isoformat(),
            "event": event,
            "details": details,
            "status": self._status
        })

    @workflow.run
    async def run(self, ticket: Ticket) -> str:
        self._status = "triaging"
        self._add_timeline_event("workflow_started", f"Priority: {ticket.priority}")

        try:
            if ticket.priority == "low":
                workflow.logger.info("🔵 LOW priority ticket {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")

                result = await workflow.execute_child_workflow(
                    LowPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"low-{ticket.ticket_id}",
                )
                self._status = "completed"
                self._add_timeline_event("workflow_completed", result)
                return result

            elif ticket.priority == "medium":
                self._status = "processing_medium_priority"
                workflow.logger.info("🟡 MEDIUM priority {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
                result = await workflow.execute_child_workflow(
                    MediumPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"medium-{ticket.ticket_id}",
                )
                self._status = "completed"
                self._add_timeline_event("workflow_completed", result)
                return result

            elif ticket.priority == "high":
                self._status = "processing_high_priority"
                # steps.append("Routed to high priority workflow")
                workflow.logger.info("🔴 HIGH priority {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
                result = await workflow.execute_child_workflow(
                    HighPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"high-{ticket.ticket_id}",
                )
                self._status = "completed"
                self._add_timeline_event("workflow_completed", result)
                return result

            else:
                self._status = "failed"
                error_msg = f"Invalid priority: {ticket.priority}"
                self._add_timeline_event("validation_failed", error_msg)
                return error_msg

        except ApplicationError as e:
            self._status = "failed"
            self._add_timeline_event("application_error", str(e))
            workflow.logger.info(f"\n❌ FAILURE: Unable to resolve ticket. Ticket added to backlog {str(e)}")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

        except Exception as e:
            self._status = "failed"
            workflow.logger.error(f"\n❌❌❌ TEMPORAL WORKFLOW FAILURE: {type(e)} {str(e)}")
            workflow.logger.error(f"Ticket stuck in status: {self._status}")
            workflow.logger.error("Manual intervention required!\n")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

@workflow.defn
class LowPriorityWorkflow(WorkflowBase):
    def __init__(self):
        self._status = "new"
        self._kb_search_attempted = False
        self._agent_assigned = False
        self._resolution_method = None
        self._customer_notified = False

    @workflow.query
    def status(self) -> str:
        return self._status

    @workflow.query
    def resolution_method(self) -> Optional[str]:
        return self._resolution_method

    @workflow.run
    async def run(self, ticket: Ticket):
        self._status = "sending_auto_response"
        workflow.logger.debug(f"{ticket.ticket_id} Starting low-priority workflow...")
        await self.do_send_auto_response(ticket)

        try:
            self._status = "searching_knowledge_base"
            self._kb_search_attempted = True
            solution = await self.do_search_knowledge_base(ticket)

            self._status = "notifying_customer"
            await self.do_notify_customer(ticket, solution)
            self._customer_notified = True

            try:
                await self.do_validate_resolution(ticket)

                self._status = "resolved"
                self._resolution_method = "automated"
                workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
                return f"Resolved automatically: {ticket.ticket_id}"

            except (ActivityError, ApplicationError)    :
                workflow.logger.warn(f"Resolution validation failed - compensating notification for {ticket.ticket_id}")
                await self.do_notify_customer(ticket,"We apologize - our initial solution may not have worked. An agent will review your case.")
                self._customer_notified = False

        except ActivityError:
            # KB Search failed -- need human help
            self._status = "assigning_to_agent"
            self._agent_assigned = True
            workflow.logger.debug(f"{ticket.ticket_id} No solution found in knowledge base, assigning to agent...")

            self._status = "agent_resolving"
            await self.do_assign_agent(ticket)
            await self.do_agent_resolve(ticket)

            self._resolution_method = "agent"
            if not self._customer_notified:
                await self.do_notify_customer(ticket, "Your ticket has been resolved by our team!")

            self._status = "resolved"
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
            return f"Resolved by agent: {ticket.ticket_id}"

@workflow.defn
class MediumPriorityWorkflow(WorkflowBase):
    def __init__(self):
        self._status = "new"
        self._assigned_agent = None
        self._agent_reserved = False
        self._investigation_result = None
        self._escalated_to_engineering = False
        self._engineering_response = None

    @workflow.query
    def status(self) -> str:
        return self._status

    @workflow.query
    def assigned_agent(self) -> Optional[str]:
        return self._assigned_agent

    @workflow.query
    def was_escalated(self) -> bool:
        return self._escalated_to_engineering

    @workflow.run
    async def run(self, ticket: Ticket):
        self._status = "assigning_agent"
        try:
            self._assigned_agent = await self.do_assign_agent(ticket)
            self._agent_reserved = True
            workflow.logger.debug(f"Reserved agent {self._assigned_agent} for ticket {ticket.ticket_id}")

            self._status = "investigating"
            assignment_result = await self.do_agent_investigate(ticket)
            self._investigation_result = assignment_result

            if assignment_result == InvestigationResult.COMPLETE.value:
                self._status = "notifying_customer"
                await self.do_notify_customer(ticket, f"Your issue has been resolved by {self._assigned_agent}!")

                self._status = "resolved"
                workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after investigation!\n")
                return f"Resolved with investigation: {ticket.ticket_id}"

            if self._agent_reserved:
                workflow.logger.info(f"Investigation failed - releasing reserved agent {self._assigned_agent}")
                await self.do_release_agent(self._assigned_agent, ticket)
                self._agent_reserved = False

            self._status = "escalating_to_engineering"
            self._escalated_to_engineering = True
            workflow.logger.debug(f"{ticket.ticket_id} Investigation failed, escalate to engineering")

            esc_result = await self.do_escalate_to_engineering(ticket)
            self._engineering_response = esc_result

            if esc_result == EscalationResult.REJECTED.value:
                self._status = "reassigning_to_agent"
                workflow.logger.debug(
                    f"{ticket.ticket_id} Engineering rejected - reassigning to agent for further investigation")
                try:
                    new_agent = await self.do_assign_agent(ticket)
                    self._assigned_agent = new_agent
                    self._agent_reserved = True

                    self._status = "agent_final_attempt"
                    await self.do_agent_resolve(ticket)
                    await self.do_notify_customer(ticket, "Resolved by agent after engineering review!")

                    self._status = "resolved"
                    return f"Resolved by agent after engineering review: {ticket.ticket_id}"

                except ActivityError:
                    if self._agent_reserved:
                        workflow.logger.warn(f"Final agent attempt failed - releasing agent {self._assigned_agent}")
                        await self.do_release_agent(self._assigned_agent, ticket)
                        self._agent_reserved = False

                    self._status = "failed"
                    workflow.logger.debug(f"{ticket.ticket_id} Agent could not resolve--notifying management")
                    await self.do_notify_customer(ticket,
              "This issue required engineering review, but no agent could resolve")
                    await self.do_notify_management(ticket)
                    return f"Agent unable to resolve, management notified: {ticket.ticket_id}"

            else:
                # Engineering accepted and resolved
                self._status = "notifying_customer"
                await self.do_notify_customer(ticket, "Resolved by engineering after escalation")

                self._status = "resolved"
                workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by engineering!\n")
                return f"Resolved by engineering: {ticket.ticket_id}"

        except Exception as e:
            # Any unexpected failure - compensate agent reservation
            if self._agent_reserved:
                workflow.logger.warn(f"Unexpected workflow failure - releasing agent {self._assigned_agent}")
                await self.do_release_agent(self._assigned_agent, ticket)
                self._agent_reserved = False
            raise

@workflow.defn
class HighPriorityWorkflow(WorkflowBase):
    def __init__(self):
        self._status = "new"
        self._assigned_agent = None
        self._escalation_result = None
        self._fix_attempted = False
        self._fix_result = None

    @workflow.query
    def status(self) -> str:
        return self._status

    @workflow.query
    def assigned_agent(self) -> Optional[str]:
        return self._assigned_agent

    @workflow.query
    def fix_attempted(self) -> bool:
        return self._fix_attempted

    @workflow.run
    async def run(self, ticket: Ticket):
        self._status = "assigning_agent"
        workflow.logger.debug(f"{ticket.ticket_id} Starting high-priority workflow...")

        self._assigned_agent = await self.do_assign_agent(ticket)

        self._status = "escalating_to_engineering"
        esc_result = await self.do_escalate_to_engineering(ticket)
        self._escalation_result = esc_result
        workflow.logger.debug(f"{ticket.ticket_id}: {esc_result}")

        self._status = "applying_urgent_fix"
        self._fix_attempted = True
        fix_result = await self.do_apply_urgent_fix(ticket)
        self._fix_result = fix_result
        workflow.logger.debug(f"{ticket.ticket_id} Urgent Fix result: {fix_result}")

        if fix_result == FixResult.FAILED.value:
            self._status = "failed"
            workflow.logger.error(f"❌ FAILURE: Could not resolve with urgent fix. Adding ticket to backlog")
            await self.do_notify_customer(ticket, "Engineering unable to resolve -- we will follow up soon!")
            await self.do_notify_management(ticket)
            return f"Failed to resolve urgent issue: {ticket.ticket_id}"  # Fixed: missing return

        else:
            self._status = "notifying_stakeholders"
            await self.do_notify_customer(ticket, "Engineering fixed it!")
            await self.do_notify_management(ticket)

            self._status = "resolved"
            workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
            return f"Resolved urgently: {ticket.ticket_id}"
