"""
Object Filtering Feature Module (Environment Intelligence Stage 2).

Responsible ONLY for filtering and validating raw detections.
"""
from ai_engine.environment.object_filtering.exceptions import ObjectFilteringError, InvalidDetectionError, FilteringConfigurationError
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_filtering.result import ObjectFilteringResult
from ai_engine.environment.object_filtering.processor import ObjectFilteringProcessorInterface
from ai_engine.environment.object_filtering.filtering_processor import FilteringProcessor

__all__ = [
    "ObjectFilteringError",
    "InvalidDetectionError",
    "FilteringConfigurationError",
    "ObjectFilteringConfig",
    "ObjectFilteringResult",
    "ObjectFilteringProcessorInterface",
    "FilteringProcessor"
]
