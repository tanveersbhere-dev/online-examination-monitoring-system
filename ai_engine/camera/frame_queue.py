import collections
import threading
from typing import Optional

from ai_engine.camera.frame import Frame

class FrameQueue:
    def __init__(self, max_size: int = 10) -> None:
        self.max_size = max_size
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._dropped_count = 0

    def put(self, frame: Frame) -> bool:
        """Puts a frame into the queue. Drops the oldest frame if full."""
        dropped = False
        with self._cond:
            if len(self._queue) >= self.max_size:
                try:
                    self._queue.popleft()
                except IndexError:
                    pass
                self._dropped_count += 1
                dropped = True
            self._queue.append(frame)
            self._cond.notify()
        return dropped

    def get(self, timeout: Optional[float] = None) -> Optional[Frame]:
        """Retrieves a frame from the queue. Blocks up to timeout if empty."""
        with self._cond:
            if not self._queue:
                signaled = self._cond.wait(timeout=timeout)
                if not signaled or not self._queue:
                    return None
            return self._queue.popleft()

    def clear(self) -> None:
        """Clears all frames from the queue."""
        with self._lock:
            self._queue.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_count

    def reset_dropped_count(self) -> None:
        with self._lock:
            self._dropped_count = 0
