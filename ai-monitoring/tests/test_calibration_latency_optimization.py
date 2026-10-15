"""
Focused Test Suite: Gaze Calibration Latency Optimization
=========================================================
Validates the 10 specific calibration timing and safety requirements:
1. 15 stable valid samples -> early completion allowed only after 1.2s.
2. 14 samples -> no early completion.
3. 15 samples before 1.2s -> no early completion.
4. unstable yaw -> no early completion.
5. unstable pitch -> no early completion.
6. off-axis calibration frames -> no early completion.
7. invalid/blink/low-confidence frames are not counted as valid samples.
8. 20 valid stable samples -> normal completion.
9. 5-second fallback works correctly.
10. existing anti-cheat/off-axis calibration rejection remains unchanged.
"""
import time
import pytest
import numpy as np

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, BoundingBox
)
from ai_engine.camera.frame import Frame
from ai_engine.calibration.calibration_engine import CalibrationEngineProcessor


def _make_context(
    face_detected=True,
    conf=0.95,
    face_width=150.0,
    pose_success=True,
    yaw=0.0,
    pitch=0.0,
    roll=0.0,
    has_iris=True,
    gaze_confidence=0.90,
    g_x=0.0,
    g_y=0.0,
    blink=False,
    ear=0.28,
    frame_id=1,
    face_count=1
):
    ctx = ExamContext()
    ctx.current_frame = Frame.from_bgr_image(
        np.zeros((480, 640, 3), dtype=np.uint8), frame_id=frame_id, timestamp=time.time()
    )
    ctx.face_info = FaceInfo(
        face_detected=face_detected,
        confidence=conf,
        bbox=BoundingBox(100, 100, face_width, face_width),
        face_count=face_count if face_detected else 0,
        presence_state="PRESENT" if face_detected else "MISSING",
        identity_consistent=True
    )
    ctx.head_pose_info = HeadPoseInfo(yaw=yaw, pitch=pitch, roll=roll, success=pose_success)
    ctx.eye_info = EyeInfo(
        left_iris_center=(0.4, 0.4) if has_iris else None,
        right_iris_center=(0.6, 0.4) if has_iris else None,
        gaze_confidence=gaze_confidence,
        combined_gaze=(g_x, g_y, 1.0),
        blink_detected=blink,
        average_ear=ear
    )
    return ctx


def test_01_early_completion_allowed_after_1_2s_with_15_stable_samples():
    """1. 15 stable valid samples -> early completion allowed only after 1.2s."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.25  # elapsed = 1.25s >= 1.2s

    for i in range(15):
        # Stable yaw & pitch with minimal natural jitter (std well below 3.5°)
        jitter = 0.2 * ((i % 3) - 1)
        ctx = _make_context(yaw=1.0 + jitter, pitch=2.0 + jitter, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 15
    assert engine.is_completed is True
    assert engine.stage == "READY"


def test_02_fourteen_samples_no_early_completion():
    """2. 14 samples -> no early completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.5  # elapsed = 1.5s >= 1.2s

    for i in range(14):
        ctx = _make_context(yaw=1.0, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 14
    assert engine.is_completed is False
    assert engine.stage == "AUTO_CALIBRATING"


def test_03_fifteen_samples_before_1_2s_no_early_completion():
    """3. 15 samples before 1.2s -> no early completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 0.9  # elapsed = 0.9s (< 1.2s)

    for i in range(15):
        ctx = _make_context(yaw=1.0, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 15
    assert engine.is_completed is False
    assert engine.stage == "AUTO_CALIBRATING"


def test_04_unstable_yaw_no_early_completion():
    """4. unstable yaw (std(yaw) > 3.5°) -> no early completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.5  # elapsed = 1.5s >= 1.2s

    # Alternate yaw between -6.0° and +6.0° (std ≈ 6.0° > 3.5°)
    for i in range(15):
        yaw_val = 6.0 if (i % 2 == 0) else -6.0
        ctx = _make_context(yaw=yaw_val, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 15
    assert engine.is_completed is False
    assert engine.stage == "AUTO_CALIBRATING"


def test_05_unstable_pitch_no_early_completion():
    """5. unstable pitch (std(pitch) > 3.5°) -> no early completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.5  # elapsed = 1.5s >= 1.2s

    # Alternate pitch between 0.0° and +10.0° (std ≈ 5.0° > 3.5°)
    for i in range(15):
        pitch_val = 10.0 if (i % 2 == 0) else 0.0
        ctx = _make_context(yaw=1.0, pitch=pitch_val, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 15
    assert engine.is_completed is False
    assert engine.stage == "AUTO_CALIBRATING"


def test_06_off_axis_calibration_frames_no_early_completion():
    """6. off-axis calibration frames -> rejected, no early completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.5

    # Candidate is looking off-axis (|yaw| = 22.0° > 14.0°)
    for i in range(20):
        ctx = _make_context(yaw=22.0, pitch=2.0, g_x=0.25, g_y=0.0, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 0
    assert engine.is_completed is False


def test_07_invalid_blink_low_confidence_not_counted_as_valid():
    """7. invalid/blink/low-confidence frames are not counted as valid samples."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.5

    # 10 valid frames
    for i in range(10):
        ctx = _make_context(yaw=1.0, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)
    assert engine.valid_samples == 10

    # 10 blink frames (rejected)
    for i in range(10):
        ctx = _make_context(blink=True, ear=0.10, frame_id=i + 11)
        engine.process(ctx)
    assert engine.valid_samples == 10

    # 10 low-confidence gaze frames (rejected)
    for i in range(10):
        ctx = _make_context(gaze_confidence=0.30, frame_id=i + 21)
        engine.process(ctx)
    assert engine.valid_samples == 10

    assert engine.is_completed is False


def test_08_twenty_valid_stable_samples_normal_completion():
    """8. 20 valid stable samples -> normal completion."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 1.05  # elapsed >= 1.0s

    for i in range(20):
        ctx = _make_context(yaw=1.0, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 20
    assert engine.is_completed is True
    assert engine.stage == "READY"


def test_09_five_second_fallback_works_correctly():
    """9. 5-second fallback works correctly when at least 10 valid samples exist."""
    engine = CalibrationEngineProcessor(
        calibration_duration_seconds=5.0,
        warmup_duration_seconds=0.5,
        target_samples=20,
        min_stable_samples_for_early_exit=15
    )
    engine.initialize()
    engine.start()
    engine.start_time = time.time() - 5.1  # elapsed = 5.1s >= 5.0s

    # Feed 12 valid samples (fewer than 15, so early exit does not fire)
    for i in range(12):
        ctx = _make_context(yaw=1.0, pitch=2.0, g_x=0.02, g_y=0.03, frame_id=i + 1)
        engine.process(ctx)

    assert engine.valid_samples == 12
    assert engine.is_completed is True
    assert engine.stage == "READY"


def test_10_anti_cheat_off_axis_rejection_remains_unchanged():
    """10. Existing anti-cheat/off-axis calibration rejection remains unchanged."""
    engine = CalibrationEngineProcessor()

    # 1. Yaw > 14.0° (off-axis right) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 22.0, 0.0, 0.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False

    # 2. Yaw < -14.0° (off-axis left) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, -22.0, 0.0, 0.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False

    # 3. Pitch < -10.0° (looking up at ceiling) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, -15.0, 0.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False

    # 4. Pitch > 18.0° (looking down at desk) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 25.0, 0.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False

    # 5. Gaze X > 0.18 -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 0.0, True, 0.90, 0.25, 0.0, False, 0.28
    ) is False

    # 6. Gaze Y < -0.10 -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 0.0, True, 0.90, 0.0, -0.15, False, 0.28
    ) is False

    # 7. Low face confidence (< 0.55) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.40, 120.0, True, 0.0, 0.0, 0.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False

    # 8. Blink -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 0.0, True, 0.90, 0.0, 0.0, True, 0.28
    ) is False

    # 9. Valid neutral frame within cone -> accepted
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 2.0, 5.0, 0.0, True, 0.90, 0.05, 0.05, False, 0.28
    ) is True
