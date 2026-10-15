"""
Context Builder
===============
Creates and maintains the ExamContext for the playground session.
Also decodes raw JPEG bytes from the browser WebSocket into a Frame object.

The AI engine is NEVER modified here — we only call its public constructors
and use Frame.from_bgr_image(), which is the documented factory method.
"""
import time
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("playground.context_builder")


class ContextBuilder:
    """
    Thin adapter between the WebSocket byte stream and the AI Engine context.

    Responsibilities:
    - Create a single ExamContext that lives for the entire monitoring session.
    - Maintain the explicit MonitoringSessionContext (standalone / PPR attached).
    - Decode JPEG bytes → BGR numpy array → Frame dataclass.
    - Track frame counter and estimated FPS.
    """

    def __init__(self, session_context=None) -> None:
        from ..adapters.session_context import MonitoringSessionContext
        self._session_context = session_context or MonitoringSessionContext.from_env()
        self._contexts = {}
        self._frame_counter: int = 0
        self._session_start: float = self._session_context.start_time
        self._last_frame_time: float = time.time()
        self._current_fps: float = 0.0

        # Initialise default contexts
        self._context = self.get_context("camera_1")

    def _build_context_instance(self):
        """Construct a new ExamContext with session info."""
        try:
            from ai_engine.core.exam_context import ExamContext, SessionInfo, SystemState
            from ai_engine.core.enums import ExamStatus

            ctx = ExamContext()

            with ctx.lock():
                # Populate session identity from MonitoringSessionContext
                sess = ctx.session_info
                sess.exam_id = self._session_context.exam_id
                sess.student_id = self._session_context.student_id
                sess.start_time = self._session_start
                ctx.session_info = sess

                # Attach explicit host session context
                ctx.monitoring_session = self._session_context

                # Mark as IN_PROGRESS so processors don't guard against NOT_STARTED
                state = ctx.system_state
                state.status = ExamStatus.IN_PROGRESS
                state.active_profile = "normal"
                ctx.system_state = state

            return ctx
        except Exception as e:
            logger.critical(f"Failed to create ExamContext: {e}", exc_info=True)
            raise

    def get_context(self, camera_id: str = "camera_1"):
        """Get or create the dedicated ExamContext for the specified camera."""
        normalized_cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id
        if normalized_cam_id not in self._contexts:
            ctx = self._build_context_instance()
            self._contexts[normalized_cam_id] = ctx
            logger.info(
                f"ExamContext created for camera '{normalized_cam_id}' in session "
                f"{self._session_context.monitoring_session_id}."
            )
        return self._contexts[normalized_cam_id]

    def decode_and_inject(self, jpeg_bytes: bytes, camera_id: str = "camera_1") -> Optional[object]:
        """
        Decode JPEG bytes → BGR numpy array → Frame → inject into the camera's dedicated ExamContext.
        Returns the created Frame, or None if decoding fails.
        """
        try:
            np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if bgr is None:
                logger.warning("cv2.imdecode returned None — corrupted JPEG?")
                return None
        except Exception as e:
            logger.error(f"JPEG decode error: {e}")
            return None

        # FPS estimation
        now = time.time()
        elapsed = now - self._last_frame_time
        self._last_frame_time = now
        if elapsed > 0:
            self._current_fps = 1.0 / elapsed

        self._frame_counter += 1

        try:
            from ai_engine.camera.frame import Frame

            # Resolve logical camera identity: normalize legacy 'playground_webcam' or empty to 'camera_1'
            normalized_cam_id = "camera_1" if (not camera_id or camera_id == "playground_webcam") else camera_id

            frame = Frame.from_bgr_image(
                bgr_image=bgr,
                camera_id=normalized_cam_id,
                fps=self._current_fps,
                frame_id=self._frame_counter,
                timestamp=now,
            )
        except Exception as e:
            logger.error(f"Frame construction error: {e}")
            return None

        # Inject into the camera-specific context
        target_ctx = self.get_context(normalized_cam_id)
        target_ctx.current_frame = frame
        self._context = target_ctx

        return frame

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def context(self):
        return self.get_context("camera_1")

    @property
    def frame_counter(self) -> int:
        return self._frame_counter

    @property
    def current_fps(self) -> float:
        return round(self._current_fps, 2)

    @property
    def session_context(self):
        return self._session_context
