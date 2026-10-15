"""
Unit tests for AI Stage 5 — Mouth Aspect Ratio Feature.
"""
import time
import unittest
from typing import List, Tuple
from unittest.mock import patch

from ai_engine.core.exam_context import ExamContext, FaceMeshInfo
from ai_engine.features.mouth_aspect_ratio.exceptions import (
    MARProcessorStateError,
    InvalidMouthLandmarksError,
    MARProcessorError,
)
from ai_engine.features.mouth_aspect_ratio.models import MARConfig
from ai_engine.features.mouth_aspect_ratio.result import MouthGeometry, MARResult
from ai_engine.features.mouth_aspect_ratio.mediapipe_processor import MediaPipeMARProcessor


def _make_valid_landmarks() -> List[Tuple[float, float, float]]:
    # Create a dummy list of 478 landmarks
    landmarks = [(0.0, 0.0, 0.0)] * 478
    from ai_engine.features.mouth_aspect_ratio.models import REQUIRED_MOUTH_INDICES
    
    # Assign specific coordinates to make distance calculations predictable
    for idx in REQUIRED_MOUTH_INDICES:
        landmarks[idx] = (0.5, 0.5, 0.0)
        
    # Let's set corner points to define width
    from ai_engine.features.mouth_aspect_ratio.models import MOUTH_LEFT_CORNER_INDEX, MOUTH_RIGHT_CORNER_INDEX
    landmarks[MOUTH_LEFT_CORNER_INDEX] = (0.4, 0.5, 0.0)
    landmarks[MOUTH_RIGHT_CORNER_INDEX] = (0.6, 0.5, 0.0)
    
    # Let's set vertical pairs to define height
    from ai_engine.features.mouth_aspect_ratio.models import MOUTH_UPPER_INNER_INDICES, MOUTH_LOWER_INNER_INDICES
    for idx in MOUTH_UPPER_INNER_INDICES:
        landmarks[idx] = (0.5, 0.45, 0.0)
    for idx in MOUTH_LOWER_INNER_INDICES:
        landmarks[idx] = (0.5, 0.55, 0.0)
        
    return landmarks


class TestMARProcessorLifecycle(unittest.TestCase):
    def test_lifecycle(self):
        processor = MediaPipeMARProcessor()
        self.assertFalse(processor.is_initialized)
        
        processor.initialize()
        self.assertTrue(processor.is_initialized)
        
        processor.start()
        self.assertTrue(processor._running)
        
        processor.stop()
        self.assertFalse(processor._running)
        
        processor.cleanup()
        self.assertFalse(processor.is_initialized)

    def test_start_before_init_raises(self):
        processor = MediaPipeMARProcessor()
        with self.assertRaises(MARProcessorStateError):
            processor.start()

    def test_extract_before_init_raises(self):
        processor = MediaPipeMARProcessor()
        with self.assertRaises(MARProcessorStateError):
            processor.extract(1, [])


class TestMediaPipeMARProcessorInference(unittest.TestCase):
    def setUp(self):
        self.processor = MediaPipeMARProcessor(MARConfig(enable_logging=False))
        self.processor.initialize()

    def test_extract_valid_landmarks(self):
        lms = _make_valid_landmarks()
        result = self.processor.extract(1, [lms])
        
        self.assertEqual(len(result.geometries), 1)
        geo = result.geometries[0]
        # Width should be 0.6 - 0.4 = 0.2
        self.assertAlmostEqual(geo.mouth_width, 0.2)
        # Height should be 0.55 - 0.45 = 0.1
        self.assertAlmostEqual(geo.mouth_height, 0.1)
        # MAR = 0.1 / 0.2 = 0.5
        self.assertAlmostEqual(geo.mar, 0.5)

    def test_extract_missing_landmarks(self):
        # Not enough landmarks to satisfy highest index
        lms = [(0.0, 0.0, 0.0)] * 10
        result = self.processor.extract(1, [lms])
        # Face is skipped
        self.assertEqual(len(result.geometries), 0)

    def test_multiple_faces(self):
        lms1 = _make_valid_landmarks()
        lms2 = _make_valid_landmarks()
        result = self.processor.extract(1, [lms1, lms2])
        self.assertEqual(len(result.geometries), 2)


class TestMediaPipeMARProcessorContext(unittest.TestCase):
    def setUp(self):
        self.processor = MediaPipeMARProcessor(MARConfig(enable_logging=False))
        self.processor.initialize()
        self.processor.start()

    def test_process_empty_context(self):
        context = ExamContext()
        self.processor.process(context)
        self.assertEqual(context.mouth_info.mar, 0.0)

    def test_process_with_face_mesh(self):
        context = ExamContext()
        fmi = FaceMeshInfo()
        fmi.face_count = 1
        fmi.all_face_landmarks = [_make_valid_landmarks()]
        fmi.frame_id = 42
        context.face_mesh_info = fmi
        
        self.processor.process(context)
        self.assertAlmostEqual(context.mouth_info.mar, 0.5)
        self.assertEqual(context.mouth_info.frame_id, 42)


if __name__ == '__main__':
    unittest.main()
