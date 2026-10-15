"""
ReviewAuditEntry Model and DTO for Review Intelligence Engine.
Stores append-only audit trails for review actions.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass(frozen=True)
class ReviewAuditEntry:
    """Immutable audit trail entry."""
    entry_id: str
    timestamp: float
    action: str  # REVIEW_STARTED, DECISION_CHANGED, NOTE_ADDED, REVIEW_CLOSED
    details: str

    def to_dto(self) -> 'ReviewAuditEntryDTO':
        return ReviewAuditEntryDTO(
            entry_id=self.entry_id,
            timestamp=self.timestamp,
            action=self.action,
            details=self.details
        )

@dataclass(frozen=True)
class ReviewAuditEntryDTO:
    """Data Transfer Object for ReviewAuditEntry."""
    entry_id: str
    timestamp: float
    action: str
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
