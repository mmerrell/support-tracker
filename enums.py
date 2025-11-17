from enum import Enum

class InvestigationResult(Enum):
    COMPLETE = "investigation_complete"
    NEEDS_ESCALATION = "needs_escalation"
    AGENT_UNAVAILABLE = "agent_unavailable"

class EscalationResult(Enum):
    ACCEPTED = "engineering_accepted"
    REJECTED = "engineering_rejected"

class FixResult(Enum):
    SUCCESS = "fix_succeeded"
    FAILED = "fix_failed"

class TicketStatus(Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"