"""
MediaPipe Face Detection implementation.

Uses the MediaPipe Tasks API (v0.10+) with the BlazeFace short-range model.
The model file is downloaded and cached automatically on first initialization.
If the model cannot be fetched (e.g., no network), a FaceDetectorModelNotFoundError
is raised at initialize() time, not at construction time.

Implementation is deliberately isolated — the only external surface is
FaceDetectorInterface. Replacing this file with a different backend (e.g.,
dlib, InsightFace) does not require changes to any other module.
"""
import logging
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List

import numpy as np

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext
from ai_engine.core.exam_context import FaceInfo
from ai_engine.detectors.face_detection.detector import FaceDetectorInterface
from ai_engine.detectors.face_detection.exceptions import (
    FaceDetectorInitializationError,
    FaceDetectorInferenceError,
    FaceDetectorModelNotFoundError,
)
from ai_engine.detectors.face_detection.models import (
    FaceDetectionConfig,
    BLAZE_FACE_SHORT_RANGE_MODEL_URL,
    BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME,
)
from ai_engine.detectors.face_detection.result import DetectedFace, FaceDetectionResult

logger = logging.getLogger("ai_engine.detectors.face_detection")

# Lazy-import MediaPipe — keeps the module importable even when MediaPipe is
# absent (e.g., during unit tests that mock the detector).
try:
    from mediapipe.tasks.python.vision import FaceDetector as _MPFaceDetector
    from mediapipe.tasks.python.vision import FaceDetectorOptions as _MPFaceDetectorOptions
    from mediapipe.tasks.python.core.base_options import BaseOptions as _MPBaseOptions
    from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
        VisionTaskRunningMode as _RunningMode,
    )
    from mediapipe import Image as _MPImage
    from mediapipe import ImageFormat as _MPImageFormat
    _MEDIAPIPE_AVAILABLE = True
except ImportError:
    _MEDIAPIPE_AVAILABLE = False
    logger.warning(
        "MediaPipe is not installed. MediaPipeFaceDetector will raise "
        "FaceDetectorInitializationError on initialize()."
    )


class MediaPipeFaceDetector(FaceDetectorInterface):
    """
    Concrete face detector backed by the MediaPipe Tasks API.

    This class is the only component in the engine that imports or calls
    MediaPipe. All other modules interact with the face detector through the
    FaceDetectorInterface abstraction.

    Thread Safety
    -------------
    MediaPipe Tasks API detectors are NOT thread-safe. This detector is
    designed to be used from a single processing thread. If concurrent access
    is required, create one instance per thread.

    Usage
    -----
    >>> from ai_engine.detectors.face_detection.models import FaceDetectionConfig
    >>> from ai_engine.detectors.face_detection.mediapipe_detector import MediaPipeFaceDetector
    >>> config = FaceDetectionConfig(min_detection_confidence=0.6, max_num_faces=2)
    >>> detector = MediaPipeFaceDetector(config=config)
    >>> detector.initialize()
    >>> detector.start()
    >>> result = detector.detect(frame)
    >>> detector.stop()
    >>> detector.cleanup()
    """

    def __init__(self, config: Optional[FaceDetectionConfig] = None) -> None:
        """
        Args:
            config: Optional configuration. Defaults to FaceDetectionConfig()
                    with conservative defaults when not provided.
        """
        super().__init__(config=config or FaceDetectionConfig())
        self._detector: Optional[object] = None
        self._initialized: bool = False
        self._running: bool = False
        self._model_path: Optional[Path] = None

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """
        Downloads (if needed) and loads the BlazeFace model, then constructs
        the MediaPipe FaceDetector.

        Raises:
            FaceDetectorInitializationError: If MediaPipe is not installed.
            FaceDetectorModelNotFoundError:  If the model file is unavailable.
        """
        if self._initialized:
            logger.debug("MediaPipeFaceDetector is already initialized; skipping.")
            return

        logger.info("Initializing MediaPipeFaceDetector …")

        if not _MEDIAPIPE_AVAILABLE:
            raise FaceDetectorInitializationError(
                "MediaPipe is not installed. Install it with: pip install mediapipe"
            )

        self._model_path = self._resolve_model_path()
        logger.info(f"Using face detection model: {self._model_path}")

        try:
            base_options = _MPBaseOptions(model_asset_path=str(self._model_path))
            options = _MPFaceDetectorOptions(
                base_options=base_options,
                running_mode=_RunningMode.IMAGE,
                min_detection_confidence=self._config.min_detection_confidence,
                min_suppression_threshold=self._config.min_suppression_threshold,
            )
            self._detector = _MPFaceDetector.create_from_options(options)
            self._initialized = True
            logger.info(
                "MediaPipeFaceDetector initialized successfully "
                f"[min_confidence={self._config.min_detection_confidence}, "
                f"max_faces={self._config.max_num_faces}]"
            )
        except Exception as exc:
            raise FaceDetectorInitializationError(
                f"Failed to create MediaPipe FaceDetector: {exc}"
            ) from exc

    def start(self) -> None:
        """Marks the detector as running. Must be called after initialize()."""
        if not self._initialized:
            raise FaceDetectorInitializationError(
                "Cannot start: detector has not been initialized. Call initialize() first."
            )
        self._running = True
        logger.info("MediaPipeFaceDetector started.")

    def process(self, context: ExamContext) -> None:
        """
        Reads the current frame from the shared context, runs face detection,
        and writes the result back to context.face_info.

        If no frame is available in the context (e.g., camera not yet active),
        the method returns silently without modifying the context.

        Args:
            context: The shared ExamContext instance.
        """
        if not self._running:
            return

        frame = context.current_frame
        if frame is None:
            return

        try:
            result = self.detect(frame)
        except FaceDetectorInferenceError as exc:
            logger.error(f"Face detection inference failed: {exc}")
            return

        self._write_to_context(context, result)

    def stop(self) -> None:
        """Pauses detection; the detector can be re-started."""
        self._running = False
        logger.info("MediaPipeFaceDetector stopped.")

    def cleanup(self) -> None:
        """Releases the MediaPipe detector and frees native resources."""
        self._running = False
        if self._detector is not None:
            try:
                self._detector.close()
            except Exception as exc:
                logger.warning(f"Error while closing MediaPipe detector: {exc}")
            self._detector = None
        self._initialized = False
        logger.info("MediaPipeFaceDetector cleaned up.")

    # ------------------------------------------------------------------ #
    #  Core detection                                                      #
    # ------------------------------------------------------------------ #

    def detect(self, frame: Frame) -> FaceDetectionResult:
        """
        Runs face detection on a single frame.

        Args:
            frame: A Frame object containing at minimum the rgb_frame array.

        Returns:
            FaceDetectionResult with all faces found (sorted by confidence).

        Raises:
            FaceDetectorInitializationError: If called before initialize().
            FaceDetectorInferenceError:      On any MediaPipe runtime error.
        """
        if not self._initialized or self._detector is None:
            raise FaceDetectorInitializationError(
                "Detector is not initialized. Call initialize() before detect()."
            )

        rgb_image: np.ndarray = frame.rgb_frame
        if rgb_image is None:
            raise FaceDetectorInferenceError("frame.rgb_frame is None — cannot run inference.")

        inference_start = time.perf_counter()

        try:
            mp_image = _MPImage(
                image_format=_MPImageFormat.SRGB,
                data=np.ascontiguousarray(rgb_image)
            )
            raw_result = self._detector.detect(mp_image)
        except Exception as exc:
            raise FaceDetectorInferenceError(
                f"MediaPipe inference error: {exc}"
            ) from exc

        inference_ms = (time.perf_counter() - inference_start) * 1000.0
        detection_timestamp = time.time()

        detected_faces = self._parse_detections(
            raw_result=raw_result,
            frame_width=frame.width,
            frame_height=frame.height,
        )

        result = FaceDetectionResult(
            faces=detected_faces,
            face_count=len(detected_faces),
            frame_id=frame.frame_id,
            detection_timestamp=detection_timestamp,
            inference_time_ms=inference_ms,
            frame_width=frame.width,
            frame_height=frame.height,
        )

        if self._config.enable_logging:
            self._log_result(result)

        return result

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_detections(
        self,
        raw_result: object,
        frame_width: int,
        frame_height: int,
    ) -> List[DetectedFace]:
        """
        Converts MediaPipe DetectionResult into a list of DetectedFace objects.

        Results are sorted by confidence descending and capped at max_num_faces.

        Args:
            raw_result: The mediapipe.tasks.python.components.containers.detections.DetectionResult
                        returned by the detector.
            frame_width:  Width of the frame in pixels.
            frame_height: Height of the frame in pixels.

        Returns:
            List of DetectedFace objects, sorted by confidence descending.
        """
        detections = getattr(raw_result, "detections", None)
        if not detections:
            return []

        faces: List[DetectedFace] = []
        for det in detections:
            # Extract bounding box (pixel coordinates)
            bb = det.bounding_box
            bbox = (
                float(bb.origin_x),
                float(bb.origin_y),
                float(bb.width),
                float(bb.height),
            )

            # Extract confidence — MediaPipe stores score in categories list
            confidence = 0.0
            if det.categories:
                confidence = float(det.categories[0].score)

            # Extract keypoints (normalized → keep as-is, [0,1] range)
            keypoints = []
            if det.keypoints:
                keypoints = [
                    (float(kp.x), float(kp.y))
                    for kp in det.keypoints
                    if kp.x is not None and kp.y is not None
                ]

            faces.append(DetectedFace(
                bbox=bbox,
                confidence=confidence,
                keypoints=keypoints,
            ))

        # Sort by confidence descending, then cap at max_num_faces
        faces.sort(key=lambda f: f.confidence, reverse=True)
        return faces[: self._config.max_num_faces]

    def _write_to_context(
        self,
        context: ExamContext,
        result: FaceDetectionResult,
    ) -> None:
        """
        Writes a FaceDetectionResult into context.face_info under the context
        lock to ensure thread safety.

        Only ExamContext.face_info is modified — no other fields are touched.

        Args:
            context: The shared ExamContext instance.
            result:  The detection result to write.
        """
        with context.lock():
            fi = context.face_info

            fi.face_count = result.face_count
            fi.face_detected = result.is_face_detected
            fi.detection_timestamp = result.detection_timestamp
            fi.frame_id = result.frame_id
            fi.all_bboxes = result.all_bboxes
            fi.all_confidences = result.all_confidences

            if result.primary_face is not None:
                primary = result.primary_face
                fi.confidence = primary.confidence
                fi.bbox = primary.bbox
                # Map keypoints to named landmark dict (MediaPipe blaze order)
                _KEYPOINT_NAMES = [
                    "right_eye", "left_eye", "nose_tip",
                    "mouth_center", "right_ear_tragion", "left_ear_tragion",
                ]
                fi.landmarks = [
                    {name: kp[idx] for idx, name in enumerate(["x", "y"])}
                    | {"name": kp_name}
                    for kp_name, kp in zip(_KEYPOINT_NAMES, primary.keypoints)
                ]
            else:
                # Reset to cleared state when no face is found
                fi.confidence = 0.0
                fi.bbox = (0.0, 0.0, 0.0, 0.0)
                fi.landmarks = []

            context.face_info = fi

    def _log_result(self, result: FaceDetectionResult) -> None:
        """Logs per-frame detection diagnostics."""
        logger.debug(
            f"FaceDetection | FrameID={result.frame_id} | "
            f"Faces={result.face_count} | "
            f"InferenceTime={result.inference_time_ms:.2f} ms | "
            f"PrimaryConfidence="
            f"{result.primary_face.confidence:.3f if result.primary_face else 0.0}"
        )
        if result.face_count > 0 and result.primary_face:
            logger.info(
                f"FaceDetection: {result.face_count} face(s) detected | "
                f"Confidence={result.primary_face.confidence:.3f}"
            )
        else:
            logger.debug("FaceDetection: No face detected in frame.")

    def _resolve_model_path(self) -> Path:
        """
        Returns the path to the face detection model file.

        Priority:
        1. Explicitly configured model_path in FaceDetectionConfig.
        2. Cached file in the model_cache_dir.
        3. Download from the official MediaPipe storage bucket and cache it.

        Returns:
            Absolute Path to the model file.

        Raises:
            FaceDetectorModelNotFoundError: If no model can be found or fetched.
        """
        # 1. Explicit model path
        if self._config.model_path is not None:
            explicit = Path(self._config.model_path)
            if explicit.exists():
                return explicit
            raise FaceDetectorModelNotFoundError(
                f"Configured model path does not exist: {explicit}"
            )

        # 2. Cached model
        cache_dir = Path(self._config.model_cache_dir)
        cached_model = cache_dir / BLAZE_FACE_SHORT_RANGE_MODEL_FILENAME
        if cached_model.exists():
            logger.debug(f"Using cached model: {cached_model}")
            return cached_model

        # 3. Download
        logger.info(
            f"Model not found in cache. Downloading from:\n  {BLAZE_FACE_SHORT_RANGE_MODEL_URL}"
        )
        return self._download_model(cached_model)

    def _download_model(self, destination: Path) -> Path:
        """
        Downloads the model file to destination.

        Args:
            destination: Full path (including filename) for the downloaded model.

        Returns:
            The destination path on success.

        Raises:
            FaceDetectorModelNotFoundError: If the download fails.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(BLAZE_FACE_SHORT_RANGE_MODEL_URL, str(destination))
            logger.info(f"Model downloaded successfully → {destination}")
            return destination
        except urllib.error.URLError as exc:
            raise FaceDetectorModelNotFoundError(
                f"Failed to download face detection model from "
                f"{BLAZE_FACE_SHORT_RANGE_MODEL_URL}: {exc}"
            ) from exc
        except Exception as exc:
            # Clean up partial file if download was interrupted
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise FaceDetectorModelNotFoundError(
                f"Unexpected error during model download: {exc}"
            ) from exc
