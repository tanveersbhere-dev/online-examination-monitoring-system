"""
Strongly typed result objects for the Behavior History module.
"""
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class BehaviorSummary:
    """
    Statistical summary of a behavior over a specific rolling window.
    
    Attributes:
        mean: The arithmetic mean of the values.
        median: The median of the values.
        minimum: The minimum value.
        maximum: The maximum value.
        std_dev: The standard deviation.
        event_frequency: Count of events (e.g. blinks) in the window.
        continuous_duration: The duration the state has remained continuous.
        recent_trend: A simple trend indicator (positive = increasing, negative = decreasing, 0 = flat).
    """
    mean: float = 0.0
    median: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0
    std_dev: float = 0.0
    event_frequency: int = 0
    continuous_duration: float = 0.0
    recent_trend: float = 0.0

@dataclass
class BehaviorHistoryResult:
    """
    Result containing updated behavior summaries across all features and window sizes.
    """
    # map of feature_name -> (map of window_size -> BehaviorSummary)
    summaries: Dict[str, Dict[int, BehaviorSummary]] = field(default_factory=dict)
    processing_time_ms: float = 0.0
