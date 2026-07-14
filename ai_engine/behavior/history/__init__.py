"""
Behavior History Feature Module.

Responsible ONLY for maintaining temporal behavioral history and generating summary statistics.
"""
from ai_engine.behavior.history.exceptions import BehaviorHistoryError, RollingWindowError, HistoryOverflowError
from ai_engine.behavior.history.models import BehaviorHistoryConfig
from ai_engine.behavior.history.rolling_window import RollingWindow
from ai_engine.behavior.history.result import BehaviorSummary, BehaviorHistoryResult
from ai_engine.behavior.history.processor import BehaviorHistoryProcessor
from ai_engine.behavior.history.temporal_history import TemporalHistoryProcessor

__all__ = [
    "BehaviorHistoryError",
    "RollingWindowError",
    "HistoryOverflowError",
    "BehaviorHistoryConfig",
    "RollingWindow",
    "BehaviorSummary",
    "BehaviorHistoryResult",
    "BehaviorHistoryProcessor",
    "TemporalHistoryProcessor"
]
