import collections
import time

class FPSTracker:
    """Calculates the rolling average frames per second (FPS) over a given window size."""
    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        self._timestamps = collections.deque(maxlen=window_size)

    def reset(self) -> None:
        """Resets the tracker timestamps."""
        self._timestamps.clear()

    def update(self) -> None:
        """Appends the current timestamp to record a new frame."""
        self._timestamps.append(time.perf_counter())

    def get_fps(self) -> float:
        """Calculates and returns the rolling FPS. Returns 0.0 if not enough data is recorded."""
        if len(self._timestamps) < 2:
            return 0.0
        
        total_time = self._timestamps[-1] - self._timestamps[0]
        if total_time <= 0:
            return 0.0
        
        return (len(self._timestamps) - 1) / total_time
