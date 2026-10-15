"""Data models for Environment History Engine."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ai_engine.core.enums import DetectedObjectType

@dataclass
class HistoryConfig:
    """Configuration for History Engine."""
    history_window_sizes: List[int] = field(default_factory=lambda: [1, 5, 10, 30])
    max_history_size: int = 1000
    cleanup_interval_seconds: float = 60.0
    summary_interval_seconds: float = 1.0
    history_expiration_seconds: float = 300.0  # Expire objects removed > 5 mins ago
    enable_logging: bool = True

@dataclass
class TrackedObjectHistory:
    """Historical data for a single tracked object."""
    track_id: int
    object_type: DetectedObjectType
    first_seen_timestamp: float
    last_seen_timestamp: float = 0.0
    total_visible_duration: float = 0.0
    appearance_count: int = 0
    consecutive_visible_frames: int = 0
    consecutive_missing_frames: int = 0
    
    average_detection_confidence: float = 0.0
    max_detection_confidence: float = 0.0
    min_detection_confidence: float = 1.0
    
    average_bbox_area: float = 0.0
    max_bbox_area: float = 0.0
    
    snapshot_references: List[str] = field(default_factory=list)
    current_state: str = "NEW"

@dataclass
class EnvironmentStatistics:
    """Global environmental statistics computed over rolling windows."""
    total_object_count: int = 0
    active_object_count: int = 0
    historical_object_count: int = 0
    
    # window_size -> max person count in that window
    person_count_history: Dict[int, int] = field(default_factory=dict)
    
    phone_presence_duration: float = 0.0
    book_presence_duration: float = 0.0
    earphone_presence_duration: float = 0.0
    smartwatch_presence_duration: float = 0.0
    
    average_objects_per_frame: float = 0.0
    processing_timestamp: float = 0.0

@dataclass
class EnvironmentHistory:
    """Root container for all historical data."""
    object_histories: Dict[int, TrackedObjectHistory] = field(default_factory=dict)
    statistics: EnvironmentStatistics = field(default_factory=EnvironmentStatistics)
