"""Focused regression tests for screen-attention classification."""

from ai_engine.intelligence.behavior_engine.temporal_state_machine import BehaviorStateMachineManager
from ai_engine.intelligence.observation_fusion.models import FaceObservation, UnifiedObservation
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.rule_engine.rules import LookingAwayTooLongRule, RepeatedDownwardGazeRule


def _observation(*, yaw=0.0, pitch=0.0, gx=0.0, gy=0.0, gaze_state="ON_SCREEN", gaze_confidence=0.95, calibration=None):
    return UnifiedObservation(
        face=FaceObservation(
            face_present=True,
            face_confidence=0.95,
            gaze_confidence=gaze_confidence,
            gaze_state=gaze_state,
            head_pose_state="FORWARD",
            behavioral_summary={
                "head_yaw": yaw,
                "head_pitch": pitch,
                "gaze_x": gx,
                "gaze_y": gy,
            },
        ),
        calibration=calibration,
    )


def test_within_screen_head_and_eye_movements_do_not_trigger_attention():
    config = RuleEngineConfig()
    looking_away = LookingAwayTooLongRule()
    downward = RepeatedDownwardGazeRule()

    scenarios = [
        _observation(),  # centred screen gaze
        _observation(yaw=-26.0, gx=-0.20),  # left side of display
        _observation(yaw=26.0, gx=0.20),  # right side of display
        _observation(pitch=5.0, gy=-0.04),   # upper display
        _observation(pitch=-5.0, gy=0.07),   # lower display
        _observation(yaw=27.0, pitch=-5.0, gx=0.10, gy=0.07),  # normal reading movement
    ]

    for observation in scenarios:
        assert not looking_away.evaluate(observation, config)[0]
        assert not downward.evaluate(observation, config)[0]


def test_moderate_head_turn_with_reliable_screen_gaze_is_not_off_screen():
    triggered, _, _ = LookingAwayTooLongRule().evaluate(
        _observation(yaw=32.0, gx=0.20), RuleEngineConfig()
    )

    assert not triggered


def test_clear_same_direction_head_and_eye_departure_is_off_screen():
    triggered, _, _ = LookingAwayTooLongRule().evaluate(
        _observation(yaw=32.0, gx=0.55, gaze_state="RIGHT"), RuleEngineConfig()
    )

    assert triggered


def test_downward_rule_requires_evidence_below_the_lower_screen_cone():
    rule = RepeatedDownwardGazeRule()
    config = RuleEngineConfig()

    assert not rule.evaluate(_observation(pitch=-26.0, gy=0.08), config)[0]
    assert rule.evaluate(_observation(pitch=-26.0, gy=0.60, gaze_state="DOWN"), config)[0]


def test_calibrated_head_deviation_uses_gaze_deviation_before_triggering():
    rule = LookingAwayTooLongRule()
    config = RuleEngineConfig()
    base = {
        "has_baseline": True,
        "head_pose_deviation": {
            "delta_yaw": 32.0,
            "abs_delta_yaw": 32.0,
            "delta_pitch": 0.0,
        },
    }

    on_screen = {**base, "gaze_deviation": {"delta_gaze_x": 0.20, "delta_gaze_y": 0.0}}
    away = {**base, "gaze_deviation": {"delta_gaze_x": 0.55, "delta_gaze_y": 0.0}}

    assert not rule.evaluate(_observation(calibration=on_screen), config)[0]
    assert rule.evaluate(_observation(calibration=away), config)[0]


def test_brief_noisy_away_estimate_does_not_activate_an_episode():
    state_machine = BehaviorStateMachineManager()
    start = 1000.0

    _, _, active = state_machine.update_frame(
        "ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=start
    )
    assert not active
    _, _, active = state_machine.update_frame(
        "ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=start + 0.4
    )
    assert not active
