"""
Unit tests for AI Module 3 — Head Pose Estimation.
"""
import time
import unittest
from typing import List, Tuple
from unittest.mock import patch, MagicMock

import numpy as np

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, FaceMeshInfo
from ai_engine.estimators.head_pose.exceptions import (
    HeadPoseEstimatorError,
    HeadPoseEstimatorStateError,
    InvalidLandmarkError,
    PoseEstimationError,
)
from ai_engine.estimators.head_pose.models import HeadPoseConfig
from ai_engine.estimators.head_pose.result import HeadPose, HeadPoseResult
from ai_engine.estimators.head_pose.solvepnp_estimator import SolvePnPHeadPoseEstimator


def _make_frame(width=640, height=480):
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    return Frame(
        frame_id=1,
        timestamp=time.time(),
        original_frame=rgb,
        rgb_frame=rgb,
        width=width,
        height=height,
        channels=3,
        fps=30.0,
        camera_id=0
    )


def _make_valid_landmarks() -> List[Tuple[float, float, float]]:
    # Create a dummy list of 468 landmarks
    landmarks = [(0.0, 0.0, 0.0)] * 468
    # Populate the required indices with generic values
    from ai_engine.estimators.head_pose.models import MP_LANDMARK_INDICES
    for i, idx in enumerate(MP_LANDMARK_INDICES):
        landmarks[idx] = (0.5 + i*0.01, 0.5 + i*0.01, 0.0)
    return landmarks


class TestHeadPoseEstimatorLifecycle(unittest.TestCase):
    def test_lifecycle(self):
        estimator = SolvePnPHeadPoseEstimator()
        self.assertFalse(estimator.is_initialized)
        
        estimator.initialize()
        self.assertTrue(estimator.is_initialized)
        
        estimator.start()
        self.assertTrue(estimator._running)
        
        estimator.stop()
        self.assertFalse(estimator._running)
        
        estimator.cleanup()
        self.assertFalse(estimator.is_initialized)

    def test_start_before_init_raises(self):
        estimator = SolvePnPHeadPoseEstimator()
        with self.assertRaises(HeadPoseEstimatorStateError):
            estimator.start()

    def test_estimate_before_init_raises(self):
        estimator = SolvePnPHeadPoseEstimator()
        with self.assertRaises(HeadPoseEstimatorStateError):
            estimator.estimate(_make_frame(), [])


class TestSolvePnPHeadPoseEstimatorInference(unittest.TestCase):
    def setUp(self):
        self.estimator = SolvePnPHeadPoseEstimator(HeadPoseConfig(enable_logging=False))
        self.estimator.initialize()

    def test_estimate_valid_landmarks(self):
        frame = _make_frame()
        lms = _make_valid_landmarks()
        result = self.estimator.estimate(frame, [lms])
        
        self.assertEqual(len(result.poses), 1)
        self.assertTrue(result.poses[0].success)
        self.assertIsNotNone(result.camera_matrix)

    def test_estimate_missing_landmarks(self):
        frame = _make_frame()
        # Not enough landmarks to satisfy MP_LANDMARK_INDICES
        lms = [(0.0, 0.0, 0.0)] * 10
        result = self.estimator.estimate(frame, [lms])
        # Face is skipped or pose not successful
        self.assertEqual(len(result.poses), 0)

    def test_estimate_invalid_frame(self):
        frame = _make_frame()
        frame.rgb_frame = None
        with self.assertRaises(PoseEstimationError):
            self.estimator.estimate(frame, [_make_valid_landmarks()])

    @patch('cv2.solvePnP', return_value=(False, None, None))
    def test_solvepnp_failure(self, mock_solvepnp):
        frame = _make_frame()
        result = self.estimator.estimate(frame, [_make_valid_landmarks()])
        self.assertEqual(len(result.poses), 1)
        self.assertFalse(result.poses[0].success)
        self.assertEqual(result.poses[0].pitch, 0.0)


class TestSolvePnPHeadPoseEstimatorContext(unittest.TestCase):
    def setUp(self):
        self.estimator = SolvePnPHeadPoseEstimator(HeadPoseConfig(enable_logging=False))
        self.estimator.initialize()
        self.estimator.start()

    def test_process_empty_context(self):
        context = ExamContext()
        self.estimator.process(context)
        self.assertFalse(context.head_pose_info.success)

    def test_process_no_face_mesh(self):
        context = ExamContext()
        context.current_frame = _make_frame()
        self.estimator.process(context)
        self.assertFalse(context.head_pose_info.success)

    def test_process_with_face_mesh(self):
        context = ExamContext()
        context.current_frame = _make_frame()
        fmi = FaceMeshInfo()
        fmi.face_count = 1
        fmi.all_face_landmarks = [_make_valid_landmarks()]
        context.face_mesh_info = fmi
        
        self.estimator.process(context)
        self.assertTrue(context.head_pose_info.success)


if __name__ == '__main__':
    unittest.main()
