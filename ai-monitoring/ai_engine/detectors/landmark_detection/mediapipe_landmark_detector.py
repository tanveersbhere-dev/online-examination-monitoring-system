"""
MediaPipe Face Landmark Detection implementation.

Uses the MediaPipe Tasks API (v0.10+) with the ``face_landmarker.task``
model that returns 478 normalised 3-D face-mesh landmarks per face
(468 canonical face-mesh + 10 iris keypoints).

Model auto-download
-------------------
The ``.task`` model file is downloaded from the official Google MediaPipe
storage bucket on first initialisation and cached locally.  If the network
is unavailable and no cached file exists, a
``LandmarkDetectorModelNotFoundError`` is raised at ``initialize()`` time.

Thread safety
-------------
MediaPipe Tasks API objects are NOT thread-safe.  Use one detector instance
per processing thread.

Scope restrictions (enforced by design)
----------------------------------------
This class ONLY performs landmark extraction.  It reads from ExamContext
exclusively via ``context.current_frame`` and ``context.face_info``.  It
writes exclusively to ``context.face_mesh_info``.  No other ExamContext field
is ever read or written.
"""
import logging
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from ai_engine.camera.frame import Frame
from ai_engine.core.exam_context import ExamContext, FaceMeshInfo
from ai_engine.detectors.landmark_detection.detector import LandmarkDetectorInterface
from ai_engine.detectors.landmark_detection.exceptions import (
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

logger = logging.getLogger("ai_engine.detectors.landmark_detection")

# ---------------------------------------------------------------------------
# Lazy MediaPipe import — keeps the module importable without MediaPipe
# installed (unit tests can mock the detector entirely).
# ---------------------------------------------------------------------------
try:
    from mediapipe.tasks.python.vision import (
        FaceLandmarker as _MPFaceLandmarker,
    )
    from mediapipe.tasks.python.vision import (
        FaceLandmarkerOptions as _MPFaceLandmarkerOptions,
    )
    from mediapipe.tasks.python.core.base_options import (
        BaseOptions as _MPBaseOptions,
    )
    from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
        VisionTaskRunningMode as _RunningMode,
    )
    from mediapipe import Image as _MPImage
    from mediapipe import ImageFormat as _MPImageFormat

    _MEDIAPIPE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MEDIAPIPE_AVAILABLE = False
    logger.warning(
        "MediaPipe is not installed. MediaPipeLandmarkDetector will raise "
        "MediaPipeInitializationError on initialize()."
    )


class MediaPipeLandmarkDetector(LandmarkDetectorInterface):
    """
    Concrete face landmark detector backed by the MediaPipe Tasks API.

    This is the only class in the engine that directly imports or calls
    MediaPipe face-landmark APIs.  All other modules interact through
    ``LandmarkDetectorInterface``.

    Usage example
    -------------
    >>> from ai_engine.detectors.landmark_detection.models import LandmarkDetectionConfig
    >>> from ai_engine.detectors.landmark_detection.mediapipe_landmark_detector import (
    ...     MediaPipeLandmarkDetector,
    ... )
    >>> config = LandmarkDetectionConfig(num_faces=1, min_face_detection_confidence=0.6)
    >>> detector = MediaPipeLandmarkDetector(config=config)
    >>> detector.initialize()
    >>> detector.start()
    >>> result = detector.extract(frame, num_faces=1)
    >>> detector.stop()
    >>> detector.cleanup()
    """

    def __init__(self, config: Optional[LandmarkDetectionConfig] = None) -> None:
        """
        Args:
            config: Optional configuration.  Falls back to conservative
                    production defaults when not provided.
        """
        super().__init__(config=config or LandmarkDetectionConfig())
        self._landmarker: Optional[object] = None
        self._initialized: bool = False
        self._running: bool = False
        self._model_path: Optional[Path] = None

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """
        Resolves (and downloads if necessary) the model file, then constructs
        the MediaPipe FaceLandmarker in IMAGE running mode.

        Raises:
            MediaPipeInitializationError:      Library not installed or options rejected.
            LandmarkDetectorModelNotFoundError: Model file unavailable.
        """
        if self._initialized:
            logger.debug(
                "MediaPipeLandmarkDetector already initialized — skipping."
            )
            return

        logger.info("Initializing MediaPipeLandmarkDetector …")

        if not _MEDIAPIPE_AVAILABLE:
            raise MediaPipeInitializationError(
                "MediaPipe is not installed. Install it with: pip install mediapipe"
            )

        self._model_path = self._resolve_model_path()
        logger.info(f"Face Landmarker model: {self._model_path}")

        try:
            base_options = _MPBaseOptions(
                model_asset_path=str(self._model_path)
            )
            options = _MPFaceLandmarkerOptions(
                base_options=base_options,
                running_mode=_RunningMode.IMAGE,
                num_faces=self._config.num_faces,
                min_face_detection_confidence=self._config.min_face_detection_confidence,
                min_face_presence_confidence=self._config.min_face_presence_confidence,
                min_tracking_confidence=self._config.min_tracking_confidence,
                output_face_blendshapes=self._config.output_face_blendshapes,
            )
            self._landmarker = _MPFaceLandmarker.create_from_options(options)
            self._initialized = True
            logger.info(
                "MediaPipeLandmarkDetector initialized successfully "
                f"[num_faces={self._config.num_faces}, "
                f"min_face_detection_confidence="
                f"{self._config.min_face_detection_confidence}]"
            )
        except Exception as exc:
            raise MediaPipeInitializationError(
                f"Failed to create MediaPipe FaceLandmarker: {exc}"
            ) from exc

    def start(self) -> None:
        """
        Marks the detector as active.

        Raises:
            LandmarkDetectorStateError: If initialize() has not succeeded.
        """
        if not self._initialized:
            raise LandmarkDetectorStateError(
                "Cannot start: call initialize() before start()."
            )
        self._running = True
        logger.info("MediaPipeLandmarkDetector started.")

    def process(self, context: ExamContext) -> None:
        """
        Orchestration method that reads from ExamContext, runs extraction,
        and writes results back to ``context.face_mesh_info``.

        Silent no-ops when:
          • The detector is not running.
          • No frame is available in the context.
          • Face detection indicates no face is present.

        Reads:  ``context.current_frame``, ``context.face_info``
        Writes: ``context.face_mesh_info``
        """
        if not self._running:
            return

        frame = context.current_frame
        if frame is None:
            return

        face_info = context.face_info
        if not face_info.face_detected:
            # No face detected by Module 1 — reset mesh to cleared state
            self._write_empty_to_context(context, frame)
            return

        num_faces = max(1, face_info.face_count)

        try:
            result = self.extract(frame, num_faces=num_faces)
        except LandmarkExtractionError as exc:
            logger.error(f"Landmark extraction failed on frame {frame.frame_id}: {exc}")
            return

        self._write_to_context(context, result)

    def stop(self) -> None:
        """Pauses landmark extraction; may be re-started."""
        self._running = False
        logger.info("MediaPipeLandmarkDetector stopped.")

    def cleanup(self) -> None:
        """Releases MediaPipe resources and resets to uninitialised state."""
        self._running = False
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception as exc:
                logger.warning(
                    f"Error while closing MediaPipe FaceLandmarker: {exc}"
                )
            self._landmarker = None
        self._initialized = False
        logger.info("MediaPipeLandmarkDetector cleaned up.")

    # ------------------------------------------------------------------ #
    #  Core landmark extraction                                            #
    # ------------------------------------------------------------------ #

    def extract(self, frame: Frame, num_faces: int) -> FaceMeshResult:
        """
        Runs face landmark inference on a single frame without mutating any
        shared state.

        Args:
            frame:     Frame containing a valid rgb_frame numpy array.
            num_faces: Maximum number of faces to extract landmarks from.

        Returns:
            FaceMeshResult with one FaceLandmarks entry per detected face.

        Raises:
            LandmarkDetectorStateError: If called before initialize().
            LandmarkExtractionError:    On any inference failure.
        """
        if not self._initialized or self._landmarker is None:
            raise LandmarkDetectorStateError(
                "Detector not initialized. Call initialize() before extract()."
            )

        rgb_image: np.ndarray = frame.rgb_frame
        if rgb_image is None:
            raise LandmarkExtractionError(
                "frame.rgb_frame is None — cannot run landmark inference."
            )

        if rgb_image.size == 0:
            raise LandmarkExtractionError(
                "frame.rgb_frame is empty (zero-size array)."
            )

        if rgb_image.ndim != 3 or rgb_image.shape[2] != 3:
            raise LandmarkExtractionError(
                f"frame.rgb_frame has unexpected shape {rgb_image.shape}; "
                "expected (H, W, 3)."
            )

        inference_start = time.perf_counter()

        try:
            mp_image = _MPImage(
                image_format=_MPImageFormat.SRGB,
                data=np.ascontiguousarray(rgb_image),
            )
            raw_result = self._landmarker.detect(mp_image)
        except Exception as exc:
            raise LandmarkExtractionError(
                f"MediaPipe FaceLandmarker inference error: {exc}"
            ) from exc

        inference_ms = (time.perf_counter() - inference_start) * 1000.0
        processing_timestamp = time.time()

        face_landmarks_list = self._parse_result(
            raw_result=raw_result,
            num_faces=num_faces,
        )

        result = FaceMeshResult(
            face_landmarks=face_landmarks_list,
            face_count=len(face_landmarks_list),
            frame_id=frame.frame_id,
            processing_timestamp=processing_timestamp,
            processing_time_ms=inference_ms,
            frame_width=frame.width,
            frame_height=frame.height,
        )

        if self._config.enable_logging:
            self._log_result(result)

        return result

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_result(
        self,
        raw_result: object,
        num_faces: int,
    ) -> List[FaceLandmarks]:
        """
        Converts the raw ``FaceLandmarkerResult`` into a list of
        ``FaceLandmarks`` objects capped at ``num_faces``.

        Args:
            raw_result: mediapipe.tasks.python.vision.face_landmarker.FaceLandmarkerResult
            num_faces:  Maximum number of faces to return.

        Returns:
            List of FaceLandmarks, one per detected face, up to ``num_faces``.
        """
        raw_face_landmarks = getattr(raw_result, "face_landmarks", None)
        if not raw_face_landmarks:
            logger.debug("FaceLandmarker returned no landmark data.")
            return []

        result_faces: List[FaceLandmarks] = []
        for face_idx, mp_landmarks in enumerate(raw_face_landmarks[:num_faces]):
            landmarks = [
                Landmark(
                    x=float(lm.x) if lm.x is not None else 0.0,
                    y=float(lm.y) if lm.y is not None else 0.0,
                    z=float(lm.z) if lm.z is not None else 0.0,
                    visibility=(
                        float(lm.visibility)
                        if lm.visibility is not None
                        else None
                    ),
                    presence=(
                        float(lm.presence)
                        if lm.presence is not None
                        else None
                    ),
                    index=lm_idx,
                )
                for lm_idx, lm in enumerate(mp_landmarks)
            ]

            result_faces.append(
                FaceLandmarks(
                    landmarks=landmarks,
                    landmark_count=len(landmarks),
                    face_index=face_idx,
                    detection_confidence=None,  # not provided by FaceLandmarker result
                )
            )

        return result_faces

    def _write_to_context(
        self,
        context: ExamContext,
        result: FaceMeshResult,
    ) -> None:
        """
        Writes a ``FaceMeshResult`` into ``context.face_mesh_info`` under the
        context lock.

        Only ``context.face_mesh_info`` is mutated.

        Args:
            context: Shared ExamContext instance.
            result:  Completed FaceMeshResult from extract().
        """
        with context.lock():
            fmi = context.face_mesh_info

            fmi.face_count = result.face_count
            fmi.processing_timestamp = result.processing_timestamp
            fmi.processing_time_ms = result.processing_time_ms
            fmi.frame_id = result.frame_id

            # Populate structured per-face landmark lists
            fmi.all_face_landmarks = []
            fmi.all_face_visibility = []
            fmi.all_face_presence = []

            for face in result.face_landmarks:
                fmi.all_face_landmarks.append(
                    [(lm.x, lm.y, lm.z) for lm in face.landmarks]
                )
                fmi.all_face_visibility.append(
                    [lm.visibility for lm in face.landmarks]
                )
                fmi.all_face_presence.append(
                    [lm.presence for lm in face.landmarks]
                )

            # Populate backward-compatible mesh_points from the primary face
            if result.primary_landmarks is not None:
                fmi.mesh_points = [
                    (lm.x, lm.y, lm.z)
                    for lm in result.primary_landmarks.landmarks
                ]
            else:
                fmi.mesh_points = []

            context.face_mesh_info = fmi

    def _write_empty_to_context(
        self,
        context: ExamContext,
        frame: Frame,
    ) -> None:
        """
        Resets face_mesh_info to a cleared state (no landmarks) while keeping
        timing and frame-id current.

        Used when face_info.face_detected is False so downstream modules can
        distinguish between 'no face' and 'stale data'.
        """
        with context.lock():
            fmi = FaceMeshInfo()
            fmi.face_count = 0
            fmi.processing_timestamp = time.time()
            fmi.processing_time_ms = 0.0
            fmi.frame_id = frame.frame_id
            context.face_mesh_info = fmi

    def _log_result(self, result: FaceMeshResult) -> None:
        """Emits per-frame landmark diagnostic messages."""
        logger.debug(
            f"LandmarkDetection | FrameID={result.frame_id} | "
            f"Faces={result.face_count} | "
            f"InferenceTime={result.processing_time_ms:.2f} ms"
        )
        if result.face_count > 0 and result.primary_landmarks:
            logger.info(
                f"LandmarkDetection: {result.face_count} face(s) processed | "
                f"Landmarks={result.primary_landmarks.landmark_count} "
                f"(primary face)"
            )
        else:
            logger.debug(
                "LandmarkDetection: No landmarks extracted in this frame."
            )

    def _resolve_model_path(self) -> Path:
        """
        Returns the path to the face landmarker ``.task`` model file.

        Priority:
          1. Explicitly configured ``config.model_path``.
          2. Cached file in ``config.model_cache_dir``.
          3. Download from official bucket and cache.

        Raises:
            LandmarkDetectorModelNotFoundError: If no model can be resolved.
        """
        if self._config.model_path is not None:
            explicit = Path(self._config.model_path)
            if explicit.exists():
                return explicit
            raise LandmarkDetectorModelNotFoundError(
                f"Configured model_path does not exist: {explicit}"
            )

        cache_dir = Path(self._config.model_cache_dir)
        cached = cache_dir / FACE_LANDMARKER_MODEL_FILENAME
        if cached.exists():
            logger.debug(f"Using cached face landmarker model: {cached}")
            return cached

        logger.info(
            "Face landmarker model not cached. Downloading from:\n"
            f"  {FACE_LANDMARKER_MODEL_URL}"
        )
        return self._download_model(cached)

    def _download_model(self, destination: Path) -> Path:
        """
        Downloads the face landmarker model to *destination*.

        Args:
            destination: Full file path (including filename) for the output.

        Returns:
            *destination* on success.

        Raises:
            LandmarkDetectorModelNotFoundError: On network or I/O failure.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(
                FACE_LANDMARKER_MODEL_URL, str(destination)
            )
            logger.info(
                f"Face landmarker model downloaded → {destination}"
            )
            return destination
        except urllib.error.URLError as exc:
            raise LandmarkDetectorModelNotFoundError(
                f"Failed to download face landmarker model from "
                f"{FACE_LANDMARKER_MODEL_URL}: {exc}"
            ) from exc
        except Exception as exc:
            destination.unlink(missing_ok=True)
            raise LandmarkDetectorModelNotFoundError(
                f"Unexpected error downloading face landmarker model: {exc}"
            ) from exc
