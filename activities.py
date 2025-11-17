import asyncio
import random

from temporalio import activity
from temporalio.exceptions import ApplicationError

from enums import InvestigationResult, EscalationResult, FixResult
from models import Ticket

@activity.defn
async def send_auto_response(ticket: Ticket) -> str:
    """Send automated acknowledgment"""
    activity.logger.debug(f"Sending auto-response to {ticket.customer_name} for ticket {ticket.ticket_id}")
    await asyncio.sleep(7)
    return f"Auto-response sent to {ticket.customer_name}"

@activity.defn
async def search_knowledge_base(ticket: Ticket) -> str:
    """Search knowledge base for solution"""
    activity.logger.debug(f"Searching knowledge base for: {ticket.issue}")
    await asyncio.sleep(7)

    # Sometimes no solution found
    if random.random() < 0.3:
        raise ApplicationError("No solution found in knowledge base", non_retryable=True)

    return "Solution found: Here's a link: [link]"

@activity.defn
async def assign_agent(ticket: Ticket):
    """Assign ticket to agent"""
    agent_type = "senior" if ticket.priority == "high" else "regular"
    activity.logger.debug(f"Assigning {agent_type} agent to ticket {ticket.ticket_id}")
    await asyncio.sleep(7)
    agent_name = "Agent-" + str(random.randint(100, 999))
    return agent_name

@activity.defn
async def agent_investigate(ticket: Ticket) -> str:
    """Agent investigates the issue"""
    activity.logger.debug(f"Agent investigating ticket {ticket.ticket_id}: {ticket.issue}")
    await asyncio.sleep(7)

    # Sometimes needs escalation
    if random.random() < 0.3:
        return InvestigationResult.NEEDS_ESCALATION.value

    return InvestigationResult.COMPLETE.value

@activity.defn
async def agent_resolve(ticket: Ticket) -> str:
    """Agent resolves the ticket"""
    activity.logger.debug(f"Agent resolving ticket {ticket.ticket_id}")
    await asyncio.sleep(7)
    if random.random() < 0.2:
        return InvestigationResult.NEEDS_ESCALATION.value

    return InvestigationResult.COMPLETE.value

@activity.defn
async def escalate_to_engineering(ticket: Ticket) -> str:
    """Escalate to engineering team"""
    activity.logger.debug(f"Escalating ticket {ticket.ticket_id} to engineering: {ticket.issue}")
    await asyncio.sleep(30)
    # Sometimes the engineering team punts to the backlog
    if random.random() < 0.2:
        return EscalationResult.REJECTED.value

    return EscalationResult.ACCEPTED.value

@activity.defn
async def apply_urgent_fix(ticket: Ticket) -> str:
    """Apply urgent fix for high priority issues"""
    activity.logger.debug(f"Applying urgent fix for ticket {ticket.ticket_id}")
    await asyncio.sleep(7)

    # Sometimes fix fails
    if random.random() < 0.1:
        return FixResult.FAILED.value

    return FixResult.SUCCESS.value

@activity.defn
async def notify_customer(ticket: Ticket, message: str) -> None:
    """Notify customer of resolution"""
    activity.logger.debug(f"Notifying {ticket.customer_name}: {message}")
    await asyncio.sleep(3)

@activity.defn
async def notify_management(ticket: Ticket):
    """Notify management for high priority tickets"""
    activity.logger.debug(f"Notifying management about {ticket.priority} priority ticket {ticket.ticket_id}")
    await asyncio.sleep(4)


@activity.defn
async def validate_resolution(ticket: Ticket) -> str:
    """Validate that resolution actually worked"""
    activity.logger.debug(f"Validating resolution for {ticket.ticket_id}")
    await asyncio.sleep(5)

    # Sometimes validation fails
    if random.random() < 0.3:
        raise ApplicationError("Customer reported solution didn't work", non_retryable=True)

    return "Resolution validated"

@activity.defn
async def release_agent(agent_name: str, ticket: Ticket) -> str:
    """Release agent from ticket assignment"""
    activity.logger.info(f"COMPENSATION: Releasing agent {agent_name} from ticket {ticket.ticket_id}")
    await asyncio.sleep(3)
    return f"Agent {agent_name} released"
