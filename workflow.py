from temporalio import workflow
from temporalio.exceptions import ApplicationError, ActivityError

from base_workflow import WorkflowBase
from models import Ticket

@workflow.defn
class SupportTicketSystem(WorkflowBase):
    @workflow.run
    async def run(self, ticket: Ticket) -> str:
        """
        Process a ticket - different paths based on priority
        """
        workflow.logger.info(f"\n{'=' * 70}\n")
        workflow.logger.info(f"Processing ticket {ticket.ticket_id}: {ticket.issue}\n")
        workflow.logger.info(f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}\n")
        workflow.logger.info(f"{'=' * 70}\n")

        try:
            if ticket.priority == "low":
                workflow.logger.info("🔵 LOW priority\n")
                ticket.status = "auto_responding"
                await self.do_send_auto_response(ticket)

                result = await workflow.execute_child_workflow(
                    LowPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"low-{ticket.ticket_id}",
                )
                return result

            elif ticket.priority == "medium":
                workflow.logger.info("🟡 MEDIUM priority\n")
                result = await workflow.execute_child_workflow(
                    MediumPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"medium-{ticket.ticket_id}",
                )
                return result

            elif ticket.priority == "high":
                workflow.logger.info("🔴 HIGH priority\n")
                result = await workflow.execute_child_workflow(
                    HighPriorityWorkflow.run,
                    ticket,
                    task_queue="workflows",
                    id=f"high-{ticket.ticket_id}",
                )
                return result

            else:
                return f"Invalid priority: {ticket.priority}"

        except Exception as e:
            workflow.logger.info(f"\n❌ FAILURE: {str(e)}")
            workflow.logger.info(f"Ticket stuck in status: {ticket.status}")
            workflow.logger.info("Manual intervention required!\n")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

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

        except ActivityError:
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

        try:
            await self.do_agent_investigate(ticket)
            ticket.status = "resolved_escalated"

            await self.do_notify_customer(ticket, "Your issue required engineering review and has been resolved!")

            workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after investigation!\n")
            return f"Resolved with investigation: {ticket.ticket_id}"

        except ActivityError:
            workflow.logger.info("Investigation failed, escalate to engineering")
            ticket.status = "resolving"
            esc_result = await self.do_escalate_to_engineering(ticket)
            if esc_result == "Engineering rejected":
                workflow.logger.info("Engineering rejected - reassigning to agent for further investigation")
                try:
                    await self.do_assign_agent(ticket)
                    final_result = await self.do_agent_resolve(ticket)
                    await self.do_notify_customer(ticket, "Resolved by agent after engineering review!")
                    return f"✅ SUCCESS: Resolved by agent after engineering review: {ticket.ticket_id}, {final_result}"

                except ActivityError:
                    # Agent couldn't resolve it after engineering punted back
                    workflow.logger.info("Agent could not resolve--notifying management")
                    await self.do_notify_customer(ticket, "This issue required engineering review, but no agent could resolve")

            else:
                await self.do_notify_customer(ticket, "Resolved by engineering after escalation")
                ticket.status = "resolved medium"
                workflow.logger.info(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by engineering!\n")
                return f"Resolved by engineering: {ticket.ticket_id}"

@workflow.defn
class HighPriorityWorkflow(WorkflowBase):
    def __init__(self):
        super().__init__()

    @workflow.run
    async def run(self, ticket: Ticket):
        workflow.logger.info("Starting high-priority workflow...")
        ticket.status = "assigning_senior_agent"
        workflow.logger.info(f"Assigning to senior agent...")
        await self.do_assign_agent(ticket)

        ticket.status = "escalating"
        esc_result = await self.do_escalate_to_engineering(ticket)
        workflow.logger.info(f"{esc_result}")

        ticket.status = "urgent_fix"
        fix_result = await self.do_apply_urgent_fix(ticket)
        workflow.logger.info(f"Urgent Fix result: {fix_result}")
        if fix_result == "Urgent Fix failed!":
            workflow.logger.info(f"Could not resolve with urgent fix: {fix_result}. Adding ticket to backlog")
            await self.do_notify_management(ticket)

        ticket.status = "notifying everyone..."
        await self.do_notify_customer(ticket, "Engineering fixed it!")
        await self.do_notify_management(ticket)
        ticket.status = "resolved_urgent"

        workflow.logger.info(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
        return f"Resolved urgently: {ticket.ticket_id}"
