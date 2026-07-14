"""
Strongly typed result objects for the Object Detection Feature module.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from ai_engine.core.exam_context import DetectedObject

@dataclass
class ObjectDetectionResult:
    """
    Result of object detection for a single frame.
    
    Attributes:
        detected_objects: List of strongly typed objects detected in the frame.
        total_object_count: Total number of valid objects detected.
        processing_timestamp: Unix epoch time when processing completed.
        processing_time_ms: Time taken for inference in milliseconds.
        frame_id: The ID of the frame processed.
    """
    detected_objects: List[DetectedObject] = field(default_factory=list)
    total_object_count: int = 0
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    frame_id: Optional[int] = None
