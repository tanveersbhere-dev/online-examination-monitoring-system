"""Data models for Rule Engine."""
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class RuleEngineConfig:
    """Configuration for Rule Engine."""
    # Mapping of rule_id to enable status
    enabled_rules: Dict[str, bool] = field(default_factory=lambda: {
        "ATT_LOOKING_AWAY": True,
        "ATT_DOWNWARD_GAZE": True,
        "ID_MISMATCH": True,
        "ID_FACE_MISSING": True,
        "ID_MULTIPLE_FACES": True,
        "UNAUTH_PHONE": True,
        "UNAUTH_BOOK": True,
        "UNAUTH_NOTEBOOK": True,
        "UNAUTH_PAPER": True,
        "COMM_EARPHONES": True,
        "COMM_HEADPHONES": True,
        "COMM_MULTIPLE_PERSONS": True,
        "ENV_CAM_OCCLUDED": True,
        "ENV_CAM_COVERED": True
    })
    
    # Custom thresholds (e.g., maximum duration allowed for looking away)
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        "looking_away_duration": 3.0,
        "downward_gaze_duration": 5.0,
        "face_missing_duration": 2.0
    })
    
    # Optional evaluation intervals to skip frames if needed (e.g. run rules every N seconds)
    evaluation_interval_seconds: float = 0.0
    enable_logging: bool = True

@dataclass
class RuleEvaluation:
    """The result of evaluating a single rule."""
    rule_id: str
    rule_name: str
    category: str
    triggered: bool
    confidence: float
    supporting_observations: str
    evaluation_timestamp: float
    evaluation_duration: float

@dataclass
class RuleStatistics:
    """Summary statistics for a rule engine run."""
    total_rules_evaluated: int = 0
    total_rules_triggered: int = 0
    triggered_by_category: Dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
