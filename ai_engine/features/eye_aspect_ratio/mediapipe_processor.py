"""
MediaPipe implementation of the Eye Aspect Ratio (EAR) feature.
"""
import math
import time
import logging
from typing import List, Tuple, Optional

from ai_engine.core.exam_context import ExamContext
from ai_engine.features.eye_aspect_ratio.processor import EyeAspectRatioProcessor
from ai_engine.features.eye_aspect_ratio.models import (
    EARConfig,
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
    REQUIRED_EYE_INDICES
)
from ai_engine.features.eye_aspect_ratio.result import (
    EARResult,
    EyeGeometry,
    EyeAspectRatio
)
from ai_engine.features.eye_aspect_ratio.exceptions import (
    EARProcessorError,
    InvalidEyeLandmarksError
)

logger = logging.getLogger(__name__)


class MediaPipeEARProcessor(EyeAspectRatioProcessor):
    """
    Computes Eye Aspect Ratio (EAR) from MediaPipe Face Mesh landmarks.
    """
    
    def __init__(self, config: EARConfig) -> None:
        super().__init__(config)
        self._initialized = False

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing MediaPipeEARProcessor...")
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("MediaPipeEARProcessor initialized successfully.")

    def start(self) -> None:
        if not self._initialized:
            raise EARProcessorError("Cannot start uninitialized processor.")
        if self._config.enable_logging:
            logger.debug("MediaPipeEARProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("MediaPipeEARProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up MediaPipeEARProcessor...")
        self._initialized = False
        if self._config.enable_logging:
            logger.debug("MediaPipeEARProcessor cleaned up.")

    def process(self, context: ExamContext) -> None:
        """
        Reads face mesh info and updates eye info.
        """
        if not self._initialized:
            raise EARProcessorError("Processor is not initialized.")

        try:
            face_mesh_info = context.face_mesh_info
            
            result = self.extract(
                frame_id=face_mesh_info.frame_id,
                all_face_landmarks=face_mesh_info.all_face_landmarks
            )
            
            # Update ExamContext.eye_info (ONLY eye_info)
            eye_info = context.eye_info
            
            primary = result.primary_geometry
            if primary:
                eye_info.left_ear = primary.ear.left_ear
                eye_info.right_ear = primary.ear.right_ear
                eye_info.average_ear = primary.ear.average_ear
                eye_info.left_eye_width = primary.left_eye_width
                eye_info.left_eye_height = primary.left_eye_height
                eye_info.right_eye_width = primary.right_eye_width
                eye_info.right_eye_height = primary.right_eye_height
                eye_info.ear_confidence = primary.confidence
            else:
                # Reset to zero if no face is processed
                eye_info.left_ear = 0.0
                eye_info.right_ear = 0.0
                eye_info.average_ear = 0.0
                eye_info.left_eye_width = 0.0
                eye_info.left_eye_height = 0.0
                eye_info.right_eye_width = 0.0
                eye_info.right_eye_height = 0.0
                eye_info.ear_confidence = 0.0
            
            eye_info.processing_timestamp = result.processing_timestamp
            eye_info.processing_time_ms = result.processing_time_ms
            if result.frame_id is not None:
                eye_info.frame_id = result.frame_id
            
            context.eye_info = eye_info
            
        except EARProcessorError:
            # Let domain exceptions bubble up
            raise
        except Exception as e:
            if self._config.enable_logging:
                logger.error(f"Unexpected error in MediaPipeEARProcessor: {e}")
            raise EARProcessorError(f"Unexpected error calculating EAR: {e}") from e

    def extract(self, frame_id: Optional[int], all_face_landmarks: List[List[Tuple[float, float, float]]]) -> EARResult:
        """
        Runs the EAR calculation on the given landmarks.
        """
        start_time = time.perf_counter()
        
        geometries = []
        
        for face_idx, landmarks in enumerate(all_face_landmarks):
            if not landmarks:
                continue
                
            self._validate_landmarks(landmarks)
            
            # Extract points (we only need x, y for Euclidean distance)
            left_pts = [(landmarks[idx][0], landmarks[idx][1]) for idx in LEFT_EYE_INDICES]
            right_pts = [(landmarks[idx][0], landmarks[idx][1]) for idx in RIGHT_EYE_INDICES]
            
            # Calculate EAR for each eye
            left_ear, left_w, left_h = self._calculate_ear(left_pts)
            right_ear, right_w, right_h = self._calculate_ear(right_pts)
            avg_ear = (left_ear + right_ear) / 2.0
            
            confidence = 1.0  # MediaPipe face mesh is considered highly confident if landmarks exist
            
            ear_metrics = EyeAspectRatio(
                left_ear=left_ear,
                right_ear=right_ear,
                average_ear=avg_ear
            )
            
            geometry = EyeGeometry(
                ear=ear_metrics,
                left_eye_width=left_w,
                left_eye_height=left_h,
                right_eye_width=right_w,
                right_eye_height=right_h,
                confidence=confidence,
                face_index=face_idx
            )
            geometries.append(geometry)
        
        end_time = time.perf_counter()
        
        return EARResult(
            geometries=geometries,
            frame_id=frame_id,
            processing_timestamp=time.time(),
            processing_time_ms=(end_time - start_time) * 1000.0
        )

    def _validate_landmarks(self, landmarks: List[Tuple[float, float, float]]) -> None:
        """
        Validates that all required landmarks are present.
        """
        max_idx = max(REQUIRED_EYE_INDICES)
        if len(landmarks) <= max_idx:
            raise InvalidEyeLandmarksError(f"Insufficient landmarks: expected at least {max_idx + 1}, got {len(landmarks)}")
            
        for idx in REQUIRED_EYE_INDICES:
            point = landmarks[idx]
            if len(point) < 2:
                raise InvalidEyeLandmarksError(f"Invalid landmark at index {idx}: expected (x, y, z), got {point}")
            # Ensure coordinates are reasonable (MediaPipe yields normalized coords mostly [0,1], but could drift slightly)
            if math.isnan(point[0]) or math.isnan(point[1]):
                 raise InvalidEyeLandmarksError(f"NaN coordinate found at landmark {idx}")

    def _calculate_ear(self, pts: List[Tuple[float, float]]) -> Tuple[float, float, float]:
        """
        Calculates Eye Aspect Ratio, width, and height.
        
        Args:
            pts: List of 6 2D points: P1..P6
            
        Returns:
            Tuple containing:
            - EAR value
            - Eye width
            - Eye height
        """
        if len(pts) != 6:
            raise InvalidEyeLandmarksError("Eye landmark array must contain exactly 6 points.")
            
        p1, p2, p3, p4, p5, p6 = pts
        
        # EAR = (||P2 - P6|| + ||P3 - P5||) / (2.0 * ||P1 - P4||)
        vertical_dist1 = self._euclidean_distance(p2, p6)
        vertical_dist2 = self._euclidean_distance(p3, p5)
        horizontal_dist = self._euclidean_distance(p1, p4)
        
        if horizontal_dist == 0.0:
            return 0.0, 0.0, (vertical_dist1 + vertical_dist2) / 2.0
            
        ear = (vertical_dist1 + vertical_dist2) / (2.0 * horizontal_dist)
        
        width = horizontal_dist
        height = (vertical_dist1 + vertical_dist2) / 2.0
        
        return ear, width, height
        
    def _euclidean_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculates 2D Euclidean distance."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
