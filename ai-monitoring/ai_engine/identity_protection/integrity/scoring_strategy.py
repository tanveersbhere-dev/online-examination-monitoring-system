"""
Centralized, Configurable Scoring Strategy for Identity Integrity.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Dict

from ai_engine.identity_protection.integrity.assessment import (
    IdentityIntegrityAssessment,
    ConfidenceLevel,
    DecisionReason
)

logger = logging.getLogger("ai_engine.identity_protection.scoring")

@dataclass
class IdentityIntegrityConfig:
    """
    Centralized configuration parameters for Identity Integrity Decision Logic.
    Avoids magic numbers throughout the system.
    """
    minimum_liveness: float = 0.50
    minimum_face_match: float = 0.60
    liveness_weight: float = 0.35
    identity_weight: float = 0.25
    mesh_weight: float = 0.15
    reflection_weight: float = 0.15
    temporal_weight: float = 0.10
    minimum_integrity: float = 0.50

class IdentityScoringStrategy:
    """
    Evaluates perception signals from IdentityProtectionObservation using a configurable weighted scoring strategy.
    """

    def compute_assessment(
        self,
        observation: Optional[Any],
        config: IdentityIntegrityConfig
    ) -> IdentityIntegrityAssessment:
        """
        Computes composite integrity score, assigns confidence levels, and selects structured decision reason codes.
        Handles missing or partial observation fields safely.
        """
        start_time = time.time()

        if observation is None:
            return IdentityIntegrityAssessment(
                identity_confidence=0.5,
                overall_liveness=0.5,
                spoof_confidence=0.5,
                integrity_score=0.5,
                stability_score=0.5,
                confidence_level=ConfidenceLevel.UNKNOWN.value,
                decision_reason=DecisionReason.INSUFFICIENT_EVIDENCE.value,
                supporting_evidence={"reason": "Observation input is None"},
                timestamp=start_time
            )

        # Extract perception inputs with safe fallbacks
        liveness_score = float(getattr(observation, "liveness_score", 1.0))
        identity_confidence = float(getattr(observation, "identity_integrity_score", 1.0))
        mesh_conf = float(getattr(observation, "mesh_confidence", 1.0))
        reflection_score = float(getattr(observation, "reflection_score", 0.0))
        temporal_conf = float(getattr(observation, "temporal_consistency", 1.0))
        spoof_conf = float(getattr(observation, "spoof_confidence", 0.0))
        liveness_state = getattr(observation, "liveness_state", "LIVE")

        # Convert reflection score to reflection quality (1.0 = no reflection artifacts)
        reflection_quality = float(max(0.0, 1.0 - reflection_score))

        # Calculate Weighted Composite Integrity Score
        weighted_integrity = (
            (liveness_score * config.liveness_weight) +
            (identity_confidence * config.identity_weight) +
            (mesh_conf * config.mesh_weight) +
            (reflection_quality * config.reflection_weight) +
            (temporal_conf * config.temporal_weight)
        )
        
        integrity_score = float(max(0.0, min(1.0, weighted_integrity)))

        # Assign Semantic Confidence Level
        if integrity_score >= 0.85:
            conf_level = ConfidenceLevel.VERY_HIGH.value
        elif integrity_score >= 0.70:
            conf_level = ConfidenceLevel.HIGH.value
        elif integrity_score >= 0.55:
            conf_level = ConfidenceLevel.MEDIUM.value
        elif integrity_score >= 0.40:
            conf_level = ConfidenceLevel.LOW.value
        else:
            conf_level = ConfidenceLevel.VERY_LOW.value

        # Select Primary Decision Reason Code based on dominant evidence
        if liveness_state == "SPOOF_CONFIRMED" or spoof_conf > 0.7:
            reason = DecisionReason.SPOOF_ATTACK_CONFIRMED.value
        elif reflection_score > 0.7:
            reason = DecisionReason.REPLAY_REFLECTION_DETECTED.value
        elif mesh_conf < 0.2:
            reason = DecisionReason.FLAT_MESH_GEOMETRY.value
        elif identity_confidence < config.minimum_face_match:
            reason = DecisionReason.LOW_IDENTITY_MATCH.value
        elif temporal_conf < 0.4:
            reason = DecisionReason.TEMPORAL_INSTABILITY.value
        elif liveness_score >= config.minimum_liveness and identity_confidence >= config.minimum_face_match:
            reason = DecisionReason.HIGH_LIVENESS_CONFIDENCE.value
        else:
            reason = DecisionReason.INSUFFICIENT_EVIDENCE.value

        supporting_evidence = {
            "raw_liveness_score": round(liveness_score, 4),
            "identity_confidence": round(identity_confidence, 4),
            "mesh_confidence": round(mesh_conf, 4),
            "reflection_score": round(reflection_score, 4),
            "temporal_consistency": round(temporal_conf, 4),
            "liveness_state": liveness_state
        }

        return IdentityIntegrityAssessment(
            identity_confidence=round(identity_confidence, 4),
            overall_liveness=round(liveness_score, 4),
            spoof_confidence=round(spoof_conf, 4),
            integrity_score=round(integrity_score, 4),
            stability_score=round(temporal_conf, 4),
            confidence_level=conf_level,
            decision_reason=reason,
            supporting_evidence=supporting_evidence,
            timestamp=start_time
        )
