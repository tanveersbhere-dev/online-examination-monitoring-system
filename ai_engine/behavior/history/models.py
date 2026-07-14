"""
Model configuration for the Behavior History Engine.
"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class BehaviorHistoryConfig:
    """
    Configuration for the Temporal History Processor.
    
    Attributes:
        window_sizes_seconds: A list of sizes in seconds for the rolling windows.
        max_history_capacity: Maximum number of elements to store per window to prevent memory overflow.
        enable_logging: Emit diagnostics at DEBUG level.
    """
    window_sizes_seconds: List[int] = field(default_factory=lambda: [1, 5, 10, 30])
    max_history_capacity: int = 1000
    enable_logging: bool = True
