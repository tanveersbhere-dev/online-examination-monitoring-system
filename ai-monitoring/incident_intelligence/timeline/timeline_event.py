"""
TimelineEvent Immutable Model and DTO.
Represents a canonical append-only timeline entry for an Incident.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from incident_intelligence.domain.evidence_reference import EvidenceReference, EvidenceReferenceDTO

@dataclass(frozen=True)
class TimelineEvent:
    """Immutable, append-only timeline event entry."""
    event_id: str
    incident_id: str
    timestamp: float
    event_type: str  # INCIDENT_CREATED, STATE_CHANGED, CONFIDENCE_UPDATED, RISK_UPDATED, EVIDENCE_ADDED, RESOLVED, etc.
    sequence_number: int
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    confidence: Optional[float] = None
    risk: Optional[float] = None
    evidence_reference: Optional[EvidenceReference] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "MONITORING_ENGINE"

    def to_dto(self) -> 'TimelineEventDTO':
        return TimelineEventDTO(
            event_id=self.event_id,
            incident_id=self.incident_id,
            timestamp=self.timestamp,
            event_type=self.event_type,
            sequence_number=self.sequence_number,
            previous_state=self.previous_state,
            new_state=self.new_state,
            confidence=self.confidence,
            risk=self.risk,
            evidence_reference=self.evidence_reference.to_dto() if self.evidence_reference else None,
            metadata=dict(self.metadata),
            source=self.source
        )

@dataclass(frozen=True)
class TimelineEventDTO:
    """Data Transfer Object for TimelineEvent."""
    event_id: str
    incident_id: str
    timestamp: float
    event_type: str
    sequence_number: int
    previous_state: Optional[str]
    new_state: Optional[str]
    confidence: Optional[float]
    risk: Optional[float]
    evidence_reference: Optional[EvidenceReferenceDTO]
    metadata: Dict[str, Any]
    source: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.evidence_reference:
            d["evidence_reference"] = self.evidence_reference.to_dict()
        return d
