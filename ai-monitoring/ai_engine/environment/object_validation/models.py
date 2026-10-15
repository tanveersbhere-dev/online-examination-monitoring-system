"""
Data Models and Configuration Schemas for Object Validation & Reliability Layer.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Any

class ValidationReason(str, Enum):
    ACCEPTED_CONFIRMED = "ACCEPTED_CONFIRMED"
    REJECTED_UNSUPPORTED_CLASS = "REJECTED_UNSUPPORTED_CLASS"
    REJECTED_LOW_CONFIDENCE = "REJECTED_LOW_CONFIDENCE"
    REJECTED_TEMPORAL_UNCONFIRMED = "REJECTED_TEMPORAL_UNCONFIRMED"
    REJECTED_UNSTABLE = "REJECTED_UNSTABLE"

@dataclass
class ClassValidationConfig:
    min_confidence: float = 0.45
    min_consecutive_frames: int = 2
    min_tracking_seconds: float = 0.0

@dataclass
class ObjectValidationConfig:
    whitelisted_classes: Set[str] = field(default_factory=lambda: {
        "CELL_PHONE",
        "PERSON",
        "BOOK",
        "NOTEBOOK",
        "REGISTER",
        "PAPER",
        "PAGE",
        "TEXTBOOK",
        "DIARY",
        "JOURNAL",
        "EXERCISE_BOOK",
        "WRITING_PAD",
        "EXAM_NOTEBOOK",
        "PRINTED_BOOK",
        "PRINTED_PAGE",
        "UNAUTHORIZED_MATERIAL",
        "LAPTOP",
        "TABLET",
        "MONITOR",
        "EARBUDS",
        "EARPHONES",
        "WIRED_HANDSFREE",
        "HEADPHONES",
        "HEADSET",
        "NECKBAND",
        "COMM_EARPHONES",
        "SMARTWATCH",
    })
    class_configs: Dict[str, ClassValidationConfig] = field(default_factory=lambda: {
        "CELL_PHONE": ClassValidationConfig(min_confidence=0.25, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "PERSON": ClassValidationConfig(min_confidence=0.45, min_consecutive_frames=8, min_tracking_seconds=0.8),
        "BOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "NOTEBOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "REGISTER": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "PAPER": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "PAGE": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "TEXTBOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "DIARY": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "JOURNAL": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "EXERCISE_BOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "WRITING_PAD": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "EXAM_NOTEBOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "PRINTED_BOOK": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "PRINTED_PAGE": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "UNAUTHORIZED_MATERIAL": ClassValidationConfig(min_confidence=0.60, min_consecutive_frames=2, min_tracking_seconds=0.0),
        # LAPTOP confidence threshold (0.45)
        "LAPTOP": ClassValidationConfig(min_confidence=0.45, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "TABLET": ClassValidationConfig(min_confidence=0.45, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "MONITOR": ClassValidationConfig(min_confidence=0.45, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "EARBUDS": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "EARPHONES": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "WIRED_HANDSFREE": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "HEADPHONES": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "HEADSET": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "NECKBAND": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "COMM_EARPHONES": ClassValidationConfig(min_confidence=0.42, min_consecutive_frames=2, min_tracking_seconds=0.0),
        "SMARTWATCH": ClassValidationConfig(min_confidence=0.35, min_consecutive_frames=2, min_tracking_seconds=0.0),
    })
    default_config: ClassValidationConfig = field(default_factory=lambda: ClassValidationConfig(min_confidence=0.35, min_consecutive_frames=2, min_tracking_seconds=0.0))
    # Temporal smoothing and majority voting configuration
    majority_vote_window: int = 10
    majority_vote_threshold: float = 0.60
    laptop_book_margin: float = 0.20
    enable_heuristic_disambiguation: bool = True
    max_missing_frames_to_expire: int = 10
    enable_logging: bool = True


@dataclass
class ValidationAuditRecord:
    frame_id: int
    object_type: str
    confidence: float
    tracking_id: Optional[int]
    status: str                         # ACCEPTED | REJECTED | PENDING_CONFIRMATION
    reason: ValidationReason
    consecutive_frames: int = 0
    tracking_seconds: float = 0.0
    details: str = ""

@dataclass
class ValidationStatistics:
    total_received: int = 0
    accepted_count: int = 0
    rejected_unsupported_class: int = 0
    rejected_low_confidence: int = 0
    rejected_unconfirmed_transient: int = 0
    active_tracks_count: int = 0
    processing_time_ms: float = 0.0
