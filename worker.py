import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflow import SupportTicketSystem
from activities import (
    agent_resolves_ticket,
    assign_agent,
    notify_customer,
    notify_management,
    escalate_to_engineering,
    apply_urgent_fix,
    investigate_issue,
    send_auto_response,
    search_knowledge_base,
    )

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        activities=[
            agent_resolves_ticket,
            assign_agent,
            notify_customer,
            notify_management,
            escalate_to_engineering,
            apply_urgent_fix,
            investigate_issue,
            send_auto_response,
            search_knowledge_base
        ],
        workflows=[SupportTicketSystem],
        task_queue="ticket-tasks"
    )
    print("Worker ready for tasks...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())