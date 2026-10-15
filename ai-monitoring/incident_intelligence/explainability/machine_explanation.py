"""
MachineExplanation Model and DTO for Explainability Engine.
Produces structured, machine-readable explanation payloads for automated policy rules.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import Incident
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot
from incident_intelligence.explainability.reason_codes import ReasonCode

@dataclass(frozen=True)
class MachineExplanation:
    """Immutable structured machine-readable explanation payload."""
    incident_id: str
    reason_codes: List[str]
    metrics: Dict[str, Any]
    evidence_ids: List[str]
    timeline_event_ids: List[str]
    analytics_snapshot_id: Optional[str]

    def to_dto(self) -> 'MachineExplanationDTO':
        return MachineExplanationDTO(
            incident_id=self.incident_id,
            reason_codes=list(self.reason_codes),
            metrics=dict(self.metrics),
            evidence_ids=list(self.evidence_ids),
            timeline_event_ids=list(self.timeline_event_ids),
            analytics_snapshot_id=self.analytics_snapshot_id
        )

@dataclass(frozen=True)
class MachineExplanationDTO:
    """Data Transfer Object for MachineExplanation."""
    incident_id: str
    reason_codes: List[str]
    metrics: Dict[str, Any]
    evidence_ids: List[str]
    timeline_event_ids: List[str]
    analytics_snapshot_id: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def generate_machine_explanation(
    incident: Incident,
    reason_codes: List[ReasonCode],
    timeline_events: Optional[List[TimelineEvent]] = None,
    analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None
) -> MachineExplanation:
    """Generate structured machine explanation payload."""
    rc_strings = [rc.code for rc in reason_codes]
    ev_ids = [ref.evidence_id for ref in incident.evidence_references]
    tl_ids = [e.event_id for e in timeline_events] if timeline_events else []

    metrics_payload = {
        "duration_seconds": incident.duration,
        "peak_confidence": incident.peak_confidence,
        "average_confidence": incident.average_confidence,
        "current_risk": incident.current_risk,
        "severity": str(incident.severity.value if hasattr(incident.severity, 'value') else incident.severity)
    }

    snap_id = analytics_snapshot.snapshot_id if analytics_snapshot else None

    return MachineExplanation(
        incident_id=incident.incident_id,
        reason_codes=rc_strings,
        metrics=metrics_payload,
        evidence_ids=ev_ids,
        timeline_event_ids=tl_ids,
        analytics_snapshot_id=snap_id
    )
