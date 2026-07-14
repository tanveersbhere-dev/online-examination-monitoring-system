"""
Unit tests for AI Module 2 — Face Landmark Detection.

All tests are self-contained and require neither a camera, a downloaded model,
nor a live network connection.  MediaPipe internals are mocked at the module
level so that every test focuses on the observable behaviour of this module's
own logic.

Test categories
---------------
1.  Exception hierarchy        — TestLandmarkDetectionExceptions
2.  Configuration              — TestLandmarkDetectionConfig
3.  Landmark dataclass         — TestLandmark
4.  FaceLandmarks dataclass    — TestFaceLandmarks
5.  FaceMeshResult dataclass   — TestFaceMeshResult
6.  Lifecycle                  — TestMediaPipeLandmarkDetectorLifecycle
7.  Inference (extract)        — TestMediaPipeLandmarkDetectorInference
8.  ExamContext integration    — TestMediaPipeLandmarkDetectorContextUpdate
9.  Model resolution           — TestModelResolution
10. Process orchestration      — TestProcessOrchestration
"""
import time
import unittest
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import numpy as np

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from ai_engine.detectors.landmark_detection.exceptions import (
    LandmarkDetectorError,
    LandmarkDetectorModelNotFoundError,
    LandmarkDetectorStateError,
    LandmarkExtractionError,
    MediaPipeInitializationError,
)
from ai_engine.detectors.landmark_detection.models import (
    FACE_LANDMARKER_MODEL_FILENAME,
    FACE_LANDMARKER_MODEL_URL,
    LandmarkDetectionConfig,
)
from ai_engine.detectors.landmark_detection.result import (
    FaceLandmarks,
    FaceMeshResult,
    Landmark,
)
from ai_engine.detectors.landmark_detection.mediapipe_landmark_detector import (
    MediaPipeLandmarkDetector,
)
from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, FaceInfo, FaceMeshInfo


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------

def _make_rgb_frame(width: int = 64, height: int = 48) -> np.ndarray:
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def _make_frame(
    frame_id: int = 1,
    width: int = 64,
    height: int = 48,
    rgb: Optional[np.ndarray] = None,
) -> Frame:
    if rgb is None:
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


def _make_mp_landmark(
    x: float = 0.5,
    y: float = 0.5,
    z: float = -0.1,
    visibility: Optional[float] = 0.9,
    presence: Optional[float] = 0.8,
) -> MagicMock:
    """Returns a MagicMock mimicking a MediaPipe NormalizedLandmark."""
    lm = MagicMock()
    lm.x = x
    lm.y = y
    lm.z = z
    lm.visibility = visibility
    lm.presence = presence
    return lm


def _make_mp_face_landmarks(n: int = 478) -> List[MagicMock]:
    """Returns a list of n mock landmarks."""
    return [_make_mp_landmark(x=i / n, y=i / n) for i in range(n)]


def _make_mp_landmarker_result(num_faces: int = 1, lm_per_face: int = 478) -> MagicMock:
    """Returns a MagicMock mimicking a MediaPipe FaceLandmarkerResult."""
    result = MagicMock()
    result.face_landmarks = [
        _make_mp_face_landmarks(lm_per_face) for _ in range(num_faces)
    ]
    return result


def _make_detector(
    num_faces: int = 1,
    enable_logging: bool = False,
) -> MediaPipeLandmarkDetector:
    config = LandmarkDetectionConfig(num_faces=num_faces, enable_logging=enable_logging)
    return MediaPipeLandmarkDetector(config=config)


def _make_initialized_detector(
    num_faces: int = 1,
    mock_landmarker: Optional[MagicMock] = None,
) -> MediaPipeLandmarkDetector:
    """
    Returns a detector that has been 'initialized' by directly wiring in a
    mock landmarker — no real model loading occurs.
    """
    det = _make_detector(num_faces=num_faces)
    det._initialized = True
    det._running = True
    det._landmarker = mock_landmarker or MagicMock()
    return det


# ---------------------------------------------------------------------------
# 1. Exception hierarchy
# ---------------------------------------------------------------------------

class TestLandmarkDetectionExceptions(unittest.TestCase):

    def test_base_is_exception(self) -> None:
        self.assertTrue(issubclass(LandmarkDetectorError, Exception))

    def test_media_pipe_init_is_base(self) -> None:
        self.assertTrue(issubclass(MediaPipeInitializationError, LandmarkDetectorError))

    def test_extraction_is_base(self) -> None:
        self.assertTrue(issubclass(LandmarkExtractionError, LandmarkDetectorError))

    def test_model_not_found_is_init(self) -> None:
        self.assertTrue(
            issubclass(LandmarkDetectorModelNotFoundError, MediaPipeInitializationError)
        )

    def test_state_error_is_base(self) -> None:
        self.assertTrue(issubclass(LandmarkDetectorStateError, LandmarkDetectorError))

    def test_can_raise_and_catch_base(self) -> None:
        with self.assertRaises(LandmarkDetectorError):
            raise LandmarkExtractionError("test")

    def test_can_raise_model_not_found(self) -> None:
        with self.assertRaises(MediaPipeInitializationError):
            raise LandmarkDetectorModelNotFoundError("missing")


# ---------------------------------------------------------------------------
# 2. Configuration
# ---------------------------------------------------------------------------

class TestLandmarkDetectionConfig(unittest.TestCase):

    def test_default_values(self) -> None:
        cfg = LandmarkDetectionConfig()
        self.assertEqual(cfg.num_faces, 1)
        self.assertAlmostEqual(cfg.min_face_detection_confidence, 0.5)
        self.assertAlmostEqual(cfg.min_face_presence_confidence, 0.5)
        self.assertAlmostEqual(cfg.min_tracking_confidence, 0.5)
        self.assertFalse(cfg.output_face_blendshapes)
        self.assertIsNone(cfg.model_path)
        self.assertIsInstance(cfg.model_cache_dir, Path)
        self.assertTrue(cfg.enable_logging)

    def test_custom_values(self) -> None:
        cfg = LandmarkDetectionConfig(num_faces=3, enable_logging=False)
        self.assertEqual(cfg.num_faces, 3)
        self.assertFalse(cfg.enable_logging)

    def test_model_constants(self) -> None:
        self.assertIn("https://", FACE_LANDMARKER_MODEL_URL)
        self.assertTrue(FACE_LANDMARKER_MODEL_FILENAME.endswith(".task"))


# ---------------------------------------------------------------------------
# 3. Landmark dataclass
# ---------------------------------------------------------------------------

class TestLandmark(unittest.TestCase):

    def test_construction(self) -> None:
        lm = Landmark(x=0.1, y=0.2, z=-0.05, visibility=0.9, presence=0.8, index=10)
        self.assertAlmostEqual(lm.x, 0.1)
        self.assertAlmostEqual(lm.y, 0.2)
        self.assertAlmostEqual(lm.z, -0.05)
        self.assertAlmostEqual(lm.visibility, 0.9)
        self.assertAlmostEqual(lm.presence, 0.8)
        self.assertEqual(lm.index, 10)

    def test_optional_fields_default_none(self) -> None:
        lm = Landmark(x=0.5, y=0.5, z=0.0)
        self.assertIsNone(lm.visibility)
        self.assertIsNone(lm.presence)
        self.assertEqual(lm.index, 0)

    def test_negative_z_allowed(self) -> None:
        lm = Landmark(x=0.5, y=0.5, z=-0.99)
        self.assertAlmostEqual(lm.z, -0.99)


# ---------------------------------------------------------------------------
# 4. FaceLandmarks dataclass
# ---------------------------------------------------------------------------

class TestFaceLandmarks(unittest.TestCase):

    def _make_landmarks(self, n: int) -> List[Landmark]:
        return [Landmark(x=i / n, y=i / n, z=0.0, index=i) for i in range(n)]

    def test_construction(self) -> None:
        lms = self._make_landmarks(468)
        fl = FaceLandmarks(landmarks=lms, landmark_count=468, face_index=0)
        self.assertEqual(fl.landmark_count, 468)
        self.assertEqual(fl.face_index, 0)
        self.assertIsNone(fl.detection_confidence)

    def test_auto_corrects_landmark_count(self) -> None:
        lms = self._make_landmarks(100)
        fl = FaceLandmarks(landmarks=lms, landmark_count=999, face_index=0)
        self.assertEqual(fl.landmark_count, 100)

    def test_get_valid_index(self) -> None:
        lms = self._make_landmarks(10)
        fl = FaceLandmarks(landmarks=lms, landmark_count=10, face_index=0)
        result = fl.get(5)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 5)

    def test_get_out_of_bounds_returns_none(self) -> None:
        lms = self._make_landmarks(5)
        fl = FaceLandmarks(landmarks=lms, landmark_count=5, face_index=0)
        self.assertIsNone(fl.get(100))
        self.assertIsNone(fl.get(-1))

    def test_with_detection_confidence(self) -> None:
        lms = self._make_landmarks(3)
        fl = FaceLandmarks(landmarks=lms, landmark_count=3, face_index=1, detection_confidence=0.95)
        self.assertAlmostEqual(fl.detection_confidence, 0.95)


# ---------------------------------------------------------------------------
# 5. FaceMeshResult dataclass
# ---------------------------------------------------------------------------

class TestFaceMeshResult(unittest.TestCase):

    def _make_face_lms(self, face_idx: int = 0, n: int = 10) -> FaceLandmarks:
        lms = [Landmark(x=0.1, y=0.2, z=0.0, index=i) for i in range(n)]
        return FaceLandmarks(landmarks=lms, landmark_count=n, face_index=face_idx)

    def _make_result(self, faces: Optional[list] = None) -> FaceMeshResult:
        faces = faces or []
        return FaceMeshResult(
            face_landmarks=faces,
            face_count=len(faces),
            frame_id=7,
            processing_timestamp=time.time(),
            processing_time_ms=3.5,
            frame_width=640,
            frame_height=480,
        )

    def test_no_faces(self) -> None:
        r = self._make_result([])
        self.assertEqual(r.face_count, 0)
        self.assertFalse(r.is_face_detected)
        self.assertIsNone(r.primary_landmarks)

    def test_single_face(self) -> None:
        fl = self._make_face_lms(face_idx=0)
        r = self._make_result([fl])
        self.assertEqual(r.face_count, 1)
        self.assertTrue(r.is_face_detected)
        self.assertIs(r.primary_landmarks, fl)

    def test_multiple_faces(self) -> None:
        fl0 = self._make_face_lms(face_idx=0)
        fl1 = self._make_face_lms(face_idx=1)
        r = self._make_result([fl0, fl1])
        self.assertEqual(r.face_count, 2)
        self.assertIs(r.get_face(0), fl0)
        self.assertIs(r.get_face(1), fl1)
        self.assertIsNone(r.get_face(99))

    def test_auto_corrects_face_count(self) -> None:
        fl = self._make_face_lms()
        r = FaceMeshResult(
            face_landmarks=[fl],
            face_count=999,
            frame_id=1,
            processing_timestamp=time.time(),
            processing_time_ms=1.0,
            frame_width=100,
            frame_height=100,
        )
        self.assertEqual(r.face_count, 1)

    def test_frame_id_preserved(self) -> None:
        r = self._make_result()
        self.assertEqual(r.frame_id, 7)

    def test_processing_time_positive(self) -> None:
        r = self._make_result()
        self.assertGreaterEqual(r.processing_time_ms, 0.0)


# ---------------------------------------------------------------------------
# 6. MediaPipeLandmarkDetector — lifecycle
# ---------------------------------------------------------------------------

class TestMediaPipeLandmarkDetectorLifecycle(unittest.TestCase):

    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MPFaceLandmarker"
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        ".MediaPipeLandmarkDetector._resolve_model_path"
    )
    def test_initialize_and_start(self, mock_resolve, mock_mp) -> None:
        mock_resolve.return_value = Path("fake_model.task")
        mock_mp.create_from_options.return_value = MagicMock()

        det = _make_detector()
        self.assertFalse(det.is_initialized)

        det.initialize()
        self.assertTrue(det.is_initialized)

        det.start()
        self.assertTrue(det._running)

    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MPFaceLandmarker"
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        ".MediaPipeLandmarkDetector._resolve_model_path"
    )
    def test_stop_and_cleanup(self, mock_resolve, mock_mp) -> None:
        mock_resolve.return_value = Path("fake.task")
        mock_instance = MagicMock()
        mock_mp.create_from_options.return_value = mock_instance

        det = _make_detector()
        det.initialize()
        det.start()
        det.stop()
        self.assertFalse(det._running)

        det.cleanup()
        self.assertFalse(det._initialized)
        mock_instance.close.assert_called_once()

    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MEDIAPIPE_AVAILABLE",
        False,
    )
    def test_initialize_raises_when_mediapipe_missing(self) -> None:
        det = _make_detector()
        with self.assertRaises(MediaPipeInitializationError):
            det.initialize()

    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MPFaceLandmarker"
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        ".MediaPipeLandmarkDetector._resolve_model_path"
    )
    def test_initialize_idempotent(self, mock_resolve, mock_mp) -> None:
        mock_resolve.return_value = Path("f.task")
        mock_mp.create_from_options.return_value = MagicMock()

        det = _make_detector()
        det.initialize()
        det.initialize()  # second call — must not recreate
        mock_mp.create_from_options.assert_called_once()

    def test_start_before_initialize_raises(self) -> None:
        det = _make_detector()
        with self.assertRaises(LandmarkDetectorStateError):
            det.start()

    def test_extract_before_initialize_raises(self) -> None:
        det = _make_detector()
        with self.assertRaises(LandmarkDetectorStateError):
            det.extract(_make_frame(), num_faces=1)

    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MEDIAPIPE_AVAILABLE",
        True,
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        "._MPFaceLandmarker"
    )
    @patch(
        "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
        ".MediaPipeLandmarkDetector._resolve_model_path"
    )
    def test_cleanup_after_initialize_without_start(self, mock_resolve, mock_mp) -> None:
        mock_resolve.return_value = Path("f.task")
        mock_instance = MagicMock()
        mock_mp.create_from_options.return_value = mock_instance

        det = _make_detector()
        det.initialize()
        det.cleanup()
        self.assertFalse(det._initialized)
        mock_instance.close.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Inference — extract()
# ---------------------------------------------------------------------------

class TestMediaPipeLandmarkDetectorInference(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_landmarker = MagicMock()
        self.det = _make_initialized_detector(num_faces=5, mock_landmarker=self.mock_landmarker)

    def _run_extract(self, mp_result: object, num_faces: int = 5) -> FaceMeshResult:
        self.mock_landmarker.detect.return_value = mp_result
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ) as mock_img:
            mock_img.return_value = MagicMock()
            return self.det.extract(_make_frame(frame_id=11), num_faces=num_faces)

    def test_no_faces_in_result(self) -> None:
        result_mock = MagicMock()
        result_mock.face_landmarks = []
        r = self._run_extract(result_mock)
        self.assertEqual(r.face_count, 0)
        self.assertFalse(r.is_face_detected)
        self.assertIsNone(r.primary_landmarks)

    def test_single_face_landmarks(self) -> None:
        r = self._run_extract(_make_mp_landmarker_result(num_faces=1, lm_per_face=478))
        self.assertEqual(r.face_count, 1)
        self.assertTrue(r.is_face_detected)
        self.assertEqual(r.primary_landmarks.landmark_count, 478)

    def test_multiple_faces(self) -> None:
        r = self._run_extract(_make_mp_landmarker_result(num_faces=3, lm_per_face=478))
        self.assertEqual(r.face_count, 3)
        self.assertEqual(len(r.face_landmarks), 3)

    def test_num_faces_cap_respected(self) -> None:
        """extract() must not return more faces than num_faces."""
        self.det._config = LandmarkDetectionConfig(num_faces=2, enable_logging=False)
        r = self._run_extract(
            _make_mp_landmarker_result(num_faces=4, lm_per_face=478),
            num_faces=2,
        )
        self.assertEqual(r.face_count, 2)

    def test_visibility_and_presence_extracted(self) -> None:
        r = self._run_extract(_make_mp_landmarker_result(num_faces=1, lm_per_face=5))
        lm0 = r.primary_landmarks.landmarks[0]
        # Our stub assigns visibility=0.9 and presence=0.8
        self.assertIsNotNone(lm0.visibility)
        self.assertIsNotNone(lm0.presence)

    def test_landmark_index_set(self) -> None:
        r = self._run_extract(_make_mp_landmarker_result(num_faces=1, lm_per_face=10))
        for idx, lm in enumerate(r.primary_landmarks.landmarks):
            self.assertEqual(lm.index, idx)

    def test_frame_id_propagated(self) -> None:
        self.mock_landmarker.detect.return_value = _make_mp_landmarker_result(0)
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ):
            r = self.det.extract(_make_frame(frame_id=42), num_faces=1)
        self.assertEqual(r.frame_id, 42)

    def test_inference_time_recorded(self) -> None:
        self.mock_landmarker.detect.return_value = _make_mp_landmarker_result(0)
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ):
            r = self.det.extract(_make_frame(), num_faces=1)
        self.assertGreaterEqual(r.processing_time_ms, 0.0)

    def test_none_rgb_frame_raises(self) -> None:
        frame = _make_frame()
        frame.rgb_frame = None  # type: ignore[assignment]
        with self.assertRaises(LandmarkExtractionError):
            self.det.extract(frame, num_faces=1)

    def test_empty_rgb_frame_raises(self) -> None:
        frame = _make_frame()
        frame.rgb_frame = np.array([], dtype=np.uint8)
        with self.assertRaises(LandmarkExtractionError):
            self.det.extract(frame, num_faces=1)

    def test_wrong_shape_frame_raises(self) -> None:
        frame = _make_frame()
        frame.rgb_frame = np.zeros((48, 64), dtype=np.uint8)  # 2-D, no channels
        with self.assertRaises(LandmarkExtractionError):
            self.det.extract(frame, num_faces=1)

    def test_inference_exception_raises_extraction_error(self) -> None:
        self.mock_landmarker.detect.side_effect = RuntimeError("mp crash")
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ):
            with self.assertRaises(LandmarkExtractionError):
                self.det.extract(_make_frame(), num_faces=1)

    def test_corrupted_frame_wrong_channel_count_raises(self) -> None:
        """A frame with 4 channels (RGBA) should raise LandmarkExtractionError."""
        frame = _make_frame()
        frame.rgb_frame = np.zeros((48, 64, 4), dtype=np.uint8)
        with self.assertRaises(LandmarkExtractionError):
            self.det.extract(frame, num_faces=1)


# ---------------------------------------------------------------------------
# 8. ExamContext integration — _write_to_context / _write_empty_to_context
# ---------------------------------------------------------------------------

class TestMediaPipeLandmarkDetectorContextUpdate(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_landmarker = MagicMock()
        self.det = _make_initialized_detector(mock_landmarker=self.mock_landmarker)

    def _build_result(
        self,
        num_faces: int = 1,
        lm_count: int = 5,
        frame_id: int = 7,
    ) -> FaceMeshResult:
        faces = []
        for fi in range(num_faces):
            lms = [Landmark(x=0.1, y=0.2, z=0.0, index=i) for i in range(lm_count)]
            faces.append(
                FaceLandmarks(landmarks=lms, landmark_count=lm_count, face_index=fi)
            )
        return FaceMeshResult(
            face_landmarks=faces,
            face_count=len(faces),
            frame_id=frame_id,
            processing_timestamp=time.time(),
            processing_time_ms=2.0,
            frame_width=640,
            frame_height=480,
        )

    # -- context write tests ------------------------------------------------

    def test_write_single_face_landmarks(self) -> None:
        ctx = ExamContext()
        result = self._build_result(num_faces=1, lm_count=468)
        self.det._write_to_context(ctx, result)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 1)
        self.assertEqual(len(fmi.all_face_landmarks), 1)
        self.assertEqual(len(fmi.all_face_landmarks[0]), 468)
        self.assertEqual(len(fmi.mesh_points), 468)
        self.assertEqual(fmi.frame_id, 7)

    def test_write_multiple_faces(self) -> None:
        ctx = ExamContext()
        result = self._build_result(num_faces=3, lm_count=10)
        self.det._write_to_context(ctx, result)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 3)
        self.assertEqual(len(fmi.all_face_landmarks), 3)
        self.assertEqual(len(fmi.all_face_visibility), 3)
        self.assertEqual(len(fmi.all_face_presence), 3)

    def test_write_no_faces_clears_mesh_points(self) -> None:
        ctx = ExamContext()
        result = self._build_result(num_faces=0)
        self.det._write_to_context(ctx, result)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 0)
        self.assertEqual(fmi.mesh_points, [])

    def test_mesh_points_match_primary_face(self) -> None:
        ctx = ExamContext()
        result = self._build_result(num_faces=2, lm_count=5)
        self.det._write_to_context(ctx, result)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        # mesh_points should be the first face's landmarks
        self.assertEqual(len(fmi.mesh_points), 5)
        first_face_lm0 = result.face_landmarks[0].landmarks[0]
        mp0 = fmi.mesh_points[0]
        self.assertAlmostEqual(mp0[0], first_face_lm0.x)
        self.assertAlmostEqual(mp0[1], first_face_lm0.y)

    def test_write_empty_resets_context(self) -> None:
        ctx = ExamContext()
        frame = _make_frame(frame_id=99)
        self.det._write_empty_to_context(ctx, frame)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 0)
        self.assertEqual(fmi.mesh_points, [])
        self.assertEqual(fmi.frame_id, 99)
        self.assertGreater(fmi.processing_timestamp, 0.0)

    def test_other_context_fields_unchanged(self) -> None:
        """_write_to_context must not mutate any ExamContext field other than face_mesh_info."""
        ctx = ExamContext()
        original_face = ctx.face_info
        original_camera = ctx.camera_state
        original_head = ctx.head_pose_info

        result = self._build_result(num_faces=1, lm_count=5)
        self.det._write_to_context(ctx, result)

        self.assertEqual(ctx.face_info.face_detected, original_face.face_detected)
        self.assertEqual(ctx.camera_state.status, original_camera.status)
        self.assertEqual(ctx.head_pose_info.yaw, original_head.yaw)

    # -- timing / frame_id traceability ------------------------------------

    def test_processing_timestamp_written(self) -> None:
        ctx = ExamContext()
        before = time.time()
        result = self._build_result(num_faces=1)
        self.det._write_to_context(ctx, result)
        after = time.time()

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertGreaterEqual(fmi.processing_timestamp, before - 1.0)
        self.assertLessEqual(fmi.processing_timestamp, after + 1.0)

    def test_processing_time_ms_written(self) -> None:
        ctx = ExamContext()
        result = self._build_result(num_faces=1)
        result.processing_time_ms = 12.5
        self.det._write_to_context(ctx, result)
        self.assertAlmostEqual(ctx.face_mesh_info.processing_time_ms, 12.5)


# ---------------------------------------------------------------------------
# 9. Process orchestration
# ---------------------------------------------------------------------------

class TestProcessOrchestration(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_landmarker = MagicMock()
        self.det = _make_initialized_detector(
            num_faces=1, mock_landmarker=self.mock_landmarker
        )

    def test_process_skips_when_not_running(self) -> None:
        ctx = ExamContext()
        self.det._running = False
        self.det.process(ctx)
        # face_mesh_info must stay at defaults
        self.assertEqual(ctx.face_mesh_info.face_count, 0)

    def test_process_skips_when_no_frame(self) -> None:
        ctx = ExamContext()
        # current_frame is None by default
        self.det.process(ctx)
        self.assertEqual(ctx.face_mesh_info.face_count, 0)

    def test_process_writes_empty_when_no_face_detected(self) -> None:
        ctx = ExamContext()
        frame = _make_frame(frame_id=5)
        ctx.current_frame = frame
        fi = ctx.face_info
        fi.face_detected = False
        ctx.face_info = fi

        self.det.process(ctx)
        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 0)
        self.assertEqual(fmi.frame_id, 5)

    def test_process_runs_extraction_when_face_detected(self) -> None:
        ctx = ExamContext()
        frame = _make_frame(frame_id=88)
        ctx.current_frame = frame

        fi = ctx.face_info
        fi.face_detected = True
        fi.face_count = 1
        ctx.face_info = fi

        self.mock_landmarker.detect.return_value = _make_mp_landmarker_result(
            num_faces=1, lm_per_face=20
        )
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ):
            self.det.process(ctx)

        fmi: FaceMeshInfo = ctx.face_mesh_info
        self.assertEqual(fmi.face_count, 1)
        self.assertEqual(fmi.frame_id, 88)

    def test_process_logs_error_on_extraction_failure(self) -> None:
        ctx = ExamContext()
        frame = _make_frame()
        ctx.current_frame = frame

        fi = ctx.face_info
        fi.face_detected = True
        fi.face_count = 1
        ctx.face_info = fi

        self.mock_landmarker.detect.side_effect = RuntimeError("crash")
        with patch(
            "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector._MPImage"
        ):
            # Must not raise; should log and return silently
            try:
                self.det.process(ctx)
            except Exception as exc:
                self.fail(f"process() raised an exception: {exc}")


# ---------------------------------------------------------------------------
# 10. Model resolution
# ---------------------------------------------------------------------------

class TestModelResolution(unittest.TestCase):

    def setUp(self) -> None:
        self.det = _make_detector()

    def test_explicit_missing_path_raises(self) -> None:
        self.det._config = LandmarkDetectionConfig(
            model_path=Path("/definitely/does/not/exist/model.task")
        )
        with self.assertRaises(LandmarkDetectorModelNotFoundError):
            self.det._resolve_model_path()

    def test_cached_model_returned(self) -> None:
        with patch("pathlib.Path.exists", return_value=True):
            self.det._config = LandmarkDetectionConfig(
                model_cache_dir=Path("/fake/cache")
            )
            result = self.det._resolve_model_path()
        self.assertEqual(result, Path("/fake/cache") / FACE_LANDMARKER_MODEL_FILENAME)

    def test_download_called_when_no_cache(self) -> None:
        with patch("pathlib.Path.exists", return_value=False), \
             patch.object(self.det, "_download_model") as mock_dl:
            fake = Path("/fake/model.task")
            mock_dl.return_value = fake
            result = self.det._resolve_model_path()
        mock_dl.assert_called_once()
        self.assertEqual(result, fake)

    def test_download_failure_raises_model_not_found(self) -> None:
        import urllib.error
        with patch("pathlib.Path.exists", return_value=False), \
             patch(
                 "ai_engine.detectors.landmark_detection.mediapipe_landmark_detector"
                 ".urllib.request.urlretrieve",
                 side_effect=urllib.error.URLError("no network"),
             ), \
             patch("pathlib.Path.mkdir"):
            with self.assertRaises(LandmarkDetectorModelNotFoundError):
                self.det._download_model(Path("/tmp/model.task"))


if __name__ == "__main__":
    unittest.main()
