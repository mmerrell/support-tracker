from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError

from base_workflow import WorkflowBase
from models import Ticket

@workflow.defn
class SupportTicketSystem(WorkflowBase):
    @workflow.run
    async def run(self, ticket: Ticket) -> str:
        try:
            if ticket.priority == "low":
                workflow.logger.info("🔵 LOW priority ticket {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
                await self.do_send_auto_response(ticket)

                result = await workflow.execute_child_workflow(
                    LowPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"low-{ticket.ticket_id}",
                )
                return result

            elif ticket.priority == "medium":
                workflow.logger.info("🟡 MEDIUM priority {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
                result = await workflow.execute_child_workflow(
                    MediumPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"medium-{ticket.ticket_id}",
                )
                return result

            elif ticket.priority == "high":
                workflow.logger.info("🔴 HIGH priority {ticket.ticket_id}: {ticket.issue}\n"
                             f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
                result = await workflow.execute_child_workflow(
                    HighPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"high-{ticket.ticket_id}",
                )
                return result

            else:
                return f"Invalid priority: {ticket.priority}"

        except ApplicationError as e:
            workflow.logger.info(f"\n❌ FAILURE: Unable to resolve ticket. Ticket added to backlog {str(e)}")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

        except Exception as e:
            workflow.logger.error(f"\n❌❌❌ TEMPORAL WORKFLOW FAILURE: {type(e)} {str(e)}")
            workflow.logger.error(f"Ticket stuck in status: {ticket.status}")
            workflow.logger.error("Manual intervention required!\n")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

@workflow.defn
class LowPriorityWorkflow(WorkflowBase):
    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.debug(f"{ticket.ticket_id} Starting low-priority workflow...")
        await self.do_send_auto_response(ticket)

        try:
            solution = await self.do_search_knowledge_base(ticket)
            await self.do_notify_customer(ticket, solution)

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
            return f"Resolved automatically: {ticket.ticket_id}"

        except ActivityError:
            # KB Search failed -- need human help
            workflow.logger.debug(f"{ticket.ticket_id} No solution found in knowledge base, assigning to agent...")
            await self.do_assign_agent(ticket)
            await self.do_agent_resolve(ticket)
            await self.do_notify_customer(ticket, "Your ticket has been resolved by our team!")

            ticket.status = "resolved_low"
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
            return f"Resolved by agent: {ticket.ticket_id}"

@workflow.defn
class MediumPriorityWorkflow(WorkflowBase):
    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.debug("Starting medium-priority workflow...")

        await self.do_assign_agent(ticket)
        assignment_result = await self.do_agent_investigate(ticket)
        if assignment_result != "agent_unavailable":
            await self.do_notify_customer(ticket, f"Your issue has been resolved by {assignment_result}!")

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after investigation!\n")
            return f"Resolved with investigation: {ticket.ticket_id}"

        workflow.logger.debug("Investigation failed, escalate to engineering")
        esc_result = await self.do_escalate_to_engineering(ticket)
        if esc_result == "Engineering rejected":
            workflow.logger.debug("Engineering rejected - reassigning to agent for further investigation")
            try:
                await self.do_assign_agent(ticket)
                final_result = await self.do_agent_resolve(ticket)
                await self.do_notify_customer(ticket, "Resolved by agent after engineering review!")
                return f"✅ SUCCESS: Resolved by agent after engineering review: {ticket.ticket_id}, {final_result}"

            except ActivityError:
                workflow.logger.debug("Agent could not resolve--notifying management")
                await self.do_notify_customer(ticket, "This issue required engineering review, but no agent could resolve")
                await self.do_notify_management(ticket)
                return f"❌ FAILURE: Agent unable to resolve, management notified"

        else:
            ticket.status = "resolved_medium"
            await self.do_notify_customer(ticket, "Resolved by engineering after escalation")
            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by engineering!\n")
            return f"Resolved by engineering: {ticket.ticket_id}"

@workflow.defn
class HighPriorityWorkflow(WorkflowBase):
    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.debug("Starting high-priority workflow...")

        workflow.logger.debug(f"Assigning to senior agent...")
        await self.do_assign_agent(ticket)

        esc_result = await self.do_escalate_to_engineering(ticket)
        workflow.logger.debug(f"{esc_result}")

        fix_result = await self.do_apply_urgent_fix(ticket)
        workflow.logger.debug(f"Urgent Fix result: {fix_result}")
        if fix_result == "Urgent Fix failed!":
            workflow.logger.error(f"❌ FAILURE: Could not resolve with urgent fix: {fix_result}. Adding ticket to backlog")
            await self.do_notify_management(ticket)

        ticket.status = "resolved_high"
        await self.do_notify_customer(ticket, "Engineering fixed it!")
        await self.do_notify_management(ticket)

        workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
        return f"Resolved urgently: {ticket.ticket_id}"
