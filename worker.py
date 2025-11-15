import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflow import SupportTicketSystem, LowPriorityWorkflow, MediumPriorityWorkflow, HighPriorityWorkflow

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

import logging

async def main():
    client = await Client.connect("localhost:7233")
    logging.basicConfig(level=logging.INFO)

    # Or more specifically for Temporal
    logging.getLogger("temporalio.workflow").setLevel(logging.INFO)

    main_worker = Worker(
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

    low_worker = Worker(
        client,
        activities=[
            send_auto_response,
            search_knowledge_base,
            notify_customer,
            assign_agent,
            agent_resolves_ticket
        ],
        workflows=[LowPriorityWorkflow],
        task_queue="low-priority-tickets"
    )

    medium_worker = Worker(
        client,
        activities=[
            assign_agent,
            investigate_issue,
            escalate_to_engineering,
            notify_customer,
            agent_resolves_ticket
        ],
        workflows=[MediumPriorityWorkflow],
        task_queue="medium-priority-tickets"
    )

    high_worker = Worker(
        client,
        activities=[
            assign_agent,
            escalate_to_engineering,
            apply_urgent_fix,
            notify_customer,
            notify_management
        ],
        workflows=[HighPriorityWorkflow],
        task_queue="high-priority-tickets"
    )

    print("Workers ready...")
    await asyncio.gather(
        main_worker.run(),
        low_worker.run(),
        medium_worker.run(),
        high_worker.run()
    )


if __name__ == "__main__":
    asyncio.run(main())