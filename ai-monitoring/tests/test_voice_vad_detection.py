"""
Unit & Integration Tests for Human Voice Detection (Silero VAD)
===============================================================
Validates:
1. Silero VAD initializes locally on CPU.
2. Acoustic noise (fan/AC hum, tones, typing) does not trigger violation.
3. Sustained human speech accumulates to >= 1.5s before triggering.
4. Exactly one active violation episode is maintained while speaking.
5. Acoustic noise during active state does NOT reset or block the 5s resolution timer.
6. Resumed speech before 5s resets the 5s timer and continues the active violation.
7. 5 continuous seconds of no human voice resolves the violation.
8. Playable WAV evidence (16kHz 16-bit mono PCM) is created with pre-roll and trailing audio.
9. HumanVoiceDetectedRule integration in rule engine.
"""
import os
import wave
import tempfile
import time
from pathlib import Path
import numpy as np
import pytest

from ai_engine.audio_detection.voice_vad_worker import VoiceActivityWorker, SileroVADDetector
from ai_engine.intelligence.observation_fusion.models import UnifiedObservation, AudioObservation
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.rule_engine.rules import HumanVoiceDetectedRule


def _generate_synthetic_tone(freq: float = 300.0, duration_sec: float = 0.5, sr: int = 16000) -> np.ndarray:
    """Generates synthetic pure sine tone mimicking AC/fan acoustic noise."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    wave_float = (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return (wave_float * 32767).astype(np.int16)


def _generate_synthetic_speech_like(duration_sec: float = 1.0, sr: int = 16000) -> np.ndarray:
    """
    Generates synthetic harmonic speech-like formant frequencies (F0=120Hz, F1=700Hz, F2=1220Hz, F3=2600Hz)
    with typical vocal tract modulation.
    """
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    # Fundamental frequency + formants
    signal = (
        0.30 * np.sin(2 * np.pi * 130 * t)
        + 0.25 * np.sin(2 * np.pi * 700 * t)
        + 0.20 * np.sin(2 * np.pi * 1220 * t)
        + 0.15 * np.sin(2 * np.pi * 2600 * t)
    )
    # Pitch pulse modulation
    mod = 0.5 * (1.0 + np.sin(2 * np.pi * 10 * t))
    signal = signal * mod
    signal = np.clip(signal, -0.95, 0.95).astype(np.float32)
    return (signal * 32767).astype(np.int16)


class TestSileroVADInitialization:
    def test_detector_initializes_on_cpu(self):
        detector = SileroVADDetector()
        assert detector.initialize() is True
        silence_chunk = np.zeros((1, 512), dtype=np.float32)
        prob = detector.predict_chunk(silence_chunk)
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 0.05

    def test_acoustic_tone_produces_low_speech_probability(self):
        detector = SileroVADDetector()
        detector.initialize()
        tone_samples = _generate_synthetic_tone(freq=120.0, duration_sec=0.1)
        tone_chunk = (tone_samples[:512].astype(np.float32) / 32768.0).reshape(1, 512)
        prob = detector.predict_chunk(tone_chunk)
        # AC/fan acoustic tone must be far below 0.50 speech threshold
        assert prob < 0.40


class TestVoiceActivityWorkerTimingLifecycle:
    @pytest.fixture
    def temp_worker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            worker = VoiceActivityWorker(evidence_dir=Path(tmpdir))
            worker.initialize()
            yield worker

    def test_acoustic_noise_does_not_trigger_violation(self, temp_worker):
        """Fans, AC, keyboard clicks alone must never trigger a human voice violation."""
        noise_samples = _generate_synthetic_tone(freq=200.0, duration_sec=3.0)
        # Push 3.0s of acoustic tone in 512-sample chunks
        for i in range(0, len(noise_samples) - 512, 512):
            temp_worker._process_chunk(noise_samples[i : i + 512])

        assert temp_worker.is_speech_active is False
        assert temp_worker._speech_accum_sec == 0.0

    def test_sustained_speech_triggers_at_1_5_seconds(self, temp_worker):
        """A violation is created ONLY after >= 1.5 seconds of qualifying sustained speech."""
        speech_chunk = np.full(512, 10000, dtype=np.int16)

        # Mock detector to simulate human speech detection (prob = 0.92)
        temp_worker._detector.predict_chunk = lambda c: 0.92

        # 1.0 second of speech (31 chunks of 32ms = 0.992s) -> must NOT trigger yet
        for _ in range(31):
            temp_worker._process_chunk(speech_chunk)

        assert temp_worker.is_speech_active is False
        assert temp_worker._speech_accum_sec < 1.50

        # Additional 0.6 seconds of speech (reaching ~1.6s total) -> MUST trigger
        for _ in range(19):
            temp_worker._process_chunk(speech_chunk)

        assert temp_worker.is_speech_active is True
        assert temp_worker._is_active_violation is True
        assert temp_worker.active_violation_id is not None
        assert temp_worker.active_violation_id.startswith("V-VOICE-")

    def test_acoustic_noise_during_active_violation_advances_resolution_timer(self, temp_worker):
        """
        During an active violation, non-speech (ambient noise, fan hum, typing)
        must NOT reset or block the 5.0s resolution timer. Only real human voice resets it.
        """
        temp_worker._detector.predict_chunk = lambda c: 0.90
        # Trigger violation with 1.6s of speech
        speech_chunk = np.full(512, 10000, dtype=np.int16)
        for _ in range(50):
            temp_worker._process_chunk(speech_chunk)
        assert temp_worker.is_speech_active is True

        # Now simulate 3.0 seconds of fan noise (prob = 0.10)
        temp_worker._detector.predict_chunk = lambda c: 0.10
        fan_chunk = _generate_synthetic_tone(freq=180.0, duration_sec=0.032)[:512]
        for _ in range(int(3.0 / 0.032)):
            temp_worker._process_chunk(fan_chunk)

        # Timer must have advanced to ~3.0s, NOT reset
        assert temp_worker.is_speech_active is True
        assert temp_worker._continuous_no_voice_sec >= 2.9

    def test_resumed_speech_resets_5s_timer_maintaining_single_episode(self, temp_worker):
        """
        If the candidate pauses for 3 seconds and speaks again before 5 seconds,
        the timer resets and the single active violation continues.
        """
        speech_chunk = np.full(512, 10000, dtype=np.int16)
        temp_worker._detector.predict_chunk = lambda c: 0.90
        for _ in range(50):
            temp_worker._process_chunk(speech_chunk)
        assert temp_worker.is_speech_active is True
        initial_id = temp_worker.active_violation_id

        # Pause 3.5 seconds
        temp_worker._detector.predict_chunk = lambda c: 0.05
        for _ in range(int(3.5 / 0.032)):
            temp_worker._process_chunk(np.zeros(512, dtype=np.int16))
        assert temp_worker.is_speech_active is True
        assert temp_worker._continuous_no_voice_sec >= 3.4

        # Resume speaking (prob = 0.95)
        temp_worker._detector.predict_chunk = lambda c: 0.95
        temp_worker._process_chunk(speech_chunk)

        # Timer must be reset to 0.0, and violation ID must remain identical!
        assert temp_worker._continuous_no_voice_sec == 0.0
        assert temp_worker.is_speech_active is True
        assert temp_worker.active_violation_id == initial_id

    def test_five_continuous_seconds_no_voice_resolves_and_saves_playable_wav(self, temp_worker):
        """
        After 5 continuous seconds without human voice:
        - Violation resolves.
        - Playable 16kHz 16-bit mono WAV evidence is written.
        - Audio contains pre-roll + speech episode + 5.0s trailing audio.
        """
        speech_chunk = np.full(512, 10000, dtype=np.int16)

        # 1. Provide 1.5s idle pre-roll
        temp_worker._detector.predict_chunk = lambda c: 0.01
        for _ in range(int(1.5 / 0.032)):
            temp_worker._process_chunk(np.zeros(512, dtype=np.int16))

        # 2. Trigger violation with 2.0s of speech
        temp_worker._detector.predict_chunk = lambda c: 0.90
        for _ in range(int(2.0 / 0.032)):
            temp_worker._process_chunk(speech_chunk)
        assert temp_worker.is_speech_active is True

        # 3. Simulate 5.1s continuous no-voice (fan/AC noise, prob = 0.05)
        temp_worker._detector.predict_chunk = lambda c: 0.05
        for _ in range(int(5.1 / 0.032)):
            temp_worker._process_chunk(np.zeros(512, dtype=np.int16))

        # Violation must resolve!
        assert temp_worker.is_speech_active is False
        assert temp_worker.active_violation_id is None

        # Check that WAV file was written to evidence_dir
        wav_files = list(temp_worker._evidence_dir.glob("*.wav"))
        assert len(wav_files) == 1
        wav_path = wav_files[0]
        assert wav_path.name.startswith("evidence_UNAUTH_VOICE_")

        # Verify WAV integrity using wave module
        with wave.open(str(wav_path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            n_frames = wf.getnframes()
            duration_sec = n_frames / 16000.0
            # Duration must be roughly ~1.5s pre-roll + 2.0s speech + 5.0s trailing = ~8.5s
            assert duration_sec >= 7.5


class TestHumanVoiceRuleIntegration:
    def test_rule_evaluates_unified_observation(self):
        rule = HumanVoiceDetectedRule()
        assert rule.rule_id == "UNAUTH_VOICE"
        assert rule.category == "Communication"

        cfg = RuleEngineConfig()

        # Observation with no audio
        obs_silent = UnifiedObservation(audio=AudioObservation(is_speaking=False, decibel_level=-60.0))
        trig, conf, reason = rule.evaluate(obs_silent, cfg)
        assert trig is False
        assert conf == 0.0

        # Observation with active speaking
        obs_speaking = UnifiedObservation(audio=AudioObservation(is_speaking=True, decibel_level=-18.5))
        trig, conf, reason = rule.evaluate(obs_speaking, cfg)
        assert trig is True
        assert conf >= 0.85
        assert "human voice" in reason.lower()

