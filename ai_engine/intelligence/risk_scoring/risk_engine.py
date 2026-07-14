"""Risk Scoring Engine implementation."""
import logging
from typing import Optional

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.risk_scoring.processor import RiskScoringProcessorInterface
from ai_engine.intelligence.risk_scoring.models import (
    RiskScoringConfig,
    RiskStatistics,
    RiskAssessment
)
from ai_engine.intelligence.risk_scoring.result import RiskScoringResult
from ai_engine.intelligence.risk_scoring.scoring_strategy import (
    ScoringStrategyInterface,
    DefaultScoringStrategy
)
from ai_engine.intelligence.risk_scoring.exceptions import RiskScoringError

logger = logging.getLogger(__name__)

class RiskScoringProcessor(RiskScoringProcessorInterface):
    """
    Converts triggered rule results into an overall examination risk assessment.
    """
    
    def __init__(self, config: RiskScoringConfig, strategy: Optional[ScoringStrategyInterface] = None) -> None:
        super().__init__(config)
        self._strategy = strategy or DefaultScoringStrategy()
        self._initialized = False
        self._statistics = RiskStatistics()

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing RiskScoringProcessor...")
        if not self._config.rule_weights or not self._config.risk_thresholds:
            raise RiskScoringError("Invalid configuration: rule_weights and risk_thresholds must be provided.")
        self._initialized = True
        self._statistics = RiskStatistics()
        if self._config.enable_logging:
            logger.debug("RiskScoringProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise RiskScoringError("Cannot start uninitialized RiskScoringProcessor.")
        if self._config.enable_logging:
            logger.debug("RiskScoringProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("RiskScoringProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up RiskScoringProcessor...")
        self._initialized = False
        self._statistics = RiskStatistics()

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise RiskScoringError("RiskScoringProcessor is not initialized.")
            
        if not hasattr(context, "rule_results") or context.rule_results is None:
            if self._config.enable_logging:
                logger.warning("No rule_results found in context. Skipping risk scoring.")
            # Emit a default zero-risk result to fulfill contract
            empty_assessment = RiskAssessment(
                overall_score=0.0,
                risk_level="NORMAL",
                contributions=[],
                triggered_rule_count=0,
                highest_priority_rule_id="NONE",
                weighted_score_breakdown={},
                processing_timestamp=0.0,
                processing_duration=0.0
            )
            setattr(context, "risk_assessment", empty_assessment)
            return

        evaluations = context.rule_results.evaluations
        
        try:
            assessment = self._strategy.calculate_score(evaluations, self._config)
            
            # Update telemetry
            self._statistics.total_assessments += 1
            n = self._statistics.total_assessments
            current_avg = self._statistics.average_score
            self._statistics.average_score = ((current_avg * (n - 1)) + assessment.overall_score) / n
            
            # Attach to context
            setattr(context, "risk_assessment", assessment)
            
            if self._config.enable_logging:
                logger.info(f"Risk Assessment: {assessment.overall_score:.2f} ({assessment.risk_level}). Triggered rules: {assessment.triggered_rule_count}")
                
        except Exception as e:
            if isinstance(e, RiskScoringError):
                raise
            raise RiskScoringError(f"Failed to calculate risk score: {e}") from e
