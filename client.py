import asyncio
import uuid

from temporalio.client import Client
from workflow import SupportTicketSystem
from models import Ticket

async def main():
    tickets = [
        Ticket("TKT-001", "Alice Johnson", "Can't login to account", "low", "initialized"),
        Ticket("TKT-002", "Bob Smith", "Payment processing error", "medium", "initialized"),
        Ticket("TKT-003", "Carol Davis", "System completely down!", "high", "initialized"),
    ]

    client = await Client.connect("localhost:7233")
    for ticket in tickets:
        handle = await client.start_workflow(
            SupportTicketSystem.process_ticket,
            args=[ticket],
            id=f"ticket-workflow-{uuid.uuid4()}",
            task_queue="ticket-tasks",
        )
        result = await handle.result()
        print(f"Result: {result}\n")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())