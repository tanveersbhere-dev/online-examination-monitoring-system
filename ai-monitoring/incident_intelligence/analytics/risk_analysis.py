"""
RiskAnalysis Model and DTO for IIAE.
Computes risk trajectory, velocity (dR/dt), escalation/recovery counters, and stability rating.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
import math

@dataclass(frozen=True)
class RiskAnalysis:
    """Immutable risk trajectory analysis."""
    current_risk: float
    peak_risk: float
    average_risk: float
    risk_escalation_count: int
    risk_recovery_count: int
    risk_velocity: float
    risk_stability: float  # 0.0 (highly unstable) to 1.0 (highly stable)

    def to_dto(self) -> 'RiskAnalysisDTO':
        return RiskAnalysisDTO(
            current_risk=self.current_risk,
            peak_risk=self.peak_risk,
            average_risk=self.average_risk,
            risk_escalation_count=self.risk_escalation_count,
            risk_recovery_count=self.risk_recovery_count,
            risk_velocity=self.risk_velocity,
            risk_stability=self.risk_stability
        )

@dataclass(frozen=True)
class RiskAnalysisDTO:
    """Data Transfer Object for RiskAnalysis."""
    current_risk: float
    peak_risk: float
    average_risk: float
    risk_escalation_count: int
    risk_recovery_count: int
    risk_velocity: float
    risk_stability: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def analyze_risk_stream(risk_values: List[float], time_stamps: List[float]) -> RiskAnalysis:
    """Analyze risk values and timestamps to compute risk velocity and stability."""
    if not risk_values:
        return RiskAnalysis(0.0, 0.0, 0.0, 0, 0, 0.0, 1.0)

    current_risk = risk_values[-1]
    peak_risk = max(risk_values)
    avg_risk = sum(risk_values) / len(risk_values)

    escalations = 0
    recoveries = 0

    for i in range(1, len(risk_values)):
        if risk_values[i] > risk_values[i - 1]:
            escalations += 1
        elif risk_values[i] < risk_values[i - 1]:
            recoveries += 1

    # Velocity (dR/dt)
    n = len(risk_values)
    if n >= 2 and len(time_stamps) == n and time_stamps[-1] > time_stamps[0]:
        dt = time_stamps[-1] - time_stamps[0]
        dR = risk_values[-1] - risk_values[0]
        velocity = dR / dt
    else:
        velocity = 0.0

    # Risk Stability (1.0 - normalized variance)
    variance = sum((r - avg_risk) ** 2 for r in risk_values) / max(1, n)
    std_dev = math.sqrt(variance)
    stability = max(0.0, min(1.0, 1.0 - (std_dev / 50.0)))

    return RiskAnalysis(
        current_risk=round(current_risk, 2),
        peak_risk=round(peak_risk, 2),
        average_risk=round(avg_risk, 2),
        risk_escalation_count=escalations,
        risk_recovery_count=recoveries,
        risk_velocity=round(velocity, 2),
        risk_stability=round(stability, 4)
    )
