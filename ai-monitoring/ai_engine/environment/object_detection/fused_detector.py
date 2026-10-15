"""
Fused Laptop and Unauthorized-Material YOLO Detector.
Authoritative detector for class 0 (unauthorized_material) and class 1 (laptop).
"""
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, DetectedObject, BoundingBox
from ai_engine.environment.object_detection.detector import ObjectDetectorInterface
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.exceptions import (
    ObjectDetectionError,
    ModelLoadError,
    InferenceError,
    InvalidFrameError,
)

logger = logging.getLogger(__name__)

EXPECTED_CLASSES: Dict[int, str] = {
    0: "unauthorized_material",
    1: "laptop",
}


def resolve_fused_checkpoint_path(path: Union[str, Path]) -> Path:
    """
    Resolves checkpoint path relative to project root or current working directory.
    Guarantees portable resolution without hardcoded absolute user paths.
    """
    p = Path(path)
    if p.is_file():
        return p.resolve()

    # Try relative to cwd
    cwd_path = Path.cwd() / p
    if cwd_path.is_file():
        return cwd_path.resolve()

    # Try relative to ai_engine directory structure (project root is 4 levels up from this file)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    root_path = project_root / p
    if root_path.is_file():
        return root_path.resolve()

    # Also check under models/yoloe directly
    direct_model = project_root / "models" / "yoloe" / p.name
    if direct_model.is_file():
        return direct_model.resolve()

    return p


class FusedLaptopMaterialDetector(ObjectDetectorInterface):
    """
    Authoritative YOLO detector for:
      - Class 0: unauthorized_material (books, notebooks, papers, loose sheets)
      - Class 1: laptop

    Loads fused_laptop_material_model.pt once at initialization and reuses it across frames.
    Suppresses fallback branches and fails explicitly if checkpoint is missing or invalid.
    """

    CLASS_MAP: Dict[int, DetectedObjectType] = {
        0: DetectedObjectType.UNAUTHORIZED_MATERIAL,
        1: DetectedObjectType.LAPTOP,
    }

    def __init__(
        self,
        config: Optional[ObjectDetectionConfig] = None,
        model_path: Optional[Union[str, Path]] = None,
        confidence_threshold: Optional[float] = None,
    ) -> None:
        cfg = config or ObjectDetectionConfig()
        super().__init__(cfg)
        self.model_path = model_path or getattr(cfg, "fused_model_path", "models/yoloe/fused_laptop_material_model.pt")
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(cfg, "fused_confidence_threshold", 0.25)
        )
        self.device = cfg.device
        self.material_confidence_threshold = getattr(cfg, "unauthorized_material_confidence_threshold", 0.9)
        self.iou_threshold = cfg.iou_threshold
        self.max_detections = cfg.max_detections
        self.enable_logging = cfg.enable_logging

        self._initialized = False
        self._model = None
        self._inference_lock = threading.Lock()
        self.resolved_checkpoint_path: Optional[Path] = None

    def initialize(self) -> None:
        """
        Loads the fused checkpoint once.
        Verifies checkpoint existence and validates exact class schema.
        Raises ModelLoadError on missing file or class mismatch.
        """
        if self.enable_logging:
            logger.debug(f"[FusedDetector] Initializing with checkpoint: {self.model_path}")

        resolved = resolve_fused_checkpoint_path(self.model_path)
        self.resolved_checkpoint_path = resolved

        if not resolved.is_file():
            raise ModelLoadError(
                f"Fused laptop/material model checkpoint not found at: {resolved}. "
                f"Expected checkpoint: {self.model_path}"
            )

        try:
            from ultralytics import YOLO

            model = YOLO(str(resolved))

            # Validate exact class schema: {0: 'unauthorized_material', 1: 'laptop'}
            actual_classes = getattr(model, "names", {})
            if isinstance(actual_classes, dict):
                cls_0 = actual_classes.get(0, "").lower()
                cls_1 = actual_classes.get(1, "").lower()
                if "unauthorized_material" not in cls_0 or "laptop" not in cls_1:
                    raise ModelLoadError(
                        f"Incompatible fused model classes at {resolved}. "
                        f"Expected {EXPECTED_CLASSES}, got {actual_classes}"
                    )
            else:
                raise ModelLoadError(f"Unexpected model class format: {actual_classes}")

            model.to(self.device)
            self._model = model
            self._initialized = True

            logger.info(
                f"[FusedDetector] Successfully loaded fused checkpoint from {resolved}. "
                f"Classes: {self._model.names}, conf={self.confidence_threshold:.2f}, "
                f"material_conf={self.material_confidence_threshold:.2f}, device={self.device}"
            )

        except ModelLoadError:
            self._model = None
            self._initialized = False
            raise
        except Exception as e:
            self._model = None
            self._initialized = False
            raise ModelLoadError(f"Failed to load fused YOLO model from {resolved}: {e}") from e

    def start(self) -> None:
        if not self._initialized:
            raise ObjectDetectionError("Cannot start uninitialized FusedLaptopMaterialDetector.")
        if self.enable_logging:
            logger.debug("[FusedDetector] Started.")

    def stop(self) -> None:
        if self.enable_logging:
            logger.debug("[FusedDetector] Stopped.")

    def cleanup(self) -> None:
        if self.enable_logging:
            logger.debug("[FusedDetector] Cleaning up...")
        self._initialized = False
        self._model = None

    def process(self, context: ExamContext) -> None:
        """
        Reads context.current_frame and appends normalized detections
        (unauthorized_material and laptop) to context.object_info.current_detections.
        """
        if not self._initialized or self._model is None:
            raise ObjectDetectionError("FusedLaptopMaterialDetector is not initialized or model unavailable.")

        frame = getattr(context, "current_frame", None)
        if frame is None or getattr(frame, "original_frame", None) is None:
            raise InvalidFrameError("Current frame is empty or invalid.")

        frame_data = frame.original_frame

        start_time = time.perf_counter()
        detected_objects: List[DetectedObject] = []

        try:
            with self._inference_lock:
                results = self._model.predict(
                    source=frame_data,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    max_det=self.max_detections,
                    verbose=False,
                )

            if results and len(results) > 0:
                result = results[0]
                if hasattr(result, "boxes") and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confs = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy()

                    for i in range(len(boxes)):
                        conf = float(confs[i])
                        cls_id = int(class_ids[i])
                        obj_type = self._map_class_id(cls_id)

                        if obj_type != DetectedObjectType.UNKNOWN:
                            if obj_type == DetectedObjectType.UNAUTHORIZED_MATERIAL and conf < getattr(self, "material_confidence_threshold", 0.9):
                                continue
                            x1, y1, x2, y2 = boxes[i]
                            bbox = BoundingBox(
                                x=float(x1),
                                y=float(y1),
                                width=float(max(0.0, x2 - x1)),
                                height=float(max(0.0, y2 - y1)),
                            )
                            detected_objects.append(
                                DetectedObject(
                                    object_type=obj_type,
                                    confidence=conf,
                                    bbox=bbox,
                                )
                            )

            proc_time_ms = (time.perf_counter() - start_time) * 1000.0

            # Append fused detections to current_detections in ExamContext
            object_info = context.object_info
            existing = getattr(object_info, "current_detections", None) or []
            object_info.current_detections = list(existing) + detected_objects
            object_info.total_object_count = len(object_info.current_detections)
            object_info.timestamp = getattr(frame, "timestamp", time.time())
            object_info.frame_id = getattr(frame, "frame_id", 0)
            object_info.processing_time_ms = getattr(object_info, "processing_time_ms", 0.0) + proc_time_ms
            context.object_info = object_info

            if detected_objects and self.enable_logging:
                logger.debug(
                    f"[FusedDetector] Frame {frame.frame_id}: Detected {len(detected_objects)} "
                    f"targets in {proc_time_ms:.2f}ms"
                )

        except Exception as e:
            if isinstance(e, (ObjectDetectionError, InvalidFrameError)):
                raise
            raise InferenceError(f"Error during fused YOLO inference: {e}") from e

    def _map_class_id(self, class_id: int) -> DetectedObjectType:
        """Maps fused model class IDs to DetectedObjectType enum."""
        return self.CLASS_MAP.get(class_id, DetectedObjectType.UNKNOWN)

