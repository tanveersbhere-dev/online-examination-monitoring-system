"""
OpenCV solvePnP implementation of Head Pose Estimation.

Uses the MediaPipe facial landmarks and a generic 3D face model to estimate
pitch, yaw, and roll via Perspective-n-Point.
"""
import logging
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, HeadPoseInfo
from ai_engine.estimators.head_pose.estimator import HeadPoseEstimatorInterface
from ai_engine.estimators.head_pose.exceptions import (
    HeadPoseEstimatorStateError,
    InvalidLandmarkError,
    PoseEstimationError,
)
from ai_engine.estimators.head_pose.models import (
    GENERIC_3D_MODEL_POINTS,
    MP_LANDMARK_INDICES,
    HeadPoseConfig,
)
from ai_engine.estimators.head_pose.result import HeadPose, HeadPoseResult

logger = logging.getLogger("ai_engine.estimators.head_pose")


class SolvePnPHeadPoseEstimator(HeadPoseEstimatorInterface):
    """
    Concrete head pose estimator using OpenCV's solvePnP.

    Extracts a subset of key landmarks (nose tip, chin, eye corners, mouth corners)
    and aligns them against a generic 3D face model to find the camera extrinsics
    (rotation and translation). Euler angles are extracted from the rotation matrix.
    """

    def __init__(self, config: Optional[HeadPoseConfig] = None) -> None:
        super().__init__(config=config or HeadPoseConfig())
        self._initialized: bool = False
        self._running: bool = False
        
        # Generic 3D model points
        self._model_points = GENERIC_3D_MODEL_POINTS
        self._landmark_indices = MP_LANDMARK_INDICES
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    def initialize(self) -> None:
        if self._initialized:
            logger.debug("SolvePnPHeadPoseEstimator already initialized.")
            return

        logger.info("Initializing SolvePnPHeadPoseEstimator...")
        
        # Validate that model points and indices length matches
        if len(self._model_points) != len(self._landmark_indices):
            raise HeadPoseEstimatorStateError(
                "Mismatch between generic 3D model points and landmark indices."
            )
            
        self._initialized = True
        logger.info("SolvePnPHeadPoseEstimator initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise HeadPoseEstimatorStateError("Call initialize() before start().")
        self._running = True
        logger.info("SolvePnPHeadPoseEstimator started.")

    def process(self, context: ExamContext) -> None:
        """
        Reads frame and face_mesh_info, runs pose estimation, and writes back
        to head_pose_info.
        """
        if not self._running:
            return

        frame = context.current_frame
        if frame is None:
            return

        # Use FaceMeshInfo since AI Module 2 outputs there
        fmi = context.face_mesh_info
        if fmi.face_count == 0 or not fmi.all_face_landmarks:
            self._write_empty_to_context(context, frame)
            return

        try:
            result = self.estimate(frame, fmi.all_face_landmarks)
        except PoseEstimationError as exc:
            logger.error(f"Head pose estimation failed on frame {frame.frame_id}: {exc}")
            return

        self._write_to_context(context, result)

    def stop(self) -> None:
        self._running = False
        logger.info("SolvePnPHeadPoseEstimator stopped.")

    def cleanup(self) -> None:
        self._running = False
        self._initialized = False
        logger.info("SolvePnPHeadPoseEstimator cleaned up.")

    def estimate(
        self,
        frame: Frame,
        all_face_landmarks: List[List[Tuple[float, float, float]]]
    ) -> HeadPoseResult:
        
        if not self._initialized:
            raise HeadPoseEstimatorStateError("Estimator not initialized.")

        if frame.rgb_frame is None or frame.rgb_frame.size == 0:
            raise PoseEstimationError("Invalid or empty frame.")

        start_time = time.perf_counter()
        
        # Approximate camera matrix
        h, w = frame.height, frame.width
        focal_length = w * self._config.focal_length_multiplier
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

        poses: List[HeadPose] = []
        
        for face_idx, landmarks in enumerate(all_face_landmarks):
            if len(landmarks) < max(self._landmark_indices) + 1:
                # Need at least up to the highest required index
                logger.warning(f"Face {face_idx} has insufficient landmarks.")
                continue

            # Extract 2D points in pixel coordinates
            image_points_list = []
            try:
                for idx in self._landmark_indices:
                    lm = landmarks[idx]
                    # lm is (x, y, z) normalised [0,1]
                    px = lm[0] * w
                    py = lm[1] * h
                    image_points_list.append([px, py])
            except IndexError as e:
                raise InvalidLandmarkError(f"Required landmark index missing: {e}") from e

            image_points = np.array(image_points_list, dtype=np.float64)

            # SolvePnP
            success, rvec, tvec = cv2.solvePnP(
                self._model_points,
                image_points,
                camera_matrix,
                self._dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if success:
                # Convert rotation vector to rotation matrix
                rmat, _ = cv2.Rodrigues(rvec)
                
                # Get Euler angles
                proj_matrix = np.hstack((rmat, tvec))
                _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)
                
                pitch, yaw, roll = [float(a[0]) for a in euler_angles]
                
                rvec_flat = rvec.flatten()
                tvec_flat = tvec.flatten()
                
                poses.append(HeadPose(
                    pitch=pitch,
                    yaw=yaw,
                    roll=roll,
                    rotation_vector=(float(rvec_flat[0]), float(rvec_flat[1]), float(rvec_flat[2])),
                    translation_vector=(float(tvec_flat[0]), float(tvec_flat[1]), float(tvec_flat[2])),
                    success=True,
                    face_index=face_idx
                ))
            else:
                poses.append(HeadPose(
                    pitch=0.0, yaw=0.0, roll=0.0,
                    rotation_vector=(0.0, 0.0, 0.0),
                    translation_vector=(0.0, 0.0, 0.0),
                    success=False,
                    face_index=face_idx
                ))

        processing_time_ms = (time.perf_counter() - start_time) * 1000.0
        
        result = HeadPoseResult(
            poses=poses,
            camera_matrix=camera_matrix.tolist(),
            distortion_coefficients=self._dist_coeffs.flatten().tolist(),
            frame_id=frame.frame_id,
            processing_timestamp=time.time(),
            processing_time_ms=processing_time_ms
        )
        
        if self._config.enable_logging:
            logger.debug(
                f"HeadPose | Frame={result.frame_id} | Faces={len(poses)} | "
                f"Time={processing_time_ms:.2f}ms"
            )
            
        return result

    def _write_to_context(self, context: ExamContext, result: HeadPoseResult) -> None:
        with context.lock():
            hpi = context.head_pose_info
            
            primary = result.primary_pose
            if primary and primary.success:
                hpi.pitch = primary.pitch
                hpi.yaw = primary.yaw
                hpi.roll = primary.roll
                hpi.rotation_vector = primary.rotation_vector
                hpi.translation_vector = primary.translation_vector
                hpi.success = True
            else:
                # Reset to zero
                hpi.pitch = 0.0
                hpi.yaw = 0.0
                hpi.roll = 0.0
                hpi.rotation_vector = None
                hpi.translation_vector = None
                hpi.success = False
                
            hpi.camera_matrix = result.camera_matrix
            hpi.distortion_coefficients = result.distortion_coefficients
            hpi.processing_timestamp = result.processing_timestamp
            hpi.processing_time_ms = result.processing_time_ms
            hpi.frame_id = result.frame_id
            
            context.head_pose_info = hpi

    def _write_empty_to_context(self, context: ExamContext, frame: Frame) -> None:
        with context.lock():
            hpi = HeadPoseInfo()
            hpi.frame_id = frame.frame_id
            hpi.processing_timestamp = time.time()
            context.head_pose_info = hpi
