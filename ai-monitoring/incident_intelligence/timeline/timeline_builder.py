"""
Timeline Builder for Incident Timeline Engine.
Consumes Incident aggregate state, EvidenceReference objects, and lifecycle events to produce TimelineEvent entries.
"""
from typing import Optional, Dict, Any, List
import time
import uuid

from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.evidence_reference import EvidenceReference
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.timeline.timeline_repository import InMemoryTimelineRepository

class TimelineBuilder:
    """Constructs and persists canonical append-only TimelineEvent entries."""

    def __init__(self, repository: Optional[InMemoryTimelineRepository] = None):
        self.repository = repository or InMemoryTimelineRepository()

    def record_incident_created(self, incident: Incident, timestamp: Optional[float] = None) -> TimelineEvent:
        """Record INCIDENT_CREATED timeline event from an Incident aggregate root."""
        ts = timestamp if timestamp is not None else incident.start_time
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident.incident_id,
            timestamp=ts,
            event_type="INCIDENT_CREATED",
            sequence_number=1,
            new_state=str(incident.status.value if hasattr(incident.status, 'value') else incident.status),
            confidence=incident.current_confidence,
            risk=incident.current_risk,
            metadata={
                "incident_type": incident.incident_type,
                "episode_id": incident.episode_id,
                "title": incident.metadata.title,
                "category": incident.metadata.category
            }
        )
        return self.repository.append(event)

    def record_state_changed(
        self,
        incident_id: str,
        previous_state: str,
        new_state: str,
        timestamp: float,
        reason: str = "State transition"
    ) -> TimelineEvent:
        """Record STATE_CHANGED timeline event."""
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident_id,
            timestamp=timestamp,
            event_type="STATE_CHANGED",
            sequence_number=0,
            previous_state=previous_state,
            new_state=new_state,
            metadata={"reason": reason}
        )
        return self.repository.append(event)

    def record_confidence_updated(
        self,
        incident_id: str,
        confidence: float,
        timestamp: float,
        frame_number: int = 1
    ) -> TimelineEvent:
        """Record CONFIDENCE_UPDATED timeline event."""
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident_id,
            timestamp=timestamp,
            event_type="CONFIDENCE_UPDATED",
            sequence_number=0,
            confidence=confidence,
            metadata={"frame_number": frame_number}
        )
        return self.repository.append(event)

    def record_risk_updated(
        self,
        incident_id: str,
        risk: float,
        timestamp: float,
        frame_number: int = 1
    ) -> TimelineEvent:
        """Record RISK_UPDATED timeline event."""
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident_id,
            timestamp=timestamp,
            event_type="RISK_UPDATED",
            sequence_number=0,
            risk=risk,
            metadata={"frame_number": frame_number}
        )
        return self.repository.append(event)

    def record_evidence_added(
        self,
        incident_id: str,
        evidence: EvidenceReference,
        timestamp: Optional[float] = None
    ) -> TimelineEvent:
        """Record EVIDENCE_ADDED timeline event carrying EvidenceReference."""
        ts = timestamp if timestamp is not None else evidence.timestamp
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident_id,
            timestamp=ts,
            event_type="EVIDENCE_ADDED",
            sequence_number=0,
            evidence_reference=evidence,
            metadata={
                "evidence_id": evidence.evidence_id,
                "importance": evidence.importance,
                "crop_type": evidence.crop_type
            }
        )
        return self.repository.append(event)

    def record_resolved(
        self,
        incident_id: str,
        timestamp: float,
        reason: str = "Incident resolved"
    ) -> TimelineEvent:
        """Record RESOLVED timeline event."""
        event = TimelineEvent(
            event_id=f"TLE-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident_id,
            timestamp=timestamp,
            event_type="RESOLVED",
            sequence_number=0,
            new_state="RESOLVED",
            metadata={"reason": reason}
        )
        return self.repository.append(event)
