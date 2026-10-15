"""
In-Memory Timeline Repository for Incident Timeline Engine.
Append-only storage adapter ensuring timeline events are never modified or deleted.
"""
from typing import List, Dict, Optional
from incident_intelligence.timeline.timeline_event import TimelineEvent

class InMemoryTimelineRepository:
    """Append-only repository storing TimelineEvent entries."""

    def __init__(self):
        self._events_by_incident: Dict[str, List[TimelineEvent]] = {}
        self._sequence_counter: Dict[str, int] = {}

    def append(self, event: TimelineEvent) -> int:
        """
        Append a new TimelineEvent entry to an incident's chronological timeline.
        Returns assigned sequence number.
        """
        incident_id = event.incident_id
        if incident_id not in self._events_by_incident:
            self._events_by_incident[incident_id] = []
            self._sequence_counter[incident_id] = 0

        # Assign sequence number if not already populated
        seq = event.sequence_number
        if seq <= 0:
            self._sequence_counter[incident_id] += 1
            seq = self._sequence_counter[incident_id]
            # Create updated event copy with correct sequence number
            event = TimelineEvent(
                event_id=event.event_id,
                incident_id=event.incident_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                sequence_number=seq,
                previous_state=event.previous_state,
                new_state=event.new_state,
                confidence=event.confidence,
                risk=event.risk,
                evidence_reference=event.evidence_reference,
                metadata=event.metadata,
                source=event.source
            )
        else:
            self._sequence_counter[incident_id] = max(self._sequence_counter[incident_id], seq)

        self._events_by_incident[incident_id].append(event)
        # Ensure chronological ordering
        self._events_by_incident[incident_id].sort(key=lambda e: (e.sequence_number, e.timestamp))
        return event

    def get_by_incident_id(self, incident_id: str) -> List[TimelineEvent]:
        """Fetch complete chronological timeline for an incident."""
        return list(self._events_by_incident.get(incident_id, []))

    def clear(self) -> None:
        """Clear repository entries (useful for testing)."""
        self._events_by_incident.clear()
        self._sequence_counter.clear()
