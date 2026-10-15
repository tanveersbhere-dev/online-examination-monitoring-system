"""
BehaviorAnalysis Model and DTO for IIAE.
Aggregates triggered rules, composite behaviors, recurrence rates, and persistence durations.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass(frozen=True)
class BehaviorAnalysis:
    """Immutable behavioral aggregation analytics."""
    triggered_rules_frequency: Dict[str, int] = field(default_factory=dict)
    composite_frequency: Dict[str, int] = field(default_factory=dict)
    behavior_recurrence_count: int = 0
    behavior_persistence_seconds: float = 0.0

    def to_dto(self) -> 'BehaviorAnalysisDTO':
        return BehaviorAnalysisDTO(
            triggered_rules_frequency=dict(self.triggered_rules_frequency),
            composite_frequency=dict(self.composite_frequency),
            behavior_recurrence_count=self.behavior_recurrence_count,
            behavior_persistence_seconds=self.behavior_persistence_seconds
        )

@dataclass(frozen=True)
class BehaviorAnalysisDTO:
    """Data Transfer Object for BehaviorAnalysis."""
    triggered_rules_frequency: Dict[str, int]
    composite_frequency: Dict[str, int]
    behavior_recurrence_count: int
    behavior_persistence_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
