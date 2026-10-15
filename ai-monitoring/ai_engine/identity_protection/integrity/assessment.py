"""
Immutable Assessment Schema and Decision Codes for Identity Protection.
"""
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any

class ConfidenceLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"
    UNKNOWN = "UNKNOWN"

class DecisionReason(str, Enum):
    HIGH_LIVENESS_CONFIDENCE = "HIGH_LIVENESS_CONFIDENCE"
    FACE_MATCH_VERIFIED = "FACE_MATCH_VERIFIED"
    REPLAY_REFLECTION_DETECTED = "REPLAY_REFLECTION_DETECTED"
    FLAT_MESH_GEOMETRY = "FLAT_MESH_GEOMETRY"
    TEMPORAL_INSTABILITY = "TEMPORAL_INSTABILITY"
    LOW_IDENTITY_MATCH = "LOW_IDENTITY_MATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SPOOF_ATTACK_CONFIRMED = "SPOOF_ATTACK_CONFIRMED"

@dataclass(frozen=True)
class IdentityIntegrityAssessment:
    """
    Immutable trust assessment produced by the Identity Integrity Engine.
    """
    identity_confidence: float = 1.0
    overall_liveness: float = 1.0
    spoof_confidence: float = 0.0
    integrity_score: float = 1.0
    stability_score: float = 1.0
    confidence_level: str = ConfidenceLevel.VERY_HIGH.value
    decision_reason: str = DecisionReason.HIGH_LIVENESS_CONFIDENCE.value
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
