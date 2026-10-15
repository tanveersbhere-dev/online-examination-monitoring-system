"""
Confidence Buildup and Temporal Decay Engine for Behavioral Intelligence.
"""
import time
from typing import Dict, Any, List
from ai_engine.intelligence.behavior_engine.behavior_event import CompositeBehaviorInstance

class ConfidenceEngine:
    """
    Computes 0-100% confidence for composite behaviors with buildup and temporal decay.
    """
    def __init__(self, decay_rate_per_sec: float = 45.0) -> None:
        self.decay_rate_per_sec: float = decay_rate_per_sec
        # Tracks historical confidence per behavior type: {behavior_name: (current_confidence, last_active_ts)}
        self._confidence_state: Dict[str, Dict[str, Any]] = {}

    def calculate_confidence(
        self,
        instance: CompositeBehaviorInstance,
        current_ts: float,
        is_actively_supported: bool
    ) -> float:
        name = instance.name
        state = self._confidence_state.get(name, {"conf": 0.0, "last_ts": current_ts})
        prev_conf = state["conf"]
        last_ts = state["last_ts"]

        elapsed = max(0.0, current_ts - last_ts)

        if is_actively_supported:
            # Buildup formula based on supporting events and duration
            event_count = len(instance.supporting_events)
            num_violations = len(instance.supporting_violations)

            target_base = 35.0
            if event_count >= 2 or num_violations >= 1:
                target_base = 50.0
            if event_count >= 3 or num_violations >= 2:
                target_base = 70.0
            if event_count >= 4 or (num_violations >= 2 and instance.duration_seconds >= 5.0):
                target_base = 92.0

            # Gradual buildup towards target_base
            buildup_step = max(5.0, elapsed * 10.0)
            new_conf = min(100.0, max(prev_conf + buildup_step, target_base))
            self._confidence_state[name] = {"conf": new_conf, "last_ts": current_ts}
            return round(new_conf, 1)
        else:
            # Temporal Decay when activity stops
            decay_amount = elapsed * self.decay_rate_per_sec
            new_conf = max(0.0, prev_conf - decay_amount)
            self._confidence_state[name] = {"conf": new_conf, "last_ts": current_ts}
            return round(new_conf, 1)

    def reset(self) -> None:
        self._confidence_state.clear()
