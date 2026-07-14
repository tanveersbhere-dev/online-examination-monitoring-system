"""
MediaPipe implementation of the Mouth Aspect Ratio (MAR) Feature module.

Calculates the MAR using inner lip landmarks provided by the face mesh.
"""
import logging
import time
import math
from typing import List, Optional, Tuple

from ai_engine.core.exam_context import ExamContext, MouthInfo
from ai_engine.features.mouth_aspect_ratio.processor import MouthAspectRatioProcessor
from ai_engine.features.mouth_aspect_ratio.exceptions import (
    MARProcessorStateError,
    InvalidMouthLandmarksError,
    MARProcessorError,
)
from ai_engine.features.mouth_aspect_ratio.models import (
    MOUTH_LEFT_CORNER_INDEX,
    MOUTH_RIGHT_CORNER_INDEX,
    MOUTH_UPPER_INNER_INDICES,
    MOUTH_LOWER_INNER_INDICES,
    REQUIRED_MOUTH_INDICES,
    MARConfig,
)
from ai_engine.features.mouth_aspect_ratio.result import MouthGeometry, MARResult

logger = logging.getLogger("ai_engine.features.mouth_aspect_ratio")


def _euclidean_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


class MediaPipeMARProcessor(MouthAspectRatioProcessor):
    """
    Concrete MAR processor using MediaPipe face mesh landmarks.
    """

    def __init__(self, config: Optional[MARConfig] = None) -> None:
        super().__init__(config=config or MARConfig())
        self._initialized: bool = False
        self._running: bool = False

    def initialize(self) -> None:
        if self._initialized:
            logger.debug("MediaPipeMARProcessor already initialized.")
            return

        logger.info("Initializing MediaPipeMARProcessor...")
        self._initialized = True
        logger.info("MediaPipeMARProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise MARProcessorStateError("Call initialize() before start().")
        self._running = True
        logger.info("MediaPipeMARProcessor started.")

    def process(self, context: ExamContext) -> None:
        if not self._running:
            return

        fmi = context.face_mesh_info
        if fmi.face_count == 0 or not fmi.all_face_landmarks:
            self._write_empty_to_context(context, fmi.frame_id)
            return

        try:
            result = self.extract(fmi.frame_id if fmi.frame_id is not None else 0, fmi.all_face_landmarks)
        except MARProcessorError as exc:
            logger.error(f"MAR extraction failed on frame {fmi.frame_id}: {exc}")
            return

        self._write_to_context(context, result)

    def stop(self) -> None:
        self._running = False
        logger.info("MediaPipeMARProcessor stopped.")

    def cleanup(self) -> None:
        self._running = False
        self._initialized = False
        logger.info("MediaPipeMARProcessor cleaned up.")

    def extract(
        self,
        frame_id: int,
        all_face_landmarks: List[List[Tuple[float, float, float]]]
    ) -> MARResult:
        
        if not self._initialized:
            raise MARProcessorStateError("Processor not initialized.")

        start_time = time.perf_counter()
        geometries: List[MouthGeometry] = []
        
        max_required_index = max(REQUIRED_MOUTH_INDICES)
        
        for face_idx, landmarks in enumerate(all_face_landmarks):
            if len(landmarks) <= max_required_index:
                logger.warning(
                    f"Face {face_idx} missing mouth landmarks. MAR extraction skipped."
                )
                continue

            try:
                left_corner = (landmarks[MOUTH_LEFT_CORNER_INDEX][0], landmarks[MOUTH_LEFT_CORNER_INDEX][1])
                right_corner = (landmarks[MOUTH_RIGHT_CORNER_INDEX][0], landmarks[MOUTH_RIGHT_CORNER_INDEX][1])
                
                upper_lips = [(landmarks[idx][0], landmarks[idx][1]) for idx in MOUTH_UPPER_INNER_INDICES]
                lower_lips = [(landmarks[idx][0], landmarks[idx][1]) for idx in MOUTH_LOWER_INNER_INDICES]
            except IndexError as e:
                raise InvalidMouthLandmarksError(f"Missing mouth landmarks: {e}") from e

            # Compute horizontal distance (width)
            width = _euclidean_distance_2d(left_corner, right_corner)
            
            # Compute vertical distances (heights)
            heights = []
            for u_pt, l_pt in zip(upper_lips, lower_lips):
                heights.append(_euclidean_distance_2d(u_pt, l_pt))
                
            avg_height = sum(heights) / len(heights) if heights else 0.0
            
            # Compute MAR
            if width > 1e-6:
                mar = avg_height / width
            else:
                mar = 0.0
                
            # Compute Mouth Center
            cx = (left_corner[0] + right_corner[0]) / 2.0
            cy = (left_corner[1] + right_corner[1]) / 2.0
            
            geometries.append(MouthGeometry(
                mar=mar,
                mouth_width=width,
                mouth_height=avg_height,
                mouth_center=(cx, cy),
                upper_lip_points=upper_lips,
                lower_lip_points=lower_lips,
                confidence=1.0,
                face_index=face_idx
            ))

        processing_time_ms = (time.perf_counter() - start_time) * 1000.0
        
        result = MARResult(
            geometries=geometries,
            frame_id=frame_id,
            processing_timestamp=time.time(),
            processing_time_ms=processing_time_ms
        )
        
        if self._config.enable_logging:
            logger.debug(
                f"MAR | Frame={result.frame_id} | Faces={len(geometries)} | "
                f"Time={processing_time_ms:.2f}ms"
            )
            
        return result

    def _write_to_context(self, context: ExamContext, result: MARResult) -> None:
        with context.lock():
            mi = context.mouth_info
            
            primary = result.primary_geometry
            if primary:
                mi.mar = primary.mar
                mi.mouth_width = primary.mouth_width
                mi.mouth_height = primary.mouth_height
                mi.mouth_center = primary.mouth_center
                mi.upper_lip_points = primary.upper_lip_points
                mi.lower_lip_points = primary.lower_lip_points
                mi.confidence = primary.confidence
            else:
                mi.mar = 0.0
                mi.mouth_width = 0.0
                mi.mouth_height = 0.0
                mi.mouth_center = None
                mi.upper_lip_points = []
                mi.lower_lip_points = []
                mi.confidence = 0.0
                
            mi.processing_timestamp = result.processing_timestamp
            mi.processing_time_ms = result.processing_time_ms
            mi.frame_id = result.frame_id
            
            context.mouth_info = mi

    def _write_empty_to_context(self, context: ExamContext, frame_id: Optional[int]) -> None:
        with context.lock():
            mi = context.mouth_info
            mi.mar = 0.0
            mi.mouth_width = 0.0
            mi.mouth_height = 0.0
            mi.mouth_center = None
            mi.upper_lip_points = []
            mi.lower_lip_points = []
            mi.confidence = 0.0
            
            mi.frame_id = frame_id
            mi.processing_timestamp = time.time()
            mi.processing_time_ms = 0.0
            context.mouth_info = mi
