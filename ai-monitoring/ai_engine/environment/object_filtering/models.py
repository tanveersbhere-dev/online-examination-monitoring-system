"""
Model configuration for the Object Filtering Feature.
"""
from dataclasses import dataclass, field
from typing import List

from ai_engine.core.enums import DetectedObjectType

@dataclass
class ObjectFilteringConfig:
    """
    Configuration for the Object Filtering Processor.
    
    Attributes:
        min_confidence: Minimum confidence required to keep an object.
        supported_classes: List of object types that pass the filter.
        max_objects: Maximum number of objects to keep per frame (after sorting by confidence).
        iou_threshold: IoU threshold for duplicate removal (NMS).
        duplicate_filtering_enabled: Whether to apply duplicate removal.
        enable_logging: Emit diagnostics at DEBUG level.
    """
    min_confidence: float = 0.22
    supported_classes: List[DetectedObjectType] = field(default_factory=lambda: [
        DetectedObjectType.PERSON,
        DetectedObjectType.CELL_PHONE,
        DetectedObjectType.LAPTOP,
        DetectedObjectType.TABLET,
        DetectedObjectType.SMARTWATCH,
        DetectedObjectType.HEADPHONES,
        DetectedObjectType.EARBUDS,
        DetectedObjectType.EARPHONES,
        DetectedObjectType.WIRED_HANDSFREE,
        DetectedObjectType.HEADSET,
        DetectedObjectType.NECKBAND,
        DetectedObjectType.COMM_EARPHONES,
        DetectedObjectType.BOOK,
        DetectedObjectType.NOTEBOOK,
        DetectedObjectType.REGISTER,
        DetectedObjectType.PAPER,
        DetectedObjectType.UNAUTHORIZED_MATERIAL,
        DetectedObjectType.KEYBOARD,
        DetectedObjectType.MOUSE,
        DetectedObjectType.MONITOR
    ])
    max_objects: int = 20
    iou_threshold: float = 0.50
    duplicate_filtering_enabled: bool = True
    enable_logging: bool = True
