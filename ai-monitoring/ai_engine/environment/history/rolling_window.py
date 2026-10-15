"""Rolling window tracking structures for Environment History Engine."""
import time
from collections import deque
from typing import Deque, Tuple, Any

class RollingWindowTimeSeries:
    """Maintains a time-series queue limited by a maximum temporal window."""
    
    def __init__(self, max_duration_seconds: float) -> None:
        self.max_duration = max_duration_seconds
        # Stores tuples of (timestamp, value)
        self._queue: Deque[Tuple[float, Any]] = deque()
        
    def add(self, timestamp: float, value: Any) -> None:
        self._queue.append((timestamp, value))
        self._cleanup(timestamp)
        
    def _cleanup(self, current_timestamp: float) -> None:
        """Removes entries older than max_duration_seconds from current_timestamp."""
        cutoff_time = current_timestamp - self.max_duration
        while self._queue and self._queue[0][0] < cutoff_time:
            self._queue.popleft()
            
    def get_max_in_window(self, current_timestamp: float, window_size: float) -> int:
        """Returns the maximum value within the specified window."""
        self._cleanup(current_timestamp)
        cutoff_time = current_timestamp - window_size
        max_val = 0
        for ts, val in self._queue:
            if ts >= cutoff_time and val > max_val:
                max_val = val
        return max_val
        
    def get_average_in_window(self, current_timestamp: float, window_size: float) -> float:
        """Returns the average value within the specified window."""
        self._cleanup(current_timestamp)
        cutoff_time = current_timestamp - window_size
        total = 0.0
        count = 0
        for ts, val in self._queue:
            if ts >= cutoff_time:
                total += val
                count += 1
        return total / count if count > 0 else 0.0

    def get_all(self):
        return list(self._queue)
