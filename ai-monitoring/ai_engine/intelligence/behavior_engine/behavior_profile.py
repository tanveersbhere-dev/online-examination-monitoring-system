"""
Candidate Behavior Profile Manager for Behavioral Intelligence Engine.
"""
import time
from typing import List, Dict, Any, Optional
from ai_engine.intelligence.behavior_engine.behavior_event import (
    CandidateBehaviorProfile, CompositeBehaviorInstance, BehaviorTimelineEvent
)

class BehaviorProfileManager:
    """
    Manages live Candidate Behavior Profile state, overall behavior score, trend, and lifecycle events.
    """
    def __init__(self) -> None:
        self.profile: CandidateBehaviorProfile = CandidateBehaviorProfile()
        self.timeline_events: List[BehaviorTimelineEvent] = []
        self._score_history: List[float] = []

    def update_profile(
        self,
        active_behaviors: List[CompositeBehaviorInstance],
        current_ts: float
    ) -> CandidateBehaviorProfile:
        # Calculate behavior score based on active composite behavior confidences
        if not active_behaviors:
            raw_score = 0.0
        else:
            # Weighted sum capped at 100
            max_conf = max(b.confidence for b in active_behaviors)
            sum_conf = sum(b.confidence for b in active_behaviors)
            raw_score = min(100.0, max_conf * 0.7 + (sum_conf - max_conf) * 0.3)

        prev_score = self.profile.behavior_score
        self.profile.behavior_score = round(raw_score, 1)

        # Update Trend
        self._score_history.append(raw_score)
        if len(self._score_history) > 20:
            self._score_history.pop(0)

        if len(self._score_history) >= 3:
            diff = self._score_history[-1] - self._score_history[-3]
            if diff > 5.0:
                self.profile.trend = "ESCALATING"
                self.profile.last_escalation = current_ts
            elif diff < -5.0:
                self.profile.trend = "RECOVERING"
                self.profile.last_recovery = current_ts
            else:
                self.profile.trend = "STABLE"

        # Determine Profile State
        prev_state = self.profile.state
        if raw_score >= 85.0:
            new_state = "CRITICAL"
        elif raw_score >= 65.0:
            new_state = "HIGH_RISK"
        elif raw_score >= 45.0:
            new_state = "SUSPICIOUS"
        elif raw_score >= 20.0:
            new_state = "SLIGHTLY_SUSPICIOUS"
        else:
            new_state = "NORMAL"

        self.profile.state = new_state
        self.profile.active_composite_behaviors = active_behaviors

        # Emit timeline events on state or behavior transitions
        self._sync_timeline(active_behaviors, current_ts)

        return self.profile

    def _sync_timeline(self, active_behaviors: List[CompositeBehaviorInstance], current_ts: float) -> None:
        active_names = {b.name for b in active_behaviors}

        for b in active_behaviors:
            # Check if this behavior is new
            existing = [t for t in self.timeline_events if t.type == b.name and t.transition in ["STARTED", "ESCALATED"]]
            if not existing:
                tev = BehaviorTimelineEvent(
                    id=f"BHEV-{b.name}-{int(current_ts * 1000) % 10000}",
                    type=b.name,
                    transition="STARTED",
                    confidence=b.confidence,
                    timestamp=current_ts,
                    description=f"Composite behavior '{b.title}' detected ({b.confidence}% confidence)",
                    duration_seconds=b.duration_seconds
                )
                self.timeline_events.append(tev)
            elif b.confidence >= 80.0 and not any(t.transition == "ESCALATED" for t in existing):
                tev = BehaviorTimelineEvent(
                    id=f"BHEV-{b.name}-ESC-{int(current_ts * 1000) % 10000}",
                    type=b.name,
                    transition="ESCALATED",
                    confidence=b.confidence,
                    timestamp=current_ts,
                    description=f"Composite behavior '{b.title}' escalated to HIGH confidence ({b.confidence}%)",
                    duration_seconds=b.duration_seconds
                )
                self.timeline_events.append(tev)

        # Check resolved behaviors
        for tev in self.timeline_events:
            if tev.type not in active_names and tev.transition not in ["RESOLVED", "RECOVERED"]:
                # Mark resolved
                res_ev = BehaviorTimelineEvent(
                    id=f"BHEV-{tev.type}-RES-{int(current_ts * 1000) % 10000}",
                    type=tev.type,
                    transition="RESOLVED",
                    confidence=0.0,
                    timestamp=current_ts,
                    description=f"Composite behavior '{tev.type}' ceased/resolved",
                    duration_seconds=round(current_ts - tev.timestamp, 1)
                )
                self.timeline_events.append(res_ev)
                tev.transition = "RESOLVED"
