import time
import logging
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger("ai_engine.utils")

class Timer:
    """Context manager to measure execution time of a code block."""
    def __init__(self, name: str = "Block", logger_instance: Optional[logging.Logger] = None) -> None:
        self.name = name
        self.logger = logger_instance or logger
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            self.elapsed = time.perf_counter() - self.start_time
            self.logger.debug(f"{self.name} execution time: {self.elapsed * 1000:.2f} ms")

def time_function(name: Optional[str] = None, logger_instance: Optional[logging.Logger] = None) -> Callable[..., Any]:
    """Decorator to measure and log execution time of a function."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        timer_name = name or func.__name__
        log = logger_instance or logger
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                log.debug(f"Function '{timer_name}' execution time: {elapsed * 1000:.2f} ms")
        return wrapper
    return decorator
