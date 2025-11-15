#!/usr/bin/env python3
"""
REAL COMPARISON: Actually run both versions
This script runs your original Python code AND your Temporal workflow
"""

import asyncio
import time

async def run_original_version():
    """Run the original non-Temporal support system with multiple tickets"""
    print("🔵 RUNNING: Original Python Version (No Temporal)")
    print("=" * 60)

    # Import and run the original system
    import original_system

    # Create diverse tickets to test different paths
    tickets = [
        original_system.Ticket("ORIG-001", "Alice Smith", "Can't login to account", "low"),
        original_system.Ticket("ORIG-002", "Bob Jones", "Payment processing stuck", "medium"),
        original_system.Ticket("ORIG-003", "Carol Williams", "Database corruption detected!", "high"),
        original_system.Ticket("ORIG-004", "Dave Brown", "API rate limits hit", "medium"),
        original_system.Ticket("ORIG-005", "Eve Davis", "SECURITY BREACH - immediate action needed", "high"),
        original_system.Ticket("ORIG-006", "Frank Wilson", "Email notifications not working", "low"),
    ]

    system = original_system.SupportTicketSystem()
    results = []
    total_start_time = time.time()

    for i, ticket in enumerate(tickets, 1):
        print(f"\n📋 Ticket {i}/6: {ticket.ticket_id} ({ticket.priority.upper()})")
        print(f"   Customer: {ticket.customer_name}")
        print(f"   Issue: {ticket.issue}")
        print("   " + "-" * 50)

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

        print(f"   ⏱️  Time: {ticket_time:.1f}s | Result: {result.split(':')[0]}")
        await asyncio.sleep(0.5)  # Brief pause between tickets

    total_time = time.time() - total_start_time

    print(f"\n📊 ORIGINAL PYTHON SUMMARY:")
    print("   " + "=" * 50)
    low_count = sum(1 for r in results if r['priority'] == 'low')
    med_count = sum(1 for r in results if r['priority'] == 'medium')
    high_count = sum(1 for r in results if r['priority'] == 'high')

    print(f"   Total tickets: {len(results)} (Low: {low_count}, Med: {med_count}, High: {high_count})")
    print(f"   Average per ticket: {total_time / len(results):.1f}s")

    successful = sum(1 for r in results if 'Failed' not in r['result'])
    print(f"   Success rate: {successful}/{len(results)} ({successful / len(results) * 100:.0f}%)")

    return total_time, results

async def run_temporal_version():
    """Run the actual Temporal workflow with multiple tickets"""
    print("\nRUNNING: Temporal Version")
    print("=" * 60)
    print("Testing same tickets with resume-from-failure behavior...")
    print()

    try:
        from temporalio.client import Client
        from workflow import SupportTicketSystem
        from models import Ticket
        import uuid

        # Connect to Temporal
        client = await Client.connect("localhost:7233")

        # Create the same diverse tickets
        tickets = [
            Ticket("TEMP-001", "Alice Smith", "Can't login to account", "low", "initialized"),
            Ticket("TEMP-002", "Bob Jones", "Payment processing stuck", "medium", "initialized"),
            Ticket("TEMP-003", "Carol Williams", "Database corruption detected!", "high", "initialized"),
            Ticket("TEMP-004", "Dave Brown", "API rate limits hit", "medium", "initialized"),
            Ticket("TEMP-005", "Eve Davis", "SECURITY BREACH - immediate action needed", "high", "initialized"),
            Ticket("TEMP-006", "Frank Wilson", "Email notifications not working", "low", "initialized"),
        ]

        results = []
        total_start_time = time.time()

        # Process tickets concurrently (show Temporal's power!)
        handles = []
        for i, ticket in enumerate(tickets, 1):
            workflow_id = f"comparison-{ticket.ticket_id}-{uuid.uuid4()}"
            handle = await client.start_workflow(
                SupportTicketSystem.process_ticket,
                args=[ticket],
                id=workflow_id,
                task_queue="workflows",
            )
            handles.append((handle, ticket, time.time()))
            print(f"🚀 Started workflow {i}/6: {ticket.ticket_id} ({ticket.priority.upper()})")

        print(f"\n🔄 Monitoring {len(handles)} concurrent workflows...")
        print("v" * 60)
        print(f"\nIf you're feeling feisty, kill the Temporal worker process while they're going,")
        print(f"\nthen restart it and watch them resume with no trouble...")
        print("^" * 60)
        print()

        # Monitor all workflows
        completed = set()
        while len(completed) < len(handles):
            for i, (handle, ticket, start_time) in enumerate(handles):
                if i in completed:
                    continue

                try:
                    # Check if completed (non-blocking)
                    result = await asyncio.wait_for(handle.result(), timeout=0.1)
                    end_time = time.time()
                    ticket_time = end_time - start_time

                    # Get final status to show steps
                    status = await handle.query(SupportTicketSystem.get_status)

                    completed.add(i)
                    results.append({
                        'ticket_id': ticket.ticket_id,
                        'priority': ticket.priority,
                        'result': result,
                        'time': ticket_time,
                        'steps': status['steps_completed']
                    })

                    print(
                        f"✅ {ticket.ticket_id}: {result.split(':')[0]} ({ticket_time:.1f}s, {len(status['steps_completed'])} steps)")

                except asyncio.TimeoutError:
                    # Still running, occasionally show progress
                    if len(completed) % 3 == 0:  # Show progress every few completions
                        try:
                            status = await handle.query(SupportTicketSystem.get_status)
                            print(f"🔄 {ticket.ticket_id}: {status['current_step']}")
                        except:
                            pass

            if len(completed) < len(handles):
                await asyncio.sleep(1)

        total_time = time.time() - total_start_time

        print(f"\n📊 TEMPORAL SUMMARY:")
        print("   " + "=" * 50)
        low_count = sum(1 for r in results if r['priority'] == 'low')
        med_count = sum(1 for r in results if r['priority'] == 'medium')
        high_count = sum(1 for r in results if r['priority'] == 'high')

        print(f"   Total tickets: {len(results)} (Low: {low_count}, Med: {med_count}, High: {high_count})")
        print(f"   Average per ticket: {total_time / len(results):.1f}s")

        successful = sum(1 for r in results if 'Failed' not in r['result'])
        print(f"   Success rate: {successful}/{len(results)} ({successful / len(results) * 100:.0f}%)")
        print(f"   Behavior: Resume from exact failure point ✅")
        print(f"   Concurrency: All workflows ran simultaneously 🚀")

        # Show step preservation details
        print(f"\n🔍 STEP PRESERVATION DETAILS:")
        for result in results:
            print(f"   {result['ticket_id']}: {len(result['steps'])} steps completed")

        return total_time, results

    except Exception as e:
        print(f"❌ Temporal version failed: {e}")
        print("\nMake sure:")
        print("1. Temporal server is running: temporal server start-dev")
        print("2. Worker is running: python worker.py")
        return None, []

async def main():
    print("Synchronous Python vs Temporal")
    print("=" * 40)
    print("Testing multiple tickets with different priorities and failure scenarios")
    print()

    print("\nThis test will show:")
    print("• Low priority: auto-response → knowledge base → agent (if needed)")
    print("• Medium priority: agent → investigate → escalate/resolve")
    print("• High priority: senior agent → escalate → urgent fix → notify all")
    print("• Different failure/success scenarios")
    print()

    # Run original version - non-Temporal
    original_time, original_results = await run_original_version()

    # Run Temporal version - Temporalized
    temporal_result = await run_temporal_version()
    temporal_time, temporal_results = temporal_result if temporal_result else (None, [])

    # Show workflow path analysis
    print(f"\n🔍 WORKFLOW PATH ANALYSIS:")
    priority_paths = {'low': [], 'medium': [], 'high': []}
    for result in temporal_results:
        priority_paths[result['priority']].append(result)

    for priority, results in priority_paths.items():
        if results:
            avg_steps = sum(len(r['steps']) for r in results) / len(results)
            avg_time = sum(r['time'] for r in results) / len(results)
            print(f"  {priority.upper()} priority ({len(results)} tickets):")
            print(f"    Avg steps: {avg_steps:.1f} | Avg time: {avg_time:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())