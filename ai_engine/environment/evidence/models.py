"""
Data models for Evidence Snapshot Manager.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import BoundingBox

@dataclass
class EvidenceConfig:
    """Configuration for evidence capture."""
    snapshot_directory: str = "snapshots"
    jpeg_quality: int = 90
    png_support: bool = False
    max_snapshots_per_object: int = 5
    bounding_box_color: tuple = (0, 255, 0) # BGR
    font_scale: float = 0.5
    line_thickness: int = 2
    enable_logging: bool = True

@dataclass
class SnapshotMetadata:
    """Additional metadata for snapshots."""
    tracking_duration: float
    reason: str
    extras: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvidenceSnapshot:
    """A single piece of snapshot evidence."""
    snapshot_id: str
    track_id: int
    object_type: DetectedObjectType
    timestamp: float
    frame_id: Optional[int]
    bbox: BoundingBox
    confidence: float
    snapshot_path: str
    snapshot_reason: str
    metadata: SnapshotMetadata
