"""
Identity Integrity Engine performing pure decision logic on perception observations.
"""
import time
import logging
from typing import Optional, Any, Dict

from ai_engine.identity_protection.integrity.assessment import (
    IdentityIntegrityAssessment,
    ConfidenceLevel,
    DecisionReason
)
from ai_engine.identity_protection.integrity.scoring_strategy import (
    IdentityIntegrityConfig,
    IdentityScoringStrategy
)

logger = logging.getLogger("ai_engine.identity_protection.integrity")

class IdentityIntegrityEngine:
    """
    Main decision engine transforming perception signals into immutable IdentityIntegrityAssessment outputs.
    Performs decision logic only — zero computer vision or neural network inference.
    """

    def __init__(
        self,
        config: Optional[IdentityIntegrityConfig] = None,
        strategy: Optional[IdentityScoringStrategy] = None
    ) -> None:
        self.config = config if config is not None else IdentityIntegrityConfig()
        self.strategy = strategy if strategy is not None else IdentityScoringStrategy()
        self._evaluation_count = 0

    def evaluate(self, observation: Optional[Any]) -> IdentityIntegrityAssessment:
        """
        Evaluates observation input safely, returning an immutable IdentityIntegrityAssessment.
        Never raises exceptions or interrupts the AI thread execution.
        """
        try:
            assessment = self.strategy.compute_assessment(observation, self.config)
            self._evaluation_count += 1
            return assessment
        except Exception as e:
            logger.error(f"Error inside IdentityIntegrityEngine.evaluate: {e}")
            return IdentityIntegrityAssessment(
                identity_confidence=0.5,
                overall_liveness=0.5,
                spoof_confidence=0.5,
                integrity_score=0.5,
                stability_score=0.5,
                confidence_level=ConfidenceLevel.UNKNOWN.value,
                decision_reason=DecisionReason.INSUFFICIENT_EVIDENCE.value,
                supporting_evidence={"evaluation_error": str(e)},
                timestamp=time.time()
            )

    def health(self) -> Dict[str, Any]:
        """Returns health diagnostic metrics for Identity Integrity Engine."""
        return {
            "engine": "IdentityIntegrityEngine",
            "evaluation_count": self._evaluation_count,
            "minimum_liveness": self.config.minimum_liveness,
            "minimum_face_match": self.config.minimum_face_match,
            "minimum_integrity": self.config.minimum_integrity
        }
