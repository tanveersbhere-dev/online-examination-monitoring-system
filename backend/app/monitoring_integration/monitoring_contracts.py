"""
Monitoring Integration Contracts
================================
Defines domain data transfer objects, constants, and event mapping definitions
connecting the Main FYP Examination System and the AI Monitoring Subsystem.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time


class MonitoringSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    ELEVATED = "ELEVATED"


class MonitoringStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


# Map subsystem event/rule names to main-system standard AIEvent types
EVENT_TYPE_MAPPING: Dict[str, str] = {
    # Object violations
    "UNAUTH_PHONE": "MOBILE_PHONE",
    "CELL_PHONE": "MOBILE_PHONE",
    "UNAUTH_BOOK": "BOOK_USAGE",
    "UNAUTH_NOTEBOOK": "BOOK_USAGE",
    "UNAUTH_PAPER": "BOOK_USAGE",
    "BOOK": "BOOK_USAGE",
    "NOTEBOOK": "BOOK_USAGE",
    "PAPER": "BOOK_USAGE",
    "ENV_BOOK_DETECTED": "BOOK_USAGE",
    # Face & identity violations
    "ID_MULTIPLE_FACES": "MULTIPLE_PERSONS",
    "COMM_MULTIPLE_PERSONS": "MULTIPLE_PERSONS",
    "ID_FACE_MISSING": "NO_FACE",
    "ID_MISMATCH": "UNKNOWN_PERSON",
    "CONFIRMED_PRESENTATION_ATTACK": "PRESENTATION_ATTACK",
    "PRESENTATION_ATTACK": "PRESENTATION_ATTACK",
    "IDENTITY_LOW_INTEGRITY": "IDENTITY_LOW_INTEGRITY",
    "IDENTITY_REPEATED_MISMATCH": "UNKNOWN_PERSON",
    "INSUFFICIENT_IDENTITY_EVIDENCE": "UNKNOWN_PERSON",
    # Attention & head pose violations
    "ATT_LOOKING_AWAY": "LOOKING_AWAY",
    "ATT_DOWNWARD_GAZE": "LOOKING_AWAY",
    # Wearable & communication devices
    "COMM_EARPHONES": "EARPHONES_DETECTED",
    "COMM_HEADPHONES": "EARPHONES_DETECTED",
    "EARPHONES": "EARPHONES_DETECTED",
    "HEADPHONES": "EARPHONES_DETECTED",
    # Camera tampering & environment
    "ENV_CAM_OCCLUDED": "CAMERA_OBSTRUCTION",
    "ENV_CAM_COVERED": "CAMERA_OBSTRUCTION",
    # Composite malpractice
    "COMPOSITE_PHONE_LOOKING_AWAY_TALKING": "COMPOSITE_PHONE_LOOKING_AWAY_TALKING",
    "COMPOSITE_FACE_MISSING_UNKNOWN": "COMPOSITE_FACE_MISSING_UNKNOWN",
    # Behavioral patterns
    "BEHAVIOR_REPEATED_PATTERN": "REPEATED_VIOLATION_PATTERN",
    "REPEATED_VIOLATION_PATTERN": "REPEATED_VIOLATION_PATTERN",
}

# Severity normalization mapping (e.g. ELEVATED -> HIGH)
SEVERITY_MAPPING: Dict[str, str] = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "ELEVATED": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
    "NORMAL": "LOW",
}

RULE_SEVERITY_MAPPING: Dict[str, str] = {
    "UNAUTH_PHONE": "CRITICAL",
    "CELL_PHONE": "CRITICAL",
    "PHONE": "CRITICAL",
    "UNAUTH_BOOK": "HIGH",
    "UNAUTH_NOTEBOOK": "HIGH",
    "UNAUTH_PAPER": "HIGH",
    "BOOK": "HIGH",
    "NOTEBOOK": "HIGH",
    "PAPER": "HIGH",
    "ID_MULTIPLE_FACES": "CRITICAL",
    "COMM_MULTIPLE_PERSONS": "CRITICAL",
    "ID_FACE_MISSING": "HIGH",
    "ID_MISMATCH": "CRITICAL",
    "ATT_LOOKING_AWAY": "MEDIUM",
    "ATT_DOWNWARD_GAZE": "MEDIUM",
    "COMM_EARPHONES": "HIGH",
    "COMM_HEADPHONES": "HIGH",
    "EARPHONES": "HIGH",
    "HEADPHONES": "HIGH",
    "ENV_CAM_OCCLUDED": "HIGH",
    "ENV_CAM_COVERED": "CRITICAL",
    "COMPOSITE_PHONE_LOOKING_AWAY_TALKING": "CRITICAL",
    "COMPOSITE_FACE_MISSING_UNKNOWN": "CRITICAL",
    "CONFIRMED_PRESENTATION_ATTACK": "CRITICAL",
    "PRESENTATION_ATTACK": "CRITICAL",
}


@dataclass
class NormalizedMonitoringEvent:
    """Normalized event ready for AIEventProcessor ingestion."""
    event_type: str
    severity: str
    confidence: float
    timestamp: float
    exam_session_id: int
    student_id: int
    source_module: str
    payload: Dict[str, Any] = field(default_factory=dict)
    frame_path: Optional[str] = None
    rule_id: Optional[str] = None
    is_lifecycle_transition: bool = False
    transition_type: Optional[str] = None  # "STARTED" | "UPDATED" | "RESOLVED"
