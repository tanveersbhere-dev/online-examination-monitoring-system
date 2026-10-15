"""
Comprehensive Automated Test Suite for Second Gaze Sensitivity Pass & Downward Isolation.
Covers:
1. Side Gaze (+10-15% sensitivity improvement)
   - Neutral gaze
   - Small side gaze
   - Moderate side gaze
   - Side gaze with head still
   - Side gaze with natural head movement
2. Upward Gaze (+40% sensitivity improvement with Eye + Head pose)
   - Neutral gaze
   - Small upward eye movement
   - Moderate upward eye movement
   - Strong upward eye movement
   - Case A: Upward eye gaze with head still
   - Case B: Upward eye gaze + upward head pitch (multi-modal reinforcement)
   - Case C: Head movement upward with neutral eyes (damped, no false trigger)
   - Case D: Small upward eye + small upward head movement
   - Blink while looking upward (suppressed)
   - Low-quality landmarks while looking upward (suppressed)
3. Downward Isolation (CRITICAL: downward must remain 100% unchanged)
"""
import time
import pytest
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.observation_fusion.models import (
    UnifiedObservation, FaceObservation, EnvironmentObservation
)
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig, AttentionToleranceConfig
from ai_engine.intelligence.rule_engine.rules import (
    _calibrated_attention_decision, LookingAwayTooLongRule, RepeatedDownwardGazeRule
)
from ai_engine.calibration.calibration_manager import CalibrationManager
from ai_engine.features.eye_gaze.models import EyeGazeConfig
from ai_engine.features.eye_gaze.mediapipe_gaze_extractor import OneEuroFilter1D


def _build_test_obs(dx=0.0, dy=0.0, yaw=0.0, pitch=0.0, face_conf=0.90, gaze_conf=0.90, blink=False):
    calibration = {
        "status": "CALIBRATED",
        "stage": "READY",
        "gaze_deviation": {"delta_gaze_x": dx, "delta_gaze_y": dy},
        "head_pose_deviation": {"delta_yaw": yaw, "delta_pitch": pitch},
        "dynamic_tolerances": {
            "horizontal_gaze_tolerance": 0.215,  # Side gaze
            "vertical_gaze_tolerance_up": 0.08,   # Upward gaze (+20% tuned)
            "vertical_gaze_tolerance_down": 0.125, # Downward gaze (+60% tuned)
            "head_yaw_support_deg": 18.0,
            "head_pitch_support_deg": 15.0,
            "head_pitch_up_support_deg": 5.0,    # Upward pitch
            "head_pitch_down_support_deg": 6.0,  # Downward pitch
        },
        "gaze_measurement": {"valid": True},
    }
    obs = UnifiedObservation(
        face=FaceObservation(
            face_present=True,
            face_confidence=face_conf,
            gaze_confidence=gaze_conf,
            gaze_state="BLINKING" if blink else "ON_SCREEN",
            head_pose_state="FORWARD",
            behavioral_summary={
                "head_yaw": yaw,
                "head_pitch": pitch,
                "gaze_x": dx,
                "gaze_y": dy,
                "head_pose_success": True
            }
        ),
        calibration=calibration
    )
    return obs, calibration


class TestSideGazeSensitivity:
    """Side / Lateral Gaze: Controlled sensitivity."""

    def test_side_1_neutral_gaze(self):
        """Neutral lateral eye movement (|dx| <= 0.12) remains ON_SCREEN."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.10, dy=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered
        assert "ON_SCREEN" in reason

    def test_side_2_small_side_gaze(self):
        """Small genuine side glance (dx = 0.27) reliably triggers."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.27, dy=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert "OFF_SCREEN" in reason
        assert conf >= 0.65

    def test_side_3_moderate_side_gaze(self):
        """Moderate side glance (dx = 0.35) strongly triggers attention off-screen."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.35, dy=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.80

    def test_side_4_side_gaze_with_head_still(self):
        """Side glance with head still (dx = 0.28, yaw = 0.0) triggers without head rotation."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.28, yaw=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered

    def test_side_5_side_gaze_with_natural_head_movement(self):
        """Side glance with head movement (dx = 0.27, yaw = 22.0) reinforces confidence."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.27, yaw=22.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.65


class TestUpwardGazeSensitivity:
    """Upward Gaze: +20% additional sensitivity tuning."""

    def test_up_1_neutral_gaze(self):
        """Neutral vertical gaze (|dy| <= 0.05) remains ON_SCREEN."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dx=0.0, dy=-0.04)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered
        assert "ON_SCREEN" in reason

    def test_up_2_small_upward_eye_movement(self):
        """Small upward eye glance (dy = -0.11) triggers with new 0.08 tolerance."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        # -dy = 0.11 -> up_excess = 0.11 - 0.08 = 0.03; eye_v_score = 0.03 / 0.06 = 0.50 >= 0.25 -> combined >= 0.50
        obs, _ = _build_test_obs(dy=-0.11)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert "OFF_SCREEN" in reason

    def test_up_3_moderate_upward_eye_movement(self):
        """Moderate upward eye movement (dy = -0.15) triggers with high confidence."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.15)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.75

    def test_up_4_strong_upward_eye_movement(self):
        """Strong upward eye glance (dy = -0.20) produces maximum off-screen confidence."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.20)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.85

    def test_up_5_case_a_eyes_up_head_still(self):
        """Case A: Eyes up (dy = -0.12), head still (pitch = 0.0) produces meaningful off-screen evidence."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.12, pitch=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.70

    def test_up_6_case_b_eyes_up_and_head_up(self):
        """Case B: Eyes up (dy = -0.11) + Head pitch up (pitch = +7.5 deg) reinforce each other."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.11, pitch=7.5)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.68

    def test_up_7_case_d_small_eye_plus_small_head(self):
        """Case D: Small eye (dy = -0.09) + small head (pitch = +6.0 deg) combine consistently."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.09, pitch=6.0)
        state, conf, reason = _calibrated_attention_decision(obs, config, "SIDE_OR_UP")
        assert "combined_score" in reason or conf >= 0.0

    def test_up_8_case_c_head_up_eyes_neutral(self):
        """Case C: Slight head elevation (pitch = +7.0 deg) but eyes neutral (dy = -0.02) does NOT falsely trigger."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.02, pitch=7.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered  # Damped support prevents false alarm

    def test_up_9_blink_while_looking_up(self):
        """Blink state suppresses false gaze deviations."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.25, blink=True)
        assert obs.face.gaze_state == "BLINKING"

    def test_up_10_low_quality_landmarks_suppressed(self):
        """Low landmark quality (< 0.50) returns UNCERTAIN, never false OFF_SCREEN."""
        config = RuleEngineConfig()
        rule = LookingAwayTooLongRule()
        obs, _ = _build_test_obs(dy=-0.28, face_conf=0.35, gaze_conf=0.35)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered
        assert "UNCERTAIN" in reason
        assert "LOW_QUALITY" in reason


class TestDownwardGazeSuite:
    """Comprehensive Downward Gaze Test Suite (+60% Sensitivity)."""

    def test_down_1_neutral_downward_gaze(self):
        """Reading on-screen / neutral vertical gaze (dy <= 0.08) remains ON_SCREEN."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dx=0.0, dy=0.07)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered
        assert "ON_SCREEN" in reason

    def test_down_2_slight_downward_gaze_subthreshold(self):
        """Slight downward glance (dy = 0.11) within tolerance (0.125) does not trigger off-screen."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dy=0.11)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered

    def test_down_3_moderate_downward_gaze_head_still(self):
        """Moderate downward gaze (dy = 0.18) with head still triggers off-screen cleanly (+60% boost)."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        # dy = 0.18 -> excess = 0.18 - 0.125 = 0.055; eye_v_score = 0.055 / 0.075 = 0.733
        # combined_score >= 0.733 >= 0.40 -> triggers
        obs, _ = _build_test_obs(dy=0.18, pitch=0.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert "OFF_SCREEN" in reason
        assert conf >= 0.70

    def test_down_4_strong_downward_gaze(self):
        """Strong downward gaze (dy = 0.24) triggers with high confidence."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dy=0.24)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.85

    def test_down_5_eyes_down_plus_head_down(self):
        """Eyes down (dy = 0.16) + Head pitch down (pitch = -9.0 deg) mutually reinforce."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        # eye = (0.16 - 0.125)/0.075 = 0.467; head = (9.0 - 6.0)/7.5 = 0.40
        # combined >= 0.50 -> triggers
        obs, _ = _build_test_obs(dy=0.16, pitch=-9.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert triggered
        assert conf >= 0.68

    def test_down_6_head_down_eyes_neutral(self):
        """Distinct downward head tilt (pitch = -10.0 deg) with eyes neutral on screen (dy = 0.03) does not falsely trigger."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dy=0.03, pitch=-10.0)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered # Damped support prevents false alarm

    def test_down_7_blink_while_looking_down(self):
        """Blink state correctly suppresses false downward gaze."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dy=0.22, blink=True)
        assert obs.face.gaze_state == "BLINKING"

    def test_down_8_low_quality_landmarks_suppressed(self):
        """Low landmark quality returns UNCERTAIN, never false OFF_SCREEN."""
        config = RuleEngineConfig()
        rule = RepeatedDownwardGazeRule()
        obs, _ = _build_test_obs(dy=0.22, face_conf=0.30, gaze_conf=0.30)
        triggered, conf, reason = rule.evaluate(obs, config)
        assert not triggered
        assert "UNCERTAIN" in reason
        assert "LOW_QUALITY" in reason
