"""
Behavior Event and Dataclass Schemas for Behavioral Intelligence Engine.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class BehaviorMemoryEntry:
    timestamp: float
    rule_name: str
    violation_id: str
    severity: str
    confidence: float
    duration: float = 0.0
    resolved: bool = False
    tracking_id: Optional[int] = None
    object_type: Optional[str] = None
    head_pose: Optional[str] = None
    gaze: Optional[str] = None
    talking: bool = False
    phone_present: bool = False
    multiple_faces: bool = False
    risk_score: float = 0.0

@dataclass
class CompositeBehaviorInstance:
    name: str                           # e.g., PHONE_USAGE, COMMUNICATION, OUTSIDE_ASSISTANCE
    title: str                          # Human-readable title
    confidence: float                   # 0.0 - 100.0
    supporting_events: List[str]        # List of rule names / event types
    supporting_violations: List[str]    # List of violation IDs
    start_time: float
    last_update: float
    duration_seconds: float = 0.0
    resolved: bool = False
    explainability: List[str] = field(default_factory=list)

@dataclass
class CandidateBehaviorProfile:
    state: str = "NORMAL"               # NORMAL | SLIGHTLY_SUSPICIOUS | SUSPICIOUS | HIGH_RISK | CRITICAL
    behavior_score: float = 0.0        # 0.0 - 100.0
    trend: str = "STABLE"               # STABLE | ESCALATING | RECOVERING
    last_escalation: Optional[float] = None
    last_recovery: Optional[float] = None
    active_composite_behaviors: List[CompositeBehaviorInstance] = field(default_factory=list)
    resolved_composite_behaviors: List[CompositeBehaviorInstance] = field(default_factory=list)

@dataclass
class BehaviorTimelineEvent:
    id: str
    type: str                           # Composite behavior type
    transition: str                     # STARTED | ESCALATED | RECOVERED | RESOLVED
    confidence: float
    timestamp: float
    description: str
    duration_seconds: float = 0.0

@dataclass
class BehaviorSessionSummary:
    behavior_score: float = 0.0
    highest_risk_state: str = "NORMAL"
    composite_behaviors_detected: List[str] = field(default_factory=list)
    total_escalations: int = 0
    avg_confidence: float = 0.0
    peak_confidence: float = 0.0
    longest_suspicious_period_sec: float = 0.0
    recovered_behaviors_count: int = 0
    overall_integrity_assessment: str = "HIGH_INTEGRITY" # HIGH_INTEGRITY | MODERATE_CONCERN | COMPROMISED
