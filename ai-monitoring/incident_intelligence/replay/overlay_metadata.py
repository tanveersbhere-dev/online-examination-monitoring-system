"""
Overlay Metadata and Generator for Replay Intelligence Engine.
Generates read-only bounding box and annotation overlay metadata without modifying video frames.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from incident_intelligence.domain.incident import Incident
from incident_intelligence.replay.frame_index import FrameIndexEntry

@dataclass(frozen=True)
class ReplayOverlayMetadata:
    """Immutable overlay metadata for rendering on UI player canvas."""
    frame_number: int
    timestamp: float
    face_box: Optional[List[int]] = None
    bounding_boxes: List[Dict[str, Any]] = field(default_factory=list)
    object_labels: List[str] = field(default_factory=list)
    confidence: float = 0.0
    rule: Optional[str] = None
    timeline_event_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ReplayOverlayGenerator:
    """Generates read-only overlay metadata for UI rendering."""

    def generate_overlay(
        self,
        incident: Incident,
        frame_entry: FrameIndexEntry,
        face_box: Optional[List[int]] = None,
        detected_objects: Optional[List[Dict[str, Any]]] = None
    ) -> ReplayOverlayMetadata:
        """Generate overlay metadata object."""
        boxes = detected_objects or []
        labels = [b.get("label", "Object") for b in boxes]

        rule_str = incident.metadata.triggered_rules[0] if incident.metadata.triggered_rules else incident.incident_type

        return ReplayOverlayMetadata(
            frame_number=frame_entry.frame_number,
            timestamp=frame_entry.timestamp,
            face_box=face_box,
            bounding_boxes=boxes,
            object_labels=labels,
            confidence=incident.current_confidence,
            rule=rule_str,
            timeline_event_summary=f"Frame #{frame_entry.frame_number} - Event: {frame_entry.timeline_event_id or 'NORMAL'}"
        )
