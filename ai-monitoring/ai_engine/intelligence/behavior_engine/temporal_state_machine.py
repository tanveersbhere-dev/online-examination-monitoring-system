"""
Temporal Behavioral State Machine for Enterprise AI Proctoring Engine.
Manages multi-stage event lifecycles, sliding window duration tracking,
gradual confidence accumulation/decay, hysteresis activation, natural movement filtering,
recurrence acceleration, and adaptive baseline calibration.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("ai_engine.behavior.state_machine")

class BehaviorState:
    NORMAL = "NORMAL"
    OBSERVED = "OBSERVED"
    MONITORING = "MONITORING"
    WARNING = "WARNING"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    ESCALATED = "ESCALATED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"

@dataclass
class RuleThresholdConfig:
    min_ignore_seconds: float = 0.8         # Durations below this are OBSERVED / ignored
    monitoring_seconds: float = 1.5         # Transition to MONITORING
    warning_seconds: float = 2.5            # Transition to WARNING
    activation_seconds: float = 3.0         # Transition to ACTIVE violation
    activation_confidence: float = 80.0     # Hysteresis activation threshold (%)
    resolution_confidence: float = 30.0     # Hysteresis resolution threshold (%)
    accumulation_rate_per_sec: float = 35.0 # Base confidence buildup rate per sec
    decay_rate_per_sec: float = 40.0        # Confidence decay rate per sec
    grace_period_seconds: float = 6.0      # Recovery tolerance duration before resolving episode
    recovering_seconds: float = 3.0        # Time spent in RECOVERING state

DEFAULT_RULE_CONFIGS: Dict[str, RuleThresholdConfig] = {
    # CATEGORY B — Behavioral Gaze & Head Events (Requires sustained ~2.0s deviation before opening active episode)
    "ATT_LOOKING_AWAY": RuleThresholdConfig(
        min_ignore_seconds=0.6, monitoring_seconds=1.2, warning_seconds=1.6, activation_seconds=2.0,
        activation_confidence=75.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ATT_DOWNWARD_GAZE": RuleThresholdConfig(
        min_ignore_seconds=0.7, monitoring_seconds=1.2, warning_seconds=1.6, activation_seconds=2.0,
        activation_confidence=75.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ATT_SIDE_GAZE": RuleThresholdConfig(
        min_ignore_seconds=0.6, monitoring_seconds=1.2, warning_seconds=1.6, activation_seconds=2.0,
        activation_confidence=75.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ATT_UPWARD_GAZE": RuleThresholdConfig(
        min_ignore_seconds=0.6, monitoring_seconds=1.2, warning_seconds=1.6, activation_seconds=2.0,
        activation_confidence=75.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ATT_HEAD_ROTATION": RuleThresholdConfig(
        min_ignore_seconds=0.6, monitoring_seconds=1.2, warning_seconds=1.6, activation_seconds=2.0,
        activation_confidence=75.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ID_FACE_MISSING": RuleThresholdConfig(
        min_ignore_seconds=0.5, monitoring_seconds=1.2, warning_seconds=2.0, activation_seconds=2.5,
        activation_confidence=80.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),
    "ENV_CAM_EVASION": RuleThresholdConfig(
        min_ignore_seconds=0.5, monitoring_seconds=1.2, warning_seconds=2.0, activation_seconds=2.5,
        activation_confidence=80.0, resolution_confidence=30.0, accumulation_rate_per_sec=40.0, decay_rate_per_sec=45.0
    ),

    # CATEGORY A — Physical Object & Security Events (Immediate activation on 1st detection frame)
    "UNAUTH_PHONE": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "UNAUTH_BOOK": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "ENV_BOOK_DETECTED": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "UNAUTH_NOTEBOOK": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "UNAUTH_PAPER": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "COMM_MULTIPLE_PERSONS": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "COMM_EARPHONES": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "COMM_EARBUDS": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "COMM_NECKBAND": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "COMM_HEADPHONES": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),
    "ID_MISMATCH": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=30.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=50.0
    ),

    # CATEGORY C — Identity Protection Subsystem Events (Persistent episodes with gradual decay & extended grace period)
    "IDENTITY_LOW_INTEGRITY": RuleThresholdConfig(
        min_ignore_seconds=1.0, monitoring_seconds=2.0, warning_seconds=3.0, activation_seconds=4.0,
        activation_confidence=75.0, resolution_confidence=25.0, accumulation_rate_per_sec=25.0, decay_rate_per_sec=15.0,
        grace_period_seconds=8.0, recovering_seconds=4.0
    ),
    "IDENTITY_INSTABILITY": RuleThresholdConfig(
        min_ignore_seconds=1.2, monitoring_seconds=2.2, warning_seconds=3.5, activation_seconds=4.5,
        activation_confidence=75.0, resolution_confidence=25.0, accumulation_rate_per_sec=25.0, decay_rate_per_sec=15.0,
        grace_period_seconds=8.0, recovering_seconds=4.0
    ),
    "CONFIRMED_PRESENTATION_ATTACK": RuleThresholdConfig(
        min_ignore_seconds=0.0, monitoring_seconds=0.0, warning_seconds=0.0, activation_seconds=0.0,
        activation_confidence=50.0, resolution_confidence=20.0, accumulation_rate_per_sec=500.0, decay_rate_per_sec=10.0,
        grace_period_seconds=10.0, recovering_seconds=5.0
    ),
    "IDENTITY_REPEATED_MISMATCH": RuleThresholdConfig(
        min_ignore_seconds=0.5, monitoring_seconds=1.5, warning_seconds=2.5, activation_seconds=3.5,
        activation_confidence=75.0, resolution_confidence=25.0, accumulation_rate_per_sec=30.0, decay_rate_per_sec=20.0,
        grace_period_seconds=8.0, recovering_seconds=4.0
    ),
    "INSUFFICIENT_IDENTITY_EVIDENCE": RuleThresholdConfig(
        min_ignore_seconds=1.5, monitoring_seconds=2.5, warning_seconds=4.0, activation_seconds=5.0,
        activation_confidence=70.0, resolution_confidence=30.0, accumulation_rate_per_sec=20.0, decay_rate_per_sec=15.0,
        grace_period_seconds=6.0, recovering_seconds=3.0
    ),
}

@dataclass
class RuleStateTracker:
    rule_id: str
    state: str = BehaviorState.NORMAL
    confidence: float = 0.0
    start_timestamp: float = 0.0
    last_update_timestamp: float = 0.0
    last_observation_timestamp: float = 0.0
    sustained_duration: float = 0.0
    occurrences_60s: List[float] = field(default_factory=list)

    def prune_occurrences(self, current_ts: float) -> None:
        cutoff = current_ts - 60.0
        self.occurrences_60s = [ts for ts in self.occurrences_60s if ts >= cutoff]

class BehaviorStateMachineManager:
    """
    Manages temporal state transitions across all rules.
    Enforces Category A immediate activation, Category B sustained activation, and Category C persistent identity episodes.
    """

    def __init__(self, rule_configs: Optional[Dict[str, RuleThresholdConfig]] = None) -> None:
        self.configs = rule_configs or DEFAULT_RULE_CONFIGS
        self.trackers: Dict[str, RuleStateTracker] = {}

    def get_tracker(self, rule_id: str, current_ts: float) -> RuleStateTracker:
        if rule_id not in self.trackers:
            self.trackers[rule_id] = RuleStateTracker(
                rule_id=rule_id,
                state=BehaviorState.NORMAL,
                confidence=0.0,
                start_timestamp=0.0,
                last_update_timestamp=current_ts,
                last_observation_timestamp=current_ts
            )
        return self.trackers[rule_id]

    def update_frame(
        self,
        rule_id: str,
        observed: bool,
        raw_confidence: float,
        current_ts: float,
        calibration_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, bool]:
        """
        Updates the rule state machine for a single frame.

        Returns:
            (state, confidence, is_active_violation)
            is_active_violation is True when state is ACTIVE, ESCALATED, or RECOVERING.
        """
        cfg = self.configs.get(rule_id, RuleThresholdConfig())
        tracker = self.get_tracker(rule_id, current_ts)
        tracker.prune_occurrences(current_ts)

        elapsed = max(0.001, current_ts - tracker.last_update_timestamp)
        tracker.last_update_timestamp = current_ts

        # 1. Apply Adaptive Calibration Baseline adjustment if available
        adj_cfg = self._apply_calibration_adjustment(cfg, rule_id, calibration_info)

        if observed:
            tracker.last_observation_timestamp = current_ts
            if tracker.start_timestamp == 0.0:
                tracker.start_timestamp = current_ts

            tracker.sustained_duration = max(0.0, current_ts - tracker.start_timestamp)

            # Recurrence acceleration multiplier (if behavior recurred in last 60s)
            recurrence_count = len(tracker.occurrences_60s)
            recurrence_mult = 1.0 + min(1.5, recurrence_count * 0.5)

            # Gradual Accumulation: C_t = min(100.0, C_{t-1} + dt * rate * mult * raw_conf)
            step = elapsed * adj_cfg.accumulation_rate_per_sec * recurrence_mult * max(0.5, raw_confidence)
            tracker.confidence = min(100.0, tracker.confidence + step)

            # If recovering, transition directly back to ACTIVE / ESCALATED seamlessly
            if tracker.state == BehaviorState.RECOVERING:
                new_state = BehaviorState.ESCALATED if recurrence_count >= 2 else BehaviorState.ACTIVE
            elif adj_cfg.activation_seconds == 0.0:
                tracker.confidence = max(80.0, tracker.confidence, raw_confidence * 100.0)
                new_state = BehaviorState.ACTIVE
            elif tracker.sustained_duration < adj_cfg.min_ignore_seconds and tracker.confidence < 35.0:
                new_state = BehaviorState.OBSERVED
            elif tracker.sustained_duration < adj_cfg.monitoring_seconds and tracker.confidence < 55.0:
                new_state = BehaviorState.MONITORING
            elif tracker.sustained_duration < adj_cfg.warning_seconds and tracker.confidence < 75.0:
                new_state = BehaviorState.WARNING
            elif tracker.sustained_duration < adj_cfg.activation_seconds or tracker.confidence < adj_cfg.activation_confidence:
                new_state = BehaviorState.CONFIRMED
            else:
                if tracker.state in (BehaviorState.ACTIVE, BehaviorState.ESCALATED):
                    new_state = BehaviorState.ESCALATED if recurrence_count >= 2 else BehaviorState.ACTIVE
                else:
                    new_state = BehaviorState.ACTIVE
                    tracker.occurrences_60s.append(current_ts)

            # Hysteresis Activation check
            if tracker.confidence >= adj_cfg.activation_confidence and tracker.sustained_duration >= adj_cfg.warning_seconds:
                if tracker.state not in (BehaviorState.ACTIVE, BehaviorState.ESCALATED):
                    new_state = BehaviorState.ACTIVE
                    tracker.occurrences_60s.append(current_ts)

            tracker.state = new_state

        else:
            # Behavior ceased on current frame -> Gradual Hysteresis Decay & Grace Period Handling
            time_since_observed = current_ts - tracker.last_observation_timestamp

            decay_step = elapsed * adj_cfg.decay_rate_per_sec
            tracker.confidence = max(0.0, tracker.confidence - decay_step)

            if tracker.state in (BehaviorState.ACTIVE, BehaviorState.ESCALATED, BehaviorState.RECOVERING):
                if time_since_observed <= adj_cfg.grace_period_seconds and tracker.confidence > adj_cfg.resolution_confidence:
                    tracker.state = BehaviorState.RECOVERING
                else:
                    tracker.state = BehaviorState.RESOLVED
                    tracker.sustained_duration = 0.0
                    tracker.start_timestamp = 0.0
            elif tracker.confidence <= adj_cfg.resolution_confidence or time_since_observed > 1.5:
                if tracker.state in (BehaviorState.WARNING, BehaviorState.CONFIRMED):
                    tracker.state = BehaviorState.RESOLVED
                else:
                    tracker.state = BehaviorState.NORMAL
                tracker.sustained_duration = 0.0
                tracker.start_timestamp = 0.0
            elif tracker.confidence <= 50.0:
                tracker.state = BehaviorState.MONITORING

        is_active_violation = tracker.state in (BehaviorState.ACTIVE, BehaviorState.ESCALATED, BehaviorState.RECOVERING)
        return tracker.state, round(tracker.confidence, 1), is_active_violation

    def _apply_calibration_adjustment(
        self,
        cfg: RuleThresholdConfig,
        rule_id: str,
        calibration_info: Optional[Dict[str, Any]]
    ) -> RuleThresholdConfig:
        """
        Dynamically adjusts rule thresholds using baseline metrics from AdaptiveCalibrationEngine.
        """
        if not calibration_info or not isinstance(calibration_info, dict):
            return cfg

        status = calibration_info.get("status", "")
        if status != "CALIBRATED":
            return cfg

        deltas = calibration_info.get("runtime_deltas", {})
        head_yaw_dev = deltas.get("head_pose_yaw_dev", 0.0)

        # If candidate has larger baseline head motion, slightly expand ignore window
        if "HEAD" in rule_id or "LOOKING" in rule_id:
            if head_yaw_dev > 15.0:
                adjusted = RuleThresholdConfig(
                    min_ignore_seconds=cfg.min_ignore_seconds + 0.3,
                    monitoring_seconds=cfg.monitoring_seconds + 0.3,
                    warning_seconds=cfg.warning_seconds + 0.4,
                    activation_seconds=cfg.activation_seconds + 0.5,
                    activation_confidence=cfg.activation_confidence,
                    resolution_confidence=cfg.resolution_confidence,
                    accumulation_rate_per_sec=cfg.accumulation_rate_per_sec,
                    decay_rate_per_sec=cfg.decay_rate_per_sec
                )
                return adjusted

        return cfg
