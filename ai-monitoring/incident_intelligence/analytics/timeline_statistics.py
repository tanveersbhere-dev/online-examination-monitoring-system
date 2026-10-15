"""
TimelineStatistics Model and DTO for IIAE.
Computes time spent per state, longest active/recovery periods, and transition frequency.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass(frozen=True)
class TimelineStatistics:
    """Immutable timeline transition and state duration statistics."""
    time_in_states_seconds: Dict[str, float] = field(default_factory=dict)
    longest_active_period_seconds: float = 0.0
    longest_recovery_period_seconds: float = 0.0
    transition_count: int = 0
    transition_frequency_per_minute: float = 0.0

    def to_dto(self) -> 'TimelineStatisticsDTO':
        return TimelineStatisticsDTO(
            time_in_states_seconds=dict(self.time_in_states_seconds),
            longest_active_period_seconds=self.longest_active_period_seconds,
            longest_recovery_period_seconds=self.longest_recovery_period_seconds,
            transition_count=self.transition_count,
            transition_frequency_per_minute=self.transition_frequency_per_minute
        )

@dataclass(frozen=True)
class TimelineStatisticsDTO:
    """Data Transfer Object for TimelineStatistics."""
    time_in_states_seconds: Dict[str, float]
    longest_active_period_seconds: float
    longest_recovery_period_seconds: float
    transition_count: int
    transition_frequency_per_minute: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
