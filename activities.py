import asyncio
import random

from temporalio import activity
from temporalio.exceptions import ApplicationError

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
async def assign_agent(ticket: Ticket) -> str:
    """Assign ticket to agent"""
    agent_type = "senior" if ticket.priority == "high" else "regular"
    activity.logger.debug(f"Assigning {agent_type} agent to ticket {ticket.ticket_id}")
    await asyncio.sleep(7)

    # Sometimes no agents available
    if random.random() < 0.15:
        return "agent_unavailable"

    agent_name = "Agent-" + str(random.randint(100, 999))
    return agent_name

@activity.defn
async def agent_investigate(ticket: Ticket) -> str:
    """Agent investigates the issue"""
    activity.logger.debug(f"Agent investigating ticket {ticket.ticket_id}: {ticket.issue}")
    await asyncio.sleep(7)

    # Sometimes needs escalation
    if random.random() < 0.2:
        return "needs_escalation"

    return "investigation_complete"

@activity.defn
async def agent_resolve(ticket: Ticket) -> str:
    """Agent resolves the ticket"""
    activity.logger.debug(f"Agent resolving ticket {ticket.ticket_id}")
    await asyncio.sleep(7)
    if random.random() < 0.2:
        raise ApplicationError("Agent could not resolve, reassigning to another agent")

    return "Ticket resolved by agent"

@activity.defn
async def escalate_to_engineering(ticket: Ticket) -> str:
    """Escalate to engineering team"""
    activity.logger.debug(f"Escalating ticket {ticket.ticket_id} to engineering: {ticket.issue}")
    await asyncio.sleep(30)
    # Sometimes the engineering team punts to the backlog
    if random.random() < 0.2:
        return "engineering_rejected"

    return "engineering_accepted"

@activity.defn
async def apply_urgent_fix(ticket: Ticket) -> str:
    """Apply urgent fix for high priority issues"""
    activity.logger.debug(f"Applying urgent fix for ticket {ticket.ticket_id}")
    await asyncio.sleep(7)

    # Sometimes fix fails
    if random.random() < 0.1:
        return "Urgent fix failed!"

    return "Urgent fix applied"

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
