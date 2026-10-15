"""Environment History Engine Module."""
from ai_engine.environment.history.models import (
    HistoryConfig,
    TrackedObjectHistory,
    EnvironmentStatistics,
    EnvironmentHistory
)
from ai_engine.environment.history.result import EnvironmentHistoryResult
from ai_engine.environment.history.rolling_window import RollingWindowTimeSeries
from ai_engine.environment.history.processor import EnvironmentHistoryProcessorInterface
from ai_engine.environment.history.temporal_history import TemporalHistoryEngine
from ai_engine.environment.history.exceptions import (
    EnvironmentHistoryError,
    HistoryOverflowError,
    HistoryProcessingError,
    InvalidHistoryStateError
)

__all__ = [
    "HistoryConfig",
    "TrackedObjectHistory",
    "EnvironmentStatistics",
    "EnvironmentHistory",
    "EnvironmentHistoryResult",
    "RollingWindowTimeSeries",
    "EnvironmentHistoryProcessorInterface",
    "TemporalHistoryEngine",
    "EnvironmentHistoryError",
    "HistoryOverflowError",
    "HistoryProcessingError",
    "InvalidHistoryStateError"
]
