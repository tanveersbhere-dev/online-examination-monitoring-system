"""
ConfidenceAnalysis Model and DTO for IIAE.
Computes statistical measures (mean, median, std_dev, slope, trend) over confidence history.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
import math

@dataclass(frozen=True)
class ConfidenceAnalysis:
    """Immutable statistical analysis of confidence trajectory."""
    current: float
    peak: float
    average: float
    median: float
    std_dev: float
    slope: float
    trend: str  # STABLE, INCREMENTAL, DECREMENTAL, VOLATILE

    def to_dto(self) -> 'ConfidenceAnalysisDTO':
        return ConfidenceAnalysisDTO(
            current=self.current,
            peak=self.peak,
            average=self.average,
            median=self.median,
            std_dev=self.std_dev,
            slope=self.slope,
            trend=self.trend
        )

@dataclass(frozen=True)
class ConfidenceAnalysisDTO:
    """Data Transfer Object for ConfidenceAnalysis."""
    current: float
    peak: float
    average: float
    median: float
    std_dev: float
    slope: float
    trend: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def analyze_confidence_stream(confidence_values: List[float], time_stamps: List[float]) -> ConfidenceAnalysis:
    """Compute statistical metrics over confidence values and timestamps."""
    if not confidence_values:
        return ConfidenceAnalysis(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "STABLE")

    current = confidence_values[-1]
    peak = max(confidence_values)
    avg = sum(confidence_values) / len(confidence_values)

    # Median
    sorted_vals = sorted(confidence_values)
    n = len(sorted_vals)
    if n % 2 == 1:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    # Standard Deviation
    variance = sum((x - avg) ** 2 for x in confidence_values) / max(1, n)
    std_dev = math.sqrt(variance)

    # Linear Regression Slope (dy/dt)
    if n >= 2 and len(time_stamps) == n and time_stamps[-1] > time_stamps[0]:
        dt = time_stamps[-1] - time_stamps[0]
        dy = confidence_values[-1] - confidence_values[0]
        slope = dy / dt
    else:
        slope = 0.0

    # Determine Trend Category
    if std_dev > 0.25:
        trend = "VOLATILE"
    elif slope > 0.02:
        trend = "INCREMENTAL"
    elif slope < -0.02:
        trend = "DECREMENTAL"
    else:
        trend = "STABLE"

    return ConfidenceAnalysis(
        current=round(current, 4),
        peak=round(peak, 4),
        average=round(avg, 4),
        median=round(median, 4),
        std_dev=round(std_dev, 4),
        slope=round(slope, 4),
        trend=trend
    )
