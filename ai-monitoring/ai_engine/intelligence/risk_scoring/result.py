"""Result models for Risk Scoring Engine."""
from dataclasses import dataclass, field
from ai_engine.intelligence.risk_scoring.models import RiskAssessment, RiskStatistics

@dataclass
class RiskScoringResult:
    """Wrapper for the final risk assessment."""
    assessment: RiskAssessment
    statistics: RiskStatistics = field(default_factory=RiskStatistics)
