from dataclasses import dataclass

@dataclass
class Ticket:
    ticket_id: str
    customer_name: str
    issue: str
    priority: str
    status: str
