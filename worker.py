import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflow import SupportTicketSystem, LowPriorityWorkflow, MediumPriorityWorkflow, HighPriorityWorkflow
from base_workflow import WORKFLOW_TASK_QUEUE, SUPPORT_TASK_QUEUE, ENGINEERING_TASK_QUEUE, ESCALATION_TASK_QUEUE

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
    validate_resolution,
    release_agent,
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
        task_queue=WORKFLOW_TASK_QUEUE
    )

    support_worker = Worker(
        client,
        activities=[
            search_knowledge_base,
            send_auto_response,
            notify_customer,
            notify_management,
            agent_resolve,
            release_agent
        ],
        task_queue=SUPPORT_TASK_QUEUE,
    )

    internal_worker = Worker(
        client,
        activities=[
            assign_agent,
            agent_investigate,
            escalate_to_engineering,
        ],
        task_queue=ESCALATION_TASK_QUEUE,
    )

    # Activities related to the product itself
    engineering_worker = Worker(
        client,
        activities=[
            apply_urgent_fix,
            validate_resolution,
        ],
        task_queue=ENGINEERING_TASK_QUEUE,
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