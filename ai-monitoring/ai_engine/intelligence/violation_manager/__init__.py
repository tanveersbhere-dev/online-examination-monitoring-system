"""Violation Manager Module."""
from ai_engine.intelligence.violation_manager.models import (
    ViolationManagerConfig,
    Violation,
    ViolationTimeline,
    ViolationStatistics,
    LifecycleEvent,
)
from ai_engine.intelligence.violation_manager.result import ViolationManagerResult
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from ai_engine.intelligence.violation_manager.processor import ViolationManagerProcessorInterface
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.exceptions import (
    ViolationManagerError,
    ViolationCreationError,
    ViolationMergeError,
    ViolationStateError,
)

__all__ = [
    "ViolationManagerConfig",
    "Violation",
    "ViolationTimeline",
    "ViolationStatistics",
    "LifecycleEvent",
    "ViolationManagerResult",
    "ViolationTimelineManager",
    "ViolationManagerProcessorInterface",
    "ViolationManagerProcessor",
    "ViolationManagerError",
    "ViolationCreationError",
    "ViolationMergeError",
    "ViolationStateError",
]

