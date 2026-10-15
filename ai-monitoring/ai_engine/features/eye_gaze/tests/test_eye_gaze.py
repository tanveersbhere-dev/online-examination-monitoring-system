"""
Unit tests for AI Stage 4 — Eye Gaze Feature Extraction.
"""
import time
import unittest
from typing import List, Tuple
from unittest.mock import patch, MagicMock

import numpy as np

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, FaceMeshInfo
from ai_engine.features.eye_gaze.exceptions import (
    EyeGazeStateError,
    InvalidIrisLandmarksError,
    EyeTrackingError,
)
from ai_engine.features.eye_gaze.models import EyeGazeConfig
from ai_engine.features.eye_gaze.result import EyeGaze, EyeGazeResult
from ai_engine.features.eye_gaze.mediapipe_gaze_extractor import MediaPipeEyeGazeExtractor


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
    # Create a dummy list of 478 landmarks (including iris and eyelids)
    landmarks = [(0.0, 0.0, 0.0)] * 478
    from ai_engine.features.eye_gaze.models import (
        LEFT_IRIS_CENTER_INDEX, RIGHT_IRIS_CENTER_INDEX,
        LEFT_EYE_LEFT_CORNER_INDEX, LEFT_EYE_RIGHT_CORNER_INDEX,
        RIGHT_EYE_LEFT_CORNER_INDEX, RIGHT_EYE_RIGHT_CORNER_INDEX,
        LEFT_EYE_UPPER_LID_INDEX, LEFT_EYE_LOWER_LID_INDEX,
        RIGHT_EYE_UPPER_LID_INDEX, RIGHT_EYE_LOWER_LID_INDEX,
    )
    landmarks[LEFT_EYE_LEFT_CORNER_INDEX] = (0.40, 0.50, 0.0)
    landmarks[LEFT_EYE_RIGHT_CORNER_INDEX] = (0.45, 0.50, 0.0)
    landmarks[LEFT_EYE_UPPER_LID_INDEX] = (0.425, 0.48, 0.0)
    landmarks[LEFT_EYE_LOWER_LID_INDEX] = (0.425, 0.52, 0.0)
    landmarks[LEFT_IRIS_CENTER_INDEX] = (0.43, 0.50, 0.0)

    landmarks[RIGHT_EYE_LEFT_CORNER_INDEX] = (0.55, 0.50, 0.0)
    landmarks[RIGHT_EYE_RIGHT_CORNER_INDEX] = (0.60, 0.50, 0.0)
    landmarks[RIGHT_EYE_UPPER_LID_INDEX] = (0.575, 0.48, 0.0)
    landmarks[RIGHT_EYE_LOWER_LID_INDEX] = (0.575, 0.52, 0.0)
    landmarks[RIGHT_IRIS_CENTER_INDEX] = (0.58, 0.50, 0.0)
    return landmarks


class TestEyeGazeExtractorLifecycle(unittest.TestCase):
    def test_lifecycle(self):
        extractor = MediaPipeEyeGazeExtractor()
        self.assertFalse(extractor.is_initialized)
        
        extractor.initialize()
        self.assertTrue(extractor.is_initialized)
        
        extractor.start()
        self.assertTrue(extractor._running)
        
        extractor.stop()
        self.assertFalse(extractor._running)
        
        extractor.cleanup()
        self.assertFalse(extractor.is_initialized)

    def test_start_before_init_raises(self):
        extractor = MediaPipeEyeGazeExtractor()
        with self.assertRaises(EyeGazeStateError):
            extractor.start()

    def test_extract_before_init_raises(self):
        extractor = MediaPipeEyeGazeExtractor()
        with self.assertRaises(EyeGazeStateError):
            extractor.extract(_make_frame(), [])


class TestMediaPipeEyeGazeExtractorInference(unittest.TestCase):
    def setUp(self):
        self.extractor = MediaPipeEyeGazeExtractor(EyeGazeConfig(enable_logging=False))
        self.extractor.initialize()

    def test_extract_valid_landmarks(self):
        frame = _make_frame()
        lms = _make_valid_landmarks()
        result = self.extractor.extract(frame, [lms])
        
        self.assertEqual(len(result.gazes), 1)
        self.assertIsNotNone(result.gazes[0].left_gaze_vector)
        self.assertIsNotNone(result.gazes[0].combined_gaze_vector)
        self.assertIsNotNone(result.gazes[0].left_iris_center)

    def test_extract_missing_landmarks(self):
        frame = _make_frame()
        # Not enough landmarks to satisfy index 473
        lms = [(0.0, 0.0, 0.0)] * 400
        result = self.extractor.extract(frame, [lms])
        # Face is skipped
        self.assertEqual(len(result.gazes), 0)

    def test_multiple_faces(self):
        frame = _make_frame()
        lms1 = _make_valid_landmarks()
        lms2 = _make_valid_landmarks()
        result = self.extractor.extract(frame, [lms1, lms2])
        self.assertEqual(len(result.gazes), 2)


class TestMediaPipeEyeGazeExtractorContext(unittest.TestCase):
    def setUp(self):
        self.extractor = MediaPipeEyeGazeExtractor(EyeGazeConfig(enable_logging=False))
        self.extractor.initialize()
        self.extractor.start()

    def test_process_empty_context(self):
        context = ExamContext()
        self.extractor.process(context)
        # Should clear or leave at zero
        self.assertEqual(context.eye_info.combined_gaze, (0.0, 0.0, 0.0))

    def test_process_no_face_mesh(self):
        context = ExamContext()
        context.current_frame = _make_frame()
        self.extractor.process(context)
        self.assertEqual(context.eye_info.combined_gaze, (0.0, 0.0, 0.0))

    def test_process_with_face_mesh(self):
        context = ExamContext()
        context.current_frame = _make_frame()
        fmi = FaceMeshInfo()
        fmi.face_count = 1
        fmi.all_face_landmarks = [_make_valid_landmarks()]
        context.face_mesh_info = fmi
        
        self.extractor.process(context)
        # Assuming our dummy points produce a non-zero vector
        self.assertNotEqual(context.eye_info.combined_gaze, (0.0, 0.0, 0.0))
        self.assertIsNotNone(context.eye_info.left_iris_center)


if __name__ == '__main__':
    unittest.main()
