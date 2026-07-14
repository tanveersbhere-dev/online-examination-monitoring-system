"""Result models for Rule Engine."""
from dataclasses import dataclass, field
from typing import List
from ai_engine.intelligence.rule_engine.models import RuleEvaluation, RuleStatistics

@dataclass
class RuleEngineResult:
    """Wrapper for the final results of the rule engine evaluation."""
    evaluations: List[RuleEvaluation] = field(default_factory=list)
    statistics: RuleStatistics = field(default_factory=RuleStatistics)
