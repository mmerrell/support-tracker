"""
Customer Support Ticket System
A ticket goes through different paths based on priority:
- LOW: auto-response → knowledge base → close
- MEDIUM: assign agent → investigate → resolve → close
- HIGH: assign senior → escalate → urgent fix → notify → close
"""

import time
import random

class Ticket:
    def __init__(self, ticket_id: str, customer_name: str, issue: str, priority: str):
        self.ticket_id = ticket_id
        self.customer_name = customer_name
        self.issue = issue
        self.priority = priority  # "low", "medium", "high"
        self.status = "new"

class AutomationService:
    """Handles automated responses"""
    def send_auto_response(self, ticket_id: str, customer_name: str) -> str:
        """Send automated acknowledgment"""
        print(f"Sending auto-response to {customer_name} for ticket {ticket_id}")
        time.sleep(1)
        return f"Auto-response sent to {customer_name}"

    def search_knowledge_base(self, issue: str) -> str:
        """Search knowledge base for solution"""
        print(f"Searching knowledge base for: {issue}")
        time.sleep(2)

        # Sometimes no solution found
        if random.random() < 0.3:
            return "no_solution"

        return "solution_found"

class AgentService:
    """Handles agent assignment and work"""
    def assign_agent(self, ticket_id: str, priority: str) -> str:
        """Assign ticket to agent"""
        agent_type = "senior" if priority == "high" else "regular"
        print(f"Assigning {agent_type} agent to ticket {ticket_id}")
        time.sleep(1)

        # Sometimes no agents available
        if random.random() < 0.15:
            raise Exception("No agents available!")

        agent_name = "Agent-" + str(random.randint(100, 999))
        return agent_name

    def investigate_issue(self, ticket_id: str, issue: str) -> str:
        """Agent investigates the issue"""
        print(f"Agent investigating ticket {ticket_id}: {issue}")
        time.sleep(2)

        # Sometimes needs escalation
        if random.random() < 0.2:
            return "needs_escalation"

        return "investigation_complete"

    def resolve_ticket(self, ticket_id: str) -> str:
        """Agent resolves the ticket"""
        print(f"Agent resolving ticket {ticket_id}")
        time.sleep(1)
        return "Ticket resolved by agent"

class EscalationService:
    """Handles escalations"""
    def escalate_to_engineering(self, ticket_id: str, issue: str) -> str:
        """Escalate to engineering team"""
        print(f"Escalating ticket {ticket_id} to engineering: {issue}")
        time.sleep(2)
        return "Escalated to engineering"

    def apply_urgent_fix(self, ticket_id: str) -> str:
        """Apply urgent fix for high priority issues"""
        print(f"Applying urgent fix for ticket {ticket_id}")
        time.sleep(3)

        # Sometimes fix fails
        if random.random() < 0.1:
            raise Exception("Urgent fix failed!")

        return "Urgent fix applied"

class NotificationService:
    """Handles notifications"""
    def notify_customer(self, customer_name: str, message: str):
        """Notify customer of resolution"""
        print(f"📧 Notifying {customer_name}: {message}")
        time.sleep(1)

    def notify_management(self, ticket_id: str, priority: str):
        """Notify management for high priority tickets"""
        print(f"📧 Notifying management about {priority} priority ticket {ticket_id}")
        time.sleep(1)

class SupportTicketSystem:
    """Main system that orchestrates ticket handling"""
    def __init__(self):
        self.automation = AutomationService()
        self.agents = AgentService()
        self.escalation = EscalationService()
        self.notifications = NotificationService()

    def process_ticket(self, ticket: Ticket) -> str:
        """
        Process a ticket - different paths based on priority
        PROBLEM: If any step fails, have to start over!
        """
        print(f"\n{'=' * 70}")
        print(f"Processing ticket {ticket.ticket_id}: {ticket.issue}")
        print(f"Priority: {ticket.priority.upper()} | Customer: {ticket.customer_name}")
        print(f"{'=' * 70}\n")

        try:
            # LOW PRIORITY PATH
            if ticket.priority == "low":
                print("🔵 Taking LOW priority path\n")

                # Step 1: Auto-response
                self._status = "auto_responding"
                auto_result = self.automation.send_auto_response(ticket.ticket_id, ticket.customer_name)
                print(f"✓ {auto_result}")

                # Step 2: Search knowledge base
                self._status = "searching_kb"
                kb_result = self.automation.search_knowledge_base(ticket.issue)
                print(f"✓ Knowledge base search: {kb_result}")

                if kb_result == "solution_found":
                    # Success path 1: Solved by automation
                    self._status = "resolved_auto"
                    self.notifications.notify_customer(
                        ticket.customer_name,
                        "Your issue has been resolved! Check the solution link."
                    )
                    print(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved automatically!\n")
                    return f"Resolved automatically: {ticket.ticket_id}"
                else:
                    # Need human help
                    print("No solution found, assigning to agent...")
                    agent = self.agents.assign_agent(ticket.ticket_id, "low")
                    print(f"✓ Assigned to {agent}")

                    resolve_result = self.agents.resolve_ticket(ticket.ticket_id)
                    print(f"✓ {resolve_result}")

                    self._status = "resolved_agent"
                    self.notifications.notify_customer(
                        ticket.customer_name,
                        "Your ticket has been resolved by our team!"
                    )
                    print(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved by agent!\n")
                    return f"Resolved by agent: {ticket.ticket_id}"

            # MEDIUM PRIORITY PATH
            elif ticket.priority == "medium":
                print("🟡 Taking MEDIUM priority path\n")

                # Step 1: Assign agent
                self._status = "assigning_agent"
                agent = self.agents.assign_agent(ticket.ticket_id, "medium")
                print(f"✓ Assigned to {agent}")

                # Step 2: Investigate
                self._status = "investigating"
                invest_result = self.agents.investigate_issue(
                    ticket.ticket_id, ticket.issue
                )
                print(f"✓ Investigation: {invest_result}")

                if invest_result == "needs_escalation":
                    # Escalate to engineering
                    print("Issue needs escalation...")
                    self._status = "escalating"
                    esc_result = self.escalation.escalate_to_engineering(
                        ticket.ticket_id, ticket.issue
                    )
                    print(f"✓ {esc_result}")

                    self._status = "resolved_escalated"
                    self.notifications.notify_customer(
                        ticket.customer_name,
                        "Your issue required engineering review and has been resolved!"
                    )
                    print(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved after escalation!\n")
                    return f"Resolved with escalation: {ticket.ticket_id}"
                else:
                    # Resolve normally
                    self._status = "resolving"
                    resolve_result = self.agents.resolve_ticket(ticket.ticket_id)
                    print(f"✓ {resolve_result}")

                    self._status = "resolved_agent"
                    self.notifications.notify_customer(
                        ticket.customer_name,
                        "Your ticket has been resolved!"
                    )
                    print(f"\n✅ SUCCESS: Ticket {ticket.ticket_id} resolved normally!\n")
                    return f"Resolved normally: {ticket.ticket_id}"

            # HIGH PRIORITY PATH
            elif ticket.priority == "high":
                print("🔴 Taking HIGH priority path\n")

                # Step 1: Assign senior agent immediately
                self._status = "assigning_senior"
                agent = self.agents.assign_agent(ticket.ticket_id, "high")
                print(f"✓ Assigned to senior: {agent}")

                # Step 2: Escalate immediately
                self._status = "escalating"
                esc_result = self.escalation.escalate_to_engineering(
                    ticket.ticket_id, ticket.issue
                )
                print(f"✓ {esc_result}")

                # Step 3: Apply urgent fix
                self._status = "urgent_fix"
                fix_result = self.escalation.apply_urgent_fix(ticket.ticket_id)
                print(f"✓ {fix_result}")

                # Step 4: Notify everyone
                self._status = "notifying"
                self.notifications.notify_customer(
                    ticket.customer_name,
                    "URGENT: Your critical issue has been resolved!"
                )
                print(f"✓ Customer notified")

                self.notifications.notify_management(ticket.ticket_id, "high")
                print(f"✓ Management notified")

                self._status = "resolved_urgent"
                print(f"\n✅ SUCCESS: HIGH priority ticket {ticket.ticket_id} resolved!\n")
                return f"Resolved urgently: {ticket.ticket_id}"

            else:
                return f"Invalid priority: {ticket.priority}"

        except Exception as e:
            print(f"\n❌ FAILURE: {str(e)}")
            print(f"Ticket stuck in status: {self._status}")
            print("Manual intervention required!\n")
            return f"Failed: {ticket.ticket_id} - {str(e)}"

def main():
    """Run the support system"""
    system = SupportTicketSystem()
    # Test different priority levels
    tickets = [
        Ticket("TKT-001", "Alice Johnson", "Can't login to account", "low"),
        Ticket("TKT-002", "Bob Smith", "Payment processing error", "medium"),
        Ticket("TKT-003", "Carol Davis", "System completely down!", "high"),
    ]

    for ticket in tickets:
        result = system.process_ticket(ticket)
        print(f"Result: {result}\n")
        time.sleep(1)  # Pause between tickets

if __name__ == "__main__":
    main()