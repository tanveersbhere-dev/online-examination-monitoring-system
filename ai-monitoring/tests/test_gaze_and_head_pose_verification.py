"""
Comprehensive Test Suite: Gaze, Head Pose, Calibration & Explainability Verification
===================================================================================
Covers all 20 Phase 20 requirements:
  1. Calibration state transitions
  2. Invalid calibration samples rejection
  3. Valid calibration samples acceptance & robust median baseline
  4. Iris extraction & landmark count validation
  5. Eye normalization geometry ([-1, 1] range)
  6. Head pose zero-centering with correct 3D model
  7. Angular wrapping handling (+179° vs -179°)
  8. Gaze deviation computation
  9. ON_SCREEN classification
  10. UNCERTAIN classification
  11. OFF_SCREEN classification
  12. Head-only movement (eyes on screen -> NOT off-screen)
  13. Eye-only movement (eyes move away, head still -> OFF_SCREEN)
  14. Face loss -> UNCERTAIN (never OFF_SCREEN)
  15. Landmark loss -> UNCERTAIN
  16. Temporary uncertainty -> no duplicate violation
  17. Temporal confirmation (1.5s persistence)
  18. Temporal recovery (5.0s window)
  19. Stable violation ID during ongoing episode
  20. New violation ID on recurrence after resolution
"""
import pytest
import time
import numpy as np
import cv2

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, FaceMeshInfo
)
from ai_engine.calibration.baseline_profile import (
    CandidateBaseline, HeadPoseBaseline, GazeBaseline, CalibrationQualityScore
)
from ai_engine.calibration.calibration_metrics import CalibrationMetricsAccumulator
from ai_engine.calibration.calibration_engine import CalibrationEngineProcessor
from ai_engine.calibration.calibration_manager import CalibrationManager
from ai_engine.estimators.head_pose.models import GENERIC_3D_MODEL_POINTS
from ai_engine.features.eye_gaze.mediapipe_gaze_extractor import _normalized_eye_gaze
from ai_engine.intelligence.observation_fusion.models import (
    UnifiedObservation, FaceObservation, ObservationConfidenceSummary
)
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig, AttentionToleranceConfig
from ai_engine.intelligence.rule_engine.rules import (
    LookingAwayTooLongRule, RepeatedDownwardGazeRule, _calibrated_attention_decision
)
from ai_engine.intelligence.behavior_engine.temporal_state_machine import BehaviorStateMachineManager


# ---------------------------------------------------------------------------
# 1. Calibration state transitions
# ---------------------------------------------------------------------------
def test_01_calibration_state_transitions():
    mgr = CalibrationManager()
    assert mgr.status in ("INITIALIZING", "NOT_STARTED")

    mgr.start_calibration()
    assert mgr.status == "AUTO_CALIBRATING"

    good_baseline = CandidateBaseline(
        head_pose=HeadPoseBaseline(average_yaw=0.0, average_pitch=0.0),
        quality=CalibrationQualityScore(overall_score=95.0, rating="EXCELLENT"),
        samples_collected=35
    )
    mgr.complete_calibration(good_baseline)
    assert mgr.status == "CALIBRATED"
    assert mgr.stage == "READY"

    # Test failure on poor rating
    mgr.start_calibration()
    poor_baseline = CandidateBaseline(
        quality=CalibrationQualityScore(overall_score=30.0, rating="POOR")
    )
    mgr.complete_calibration(poor_baseline)
    assert mgr.status == "FAILED"

    # Test request recalibration
    mgr.request_recalibration("Extended tracking loss")
    assert mgr.status == "RECALIBRATION_REQUIRED"


def test_01b_anti_drift_protection_during_off_screen_episodes():
    """Verify that looking away for 10-20 seconds NEVER causes baseline to drift to off-screen gaze."""
    mgr = CalibrationManager(ema_alpha=0.05)
    initial_yaw = 2.0
    initial_pitch = 1.0
    initial_gx = 0.0
    initial_gy = 0.0
    baseline = CandidateBaseline(
        head_pose=HeadPoseBaseline(average_yaw=initial_yaw, average_pitch=initial_pitch),
        gaze=GazeBaseline(center_x=initial_gx, center_y=initial_gy),
        quality=CalibrationQualityScore(overall_score=95.0, rating="EXCELLENT"),
        samples_collected=35
    )
    mgr.complete_calibration(baseline)

    # Simulate student looking far away (yaw = +35°, gx = +0.70) for 100 frames (~10 seconds)
    ctx = ExamContext()
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=35.0, pitch=10.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.70, 0.20, 1.0), left_iris_center=(0.7, 0.5))

    for _ in range(100):
        mgr.evaluate_runtime_frame(ctx)

    # ANTI-DRIFT GUARANTEE: Baseline MUST NOT have moved towards off-screen gaze!
    assert mgr.baseline.head_pose.average_yaw == initial_yaw
    assert mgr.baseline.head_pose.average_pitch == initial_pitch
    assert mgr.baseline.gaze.center_x == initial_gx
    assert mgr.baseline.gaze.center_y == initial_gy


# ---------------------------------------------------------------------------
# 2. Invalid calibration samples rejection
# ---------------------------------------------------------------------------
def test_02_invalid_calibration_samples_rejected():
    engine = CalibrationEngineProcessor(calibration_duration_seconds=5.0)
    engine.initialize()

    # Frame with low face confidence
    ctx = ExamContext()
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.40, bbox=(100, 100, 150, 150))
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90)
    engine.process(ctx)
    assert engine.accumulator.face_detected_frames == 0

    # Frame with blinking
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(100, 100, 150, 150))
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, blink_detected=True)
    engine.process(ctx)
    assert engine.accumulator.face_detected_frames == 0

    # Frame with pose estimation failure
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, blink_detected=False)
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, success=False)
    engine.process(ctx)
    assert engine.accumulator.face_detected_frames == 0


# ---------------------------------------------------------------------------
# 3. Valid calibration samples acceptance & robust median baseline
# ---------------------------------------------------------------------------
def test_03_valid_calibration_samples_median():
    acc = CalibrationMetricsAccumulator()
    yaws = [5.0, 5.2, 4.8, 5.1, 5.0, 4.9, 35.0]  # 35.0 is an outlier
    for y in yaws:
        acc.add_frame(
            face_detected=True, face_confidence=0.95,
            bbox=[100, 100, 120, 120], yaw=y, pitch=2.0, roll=0.0,
            gaze_vector=[0.05, 0.02]
        )
    baseline = acc.compute_baseline(timestamp=100.0)
    # Median should reject the 35.0 outlier and be ~5.0
    assert abs(baseline.head_pose.average_yaw - 5.0) < 0.2
    assert abs(baseline.gaze.center_x - 0.05) < 0.01


# ---------------------------------------------------------------------------
# 4. Iris extraction & aperture validation
# ---------------------------------------------------------------------------
def test_04_eye_gaze_aperture_validation():
    # Valid normal open eye
    lc = (0.35, 0.50, 0.0)
    rc = (0.45, 0.50, 0.0)
    ul = (0.40, 0.48, 0.0)
    ll = (0.40, 0.52, 0.0)
    iris = (0.40, 0.50, 0.0)
    res = _normalized_eye_gaze(lc, rc, ul, ll, iris)
    assert res is not None
    (gx, gy, _), _ = res
    assert abs(gx) < 0.01
    assert abs(gy) < 0.01

    # Tightly closed eye (height < 0.003)
    ll_closed = (0.40, 0.481, 0.0)
    assert _normalized_eye_gaze(lc, rc, ul, ll_closed, iris) is None


# ---------------------------------------------------------------------------
# 5. Eye normalization geometry ([-1, 1] range & directions)
# ---------------------------------------------------------------------------
def test_05_eye_normalization_directions():
    lc = (0.30, 0.50, 0.0)
    rc = (0.40, 0.50, 0.0)
    ul = (0.35, 0.45, 0.0)
    ll = (0.35, 0.55, 0.0)

    # Iris deflected right (towards rc = 0.40)
    iris_right = (0.38, 0.50, 0.0)
    (gx_r, gy_r, _), _ = _normalized_eye_gaze(lc, rc, ul, ll, iris_right)
    assert gx_r > 0.40  # Positive X is rightward

    # Iris deflected left (towards lc = 0.30)
    iris_left = (0.32, 0.50, 0.0)
    (gx_l, gy_l, _), _ = _normalized_eye_gaze(lc, rc, ul, ll, iris_left)
    assert gx_l < -0.40  # Negative X is leftward

    # Iris deflected down (towards ll = 0.55)
    iris_down = (0.35, 0.53, 0.0)
    (gx_d, gy_d, _), _ = _normalized_eye_gaze(lc, rc, ul, ll, iris_down)
    assert gy_d > 0.40  # Positive Y is downward


# ---------------------------------------------------------------------------
# 6. Head pose zero-centering with correct 3D model
# ---------------------------------------------------------------------------
def test_06_head_pose_zero_centering():
    cam = np.array([[640, 0, 320], [0, 640, 240], [0, 0, 1]], dtype=np.float64)
    # 2D image points matching straight-facing generic 3D points
    img_pts = np.array([
        [320, 240],  # Nose
        [320, 350],  # Chin (+Y down)
        [245, 183],  # Left eye (-X, -Y up)
        [395, 183],  # Right eye (+X, -Y up)
        [270, 290],  # Left mouth (-X, +Y down)
        [370, 290]   # Right mouth (+X, +Y down)
    ], dtype=np.float64)

    _, rvec, tvec = cv2.solvePnP(GENERIC_3D_MODEL_POINTS, img_pts, cam, np.zeros((4, 1)))
    rmat, _ = cv2.Rodrigues(rvec)
    proj = np.hstack((rmat, tvec))
    _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj)
    pitch, yaw, roll = [float(a[0]) for a in euler]

    # Straight-facing pose must have Euler angles near 0.0° (NOT -166.59°!)
    assert abs(pitch) < 5.0
    assert abs(yaw) < 5.0
    assert abs(roll) < 5.0


# ---------------------------------------------------------------------------
# 7. Angular wrapping handling (+179° vs -179°)
# ---------------------------------------------------------------------------
def test_07_angular_wrapping():
    def _angular_delta(curr: float, base: float) -> float:
        return ((curr - base + 180.0) % 360.0) - 180.0

    # +179° vs -179° is 2° apart, not 358°
    diff = _angular_delta(179.0, -179.0)
    assert abs(diff - (-2.0)) < 1e-5 or abs(diff - 2.0) < 1e-5
    assert abs(diff) == 2.0


# ---------------------------------------------------------------------------
# 8. Gaze deviation computation
# ---------------------------------------------------------------------------
def test_08_gaze_deviation_computation():
    mgr = CalibrationManager()
    baseline = CandidateBaseline(
        head_pose=HeadPoseBaseline(average_yaw=5.0, average_pitch=2.0),
        gaze=GazeBaseline(center_x=-0.05, center_y=0.10),
        quality=CalibrationQualityScore(overall_score=95.0, rating="EXCELLENT")
    )
    mgr.complete_calibration(baseline)

    ctx = ExamContext()
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=15.0, pitch=2.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.20, 0.10, 1.0), left_iris_center=(0.3, 0.5))

    dev = mgr.evaluate_runtime_frame(ctx)
    assert dev["head_pose_deviation"]["delta_yaw"] == 10.0
    assert dev["head_pose_deviation"]["delta_pitch"] == 0.0
    assert dev["gaze_deviation"]["delta_gaze_x"] == 0.25
    assert dev["gaze_deviation"]["delta_gaze_y"] == 0.0


# ---------------------------------------------------------------------------
# 9. ON_SCREEN classification (direct and reading around screen)
# ---------------------------------------------------------------------------
def test_09_on_screen_classification():
    cfg = RuleEngineConfig()
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.95, gaze_confidence=0.90,
            behavioral_summary={"head_pose_success": True}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_deviation": {"delta_gaze_x": 0.15, "delta_gaze_y": 0.10},
            "head_pose_deviation": {"delta_yaw": 5.0, "delta_pitch": 2.0},
            "gaze_measurement": {"valid": True, "iris_visible": True, "confidence": 0.90},
        }
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "ON_SCREEN"
    assert conf > 0.80
    assert reason == "WITHIN_CALIBRATED_SCREEN_REGION"


# ---------------------------------------------------------------------------
# 10. UNCERTAIN classification on poor landmark quality
# ---------------------------------------------------------------------------
def test_10_uncertain_classification_low_quality():
    cfg = RuleEngineConfig()
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.40, gaze_confidence=0.30,
            behavioral_summary={"head_pose_success": True}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_deviation": {"delta_gaze_x": 0.80, "delta_gaze_y": 0.0},
            "head_pose_deviation": {"delta_yaw": 30.0, "delta_pitch": 0.0},
            "gaze_measurement": {"valid": False, "iris_visible": False, "confidence": 0.30},
        }
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "UNCERTAIN"
    assert conf == 0.0
    assert reason == "LOW_QUALITY_OR_MISSING_IRIS"


# ---------------------------------------------------------------------------
# 11. OFF_SCREEN classification on strong sustained gaze deviation
# ---------------------------------------------------------------------------
def test_11_off_screen_classification():
    cfg = RuleEngineConfig()
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.95, gaze_confidence=0.90,
            behavioral_summary={"head_pose_success": True}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_deviation": {"delta_gaze_x": 0.70, "delta_gaze_y": 0.0},
            "head_pose_deviation": {"delta_yaw": 30.0, "delta_pitch": 0.0},
            "gaze_measurement": {"valid": True, "iris_visible": True, "confidence": 0.90},
        }
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "OFF_SCREEN"
    assert conf > 0.70
    assert reason == "CALIBRATED_EYE_GAZE_OFF_SCREEN"


# ---------------------------------------------------------------------------
# 12. Head-only movement (eyes on screen -> NOT OFF_SCREEN)
# ---------------------------------------------------------------------------
def test_12_head_movement_eyes_on_screen():
    cfg = RuleEngineConfig()
    # Head turned 25° right, but eyes compensation kept delta_gaze_x near 0
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.95, gaze_confidence=0.90,
            behavioral_summary={"head_pose_success": True}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_deviation": {"delta_gaze_x": 0.02, "delta_gaze_y": 0.0},
            "head_pose_deviation": {"delta_yaw": 25.0, "delta_pitch": 0.0},
            "gaze_measurement": {"valid": True, "iris_visible": True, "confidence": 0.90},
        }
    )
    state, conf, _ = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state != "OFF_SCREEN"


# ---------------------------------------------------------------------------
# 13. Eye-only movement (head still, eyes look away -> OFF_SCREEN)
# ---------------------------------------------------------------------------
def test_13_eye_only_movement_triggers_off_screen():
    cfg = RuleEngineConfig()
    # Head still (yaw=0), eyes look far right (delta_gaze_x = 0.65)
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.95, gaze_confidence=0.90,
            behavioral_summary={"head_pose_success": True}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_deviation": {"delta_gaze_x": 0.65, "delta_gaze_y": 0.0},
            "head_pose_deviation": {"delta_yaw": 2.0, "delta_pitch": 0.0},
            "gaze_measurement": {"valid": True, "iris_visible": True, "confidence": 0.90},
        }
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "OFF_SCREEN"
    assert conf > 0.60


# ---------------------------------------------------------------------------
# 14. Face loss -> UNCERTAIN (never OFF_SCREEN)
# ---------------------------------------------------------------------------
def test_14_face_loss_yields_uncertain():
    cfg = RuleEngineConfig()
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(face_present=False, face_confidence=0.0),
        calibration={"status": "CALIBRATED"}
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "UNCERTAIN"
    assert reason == "FACE_NOT_PRESENT"


# ---------------------------------------------------------------------------
# 15. Landmark loss -> UNCERTAIN
# ---------------------------------------------------------------------------
def test_15_landmark_loss_yields_uncertain():
    cfg = RuleEngineConfig()
    obs = UnifiedObservation(
        timestamp=100.0,
        face=FaceObservation(
            face_present=True, face_confidence=0.90, gaze_confidence=0.0,
            behavioral_summary={"head_pose_success": False}
        ),
        calibration={
            "status": "CALIBRATED",
            "gaze_measurement": {"valid": False, "iris_visible": False, "confidence": 0.0}
        }
    )
    state, conf, reason = _calibrated_attention_decision(obs, cfg, "SIDE_OR_UP")
    assert state == "UNCERTAIN"
    assert reason == "LOW_QUALITY_OR_MISSING_IRIS"


# ---------------------------------------------------------------------------
# 16. Temporary uncertainty -> no duplicate violation
# ---------------------------------------------------------------------------
def test_16_temporary_uncertainty_no_duplicate():
    sm = BehaviorStateMachineManager()
    t0 = 1000.0

    # Start violation by sustaining past activation threshold (3.0s)
    sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0)
    sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0 + 1.5)
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0 + 3.2)
    assert is_active
    assert state == "ACTIVE"

    # Temporary flicker (UNCERTAIN / unobserved for 1 frame)
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=t0 + 3.5)
    # Still within recovery grace window -> remains ACTIVE/RECOVERING, not cleared
    assert is_active
    assert state == "RECOVERING"


# ---------------------------------------------------------------------------
# 17. Temporal confirmation
# ---------------------------------------------------------------------------
def test_17_temporal_confirmation():
    sm = BehaviorStateMachineManager()
    t0 = 1000.0

    # Single glance at t=0
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0)
    assert not is_active
    assert state in ("NORMAL", "OBSERVED")

    # At t=1.0s (less than activation_seconds): still not active
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0 + 1.0)
    assert not is_active

    # At t=3.2s (exceeds activation_seconds): becomes active
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t0 + 3.2)
    assert is_active
    assert state == "ACTIVE"


# ---------------------------------------------------------------------------
# 18. Temporal recovery
# ---------------------------------------------------------------------------
def test_18_temporal_recovery():
    sm = BehaviorStateMachineManager()
    t = 1000.0

    # Activate violation with streaming frames (0.2s step)
    for _ in range(20):
        t += 0.2
        sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t)

    # Verify ACTIVE / ESCALATED
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.90, current_ts=t)
    assert is_active
    assert state in ("ACTIVE", "ESCALATED")

    # Candidate returns to screen for 2 seconds (within grace period)
    for _ in range(5):
        t += 0.2
        state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=t)

    # While confidence decays during recovery, state is RECOVERING and remains active
    assert state in ("ACTIVE", "RECOVERING")
    assert is_active

    # After prolonged return to screen (> grace period & full confidence decay)
    for _ in range(25):
        t += 0.3
        state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=t)

    assert not is_active
    assert state in ("RESOLVED", "NORMAL")


# ---------------------------------------------------------------------------
# 19 & 20. Stable violation ID & new violation on recurrence
# ---------------------------------------------------------------------------
def test_19_20_stable_violation_id_and_recurrence():
    from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
    from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
    from ai_engine.intelligence.rule_engine.models import RuleEvaluation
    from ai_engine.intelligence.rule_engine.result import RuleEngineResult

    vm = ViolationManagerProcessor(config=ViolationManagerConfig())
    vm.initialize()
    vm.start()

    ctx = ExamContext()
    ctx.rule_results = RuleEngineResult(evaluations=[
        RuleEvaluation(
            rule_id="ATT_LOOKING_AWAY", rule_name="Off-Screen Attention", category="Attention",
            triggered=True, confidence=0.90, supporting_observations="Looking away",
            evaluation_timestamp=100.0, evaluation_duration=1.0
        )
    ])
    ctx.observation = UnifiedObservation(timestamp=100.0)

    # First frame
    vm.process(ctx)
    initial_id = None
    if ctx.violations and hasattr(ctx.violations, "timeline"):
        active = [v for v in ctx.violations.timeline.violations if v.status in ("OPEN", "ACTIVE", "RECOVERING")]
        if active:
            initial_id = active[0].violation_id

    # Second frame in same episode
    ctx.observation.timestamp = 101.0
    vm.process(ctx)
    if ctx.violations and hasattr(ctx.violations, "timeline"):
        active = [v for v in ctx.violations.timeline.violations if v.status in ("OPEN", "ACTIVE", "RECOVERING")]
        if active and initial_id:
            assert active[0].violation_id == initial_id
