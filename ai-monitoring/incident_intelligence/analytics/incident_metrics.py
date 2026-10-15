"""
IncidentMetrics Model and DTO for IIAE.
Calculates core episode duration splits, keyframe density, and counter metrics.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class IncidentMetrics:
    """Immutable metrics object for an incident."""
    total_duration_seconds: float
    active_duration_seconds: float
    recovery_duration_seconds: float
    escalation_count: int
    recovery_count: int
    resolution_time: Optional[float]
    evidence_count: int
    evidence_density_per_minute: float
    keyframe_count: int

    def to_dto(self) -> 'IncidentMetricsDTO':
        return IncidentMetricsDTO(
            total_duration_seconds=self.total_duration_seconds,
            active_duration_seconds=self.active_duration_seconds,
            recovery_duration_seconds=self.recovery_duration_seconds,
            escalation_count=self.escalation_count,
            recovery_count=self.recovery_count,
            resolution_time=self.resolution_time,
            evidence_count=self.evidence_count,
            evidence_density_per_minute=self.evidence_density_per_minute,
            keyframe_count=self.keyframe_count
        )

@dataclass(frozen=True)
class IncidentMetricsDTO:
    """Data Transfer Object for IncidentMetrics."""
    total_duration_seconds: float
    active_duration_seconds: float
    recovery_duration_seconds: float
    escalation_count: int
    recovery_count: int
    resolution_time: Optional[float]
    evidence_count: int
    evidence_density_per_minute: float
    keyframe_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
