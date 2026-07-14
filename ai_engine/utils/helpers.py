import time
import uuid
from typing import Tuple

def get_current_timestamp() -> float:
    """Returns the current Unix epoch time in seconds."""
    return time.time()

def generate_uuid() -> str:
    """Generates a standard UUID version 4 string."""
    return str(uuid.uuid4())

def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """Parses a resolution string like '1280x720' into a tuple of integers (width, height)."""
    try:
        parts = resolution_str.lower().split("x")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    raise ValueError(f"Invalid resolution format: {resolution_str}. Expected format 'WIDTHxHEIGHT' (e.g. '640x480').")
