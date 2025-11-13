#!/usr/bin/env python3
"""
Interactive Pause/Resume Demo
Shows Temporal's ability to pause and resume workflows mid-execution
"""

import asyncio
import uuid
import time
from temporalio.client import Client
from workflow import SupportTicketSystem
from models import Ticket

async def interactive_pause_resume_demo():
    """Interactive demo showing pause/resume capabilities"""
    print("Interactive demo: Pause & Resume Workflow")
    print("=" * 70)
    print()

    try:
        client = await Client.connect("localhost:7233")

        # Create a high-priority ticket (has the most steps)
        ticket = Ticket("PAUSE-001", "Interactive User", "Critical system outage!", "high", "initialized")

        workflow_id = f"interactive-demo-{uuid.uuid4()}"

        print(f"🚀 Starting workflow: {workflow_id}")
        print(f"📋 Ticket: {ticket.ticket_id} - {ticket.issue}")
        print()

        # Start the workflow
        handle = await client.start_workflow(
            SupportTicketSystem.process_ticket,
            args=[ticket],
            id=workflow_id,
            task_queue="ticket-tasks",
        )

        print("Workflow started! Now...")
        print()

        # Monitor and provide interactive controls
        workflow_completed = False

        while not workflow_completed:
            print("What would you like to do? Press one of these keys:")
            print("  [s] - Show current status")
            print("  [p] - Pause workflow")
            print("  [r] - Resume workflow")
            print("  [w] - Wait and watch")
            print("  [q] - Quit demo (workflow continues running)")
            print()

            choice = input("Choose action (s/p/r/w/q): ").lower().strip()

            if choice == 's':
                try:
                    status = await handle.query(SupportTicketSystem.get_status)
                    print(f"\nWorkflow status:")
                    print(f"   Priority: {status['ticket_priority']}")
                    print(f"   Current Step: {status['current_step']}")
                    print(f"   Steps Completed: {len(status['steps_completed'])}")
                    print(f"   Progress: {status['steps_completed']}")
                    print()
                except Exception as e:
                    print(f"❌ Could not query status: {e}")

            elif choice == 'p':
                print("⏸️  PAUSING workflow...")
                await handle.signal(SupportTicketSystem.pause)
                print("✅ Workflow paused! It will stop at the next step.")
                print("   💡 Try this with regular Python - impossible! 😉")
                print()

            elif choice == 'r':
                print("▶️  RESUMING workflow...")
                await handle.signal(SupportTicketSystem.resume)
                print("✅ Workflow resumed! Continuing from exactly where it left off.")
                print()

            elif choice == 'w':
                # Wait and watch
                print("Watching workflow progress...")
                for i in range(5):
                    try:
                        # Check if completed
                        result = await asyncio.wait_for(handle.result(), timeout=1.0)
                        print(f"🎉 WORKFLOW COMPLETED!")
                        print(f"Result: {result}")
                        workflow_completed = True
                        break
                    except asyncio.TimeoutError:
                        # Still running, show status
                        try:
                            status = await handle.query(SupportTicketSystem.get_status)
                            print(
                                f"   Step {i + 1}: {status['current_step']} | Completed: {len(status['steps_completed'])}")
                        except:
                            print(f"   Step {i + 1}: Checking...")
                        await asyncio.sleep(2)

                if not workflow_completed:
                    print("   Still running... use other commands to interact!")
                print()

            elif choice == 'q':
                print("👋 Exiting demo...")
                print(f"💡 Workflow {workflow_id} continues running!")
                print("   You can reconnect to it later - that's Temporal's persistence!")
                break

            else:
                print("❌ Invalid choice. Try again.")

        if workflow_completed:
            # Show final status
            final_status = await handle.query(SupportTicketSystem.get_status)
            print(f"\nFINAL STATUS:")
            print(f"   All Steps: {final_status['steps_completed']}")
            print(f"   Total Steps: {len(final_status['steps_completed'])}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("\nMake sure:")
        print("1. Temporal server is running: temporal server start-dev")
        print("2. Worker is running: python worker.py")

async def main():
    print("🎫 TEMPORAL PAUSE/RESUME DEMONSTRATION")
    print("=" * 70)
    print()
    print("This demo shows capabilities that are IMPOSSIBLE with regular Python:")
    print("• Pause a running workflow mid-execution")
    print("• Resume it exactly where it left off")
    print("• Query workflow state in real-time")
    print("• A"
          "ll state is automatically preserved")
    print()

    # Check prerequisites
    try:
        from temporalio.client import Client
        print("✅ Temporal client available")
    except ImportError:
        print("❌ Temporal not installed. Run: pip install temporalio")
        return

    print()
    input("Press Enter to start the interactive demo...")

    await interactive_pause_resume_demo()

    print("\n" + "=" * 70)
    print("🎯 WHAT YOU JUST SAW:")
    print("=" * 70)
    print("✅ Real-time workflow monitoring with queries")
    print("✅ Pause a running workflow mid-execution")
    print("✅ Resume from the exact same point")
    print("✅ Perfect state preservation across pause/resume")
    print("✅ Interactive control of long-running processes")
    print()
    print("💡 This is DURABLE EXECUTION - the core power of Temporal!")
    print("🚀 Try doing this with regular Python code - impossible! 😎")


if __name__ == "__main__":
    asyncio.run(main())