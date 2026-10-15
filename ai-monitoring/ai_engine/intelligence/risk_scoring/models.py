"""Data models for Risk Scoring Engine."""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class RiskScoringConfig:
    """Configuration for Risk Scoring Engine."""
    # Configurable weights per rule id
    rule_weights: Dict[str, float] = field(default_factory=lambda: {
        "ID_MISMATCH": 0.0,
        "ID_FACE_MISSING": 45.0,
        "ID_MULTIPLE_FACES": 50.0,
        "UNAUTH_PHONE": 30.0,
        "UNAUTH_BOOK": 15.0,
        "ENV_BOOK_DETECTED": 15.0,
        "UNAUTH_NOTEBOOK": 20.0,
        "UNAUTH_PAPER": 20.0,
        "COMM_EARPHONES": 25.0,
        "COMM_HEADPHONES": 30.0,
        "COMM_MULTIPLE_PERSONS": 40.0,
        "ENV_CAM_OCCLUDED": 50.0,
        "ENV_CAM_COVERED": 50.0,
        "ATT_LOOKING_AWAY": 20.0,
        "ATT_DOWNWARD_GAZE": 15.0
    })
    
    # Thresholds mapping severity string to a tuple of (min_inclusive, max_inclusive)
    risk_thresholds: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "NORMAL": (0.0, 20.0),
        "LOW": (20.01, 40.0),
        "MEDIUM": (40.01, 60.0),
        "HIGH": (60.01, 80.0),
        "CRITICAL": (80.01, 100.0)
    })
    
    max_score: float = 100.0
    enable_logging: bool = True

@dataclass
class RiskContribution:
    """Represents a single rule's contribution to the final risk score."""
    rule_id: str
    rule_name: str
    weight: float
    contribution: float  # Normalized or raw value contributed

@dataclass
class RiskAssessment:
    """The final calculated risk assessment."""
    overall_score: float
    risk_level: str
    contributions: List[RiskContribution]
    triggered_rule_count: int
    highest_priority_rule_id: str
    weighted_score_breakdown: Dict[str, float]
    processing_timestamp: float
    processing_duration: float

@dataclass
class RiskStatistics:
    """Telemetry data for risk engine runs."""
    total_assessments: int = 0
    average_score: float = 0.0
