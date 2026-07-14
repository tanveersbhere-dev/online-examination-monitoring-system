"""
Unit tests for the Face Detection module.

All tests use mocking and stub objects so they can run without:
• A physical camera
• A downloaded model file
• A network connection

Test strategy
-------------
1. result.py    — Pure dataclass / property tests (no mocking needed).
2. models.py    — Configuration dataclass tests.
3. exceptions.py — Hierarchy tests.
4. detector.py  — Abstract interface checks via a minimal stub.
5. mediapipe_detector.py — Full lifecycle tests with a fully mocked MediaPipe
                           so inference is deterministic.
"""
import time
import types
import unittest
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from ai_engine.detectors.face_detection.exceptions import (
    FaceDetectorError,
    FaceDetectorInitializationError,
    FaceDetectorInferenceError,
    FaceDetectorModelNotFoundError,
)
from ai_engine.detectors.face_detection.models import (
    FaceDetectionConfig,
    DEFAULT_MODEL_CACHE_DIR,
    BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME,
    BLAZE_FACE_SHORT_RANGE_MODEL_URL,
)
from ai_engine.detectors.face_detection.result import DetectedFace, FaceDetectionResult
from ai_engine.detectors.face_detection.mediapipe_detector import MediaPipeFaceDetector
from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, FaceInfo


# ---------------------------------------------------------------------------
# Helpers / Stubs
# ---------------------------------------------------------------------------

def _make_rgb_frame(width: int = 64, height: int = 48) -> np.ndarray:
    """Returns a tiny random RGB numpy array suitable for testing."""
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def _make_frame(frame_id: int = 1, width: int = 64, height: int = 48) -> Frame:
    """Returns a minimal Frame instance backed by random pixel data."""
    rgb = _make_rgb_frame(width, height)
    return Frame(
        frame_id=frame_id,
        timestamp=time.time(),
        original_frame=rgb,
        rgb_frame=rgb,
        width=width,
        height=height,
        channels=3,
        fps=30.0,
        camera_id=0,
    )


def _make_mp_detection(
    x: int = 10, y: int = 10, w: int = 50, h: int = 60, score: float = 0.9
) -> MagicMock:
    """
    Builds a MagicMock that mimics a
    mediapipe.tasks.python.components.containers.detections.Detection object.
    """
    detection = MagicMock()
    detection.bounding_box.origin_x = x
    detection.bounding_box.origin_y = y
    detection.bounding_box.width = w
    detection.bounding_box.height = h
    category = MagicMock()
    category.score = score
    detection.categories = [category]
    kp1, kp2 = MagicMock(), MagicMock()
    kp1.x, kp1.y = 0.3, 0.4
    kp2.x, kp2.y = 0.6, 0.4
    detection.keypoints = [kp1, kp2]
    return detection


def _make_mp_result(detections: list) -> MagicMock:
    """Returns a MagicMock that mimics a MediaPipe DetectionResult."""
    result = MagicMock()
    result.detections = detections
    return result


# ---------------------------------------------------------------------------
# 1. Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestFaceDetectionExceptions(unittest.TestCase):
    """Validates exception class hierarchy."""

    def test_base_is_exception(self) -> None:
        self.assertTrue(issubclass(FaceDetectorError, Exception))

    def test_initialization_error_is_base(self) -> None:
        self.assertTrue(issubclass(FaceDetectorInitializationError, FaceDetectorError))

    def test_inference_error_is_base(self) -> None:
        self.assertTrue(issubclass(FaceDetectorInferenceError, FaceDetectorError))

    def test_model_not_found_is_initialization(self) -> None:
        self.assertTrue(issubclass(FaceDetectorModelNotFoundError, FaceDetectorInitializationError))

    def test_raise_and_catch(self) -> None:
        with self.assertRaises(FaceDetectorError):
            raise FaceDetectorInferenceError("test")


# ---------------------------------------------------------------------------
# 2. Model configuration tests
# ---------------------------------------------------------------------------

class TestFaceDetectionConfig(unittest.TestCase):
    """Validates FaceDetectionConfig defaults and field types."""

    def test_default_values(self) -> None:
        config = FaceDetectionConfig()
        self.assertAlmostEqual(config.min_detection_confidence, 0.5)
        self.assertAlmostEqual(config.min_suppression_threshold, 0.3)
        self.assertEqual(config.max_num_faces, 5)
        self.assertIsNone(config.model_path)
        self.assertIsInstance(config.model_cache_dir, Path)
        self.assertTrue(config.enable_logging)

    def test_custom_values(self) -> None:
        config = FaceDetectionConfig(
            min_detection_confidence=0.7,
            max_num_faces=1,
            enable_logging=False,
        )
        self.assertAlmostEqual(config.min_detection_confidence, 0.7)
        self.assertEqual(config.max_num_faces, 1)
        self.assertFalse(config.enable_logging)

    def test_constants_exist(self) -> None:
        self.assertIn("https://", BLAZE_FACE_SHORT_RANGE_MODEL_URL)
        self.assertTrue(BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME.endswith(".task"))


# ---------------------------------------------------------------------------
# 3. DetectedFace tests
# ---------------------------------------------------------------------------

class TestDetectedFace(unittest.TestCase):
    """Validates DetectedFace dataclass."""

    def test_construction(self) -> None:
        face = DetectedFace(bbox=(10.0, 20.0, 50.0, 60.0), confidence=0.85)
        self.assertEqual(face.bbox, (10.0, 20.0, 50.0, 60.0))
        self.assertAlmostEqual(face.confidence, 0.85)
        self.assertEqual(face.keypoints, [])

    def test_with_keypoints(self) -> None:
        face = DetectedFace(
            bbox=(0.0, 0.0, 30.0, 40.0),
            confidence=0.75,
            keypoints=[(0.3, 0.4), (0.6, 0.4)],
        )
        self.assertEqual(len(face.keypoints), 2)
        self.assertAlmostEqual(face.keypoints[0][0], 0.3)

    def test_invalid_confidence_raises(self) -> None:
        with self.assertRaises(ValueError):
            DetectedFace(bbox=(0.0, 0.0, 10.0, 10.0), confidence=1.5)

    def test_zero_confidence_valid(self) -> None:
        face = DetectedFace(bbox=(0.0, 0.0, 10.0, 10.0), confidence=0.0)
        self.assertAlmostEqual(face.confidence, 0.0)


# ---------------------------------------------------------------------------
# 4. FaceDetectionResult tests
# ---------------------------------------------------------------------------

class TestFaceDetectionResult(unittest.TestCase):
    """Validates FaceDetectionResult behaviour."""

    def _make_result(self, faces: Optional[list] = None) -> FaceDetectionResult:
        faces = faces or []
        return FaceDetectionResult(
            faces=faces,
            face_count=len(faces),
            frame_id=42,
            detection_timestamp=time.time(),
            inference_time_ms=5.0,
            frame_width=640,
            frame_height=480,
        )

    def test_no_faces(self) -> None:
        result = self._make_result([])
        self.assertEqual(result.face_count, 0)
        self.assertFalse(result.is_face_detected)
        self.assertIsNone(result.primary_face)
        self.assertEqual(result.all_bboxes, [])
        self.assertEqual(result.all_confidences, [])

    def test_single_face(self) -> None:
        face = DetectedFace(bbox=(5.0, 5.0, 40.0, 50.0), confidence=0.9)
        result = self._make_result([face])
        self.assertEqual(result.face_count, 1)
        self.assertTrue(result.is_face_detected)
        self.assertIs(result.primary_face, face)
        self.assertEqual(result.all_bboxes, [(5.0, 5.0, 40.0, 50.0)])
        self.assertEqual(result.all_confidences, [0.9])

    def test_multiple_faces(self) -> None:
        f1 = DetectedFace(bbox=(0.0, 0.0, 30.0, 40.0), confidence=0.8)
        f2 = DetectedFace(bbox=(50.0, 0.0, 30.0, 40.0), confidence=0.6)
        result = self._make_result([f1, f2])
        self.assertEqual(result.face_count, 2)
        self.assertEqual(len(result.all_bboxes), 2)
        self.assertEqual(len(result.all_confidences), 2)

    def test_face_count_auto_corrected(self) -> None:
        """face_count should self-correct if it doesn't match len(faces)."""
        face = DetectedFace(bbox=(0.0, 0.0, 10.0, 10.0), confidence=0.5)
        result = FaceDetectionResult(
            faces=[face],
            face_count=99,  # intentionally wrong
            frame_id=1,
            detection_timestamp=time.time(),
            inference_time_ms=1.0,
            frame_width=100,
            frame_height=100,
        )
        self.assertEqual(result.face_count, 1)


# ---------------------------------------------------------------------------
# 5. MediaPipeFaceDetector — lifecycle tests (no real model)
# ---------------------------------------------------------------------------

class TestMediaPipeFaceDetectorLifecycle(unittest.TestCase):
    """
    Tests the detector lifecycle (initialize/start/stop/cleanup) using a
    fully mocked MediaPipe stack so no model file or network is needed.
    """

    def _make_detector(self, max_faces: int = 2) -> MediaPipeFaceDetector:
        config = FaceDetectionConfig(
            min_detection_confidence=0.5,
            max_num_faces=max_faces,
            enable_logging=False,
        )
        return MediaPipeFaceDetector(config=config)

    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch("ai_engine.detectors.face_detection.mediapipe_detector._MPFaceDetector")
    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector.MediaPipeFaceDetector."
        "_resolve_model_path"
    )
    def test_initialize_and_start(self, mock_resolve, mock_mp_detector) -> None:
        mock_resolve.return_value = Path("fake_model.task")
        mock_mp_detector.create_from_options.return_value = MagicMock()

        detector = self._make_detector()
        self.assertFalse(detector.is_initialized)

        detector.initialize()
        self.assertTrue(detector.is_initialized)

        detector.start()
        self.assertTrue(detector._running)

    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch("ai_engine.detectors.face_detection.mediapipe_detector._MPFaceDetector")
    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector.MediaPipeFaceDetector."
        "_resolve_model_path"
    )
    def test_stop_and_cleanup(self, mock_resolve, mock_mp_detector) -> None:
        mock_resolve.return_value = Path("fake_model.task")
        mock_instance = MagicMock()
        mock_mp_detector.create_from_options.return_value = mock_instance

        detector = self._make_detector()
        detector.initialize()
        detector.start()
        detector.stop()
        self.assertFalse(detector._running)

        detector.cleanup()
        self.assertFalse(detector._initialized)
        mock_instance.close.assert_called_once()

    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector._MEDIAPIPE_AVAILABLE",
        False,
    )
    def test_initialize_raises_when_mediapipe_missing(self) -> None:
        detector = self._make_detector()
        with self.assertRaises(FaceDetectorInitializationError):
            detector.initialize()

    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch("ai_engine.detectors.face_detection.mediapipe_detector._MPFaceDetector")
    @patch(
        "ai_engine.detectors.face_detection.mediapipe_detector.MediaPipeFaceDetector."
        "_resolve_model_path"
    )
    def test_initialize_idempotent(self, mock_resolve, mock_mp_detector) -> None:
        """initialize() should be safe to call multiple times."""
        mock_resolve.return_value = Path("fake_model.task")
        mock_mp_detector.create_from_options.return_value = MagicMock()

        detector = self._make_detector()
        detector.initialize()
        detector.initialize()  # second call — should not raise or re-create
        mock_mp_detector.create_from_options.assert_called_once()

    def test_detect_before_initialize_raises(self) -> None:
        detector = self._make_detector()
        frame = _make_frame()
        with self.assertRaises(FaceDetectorInitializationError):
            detector.detect(frame)

    def test_start_before_initialize_raises(self) -> None:
        detector = self._make_detector()
        with self.assertRaises(FaceDetectorInitializationError):
            detector.start()


# ---------------------------------------------------------------------------
# 6. MediaPipeFaceDetector — detect() inference tests
# ---------------------------------------------------------------------------

class TestMediaPipeFaceDetectorInference(unittest.TestCase):
    """
    Tests detect() with mocked MediaPipe so we exercise parsing logic without
    any real model or image processing.
    """

    def setUp(self) -> None:
        self.config = FaceDetectionConfig(
            min_detection_confidence=0.5,
            max_num_faces=5,
            enable_logging=False,
        )
        self.detector = MediaPipeFaceDetector(config=self.config)
        # Manually bypass initialization
        self.detector._initialized = True
        self.detector._running = True
        self.mock_mp_detector = MagicMock()
        self.detector._detector = self.mock_mp_detector

    def _run_detect(self, mp_detections: list) -> FaceDetectionResult:
        """Helper to run detect() with given raw detection mocks."""
        self.mock_mp_detector.detect.return_value = _make_mp_result(mp_detections)

        # Patch MediaPipe image construction so it doesn't require the native lib
        with patch(
            "ai_engine.detectors.face_detection.mediapipe_detector._MPImage"
        ) as mock_img:
            mock_img.return_value = MagicMock()
            frame = _make_frame(frame_id=7)
            return self.detector.detect(frame)

    def test_no_faces_detected(self) -> None:
        self.mock_mp_detector.detect.return_value = _make_mp_result([])
        with patch("ai_engine.detectors.face_detection.mediapipe_detector._MPImage"):
            result = self.detector.detect(_make_frame())
        self.assertEqual(result.face_count, 0)
        self.assertFalse(result.is_face_detected)
        self.assertIsNone(result.primary_face)

    def test_single_face_detected(self) -> None:
        det = _make_mp_detection(x=10, y=20, w=50, h=60, score=0.9)
        result = self._run_detect([det])
        self.assertEqual(result.face_count, 1)
        self.assertTrue(result.is_face_detected)
        face = result.primary_face
        self.assertIsNotNone(face)
        self.assertAlmostEqual(face.confidence, 0.9)
        self.assertEqual(face.bbox, (10.0, 20.0, 50.0, 60.0))

    def test_multiple_faces_sorted_by_confidence(self) -> None:
        d1 = _make_mp_detection(score=0.6)
        d2 = _make_mp_detection(score=0.95)
        d3 = _make_mp_detection(score=0.75)
        result = self._run_detect([d1, d2, d3])
        self.assertEqual(result.face_count, 3)
        confidences = result.all_confidences
        self.assertGreater(confidences[0], confidences[1])
        self.assertGreater(confidences[1], confidences[2])

    def test_max_num_faces_respected(self) -> None:
        """Detections exceeding max_num_faces should be truncated."""
        self.detector._config = FaceDetectionConfig(max_num_faces=2, enable_logging=False)
        detections = [_make_mp_detection(score=0.9 - i * 0.1) for i in range(5)]
        result = self._run_detect(detections)
        self.assertEqual(result.face_count, 2)

    def test_keypoints_extracted(self) -> None:
        det = _make_mp_detection()  # has 2 mock keypoints
        result = self._run_detect([det])
        self.assertGreater(len(result.primary_face.keypoints), 0)

    def test_frame_id_propagated(self) -> None:
        self.mock_mp_detector.detect.return_value = _make_mp_result([])
        with patch("ai_engine.detectors.face_detection.mediapipe_detector._MPImage"):
            frame = _make_frame(frame_id=42)
            result = self.detector.detect(frame)
        self.assertEqual(result.frame_id, 42)

    def test_inference_time_positive(self) -> None:
        self.mock_mp_detector.detect.return_value = _make_mp_result([])
        with patch("ai_engine.detectors.face_detection.mediapipe_detector._MPImage"):
            result = self.detector.detect(_make_frame())
        self.assertGreaterEqual(result.inference_time_ms, 0.0)

    def test_inference_error_raises(self) -> None:
        self.mock_mp_detector.detect.side_effect = RuntimeError("mp crash")
        with patch("ai_engine.detectors.face_detection.mediapipe_detector._MPImage"):
            with self.assertRaises(FaceDetectorInferenceError):
                self.detector.detect(_make_frame())

    def test_none_rgb_frame_raises(self) -> None:
        frame = _make_frame()
        frame.rgb_frame = None  # type: ignore[assignment]
        with self.assertRaises(FaceDetectorInferenceError):
            self.detector.detect(frame)


# ---------------------------------------------------------------------------
# 7. ExamContext integration — _write_to_context
# ---------------------------------------------------------------------------

class TestMediaPipeFaceDetectorContextUpdate(unittest.TestCase):
    """
    Verifies that detect() results are written into ExamContext.face_info
    correctly and that ONLY face_info is mutated.
    """

    def setUp(self) -> None:
        config = FaceDetectionConfig(enable_logging=False)
        self.detector = MediaPipeFaceDetector(config=config)
        self.detector._initialized = True
        self.detector._running = True
        self.mock_mp = MagicMock()
        self.detector._detector = self.mock_mp

    def _build_result(self, faces: list) -> FaceDetectionResult:
        return FaceDetectionResult(
            faces=faces,
            face_count=len(faces),
            frame_id=99,
            detection_timestamp=time.time(),
            inference_time_ms=3.0,
            frame_width=640,
            frame_height=480,
        )

    def test_face_info_updated_with_one_face(self) -> None:
        context = ExamContext()
        face = DetectedFace(
            bbox=(10.0, 20.0, 50.0, 60.0),
            confidence=0.88,
            keypoints=[(0.3, 0.4), (0.6, 0.4)],
        )
        result = self._build_result([face])
        self.detector._write_to_context(context, result)

        fi: FaceInfo = context.face_info
        self.assertTrue(fi.face_detected)
        self.assertEqual(fi.face_count, 1)
        self.assertAlmostEqual(fi.confidence, 0.88)
        self.assertEqual(fi.bbox, (10.0, 20.0, 50.0, 60.0))
        self.assertEqual(fi.frame_id, 99)

    def test_face_info_cleared_when_no_face(self) -> None:
        context = ExamContext()
        result = self._build_result([])
        self.detector._write_to_context(context, result)

        fi: FaceInfo = context.face_info
        self.assertFalse(fi.face_detected)
        self.assertEqual(fi.face_count, 0)
        self.assertAlmostEqual(fi.confidence, 0.0)
        self.assertEqual(fi.bbox, (0.0, 0.0, 0.0, 0.0))
        self.assertEqual(fi.landmarks, [])

    def test_multiple_faces_all_bboxes(self) -> None:
        context = ExamContext()
        f1 = DetectedFace(bbox=(0.0, 0.0, 30.0, 40.0), confidence=0.9)
        f2 = DetectedFace(bbox=(50.0, 0.0, 30.0, 40.0), confidence=0.7)
        result = self._build_result([f1, f2])
        self.detector._write_to_context(context, result)

        fi: FaceInfo = context.face_info
        self.assertEqual(fi.face_count, 2)
        self.assertEqual(len(fi.all_bboxes), 2)
        self.assertEqual(len(fi.all_confidences), 2)

    def test_other_context_fields_unchanged(self) -> None:
        """Writing face_info must not alter any other ExamContext section."""
        context = ExamContext()
        original_camera = context.camera_state
        original_audio = context.audio_info
        original_system = context.system_state

        result = self._build_result([])
        self.detector._write_to_context(context, result)

        self.assertEqual(context.camera_state.status, original_camera.status)
        self.assertEqual(context.audio_info.is_speaking, original_audio.is_speaking)
        self.assertEqual(context.system_state.status, original_system.status)

    def test_process_skips_when_not_running(self) -> None:
        context = ExamContext()
        self.detector._running = False
        self.detector.process(context)
        # face_info should remain at defaults
        self.assertFalse(context.face_info.face_detected)

    def test_process_skips_when_no_frame(self) -> None:
        context = ExamContext()
        # current_frame is None by default
        self.detector.process(context)
        self.assertFalse(context.face_info.face_detected)

    def test_process_runs_detection_with_frame(self) -> None:
        context = ExamContext()
        frame = _make_frame(frame_id=55)
        context.current_frame = frame

        self.mock_mp.detect.return_value = _make_mp_result(
            [_make_mp_detection(score=0.8)]
        )
        with patch("ai_engine.detectors.face_detection.mediapipe_detector._MPImage"):
            self.detector.process(context)

        fi = context.face_info
        self.assertTrue(fi.face_detected)
        self.assertEqual(fi.frame_id, 55)


# ---------------------------------------------------------------------------
# 8. Model resolution tests
# ---------------------------------------------------------------------------

class TestModelResolution(unittest.TestCase):
    """Tests _resolve_model_path logic without touching the filesystem."""

    def setUp(self) -> None:
        self.detector = MediaPipeFaceDetector(config=FaceDetectionConfig())

    def test_explicit_model_path_missing_raises(self) -> None:
        self.detector._config = FaceDetectionConfig(
            model_path=Path("/definitely/does/not/exist/model.task")
        )
        with self.assertRaises(FaceDetectorModelNotFoundError):
            self.detector._resolve_model_path()

    def test_cached_model_returned(self) -> None:
        with patch("pathlib.Path.exists", return_value=True):
            self.detector._config = FaceDetectionConfig(
                model_cache_dir=Path("/fake/cache")
            )
            result = self.detector._resolve_model_path()
        expected = Path("/fake/cache") / BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME
        self.assertEqual(result, expected)

    def test_download_called_when_no_cache(self) -> None:
        with patch("pathlib.Path.exists", return_value=False), \
             patch.object(self.detector, "_download_model") as mock_dl:
            fake_path = Path("/fake/cache/model.task")
            mock_dl.return_value = fake_path
            result = self.detector._resolve_model_path()
        mock_dl.assert_called_once()
        self.assertEqual(result, fake_path)


if __name__ == "__main__":
    unittest.main()
