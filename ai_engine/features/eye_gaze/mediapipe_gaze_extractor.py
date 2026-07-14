"""
MediaPipe implementation of Eye Gaze Feature Extraction.

Calculates eye gaze vectors based on the relative position of the iris center
compared to the eye corners.
"""
import logging
import time
from typing import List, Optional, Tuple
import math

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, EyeInfo
from ai_engine.features.eye_gaze.extractor import EyeGazeExtractorInterface
from ai_engine.features.eye_gaze.exceptions import (
    EyeGazeStateError,
    EyeTrackingError,
    InvalidIrisLandmarksError,
)
from ai_engine.features.eye_gaze.models import (
    LEFT_IRIS_CENTER_INDEX,
    RIGHT_IRIS_CENTER_INDEX,
    LEFT_EYE_LEFT_CORNER_INDEX,
    LEFT_EYE_RIGHT_CORNER_INDEX,
    RIGHT_EYE_LEFT_CORNER_INDEX,
    RIGHT_EYE_RIGHT_CORNER_INDEX,
    EyeGazeConfig,
)
from ai_engine.features.eye_gaze.result import EyeCenter, IrisCenter, EyeGaze, EyeGazeResult

logger = logging.getLogger("ai_engine.features.eye_gaze")


def _calculate_gaze_vector(
    left_corner: Tuple[float, float, float],
    right_corner: Tuple[float, float, float],
    iris_center: Tuple[float, float, float]
) -> Tuple[Tuple[float, float, float], Tuple[float, float]]:
    """
    Computes the gaze vector and the 2D eye center.
    """
    # 3D Eye Center
    cx = (left_corner[0] + right_corner[0]) / 2.0
    cy = (left_corner[1] + right_corner[1]) / 2.0
    cz = (left_corner[2] + right_corner[2]) / 2.0
    
    # Vector from center to iris
    dx = iris_center[0] - cx
    dy = iris_center[1] - cy
    dz = iris_center[2] - cz
    
    # Normalize
    norm = math.sqrt(dx*dx + dy*dy + dz*dz)
    if norm > 1e-6:
        dx /= norm
        dy /= norm
        dz /= norm
    else:
        dx, dy, dz = 0.0, 0.0, 1.0  # Default forward
        
    return (dx, dy, dz), (cx, cy)


class MediaPipeEyeGazeExtractor(EyeGazeExtractorInterface):
    """
    Concrete eye gaze extractor using MediaPipe face mesh landmarks.
    """

    def __init__(self, config: Optional[EyeGazeConfig] = None) -> None:
        super().__init__(config=config or EyeGazeConfig())
        self._initialized: bool = False
        self._running: bool = False

    def initialize(self) -> None:
        if self._initialized:
            logger.debug("MediaPipeEyeGazeExtractor already initialized.")
            return

        logger.info("Initializing MediaPipeEyeGazeExtractor...")
        self._initialized = True
        logger.info("MediaPipeEyeGazeExtractor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise EyeGazeStateError("Call initialize() before start().")
        self._running = True
        logger.info("MediaPipeEyeGazeExtractor started.")

    def process(self, context: ExamContext) -> None:
        if not self._running:
            return

        frame = context.current_frame
        if frame is None:
            return

        fmi = context.face_mesh_info
        if fmi.face_count == 0 or not fmi.all_face_landmarks:
            self._write_empty_to_context(context, frame)
            return

        try:
            result = self.extract(frame, fmi.all_face_landmarks)
        except EyeTrackingError as exc:
            logger.error(f"Eye gaze extraction failed on frame {frame.frame_id}: {exc}")
            return

        self._write_to_context(context, result)

    def stop(self) -> None:
        self._running = False
        logger.info("MediaPipeEyeGazeExtractor stopped.")

    def cleanup(self) -> None:
        self._running = False
        self._initialized = False
        logger.info("MediaPipeEyeGazeExtractor cleaned up.")

    def extract(
        self,
        frame: Frame,
        all_face_landmarks: List[List[Tuple[float, float, float]]]
    ) -> EyeGazeResult:
        
        if not self._initialized:
            raise EyeGazeStateError("Extractor not initialized.")

        start_time = time.perf_counter()
        gazes: List[EyeGaze] = []
        
        max_required_index = max(
            LEFT_IRIS_CENTER_INDEX, RIGHT_IRIS_CENTER_INDEX,
            LEFT_EYE_LEFT_CORNER_INDEX, LEFT_EYE_RIGHT_CORNER_INDEX,
            RIGHT_EYE_LEFT_CORNER_INDEX, RIGHT_EYE_RIGHT_CORNER_INDEX
        )
        
        for face_idx, landmarks in enumerate(all_face_landmarks):
            if len(landmarks) <= max_required_index:
                logger.warning(
                    f"Face {face_idx} missing iris landmarks. Gaze extraction skipped."
                )
                continue

            try:
                l_iris = landmarks[LEFT_IRIS_CENTER_INDEX]
                l_left_c = landmarks[LEFT_EYE_LEFT_CORNER_INDEX]
                l_right_c = landmarks[LEFT_EYE_RIGHT_CORNER_INDEX]
                
                r_iris = landmarks[RIGHT_IRIS_CENTER_INDEX]
                r_left_c = landmarks[RIGHT_EYE_LEFT_CORNER_INDEX]
                r_right_c = landmarks[RIGHT_EYE_RIGHT_CORNER_INDEX]
            except IndexError as e:
                raise InvalidIrisLandmarksError(f"Missing eye landmarks: {e}") from e

            # Compute vectors
            left_vec, left_center_2d = _calculate_gaze_vector(l_left_c, l_right_c, l_iris)
            right_vec, right_center_2d = _calculate_gaze_vector(r_left_c, r_right_c, r_iris)
            
            # Combined vector (average)
            cx = (left_vec[0] + right_vec[0]) / 2.0
            cy = (left_vec[1] + right_vec[1]) / 2.0
            cz = (left_vec[2] + right_vec[2]) / 2.0
            norm = math.sqrt(cx*cx + cy*cy + cz*cz)
            if norm > 1e-6:
                comb_vec = (cx/norm, cy/norm, cz/norm)
            else:
                comb_vec = (0.0, 0.0, 1.0)
                
            gazes.append(EyeGaze(
                left_gaze_vector=left_vec,
                right_gaze_vector=right_vec,
                combined_gaze_vector=comb_vec,
                left_iris_center=IrisCenter(x=l_iris[0], y=l_iris[1]),
                right_iris_center=IrisCenter(x=r_iris[0], y=r_iris[1]),
                left_eye_center=EyeCenter(x=left_center_2d[0], y=left_center_2d[1]),
                right_eye_center=EyeCenter(x=right_center_2d[0], y=right_center_2d[1]),
                confidence=1.0,  # Based on landmark presence if available
                face_index=face_idx
            ))

        processing_time_ms = (time.perf_counter() - start_time) * 1000.0
        
        result = EyeGazeResult(
            gazes=gazes,
            frame_id=frame.frame_id if frame else None,
            processing_timestamp=time.time(),
            processing_time_ms=processing_time_ms
        )
        
        if self._config.enable_logging:
            logger.debug(
                f"EyeGaze | Frame={result.frame_id} | Faces={len(gazes)} | "
                f"Time={processing_time_ms:.2f}ms"
            )
            
        return result

    def _write_to_context(self, context: ExamContext, result: EyeGazeResult) -> None:
        with context.lock():
            ei = context.eye_info
            
            primary = result.primary_gaze
            if primary:
                ei.gaze_left = primary.left_gaze_vector
                ei.gaze_right = primary.right_gaze_vector
                ei.combined_gaze = primary.combined_gaze_vector
                
                ei.left_iris_center = (primary.left_iris_center.x, primary.left_iris_center.y) if primary.left_iris_center else None
                ei.right_iris_center = (primary.right_iris_center.x, primary.right_iris_center.y) if primary.right_iris_center else None
                ei.left_eye_center = (primary.left_eye_center.x, primary.left_eye_center.y) if primary.left_eye_center else None
                ei.right_eye_center = (primary.right_eye_center.x, primary.right_eye_center.y) if primary.right_eye_center else None
                
                ei.gaze_confidence = primary.confidence
            else:
                ei.gaze_left = (0.0, 0.0, 0.0)
                ei.gaze_right = (0.0, 0.0, 0.0)
                ei.combined_gaze = (0.0, 0.0, 0.0)
                ei.left_iris_center = None
                ei.right_iris_center = None
                ei.left_eye_center = None
                ei.right_eye_center = None
                ei.gaze_confidence = 0.0
                
            ei.processing_timestamp = result.processing_timestamp
            ei.processing_time_ms = result.processing_time_ms
            ei.frame_id = result.frame_id
            
            context.eye_info = ei

    def _write_empty_to_context(self, context: ExamContext, frame: Frame) -> None:
        with context.lock():
            # Only reset the fields managed by this module
            ei = context.eye_info
            ei.gaze_left = (0.0, 0.0, 0.0)
            ei.gaze_right = (0.0, 0.0, 0.0)
            ei.combined_gaze = (0.0, 0.0, 0.0)
            ei.left_iris_center = None
            ei.right_iris_center = None
            ei.left_eye_center = None
            ei.right_eye_center = None
            ei.gaze_confidence = 0.0
            
            ei.frame_id = frame.frame_id if frame else None
            ei.processing_timestamp = time.time()
            ei.processing_time_ms = 0.0
            context.eye_info = ei
