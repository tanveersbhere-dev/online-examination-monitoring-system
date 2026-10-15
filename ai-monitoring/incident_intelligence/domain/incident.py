"""
Incident Aggregate Root and IncidentDTO implementation.
Conforms strictly to Package 10.1 of the Incident Intelligence Platform Architecture Specification.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import time

from incident_intelligence.domain.enums import IncidentState, IncidentSeverity, IncidentPriority
from incident_intelligence.domain.versions import INCIDENT_SCHEMA_VERSION
from incident_intelligence.domain.metadata import IncidentMetadata, MetadataDTO
from incident_intelligence.domain.evidence_reference import EvidenceReference, EvidenceReferenceDTO
from incident_intelligence.domain.history import (
    ConfidenceHistoryEntry,
    RiskHistoryEntry,
    StateHistoryEntry,
    HistoryDTO
)

@dataclass
class Incident:
    """
    Incident Aggregate Root.
    Owns the lifecycle, evidence references, and history logs of a high-level incident.
    """
    incident_id: str
    episode_id: str
    incident_type: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    priority: IncidentPriority = IncidentPriority.P3_MEDIUM
    status: IncidentState = IncidentState.STARTED
    start_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    resolved_time: Optional[float] = None
    duration: float = 0.0
    current_confidence: float = 0.0
    peak_confidence: float = 0.0
    average_confidence: float = 0.0
    current_risk: float = 0.0
    current_state: IncidentState = IncidentState.STARTED
    metadata: IncidentMetadata = field(default_factory=IncidentMetadata)
    confidence_history: List[ConfidenceHistoryEntry] = field(default_factory=list)
    risk_history: List[RiskHistoryEntry] = field(default_factory=list)
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    evidence_references: List[EvidenceReference] = field(default_factory=list)
    domain_events: List[Any] = field(default_factory=list)
    schema_version: str = INCIDENT_SCHEMA_VERSION

    def append_confidence(self, timestamp: float, confidence_value: float, frame_number: int) -> None:
        """Append an immutable confidence entry and update metrics."""
        entry = ConfidenceHistoryEntry(timestamp, confidence_value, frame_number)
        self.confidence_history.append(entry)
        self.current_confidence = confidence_value
        self.peak_confidence = max(self.peak_confidence, confidence_value)
        total_conf = sum(e.confidence_value for e in self.confidence_history)
        self.average_confidence = round(total_conf / len(self.confidence_history), 4)
        self.last_updated = timestamp
        self.duration = round(max(0.0, self.last_updated - self.start_time), 2)

    def append_risk(self, timestamp: float, risk_value: float, frame_number: int) -> None:
        """Append an immutable risk score entry."""
        entry = RiskHistoryEntry(timestamp, risk_value, frame_number)
        self.risk_history.append(entry)
        self.current_risk = risk_value
        self.last_updated = timestamp

    def transition_state(self, timestamp: float, new_state: IncidentState, reason: str) -> None:
        """Transition lifecycle state and record state history entry."""
        prev_state = self.current_state.value if isinstance(self.current_state, IncidentState) else str(self.current_state)
        new_state_val = new_state.value if isinstance(new_state, IncidentState) else str(new_state)
        
        entry = StateHistoryEntry(timestamp, prev_state, new_state_val, reason)
        self.state_history.append(entry)
        
        self.current_state = new_state
        self.status = new_state
        self.last_updated = timestamp
        self.duration = round(max(0.0, self.last_updated - self.start_time), 2)

        if new_state == IncidentState.RESOLVED and self.resolved_time is None:
            self.resolved_time = timestamp

    def add_evidence_reference(self, evidence_ref: EvidenceReference) -> None:
        """Add an immutable evidence reference to the aggregate root."""
        self.evidence_references.append(evidence_ref)

    def to_dto(self) -> 'IncidentDTO':
        """Convert Aggregate Root into pure Data Transfer Object (DTO)."""
        return IncidentDTO(
            incident_id=self.incident_id,
            episode_id=self.episode_id,
            incident_type=self.incident_type,
            severity=self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            priority=self.priority.value if isinstance(self.priority, Enum) else str(self.priority),
            status=self.status.value if isinstance(self.status, Enum) else str(self.status),
            start_time=self.start_time,
            last_updated=self.last_updated,
            resolved_time=self.resolved_time,
            duration=self.duration,
            current_confidence=self.current_confidence,
            peak_confidence=self.peak_confidence,
            average_confidence=self.average_confidence,
            current_risk=self.current_risk,
            current_state=self.current_state.value if isinstance(self.current_state, Enum) else str(self.current_state),
            metadata=self.metadata.to_dto(),
            history=HistoryDTO(
                confidence_history=[e.to_dict() for e in self.confidence_history],
                risk_history=[e.to_dict() for e in self.risk_history],
                state_history=[e.to_dict() for e in self.state_history]
            ),
            evidence_references=[ref.to_dto() for ref in self.evidence_references],
            schema_version=self.schema_version
        )

# Fix for Enum check in to_dto
from enum import Enum

@dataclass(frozen=True)
class IncidentDTO:
    """Pure Data Transfer Object for Incident serialization across network or IPC boundaries."""
    incident_id: str
    episode_id: str
    incident_type: str
    severity: str
    priority: str
    status: str
    start_time: float
    last_updated: float
    resolved_time: Optional[float]
    duration: float
    current_confidence: float
    peak_confidence: float
    average_confidence: float
    current_risk: float
    current_state: str
    metadata: MetadataDTO
    history: HistoryDTO
    evidence_references: List[EvidenceReferenceDTO]
    schema_version: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary representation."""
        title_val = getattr(self.metadata, "title", None) or self.incident_type
        category_val = getattr(self.metadata, "category", None) or "Security"
        desc_val = getattr(self.metadata, "description", None) or ""
        return {
            "incident_id": self.incident_id,
            "episode_id": self.episode_id,
            "incident_type": self.incident_type,
            "title": title_val,
            "category": category_val,
            "description": desc_val,
            "severity": self.severity,
            "priority": self.priority,
            "status": self.status,
            "start_time": self.start_time,
            "last_updated": self.last_updated,
            "resolved_time": self.resolved_time,
            "duration": self.duration,
            "current_confidence": self.current_confidence,
            "peak_confidence": self.peak_confidence,
            "average_confidence": self.average_confidence,
            "current_risk": self.current_risk,
            "current_state": self.current_state,
            "metadata": self.metadata.to_dict(),
            "history": self.history.to_dict(),
            "evidence_references": [ref.to_dict() for ref in self.evidence_references],
            "schema_version": self.schema_version
        }
