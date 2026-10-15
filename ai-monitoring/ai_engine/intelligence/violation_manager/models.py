"""Data models for Violation Manager."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Lifecycle event — the canonical transition message emitted by ViolationManager.
# Downstream consumers (WebSocket, frontend timeline, evidence capture) must
# only react to these events, never to raw per-frame rule evaluations.
# ---------------------------------------------------------------------------

@dataclass
class LifecycleEvent:
    """
    A single violation lifecycle transition.

    event_type values:
      "STARTED"  — violation first detected; evidence should be captured.
      "UPDATED"  — violation severity escalated while active.
      "RESOLVED" — violation auto-closed after inactivity timeout.
    """
    event_type: str           # "STARTED" | "UPDATED" | "RESOLVED"
    violation_id: str
    violation_type: str
    violation_category: str
    severity: str
    risk_score: float
    triggered_rules: List[str]
    timestamp: float          # wall-clock time this transition was detected
    start_timestamp: float    # when the violation was first opened
    end_timestamp: Optional[float] = None
    description: str = ""
    current_confidence: float = 0.0
    peak_confidence: float = 0.0
    detection_count: int = 0
    duration: float = 0.0
    camera_id: str = "camera_1"


@dataclass
class ViolationManagerConfig:
    """Configuration for Violation Manager."""
    merge_window_seconds: float = 15.0
    auto_close_timeout_seconds: float = 5.0
    maximum_active_violations: int = 100
    duplicate_detection_seconds: float = 15.0
    enable_logging: bool = True
    
    # ── Professional Proctoring Debounce & Cooldown Configuration ───────
    debounce_window_seconds: float = 1.5           # Sustained observation window before opening an incident
    min_confirming_frames: int = 3                 # Minimum observations before CONFIRMED
    min_confirming_ratio: float = 0.60             # Ratio of positive frames required in debounce window
    min_candidate_confidence: float = 0.40         # Pre-filter threshold for rule signals
    cooldown_duration_seconds: float = 12.0        # Enterprise debounce exit cooldown before RESOLVED
    dedup_coalesce_window_seconds: float = 15.0    # Grace window to coalesce reopened violations into same episode (<15s coalesces)
    periodic_resnapshot_interval_seconds: float = 30.0  # Periodic corroborating re-snapshot interval
    max_captures_per_type_per_minute: int = 6      # allows separate episodes while limiting evidence writes
    max_evidence_items: int = 15                   # Hard capacity ceiling for session evidence gallery
    max_snapshots_per_violation: int = 3           # primary evidence + two strongest additional keyframes
    attention_confirmation_seconds: float = 1.5     # sustained evidence required before opening attention episode
    attention_min_confirming_frames: int = 3        # protects against single-frame gaze jitter
    attention_grace_seconds: float = 5.0            # tolerate normal detector gaps before resolving attention

    # Per-violation debounce confirmation windows (seconds)
    per_violation_debounce_seconds: dict = field(default_factory=lambda: {
        "UNAUTH_PHONE": 1.5,
        "UNAUTH_BOOK": 1.2,
        "ENV_BOOK_DETECTED": 1.2,
        "UNAUTH_NOTEBOOK": 1.2,
        "UNAUTH_REGISTER": 1.2,
        "UNAUTH_PAPER": 1.2,
        "UNAUTH_LAPTOP": 1.5,
        "ATT_LOOKING_AWAY": 1.5,
        "ATT_DOWNWARD_GAZE": 1.5,
        "ID_MISMATCH": 2.0,
        "ID_FACE_MISSING": 2.0,
        "ID_MULTIPLE_FACES": 2.0,
        "COMM_EARPHONES": 1.5,
        "COMM_HEADPHONES": 1.5,
        "COMM_MULTIPLE_PERSONS": 1.5,
        "BEHAVIOR_REPEATED_PATTERN": 3.0,
        "IDENTITY_LOW_INTEGRITY": 3.0,
        "IDENTITY_REPEATED_MISMATCH": 3.0,
        "CONFIRMED_PRESENTATION_ATTACK": 3.0,
    })

    # Fast per-violation resolution / cooldown timeouts (seconds)
    per_violation_timeouts: dict = field(default_factory=lambda: {
        "UNAUTH_PHONE": 5.0,
        "UNAUTH_BOOK": 3.5,
        "ENV_BOOK_DETECTED": 3.5,
        "UNAUTH_NOTEBOOK": 3.5,
        "UNAUTH_REGISTER": 3.5,
        "UNAUTH_PAPER": 3.5,
        "UNAUTH_LAPTOP": 5.0,
        "ATT_LOOKING_AWAY": 5.0,
        "ATT_DOWNWARD_GAZE": 5.0,
        "ID_MISMATCH": 5.0,
        "ID_FACE_MISSING": 5.0,
        "ID_MULTIPLE_FACES": 5.0,
        "COMM_EARPHONES": 5.0,
        "COMM_HEADPHONES": 5.0,
        "COMM_MULTIPLE_PERSONS": 5.0,
        "BEHAVIOR_REPEATED_PATTERN": 5.0,
        "IDENTITY_LOW_INTEGRITY": 5.0,
        "IDENTITY_REPEATED_MISMATCH": 5.0,
        "CONFIRMED_PRESENTATION_ATTACK": 5.0,
    })
    # Evidence capture — owned exclusively by ViolationManager
    evidence_dir: Optional[Path] = None


@dataclass
class Violation:
    """Represents an examination behavior episode / violation."""
    violation_id: str
    violation_type: str
    violation_category: str
    severity: str
    risk_score: float
    triggered_rules: List[str] = field(default_factory=list)
    supporting_evidence_references: List[str] = field(default_factory=list)
    start_timestamp: float = 0.0
    last_updated_timestamp: float = 0.0
    end_timestamp: Optional[float] = None
    status: str = "OPEN"  # OPEN, ACTIVE, RESOLVED, DISMISSED, MERGED
    description: str = ""
    # Episode-based management metrics
    peak_confidence: float = 0.0
    current_confidence: float = 0.0
    confidence_sum: float = 0.0
    confidence_samples: int = 0
    detection_count: int = 0
    last_observation_timestamp: float = 0.0
    interruption_count: int = 0
    was_interrupted: bool = False
    peak_frame_data: Any = None
    # Professional Debounce & Evidence Tracking
    candidate_first_seen: float = 0.0
    candidate_frame_count: int = 0
    is_confirmed: bool = False
    evidence_captured: bool = False
    last_evidence_timestamp: float = 0.0
    evidence_capture_count: int = 0
    camera_id: str = "camera_1"


@dataclass
class ViolationTimeline:
    """Chronological history of violations."""
    violations: List[Violation] = field(default_factory=list)


@dataclass
class ViolationStatistics:
    """Telemetry data for the violation manager."""
    total_violations_created: int = 0
    currently_active: int = 0
    total_merged: int = 0
    total_resolved: int = 0
    total_evidence_captured: int = 0
    total_candidates_debounced: int = 0

