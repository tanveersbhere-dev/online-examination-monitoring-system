"""Data models for Violation Manager."""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ViolationManagerConfig:
    """Configuration for Violation Manager."""
    merge_window_seconds: float = 10.0
    auto_close_timeout_seconds: float = 30.0
    maximum_active_violations: int = 100
    duplicate_detection_seconds: float = 5.0
    enable_logging: bool = True

@dataclass
class Violation:
    """Represents an examination violation."""
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
    status: str = "OPEN" # OPEN, ACTIVE, RESOLVED, DISMISSED, MERGED
    description: str = ""

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
