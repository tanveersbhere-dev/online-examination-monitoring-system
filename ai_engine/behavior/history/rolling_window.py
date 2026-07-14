"""
Rolling window implementation for temporal data.
"""
from collections import deque
import statistics
from typing import Tuple, List, Union

from ai_engine.behavior.history.exceptions import HistoryOverflowError
from ai_engine.behavior.history.result import BehaviorSummary

class RollingWindow:
    """
    Stores a temporal sequence of values restricted by a time window.
    Supports efficient appends and time-based pruning.
    """
    def __init__(self, window_size_seconds: float, max_capacity: int):
        self._window_size_seconds = window_size_seconds
        self._max_capacity = max_capacity
        # Store tuples of (timestamp, value)
        self._data: deque[Tuple[float, Union[float, int, bool]]] = deque()
        self._last_continuous_state = None
        self._continuous_state_start = 0.0

    def append(self, timestamp: float, value: Union[float, int, bool]) -> None:
        """Appends a new value and prunes expired ones."""
        if len(self._data) >= self._max_capacity:
            # We prune before checking capacity limit
            self.prune(timestamp)
            if len(self._data) >= self._max_capacity:
                raise HistoryOverflowError(f"Rolling window capacity ({self._max_capacity}) exceeded.")
                
        self._data.append((timestamp, value))
        self.prune(timestamp)
        
        # Track continuous state for boolean/discrete variables
        if isinstance(value, bool) or isinstance(value, str):
            if value != self._last_continuous_state:
                self._last_continuous_state = value
                self._continuous_state_start = timestamp
        else:
            self._last_continuous_state = None
            self._continuous_state_start = 0.0

    def prune(self, current_timestamp: float) -> None:
        """Removes values older than current_timestamp - window_size_seconds."""
        cutoff_time = current_timestamp - self._window_size_seconds
        while self._data and self._data[0][0] < cutoff_time:
            self._data.popleft()

    def get_values(self) -> List[Union[float, int, bool]]:
        return [v for _, v in self._data]
        
    def get_timestamps(self) -> List[float]:
        return [t for t, _ in self._data]

    def calculate_statistics(self, current_timestamp: float) -> BehaviorSummary:
        """Calculates statistics for the current window."""
        self.prune(current_timestamp)
        
        if not self._data:
            return BehaviorSummary()
            
        values = self.get_values()
        
        # If boolean/string, frequency is True count. Min/Max/Mean don't apply similarly.
        # But for numeric, calculate all.
        
        summary = BehaviorSummary()
        
        # Determine if data is numeric
        is_numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)
        is_bool = all(isinstance(v, bool) for v in values)
        
        if is_numeric and len(values) > 0:
            summary.minimum = min(values)
            summary.maximum = max(values)
            summary.mean = statistics.mean(values)
            summary.median = statistics.median(values)
            if len(values) > 1:
                summary.std_dev = statistics.stdev(values)
                
            # Recent trend: simple linear diff between avg of last 10% and first 10%
            n = len(values)
            if n >= 2:
                chunk = max(1, n // 10)
                first_avg = statistics.mean(values[:chunk])
                last_avg = statistics.mean(values[-chunk:])
                summary.recent_trend = float(last_avg - first_avg)
                
        elif is_bool:
            # For boolean, frequency of True events
            summary.event_frequency = sum(1 for v in values if v)
            
        # Continuous duration for current state
        if self._last_continuous_state is not None and self._continuous_state_start > 0:
            summary.continuous_duration = current_timestamp - self._continuous_state_start
            
        return summary
