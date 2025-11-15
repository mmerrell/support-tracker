import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from workflow import SupportTicketSystem, LowPriorityWorkflow, MediumPriorityWorkflow, HighPriorityWorkflow

from activities import (
    agent_resolve,
    assign_agent,
    notify_customer,
    notify_management,
    escalate_to_engineering,
    apply_urgent_fix,
    agent_investigate,
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
        workflows=[SupportTicketSystem, LowPriorityWorkflow, MediumPriorityWorkflow, HighPriorityWorkflow],
        task_queue="workflows"
    )

    support_worker = Worker(
        client,
        activities=[
            search_knowledge_base,
            send_auto_response,
            notify_customer,
            notify_management,
            agent_resolve,
        ],
        task_queue="support"
    )

    internal_worker = Worker(
        client,
        activities=[
            assign_agent,
            agent_investigate,
            escalate_to_engineering,
        ],
        task_queue="internal"
    )

    # Activities related to the product itself
    engineering_worker = Worker(
        client,
        activities=[
            apply_urgent_fix,
        ],
        task_queue="engineering"
    )

    print("Workers ready...")
    await asyncio.gather(
        main_worker.run(),
        support_worker.run(),
        internal_worker.run(),
        engineering_worker.run()
    )

if __name__ == "__main__":
    asyncio.run(main())