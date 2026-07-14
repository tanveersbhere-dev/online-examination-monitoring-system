"""Exceptions for Risk Scoring Engine."""
from ai_engine.core.exceptions import AIEngineError

class RiskScoringError(AIEngineError):
    """Base exception for risk scoring errors."""
    pass

class InvalidWeightConfigurationError(RiskScoringError):
    """Raised when the rule weights are missing or invalid."""
    pass

class ScoreCalculationError(RiskScoringError):
    """Raised when score normalization or calculation fails."""
    pass
