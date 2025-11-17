#!/usr/bin/env python3
"""
This script runs your original Python code AND your Temporal workflow
"""

import asyncio
import time
import uuid

async def run_original_version():
    """Run the original non-Temporal support system"""
    print("🔵 RUNNING: Original Python Version (No Temporal)")
    print("=" * 60)

    import original_system

    tickets = [
        original_system.Ticket("ORIG-001", "Alice Smith", "Can't login to account"),
        original_system.Ticket("ORIG-002", "Bob Jones", "Payment processing stuck"),
        original_system.Ticket("ORIG-003", "Carol Williams", "Database corruption detected!"),
    ]

    system = original_system.SupportTicketSystem()
    results = []
    total_start_time = time.time()

    for i, ticket in enumerate(tickets, 1):
        print(f"\n📋 Ticket {i}/{len(tickets)}: {ticket.ticket_id} ({ticket.priority.upper()})")
        start_time = time.time()
        result = system.process_ticket(ticket)
        end_time = time.time()

        ticket_time = end_time - start_time
        results.append({
            'ticket_id': ticket.ticket_id,
            'priority': ticket.priority,
            'result': result,
            'time': ticket_time
        })

        print(f"   ⏱️  Time: {ticket_time:.1f}s | Result: {result}")

    total_time = time.time() - total_start_time
    print(f"\n📊 ORIGINAL SUMMARY: {len(results)} tickets in {total_time:.1f}s")
    return total_time, results

async def run_temporal_version():
    """Run the Temporal workflow version"""
    print("\n🟡 RUNNING: Temporal Version")
    print("=" * 60)

    try:
        from temporalio.client import Client
        from workflow import SupportTicketSystem
        from models import Ticket

        client = await Client.connect("localhost:7233")

        tickets = [
            Ticket("TEMP-001", "Alice Smith", "Can't login to account", "low"),
            Ticket("TEMP-002", "Bob Jones", "Payment processing stuck", "medium"),
            Ticket("TEMP-003", "Carol Williams", "Database corruption detected!", "high"),
            Ticket("TEMP-004", "Dave Brown", "API rate limits hit", "medium"),
            Ticket("TEMP-005", "Eve Davis", "SECURITY BREACH - immediate action needed", "high"),
            Ticket("TEMP-006", "Frank Miller", "Out of ideas", "low"),
            Ticket("TEMP-007", "Spongebob Squarepants", "Job stinks", "high"),
        ]

        results = []
        total_start_time = time.time()

        # Start all workflows concurrently
        handles = []
        for i, ticket in enumerate(tickets, 1):
            workflow_id = f"comparison-{ticket.ticket_id}-{uuid.uuid4()}"
            handle = await client.start_workflow(
                SupportTicketSystem.run,
                ticket,
                id=workflow_id,
                task_queue="workflows",
            )
            handles.append((handle, ticket, time.time()))
            print(f"🚀 Started workflow {i}/{len(tickets)}: {ticket.ticket_id}")

        print(f"\n🔄 Monitoring {len(handles)} concurrent workflows...")

        # Wait for all to complete
        for handle, ticket, start_time in handles:
            result = await handle.result()
            end_time = time.time()
            ticket_time = end_time - start_time

            results.append({
                'ticket_id': ticket.ticket_id,
                'priority': ticket.priority,
                'result': result,
                'time': ticket_time,
            })

            print(f"✅ {ticket.ticket_id}: {result} ({ticket_time:.1f}s)")

        total_time = time.time() - total_start_time
        print(f"\n📊 TEMPORAL SUMMARY: {len(results)} tickets in {total_time:.1f}s (concurrent)")
        print("   ✅ Resume-from-failure behavior")
        print("   🚀 Concurrent execution")
        print("   If you kill this process now, workflows continue with no interruption")
        return total_time, results

    except Exception as e:
        print(f"❌ Temporal version failed: {e}")
        return None, []

async def main():
    print("🎫 COMPARISON: Synchronous Python vs Temporal")
    print("=" * 60)

    original_time, original_results = await run_original_version()
    temporal_time, temporal_results = await run_temporal_version()

    if temporal_results:
        print(f"\n🏁 COMPARISON RESULTS:")
        print(f"   Original: {original_time:.1f}s (sequential)")
        print(f"   Temporal: {temporal_time:.1f}s (concurrent)")
        print(f"   Speedup: {original_time / temporal_time:.1f}x faster!")

if __name__ == "__main__":
    asyncio.run(main())
