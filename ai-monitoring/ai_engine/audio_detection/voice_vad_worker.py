"""
Voice VAD Worker & Silero VAD Detector
======================================
Dedicated isolated worker for microphone human voice detection using Silero VAD on CPU.

Specifications:
- Strictly Camera 1 (laptop/PC) microphone audio.
- Local ONNX execution on CPU (zero network requests, sub-millisecond inference).
- Distinguishes human voice from acoustic background noise (fans, AC, keyboard clicks, typing).
- Triggers only after >= 1.5s accumulated qualifying sustained speech.
- Maintains exactly one active violation for the episode.
- Resolves only after 5 continuous seconds WITHOUT human voice (acoustic noise does NOT reset timer).
- Captures 16kHz 16-bit mono PCM WAV evidence (1.5s pre-roll + speech episode + 5s trailing audio).
"""
from __future__ import annotations

import io
import logging
import math
import os
import threading
import time
import uuid
import wave
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import onnxruntime as ort

logger = logging.getLogger("playground.voice_vad")

# Default model path in local project
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "vad" / "silero_vad.onnx"


class SileroVADDetector:
    """
    Lightweight, thread-safe Silero VAD ONNX wrapper executing locally on CPU.
    Takes 512 samples (32ms at 16kHz) and outputs speech probability [0.0, 1.0].
    """

    SAMPLE_RATE = 16000
    WINDOW_SIZE = 512  # 32ms at 16kHz
    CONTEXT_SIZE = 64

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self._session: Optional[ort.InferenceSession] = None
        self._state: np.ndarray = np.zeros((2, 1, 128), dtype=np.float32)
        self._context: np.ndarray = np.zeros((1, self.CONTEXT_SIZE), dtype=np.float32)
        self._sr_tensor: np.ndarray = np.array(self.SAMPLE_RATE, dtype=np.int64)
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> bool:
        with self._lock:
            if self._initialized:
                return True
            try:
                # If local model doesn't exist, check torch hub cache
                target_path = self.model_path
                if not target_path.exists():
                    cache_path = Path(os.path.expanduser("~/.cache/torch/hub/snakers4_silero-vad_master/src/silero_vad/data/silero_vad.onnx"))
                    if cache_path.exists():
                        target_path = cache_path

                if not target_path.exists():
                    logger.error(f"Silero VAD model not found at {target_path}")
                    return False

                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                opts.log_severity_level = 3  # Errors only

                self._session = ort.InferenceSession(
                    str(target_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self.reset_states()
                self._initialized = True
                logger.info(f"[SileroVAD] Loaded model successfully from {target_path}")
                return True
            except Exception as e:
                logger.error(f"[SileroVAD] Failed to initialize model: {e}", exc_info=True)
                return False

    def reset_states(self) -> None:
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT_SIZE), dtype=np.float32)

    def predict_chunk(self, chunk_float32: np.ndarray) -> float:
        """
        Predict speech probability for a single 512-sample float32 chunk (-1.0 to 1.0).
        Thread-safe, returns float in [0.0, 1.0].
        """
        if not self._initialized:
            if not self.initialize():
                return 0.0

        if chunk_float32.shape != (1, self.WINDOW_SIZE):
            chunk_float32 = chunk_float32.reshape(1, self.WINDOW_SIZE)

        with self._lock:
            try:
                # Concatenate sliding context + current 512 samples
                inp = np.concatenate([self._context, chunk_float32], axis=1).astype(np.float32)
                ort_inputs = {
                    "input": inp,
                    "state": self._state,
                    "sr": self._sr_tensor,
                }
                out, new_state = self._session.run(None, ort_inputs)
                self._state = new_state
                self._context = inp[:, -self.CONTEXT_SIZE:]
                prob = float(out[0, 0])
                return prob
            except Exception as e:
                logger.debug(f"[SileroVAD] Inference error: {e}")
                return 0.0


class VoiceActivityWorker:
    """
    Dedicated background worker for Camera 1 microphone audio ingress,
    Silero VAD evaluation, and authoritative human voice violation timing.
    """

    SPEECH_THRESHOLD = 0.40          # Probability threshold for speech chunk
    TRIGGER_DURATION_SEC = 1.50      # Speech activity required to trigger violation
    RESOLVE_NO_VOICE_SEC = 5.00      # Continuous no-voice time required to resolve
    PRE_ROLL_SEC = 1.50              # Audio pre-roll retained prior to speech trigger
    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2             # 16-bit mono PCM

    def __init__(self, evidence_dir: Optional[Path] = None):
        self._detector = SileroVADDetector()
        self._evidence_dir = evidence_dir or (Path(__file__).resolve().parent.parent.parent / "backend" / "evidence")
        self._evidence_dir.mkdir(parents=True, exist_ok=True)

        # Ingress PCM buffer (int16 samples)
        self._pcm_queue: Deque[np.int16] = deque()
        self._lock = threading.RLock()

        # Pre-roll rolling ring buffer (stores Int16 samples)
        self._max_pre_roll_samples = int(self.PRE_ROLL_SEC * self.SAMPLE_RATE)
        self._pre_roll_buffer: Deque[np.int16] = deque(maxlen=self._max_pre_roll_samples)

        # Active episode recorded audio samples
        self._active_recording: List[np.int16] = []

        # Timing and state machine
        self._speech_accum_sec: float = 0.0
        self._continuous_no_voice_sec: float = 0.0
        self._inter_word_gap_sec: float = 0.0
        self._is_active_violation: bool = False
        self._active_violation_id: Optional[str] = None
        self._episode_start_time: float = 0.0
        self._peak_confidence: float = 0.0
        self._confidence_samples: List[float] = []

        # Current audio telemetry
        self._latest_speech_prob: float = 0.0
        self._latest_db_level: float = -100.0
        self._last_ingress_time: float = 0.0

        # Background processing thread
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def initialize(self) -> bool:
        return self._detector.initialize()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self.initialize()
            self._worker_thread = threading.Thread(target=self._process_loop, daemon=True, name="VoiceVADWorker")
            self._worker_thread.start()
            logger.info("[VoiceVADWorker] Background processing thread started.")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        logger.info("[VoiceVADWorker] Background processing thread stopped.")

    def push_pcm_bytes(self, data: bytes) -> None:
        """
        Accepts binary 16kHz 16-bit mono PCM chunks from WebSocket.
        Thread-safe, non-blocking ingestion.
        """
        if not data:
            return
        try:
            samples = np.frombuffer(data, dtype=np.int16)
            with self._lock:
                self._pcm_queue.extend(samples)
                self._last_ingress_time = time.time()
        except Exception as e:
            logger.debug(f"[VoiceVADWorker] Error pushing PCM bytes: {e}")

    def _process_loop(self) -> None:
        """Continuously pulls 512-sample chunks from _pcm_queue and evaluates Silero VAD."""
        while self._running:
            chunk = None
            with self._lock:
                if len(self._pcm_queue) >= 512:
                    chunk = np.array([self._pcm_queue.popleft() for _ in range(512)], dtype=np.int16)

            if chunk is None:
                time.sleep(0.010)
                continue

            self._process_chunk(chunk)

    def _process_chunk(self, chunk_int16: np.ndarray) -> None:
        """Evaluates a single 512-sample chunk through Silero VAD and updates state machine."""
        dt = 512.0 / self.SAMPLE_RATE  # 0.032 seconds

        # Convert to float32 [-1.0, 1.0]
        chunk_float = chunk_int16.astype(np.float32) / 32768.0

        # Calculate dB level
        rms = float(np.sqrt(np.mean(chunk_float ** 2)))
        db = 20.0 * math.log10(rms + 1e-6) if rms > 1e-6 else -100.0

        # Predict speech probability via Silero VAD
        prob = self._detector.predict_chunk(chunk_float)
        is_speech = (prob >= self.SPEECH_THRESHOLD)

        with self._lock:
            self._latest_speech_prob = prob
            self._latest_db_level = round(db, 1)

            if not self._is_active_violation:
                if is_speech:
                    if self._speech_accum_sec == 0.0:
                        # First qualifying speech chunk: capture snapshot of pre-roll prior to speech
                        self._active_recording = list(self._pre_roll_buffer)
                    self._active_recording.extend(chunk_int16)

                    self._speech_accum_sec += dt
                    self._inter_word_gap_sec = 0.0
                    self._confidence_samples.append(prob)

                    # Trigger rule: >= 1.5 seconds sustained speech
                    if self._speech_accum_sec >= self.TRIGGER_DURATION_SEC:
                        self._trigger_violation()
                else:
                    # Maintain sliding pre-roll buffer when not speaking
                    self._pre_roll_buffer.extend(chunk_int16)

                    # Brief pause tolerance before trigger (0.8s natural pause between syllables/words)
                    if self._speech_accum_sec > 0.0:
                        self._active_recording.extend(chunk_int16)
                        self._inter_word_gap_sec += dt
                        if self._inter_word_gap_sec > 0.80:
                            # Reset accumulator if gap is too long
                            self._speech_accum_sec = 0.0
                            self._inter_word_gap_sec = 0.0
                            self._confidence_samples.clear()
                            self._active_recording.clear()

            else:
                # Active violation episode: record all incoming samples
                self._active_recording.extend(chunk_int16)
                self._confidence_samples.append(prob)
                self._peak_confidence = max(self._peak_confidence, prob)

                if is_speech:
                    # Speech resumes! Reset continuous no-voice timer.
                    self._continuous_no_voice_sec = 0.0
                else:
                    # Continuous no-voice timer advances (fan/AC/typing do NOT reset this timer)
                    self._continuous_no_voice_sec += dt

                    # Resolution rule: 5.0 continuous seconds without human voice
                    if self._continuous_no_voice_sec >= self.RESOLVE_NO_VOICE_SEC:
                        self._resolve_violation()

    def _trigger_violation(self) -> None:
        """Transitions into active violation state upon >= 1.5s speech."""
        self._is_active_violation = True
        self._active_violation_id = f"V-VOICE-{uuid.uuid4().hex[:8].upper()}"
        self._episode_start_time = time.time()
        self._continuous_no_voice_sec = 0.0
        self._peak_confidence = max(self._confidence_samples) if self._confidence_samples else 0.90

        # If not already initialized from speech onset, initialize with pre-roll buffer
        if not self._active_recording:
            self._active_recording = list(self._pre_roll_buffer)
        logger.info(
            f"[VoiceVADWorker - TRIGGER] Human voice violation {self._active_violation_id} "
            f"started after {self._speech_accum_sec:.2f}s sustained speech (conf={self._peak_confidence:.2f})"
        )

    def _resolve_violation(self) -> None:
        """Transitions out of active violation state and saves playable audio evidence."""
        v_id = self._active_violation_id or f"V-VOICE-{uuid.uuid4().hex[:8].upper()}"
        now = time.time()
        total_audio_sec = len(self._active_recording) / self.SAMPLE_RATE
        avg_conf = sum(self._confidence_samples) / max(1, len(self._confidence_samples))

        logger.info(
            f"[VoiceVADWorker - RESOLVE] Human voice violation {v_id} resolved after "
            f"{self.RESOLVE_NO_VOICE_SEC:.1f}s continuous no-voice. Saving {total_audio_sec:.1f}s WAV evidence..."
        )

        # Save playable WAV evidence
        wav_filename = f"evidence_UNAUTH_VOICE_{v_id}_{int(now)}.wav"
        wav_path = self._evidence_dir / wav_filename
        try:
            pcm_bytes = np.array(self._active_recording, dtype=np.int16).tobytes()
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.BYTES_PER_SAMPLE)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(pcm_bytes)
            logger.info(f"[VoiceVADWorker] Successfully saved playable WAV: {wav_path} ({len(pcm_bytes)} bytes)")

            # Record evidence snapshot into SQLite database
            self._persist_evidence_record(v_id, wav_filename, str(wav_path), now, self._peak_confidence, total_audio_sec)
        except Exception as e:
            logger.error(f"[VoiceVADWorker] Failed to write WAV evidence: {e}", exc_info=True)

        # Reset state for subsequent violations
        self._is_active_violation = False
        self._active_violation_id = None
        self._speech_accum_sec = 0.0
        self._continuous_no_voice_sec = 0.0
        self._inter_word_gap_sec = 0.0
        self._active_recording.clear()
        self._confidence_samples.clear()
        self._pre_roll_buffer.clear()

    def _persist_evidence_record(
        self,
        violation_id: str,
        filename: str,
        filepath: str,
        timestamp: float,
        confidence: float,
        duration: float,
    ) -> None:
        """Links the saved WAV evidence file to the active session in SQLite."""
        try:
            import json
            from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
            from backend.database.session_repository import session_repository
            from backend.database.db import get_db_connection

            sid = monitoring_persistence_adapter.active_session_id or "standalone_session"
            target_v_id = violation_id

            # Link with existing UNAUTH_VOICE violation if present, or create authoritative violation entry
            try:
                conn = get_db_connection()
                with conn:
                    cur = conn.execute(
                        "SELECT id FROM violations WHERE session_id = ? AND violation_type = 'UNAUTH_VOICE' ORDER BY start_time DESC LIMIT 1",
                        (sid,)
                    )
                    row = cur.fetchone()
                    if row:
                        target_v_id = row["id"]
                    else:
                        start_ts = timestamp - duration
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO violations (
                                id, session_id, episode_id, violation_type, category, title, description,
                                status, start_time, end_time, duration, peak_confidence, avg_confidence,
                                detection_count, risk_score, triggered_rules_json, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                target_v_id,
                                sid,
                                target_v_id,
                                "UNAUTH_VOICE",
                                "Communication & Speech",
                                "Unauthorized Human Voice",
                                f"Human speech detected ({duration:.1f}s)",
                                "RESOLVED",
                                start_ts,
                                timestamp,
                                float(duration),
                                float(confidence),
                                float(confidence),
                                1,
                                75.0,
                                json.dumps(["UNAUTH_VOICE"]),
                                timestamp,
                                timestamp,
                            ),
                        )
                conn.close()
            except Exception as e_link:
                logger.debug(f"[VoiceVADWorker] Could not query/link violation in DB: {e_link}")

            meta = {
                "evidence_type": "AUDIO",
                "audio_format": "WAV",
                "sample_rate": 16000,
                "channels": 1,
                "duration_seconds": round(duration, 2),
                "violation_type": "UNAUTH_VOICE",
                "camera_id": "camera_1",
            }
            session_repository.record_evidence(
                session_id=sid,
                violation_id=target_v_id,
                filename=filename,
                filepath=filepath,
                timestamp=timestamp,
                confidence=round(confidence, 4),
                duration=round(duration, 2),
                metadata=meta,
            )
            logger.info(f"[VoiceVADWorker] Evidence recorded in DB for session={sid}, violation={target_v_id}")
        except Exception as e:
            logger.debug(f"[VoiceVADWorker] Could not persist evidence to DB: {e}")

    # Public state getters for pipeline integration
    @property
    def is_speech_active(self) -> bool:
        with self._lock:
            return self._is_active_violation

    @property
    def current_db(self) -> float:
        with self._lock:
            return self._latest_db_level

    @property
    def current_speech_prob(self) -> float:
        with self._lock:
            return self._latest_speech_prob

    @property
    def active_violation_id(self) -> Optional[str]:
        with self._lock:
            return self._active_violation_id

    def get_audio_state(self) -> Tuple[bool, float, float, float]:
        """Returns (is_active_speaking, db_level, noise_level, speech_prob)."""
        with self._lock:
            return (
                self._is_active_violation,
                self._latest_db_level,
                0.0,
                self._latest_speech_prob,
            )


# Global singleton instance
voice_vad_worker = VoiceActivityWorker()
