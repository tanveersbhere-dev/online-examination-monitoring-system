from dataclasses import dataclass, field
from typing import List, Dict

from ai_engine.core.enums import DetectedObjectType

@dataclass
class ObjectDetectionConfig:
    """
    Configuration for the Object Detector.
    
    Attributes:
        confidence_threshold: Minimum confidence [0.0, 1.0] for an object to be reported.
        iou_threshold: Intersection over Union threshold for Non-Maximum Suppression.
        max_detections: Maximum number of objects to detect in a single frame.
        enabled_classes: List of object types to detect and report.
        model_path: Path or name of the offline model file (e.g., yolo11n.pt).
        device: Device to use for inference ("cpu").
        enable_logging: Emit diagnostics at DEBUG level.
    """
    confidence_threshold: float = 0.22
    iou_threshold: float = 0.45
    max_detections: int = 100
    enabled_classes: List[DetectedObjectType] = field(default_factory=lambda: [
        DetectedObjectType.PERSON,
        DetectedObjectType.CELL_PHONE,
        DetectedObjectType.LAPTOP,
        DetectedObjectType.TABLET,
        DetectedObjectType.SMARTWATCH,
        DetectedObjectType.HEADPHONES,
        DetectedObjectType.EARBUDS,
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
    model_path: str = "yolov8n.pt"
    fused_model_path: str = "models/yoloe/fused_laptop_material_model.pt"
    fused_confidence_threshold: float = 0.25
    unauthorized_material_confidence_threshold: float = 0.9
    device: str = "cpu"
    enable_logging: bool = True
