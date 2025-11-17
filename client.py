import asyncio
import uuid
import time

from temporalio.client import Client
from workflow import SupportTicketSystem
from models import Ticket

async def main():
    tickets = [
        Ticket("TEMP-001", "Alice Smith", "Can't login to account", "low"),
        Ticket("TEMP-002", "Bob Jones", "Payment processing stuck", "medium"),
        Ticket("TEMP-003", "Carol Williams", "Database corruption detected!", "high"),
        Ticket("TEMP-004", "Dave Brown", "API rate limits hit", "medium"),
        Ticket("TEMP-005", "Eve Davis", "SECURITY BREACH - immediate action needed", "high"),
        Ticket("TEMP-006", "Frank Miller", "Out of ideas", "low"),
        Ticket("TEMP-007", "Spongebob Squarepants", "Job stinks", "high"),
        Ticket("TEMP-008", "Patrick Star", "Adulting is hard", "low"),
        Ticket("TEMP-009", "Mr Krab", "Calculator broke", "low"),
        Ticket("TEMP-010", "Kevin Flynn", "Pet project went rogue", "high"),
        Ticket("TEMP-011", "Edward Dillinger", "Email notifications not working", "low"),
        Ticket("TEMP-012", "Quorra", "Matrix syndrome", "low"),
        Ticket("TEMP-013", "Wendy Carlos", "Ahead of her time", "high"),
        Ticket("TEMP-014", "Trent Reznor", "Excessive talent", "medium"),
        Ticket("TEMP-015", "Atticus Ross", "Misunderstood in his time", "low"),
        Ticket("TEMP-016", "Jordan Holmes", "Can't stop screaming", "low"),
        Ticket("TEMP-017", "Dan Friesen", "The mysterious professor won't disclose identity", "medium"),
        Ticket("TEMP-018", "Robert Evans", "There are bad people out there", "high"),
        Ticket("TEMP-019", "Jamie Loftus", "Hot dog is a sandwich and someone disagrees", "medium"),
        Ticket("TEMP-020", "Adam Driver", "Still too emo", "low"),
        Ticket("TEMP-021", "Max Rocketansky", "People can't get enough Type O", "high"),
        Ticket("TEMP-022", "Imperator Furiosa", "Boss too demanding", "medium"),
        Ticket("TEMP-023", "Wow Platinum", "It's right there in the name", "low"),
        Ticket("TEMP-024", "Vito Corleone", "Oranges aren't right", "high"),
        Ticket("TEMP-025", "Vincent Vega", "Incorrect shoe type for twist contest", "low"),
        Ticket("TEMP-026", "Mia Wallace", "Director won't give me socks", "medium"),
        Ticket("TEMP-027", "Waylon Smithers", "Boss too demanding", "high"),
        Ticket("TEMP-028", "Montgomery Burns", "Employees lazy and ungrateful", "low"),
        Ticket("TEMP-029", "Michael Albertson", "Nobody knows my name", "medium"),
        Ticket("TEMP-030", "Maggie Simpson", "I have a lot to say", "low"),
    ]

    client = await Client.connect("localhost:7233")

    # Process tickets concurrently (show Temporal's power!)
    handles = []
    for i, ticket in enumerate(tickets, 1):
        workflow_id = f"ticket-{ticket.priority}-{ticket.ticket_id}-{uuid.uuid4()}"
        handle = await client.start_workflow(
            SupportTicketSystem.run,
            ticket,
            id=workflow_id,
            task_queue="workflows",
        )
        handles.append((handle, ticket, time.time()))
        print(f"🚀 Started workflow {i}/{len(tickets)}: {ticket.ticket_id} ({ticket.priority.upper()})")


if __name__ == "__main__":
    asyncio.run(main())