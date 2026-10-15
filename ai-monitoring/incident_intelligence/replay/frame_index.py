"""
FrameIndex Model and Indexer for Replay Intelligence Engine.
Provides deterministic lookup by frame number, timestamp, incident ID, or evidence ID.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

@dataclass(frozen=True)
class FrameIndexEntry:
    """Immutable frame index entry mapping video frame index to domain signals."""
    frame_number: int
    timestamp: float
    incident_id: str
    timeline_event_id: Optional[str] = None
    evidence_reference_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class FrameIndex:
    """Deterministic frame index container and fast lookup structure."""

    def __init__(self):
        self._by_frame: Dict[int, FrameIndexEntry] = {}
        self._by_timestamp: List[FrameIndexEntry] = []
        self._by_timeline_event: Dict[str, FrameIndexEntry] = {}
        self._by_evidence_ref: Dict[str, FrameIndexEntry] = {}

    def add_entry(self, entry: FrameIndexEntry) -> None:
        """Add a frame index entry."""
        self._by_frame[entry.frame_number] = entry
        self._by_timestamp.append(entry)
        self._by_timestamp.sort(key=lambda e: e.timestamp)

        if entry.timeline_event_id:
            self._by_timeline_event[entry.timeline_event_id] = entry
        if entry.evidence_reference_id:
            self._by_evidence_ref[entry.evidence_reference_id] = entry

    def get_by_frame(self, frame_number: int) -> Optional[FrameIndexEntry]:
        """Fetch frame entry by frame number."""
        return self._by_frame.get(frame_number)

    def get_nearest_by_timestamp(self, timestamp: float) -> Optional[FrameIndexEntry]:
        """Fetch frame entry closest to a given timestamp."""
        if not self._by_timestamp:
            return None
        return min(self._by_timestamp, key=lambda e: abs(e.timestamp - timestamp))

    def get_by_timeline_event(self, timeline_event_id: str) -> Optional[FrameIndexEntry]:
        """Fetch frame entry linked to a specific timeline event."""
        return self._by_timeline_event.get(timeline_event_id)

    def get_by_evidence_ref(self, evidence_ref_id: str) -> Optional[FrameIndexEntry]:
        """Fetch frame entry linked to an evidence reference."""
        return self._by_evidence_ref.get(evidence_ref_id)

    def list_all(self) -> List[FrameIndexEntry]:
        """List all entries chronologically."""
        return list(self._by_timestamp)
