"""
Timeline Query Service for Incident Timeline Engine.
Provides high-performance query methods over the canonical append-only timeline repository.
"""
from typing import List, Optional, Tuple, Dict, Any
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.timeline.timeline_repository import InMemoryTimelineRepository

class TimelineQueryService:
    """Query service providing flexible filtering over timeline repository entries."""

    def __init__(self, repository: InMemoryTimelineRepository):
        self.repository = repository

    def get_complete_timeline(self, incident_id: str) -> List[TimelineEvent]:
        """Fetch complete chronological timeline for an incident."""
        return self.repository.get_by_incident_id(incident_id)

    def get_events_by_type(self, incident_id: str, event_type: str) -> List[TimelineEvent]:
        """Filter events by event_type (e.g. STATE_CHANGED, EVIDENCE_ADDED)."""
        events = self.repository.get_by_incident_id(incident_id)
        return [e for e in events if e.event_type == event_type]

    def get_events_by_time_range(
        self,
        incident_id: str,
        start_time: float,
        end_time: float
    ) -> List[TimelineEvent]:
        """Filter events falling within a specific Unix timestamp window."""
        events = self.repository.get_by_incident_id(incident_id)
        return [e for e in events if start_time <= e.timestamp <= end_time]

    def get_evidence_events(self, incident_id: str) -> List[TimelineEvent]:
        """Filter timeline events containing evidence references."""
        events = self.repository.get_by_incident_id(incident_id)
        return [e for e in events if e.event_type == "EVIDENCE_ADDED" or e.evidence_reference is not None]

    def get_confidence_history(self, incident_id: str) -> List[Tuple[float, float]]:
        """Return list of (timestamp, confidence_value) tuples."""
        events = self.repository.get_by_incident_id(incident_id)
        return [(e.timestamp, e.confidence) for e in events if e.confidence is not None]

    def get_state_history(self, incident_id: str) -> List[Dict[str, Any]]:
        """Return chronological record of state transition dictionaries."""
        events = self.repository.get_by_incident_id(incident_id)
        state_events = [e for e in events if e.event_type in ("INCIDENT_CREATED", "STATE_CHANGED", "RESOLVED")]
        result = []
        for e in state_events:
            result.append({
                "sequence_number": e.sequence_number,
                "timestamp": e.timestamp,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "reason": e.metadata.get("reason", "")
            })
        return result
