"""
Strongly typed result objects for the Object Filtering module.
"""
from dataclasses import dataclass, field
from typing import List

from ai_engine.core.exam_context import FilteredObject, FilteringStatistics

@dataclass
class ObjectFilteringResult:
    """
    Result of the object filtering process for a single frame.
    
    Attributes:
        filtered_detections: The final list of validated and filtered objects.
        statistics: Metrics on what was accepted/rejected.
        processing_time_ms: Time taken to filter.
    """
    filtered_detections: List[FilteredObject] = field(default_factory=list)
    statistics: FilteringStatistics = field(default_factory=FilteringStatistics)
    processing_time_ms: float = 0.0
