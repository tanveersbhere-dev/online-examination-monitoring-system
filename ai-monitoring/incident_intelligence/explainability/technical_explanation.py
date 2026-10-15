"""
TechnicalExplanation Model and DTO for Explainability Engine.
Generates objective, un-embellished technical diagnostic traces.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import Incident
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot

@dataclass(frozen=True)
class TechnicalExplanation:
    """Immutable technical diagnostic explanation trace."""
    incident_id: str
    incident_type: str
    rule_transitions: List[str]
    timeline_event_ids: List[str]
    sequence_range: str
    confidence_trace: Dict[str, float]
    risk_trace: Dict[str, float]
    evidence_ids: List[str]

    def to_dto(self) -> 'TechnicalExplanationDTO':
        return TechnicalExplanationDTO(
            incident_id=self.incident_id,
            incident_type=self.incident_type,
            rule_transitions=list(self.rule_transitions),
            timeline_event_ids=list(self.timeline_event_ids),
            sequence_range=self.sequence_range,
            confidence_trace=dict(self.confidence_trace),
            risk_trace=dict(self.risk_trace),
            evidence_ids=list(self.evidence_ids)
        )

@dataclass(frozen=True)
class TechnicalExplanationDTO:
    """Data Transfer Object for TechnicalExplanation."""
    incident_id: str
    incident_type: str
    rule_transitions: List[str]
    timeline_event_ids: List[str]
    sequence_range: str
    confidence_trace: Dict[str, float]
    risk_trace: Dict[str, float]
    evidence_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def generate_technical_explanation(
    incident: Incident,
    timeline_events: Optional[List[TimelineEvent]] = None,
    analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None
) -> TechnicalExplanation:
    """Generate deterministic technical diagnostic trace."""
    rule_trans = [f"Rule: {r}" for r in incident.metadata.triggered_rules]

    tl_ids = [e.event_id for e in timeline_events] if timeline_events else []
    seq_range = f"Seq #{timeline_events[0].sequence_number}..#{timeline_events[-1].sequence_number}" if (timeline_events and len(timeline_events) > 1) else "Seq #1"

    conf_trace = {
        "peak": incident.peak_confidence,
        "avg": incident.average_confidence,
        "current": incident.current_confidence
    }
    if analytics_snapshot:
        conf_trace["slope"] = analytics_snapshot.confidence_analysis.slope
        conf_trace["std_dev"] = analytics_snapshot.confidence_analysis.std_dev

    risk_trace = {
        "current_risk": incident.current_risk,
        "peak_risk": incident.current_risk
    }
    if analytics_snapshot:
        risk_trace["peak_risk"] = analytics_snapshot.risk_analysis.peak_risk
        risk_trace["velocity"] = analytics_snapshot.risk_analysis.risk_velocity

    ev_ids = [ref.evidence_id for ref in incident.evidence_references]

    return TechnicalExplanation(
        incident_id=incident.incident_id,
        incident_type=incident.incident_type,
        rule_transitions=rule_trans,
        timeline_event_ids=tl_ids,
        sequence_range=seq_range,
        confidence_trace=conf_trace,
        risk_trace=risk_trace,
        evidence_ids=ev_ids
    )
