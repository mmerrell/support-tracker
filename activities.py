import asyncio
import random

from temporalio import activity
from temporalio.exceptions import ApplicationError


@activity.defn
async def send_auto_response(ticket_id: str, customer_name: str) -> str:
    """Send automated acknowledgment"""
    activity.logger.info(f"Sending auto-response to {customer_name} for ticket {ticket_id}")
    await asyncio.sleep(7)
    return f"Auto-response sent to {customer_name}"

@activity.defn
async def search_knowledge_base(issue: str) -> str:
    """Search knowledge base for solution"""
    activity.logger.info(f"Searching knowledge base for: {issue}")
    await asyncio.sleep(7)

    # Sometimes no solution found
    if random.random() < 0.3:
        raise ApplicationError("No solution found in knowledge base", non_retryable=True)

    return "Solution found: Here's a link: [link]"

@activity.defn
async def assign_agent(ticket_id: str, priority: str) -> str:
    """Assign ticket to agent"""
    agent_type = "senior" if priority == "high" else "regular"
    activity.logger.info(f"Assigning {agent_type} agent to ticket {ticket_id}")
    await asyncio.sleep(7)

    # Sometimes no agents available
    if random.random() < 0.15:
        raise Exception("No agents available!")

    agent_name = "Agent-" + str(random.randint(100, 999))
    return agent_name

@activity.defn
async def agent_investigate(ticket_id: str, issue: str) -> str:
    """Agent investigates the issue"""
    activity.logger.info(f"Agent investigating ticket {ticket_id}: {issue}")
    await asyncio.sleep(7)

    # Sometimes needs escalation
    if random.random() < 0.2:
        return "needs_escalation"

    return "investigation_complete"

@activity.defn
async def agent_resolve(ticket_id: str) -> str:
    """Agent resolves the ticket"""
    activity.logger.info(f"Agent resolving ticket {ticket_id}")
    await asyncio.sleep(7)
    if random.random() < 0.2:
        raise Exception("Agent could not accept, reassigning")

    return "Ticket resolved by agent"

@activity.defn
async def escalate_to_engineering(ticket_id: str, issue: str) -> str:
    """Escalate to engineering team"""
    activity.logger.info(f"Escalating ticket {ticket_id} to engineering: {issue}")
    await asyncio.sleep(7)
    # Sometimes the engineering team punts to the backlog
    if random.random() < 0.2:
        raise Exception("Engineering team rejected")

    return "Escalated to engineering"

@activity.defn
async def apply_urgent_fix(ticket_id: str) -> str:
    """Apply urgent fix for high priority issues"""
    activity.logger.info(f"Applying urgent fix for ticket {ticket_id}")
    await asyncio.sleep(7)

    # Sometimes fix fails
    if random.random() < 0.1:
        raise Exception("Urgent fix failed!")

    return "Urgent fix applied"

@activity.defn
async def notify_customer(customer_name: str, message: str):
    """Notify customer of resolution"""
    activity.logger.info(f"Notifying {customer_name}: {message}")
    await asyncio.sleep(1)

@activity.defn
async def notify_management(ticket_id: str, priority: str):
    """Notify management for high priority tickets"""
    activity.logger.info(f"Notifying management about {priority} priority ticket {ticket_id}")
    await asyncio.sleep(1)
