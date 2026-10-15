"""
Unit tests for Violation Persistence and Event Lifecycle fast resolution.
"""
import time
import unittest
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from ai_engine.intelligence.behavior_engine.behavior_engine import BehaviorEngineProcessor
from ai_engine.intelligence.behavior_engine.behavior_event import BehaviorMemoryEntry

class TestViolationLifecycle(unittest.TestCase):

    def test_01_unauth_phone_fast_resolution(self):
        """Verify UNAUTH_PHONE opens immediately and resolves within 1.0s of disappearance."""
        config = ViolationManagerConfig(auto_close_timeout_seconds=1.0)
        mgr = ViolationTimelineManager(config)
        start_ts = time.time()

        # Frame 1: Phone detected -> STARTED
        triggered_rules = [{"rule_id": "UNAUTH_PHONE", "category": "UNAUTHORIZED_OBJECT", "confidence": 0.95}]
        events = mgr.process_triggers(triggered_rules, risk_score=50.0, risk_level="HIGH", evidence_refs=[], current_time=start_ts)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "STARTED")
        self.assertEqual(events[0].violation_type, "UNAUTH_PHONE")

        # Frame 2: Phone disappears at +0.2s (still OPEN/ACTIVE within 0.8s window)
        events = mgr.process_triggers([], risk_score=0.0, risk_level="NORMAL", evidence_refs=[], current_time=start_ts + 0.2)
        self.assertEqual(len(events), 0)
        self.assertEqual(len([v for v in mgr.timeline.violations if v.status in ("OPEN", "ACTIVE")]), 1)

        # Frame 3: Phone still missing at +0.9s (crosses 0.8s threshold -> RESOLVED)
        events = mgr.process_triggers([], risk_score=0.0, risk_level="NORMAL", evidence_refs=[], current_time=start_ts + 0.9)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RESOLVED")
        self.assertEqual(events[0].violation_type, "UNAUTH_PHONE")
        self.assertEqual(len([v for v in mgr.timeline.violations if v.status in ("OPEN", "ACTIVE")]), 0)

    def test_02_looking_away_fast_resolution(self):
        """Verify ATT_LOOKING_AWAY resolves within 0.6-0.8s when user looks back."""
        config = ViolationManagerConfig()
        mgr = ViolationTimelineManager(config)
        start_ts = time.time()

        # Frame 1: Looking away detected
        triggered_rules = [{"rule_id": "ATT_LOOKING_AWAY", "category": "GAZE_DEVIATION", "confidence": 0.90}]
        events = mgr.process_triggers(triggered_rules, risk_score=30.0, risk_level="MEDIUM", evidence_refs=[], current_time=start_ts)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "STARTED")

        # Frame 2: User looks back at +0.7s (crosses 0.6s threshold for ATT_LOOKING_AWAY)
        events = mgr.process_triggers([], risk_score=0.0, risk_level="NORMAL", evidence_refs=[], current_time=start_ts + 0.7)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RESOLVED")

    def test_03_composite_behavior_fast_decay_and_resolution(self):
        """Verify composite behavior PHONE_USAGE decays confidence and resolves when phone disappears."""
        beha_engine = BehaviorEngineProcessor()
        beha_engine.initialize()
        beha_engine.start()
        now_ts = time.time()

        # Frame 1: Active phone entry 2.0s ago
        old_entry = BehaviorMemoryEntry(
            timestamp=now_ts - 2.0,
            rule_name="UNAUTH_PHONE",
            violation_id="viol_1",
            severity="HIGH",
            confidence=0.95,
            object_type="CELL_PHONE",
            phone_present=True
        )
        beha_engine.memory.add_entry(old_entry)

        # Process frame at current time (2.0s after phone entry)
        ctx = ExamContext()
        beha_engine.process(ctx)

        res = getattr(ctx, "behavior_result", {})
        active = res.get("summary", {}).get("composite_behaviors_detected", [])
        self.assertNotIn("Unauthorized Cell Phone Usage", active)
        self.assertNotIn("PHONE_USAGE", beha_engine.active_behaviors)

if __name__ == "__main__":
    unittest.main()
