"""
Timeline Projection Service for Incident Timeline Engine.
Generates Human, Technical, and Reviewer timeline projections from canonical timeline events.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from incident_intelligence.timeline.timeline_event import TimelineEvent, TimelineEventDTO
from incident_intelligence.timeline.timeline_query import TimelineQueryService

@dataclass(frozen=True)
class HumanTimelineProjection:
    """Human-readable timeline projection for general review."""
    incident_id: str
    summary_title: str
    duration_text: str
    event_summaries: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class TechnicalTimelineProjection:
    """Technical diagnostic timeline projection for engineering and audit logs."""
    incident_id: str
    total_events: int
    confidence_trajectory: List[Dict[str, Any]]
    risk_trajectory: List[Dict[str, Any]]
    state_sequence: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ReviewerTimelineProjection:
    """Targeted reviewer timeline projection highlighting keyframe evidence and escalation milestones."""
    incident_id: str
    start_time: float
    end_time: Optional[float]
    keyframe_evidence: List[Dict[str, Any]]
    escalation_events: List[Dict[str, Any]]
    final_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TimelineProjectionService:
    """Generates view projections from timeline repository queries."""

    def __init__(self, query_service: TimelineQueryService):
        self.query_service = query_service

    def generate_human_projection(self, incident_id: str, title: str = "Behavioral Incident") -> HumanTimelineProjection:
        """Generate human-friendly timeline projection."""
        events = self.query_service.get_complete_timeline(incident_id)
        if not events:
            return HumanTimelineProjection(incident_id, title, "0.0s", [])

        t_start = events[0].timestamp
        t_end = events[-1].timestamp
        dur_sec = max(0.0, round(t_end - t_start, 1))

        summaries = []
        for e in events:
            if e.event_type == "INCIDENT_CREATED":
                text = f"Incident initiated ({e.metadata.get('incident_type', 'Anomaly')})"
            elif e.event_type == "STATE_CHANGED":
                text = f"State changed to {e.new_state}"
            elif e.event_type == "EVIDENCE_ADDED":
                text = f"Keyframe evidence attached (Importance: {e.metadata.get('importance', 0.5):.2f})"
            elif e.event_type == "RESOLVED":
                text = f"Incident resolved ({e.metadata.get('reason', 'Resolved')})"
            else:
                text = f"Event: {e.event_type}"

            summaries.append({
                "sequence_number": e.sequence_number,
                "timestamp": round(e.timestamp, 2),
                "summary": text
            })

        return HumanTimelineProjection(
            incident_id=incident_id,
            summary_title=title,
            duration_text=f"{dur_sec:.1f}s",
            event_summaries=summaries
        )

    def generate_technical_projection(self, incident_id: str) -> TechnicalTimelineProjection:
        """Generate technical timeline projection with diagnostic trajectory streams."""
        events = self.query_service.get_complete_timeline(incident_id)

        conf_traj = [
            {"seq": e.sequence_number, "ts": e.timestamp, "conf": e.confidence}
            for e in events if e.confidence is not None
        ]
        risk_traj = [
            {"seq": e.sequence_number, "ts": e.timestamp, "risk": e.risk}
            for e in events if e.risk is not None
        ]
        state_seq = self.query_service.get_state_history(incident_id)

        return TechnicalTimelineProjection(
            incident_id=incident_id,
            total_events=len(events),
            confidence_trajectory=conf_traj,
            risk_trajectory=risk_traj,
            state_sequence=state_seq
        )

    def generate_reviewer_projection(self, incident_id: str) -> ReviewerTimelineProjection:
        """Generate focused proctor reviewer timeline projection."""
        events = self.query_service.get_complete_timeline(incident_id)
        if not events:
            return ReviewerTimelineProjection(incident_id, 0.0, None, [], [], "UNKNOWN")

        t_start = events[0].timestamp
        t_end = events[-1].timestamp if events[-1].event_type == "RESOLVED" else None

        evidence_events = [
            e.to_dto().to_dict() for e in events if e.event_type == "EVIDENCE_ADDED" or e.evidence_reference is not None
        ]
        escalation_events = [
            e.to_dto().to_dict() for e in events if e.event_type == "STATE_CHANGED" and e.new_state == "ESCALATED"
        ]
        final_status = events[-1].new_state or events[-1].event_type

        return ReviewerTimelineProjection(
            incident_id=incident_id,
            start_time=t_start,
            end_time=t_end,
            keyframe_evidence=evidence_events,
            escalation_events=escalation_events,
            final_status=final_status
        )
