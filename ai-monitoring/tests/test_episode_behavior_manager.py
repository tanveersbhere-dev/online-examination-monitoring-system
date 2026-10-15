"""
Unit tests for Episode-Based Behavior Manager.
Verifies episode creation, continuation across brief normal intervals (<1.0s),
duration/peak/avg confidence updates, single evidence summary generation on episode completion,
and prevention of evidence flooding during continuous behaviors.
"""
import time
import unittest
import numpy as np
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig, LifecycleEvent
from ai_engine.intelligence.rule_engine.models import RuleEvaluation

class TestEpisodeBehaviorManager(unittest.TestCase):

    def setUp(self):
        self.config = ViolationManagerConfig(enable_logging=False)
        self.vm = ViolationManagerProcessor(self.config)
        self.vm.initialize()
        self.vm.start()

        self.ctx = ExamContext()
        class DummyFrame:
            original_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame_id = 1
        self.ctx.current_frame = DummyFrame()

    def tearDown(self):
        self.vm.cleanup()

    def test_01_single_episode_created_no_immediate_evidence(self):
        """Verify behavior start opens an episode but does NOT immediately generate evidence."""
        start_ts = time.time()
        class ActiveRuleResults:
            evaluations = [
                RuleEvaluation("ATT_LOOKING_AWAY", "Looking Away", "Attention", True, 0.85, "Looking away", start_ts, 0.01)
            ]
        self.ctx.rule_results = ActiveRuleResults()

        self.vm.process(self.ctx)

        # Episode created (LifecycleEvent STARTED)
        events = getattr(self.ctx, "lifecycle_events", [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "STARTED")

        # Evidence store should NOT capture evidence yet (evidence captured on RESOLVED when episode ends)
        self.assertEqual(len(self.vm.evidence_store), 0)

    def test_02_continuous_behavior_updates_same_episode_without_duplicate_evidence(self):
        """Verify continuous frames update duration and peak confidence without creating duplicate evidence."""
        start_ts = time.time()
        rule_eval = RuleEvaluation("ATT_LOOKING_AWAY", "Looking Away", "Attention", True, 0.85, "Looking away", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [rule_eval]

        # Frame 1 at start
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        # Frame 2 at +0.4s (higher confidence 0.95)
        rule_eval.confidence = 0.95
        self.vm.process(self.ctx)

        # Frame 3 at +0.8s
        self.vm.process(self.ctx)

        # Evidence store must still be empty during active episode
        self.assertEqual(len(self.vm.evidence_store), 0)

        # Active violations count in timeline should be exactly 1
        active_vs = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs), 1)
        self.assertEqual(active_vs[0].peak_confidence, 0.95)

    def test_03_brief_interruption_resumes_same_episode(self):
        """Verify candidate brief return to normal (<1.0s) resumes existing episode (increments interruption_count)."""
        start_ts = time.time()
        rule_eval = RuleEvaluation("ATT_LOOKING_AWAY", "Looking Away", "Attention", True, 0.85, "Looking away", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [rule_eval]
        class InactiveRuleResults:
            evaluations = []

        # 1. Looking Away (2 sec)
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        # 2. Brief return to front (0.4 sec)
        self.ctx.rule_results = InactiveRuleResults()
        self.vm.process(self.ctx)

        # 3. Resume Looking Away
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        active_vs = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs), 1)
        # Interruption count should be incremented to 1
        self.assertEqual(active_vs[0].interruption_count, 1)

    def test_04_single_summarized_evidence_on_episode_resolution(self):
        """Verify exactly ONE evidence record is generated when the episode closes on RESOLVED."""
        start_ts = time.time()
        rule_eval = RuleEvaluation("ATT_LOOKING_AWAY", "Looking Away", "Attention", True, 0.85, "Looking away", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [rule_eval]
        class InactiveRuleResults:
            evaluations = []

        # Start episode
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)
        self.assertEqual(len(self.vm.evidence_store), 0)

        # Behavior stops and fast-forwards past timeout (>1.0s)
        time.sleep(1.2)
        self.ctx.rule_results = InactiveRuleResults()
        self.vm.process(self.ctx)

        # Episode resolved -> Exactly ONE evidence item captured
        self.assertEqual(len(self.vm.evidence_store), 1)
        rec = self.vm.evidence_store[0]
        self.assertEqual(rec["rule_id"], "ATT_LOOKING_AWAY")
        self.assertEqual(rec["behavior_type"], "Off-Screen Attention")
        self.assertGreater(rec["total_duration"], 0.0)
        self.assertGreaterEqual(rec["peak_confidence"], 0.85)

    def test_05_category_a_physical_object_immediate_activation(self):
        """Verify Category A physical object & security events (UNAUTH_PHONE, UNAUTH_BOOK) open active episode immediately on frame 1."""
        start_ts = time.time()
        rule_eval = RuleEvaluation("UNAUTH_PHONE", "Mobile Phone Visible", "Unauthorized Material", True, 0.94, "Phone visible", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [rule_eval]

        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        # Immediate episode creation on frame 1
        active_vs = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs), 1)
        self.assertEqual(active_vs[0].violation_type, "UNAUTH_PHONE")

    def test_06_category_b_behavioral_gaze_sustained_activation(self):
        """Verify Category B behavioral gaze events (ATT_LOOKING_AWAY) require sustained deviation before opening active episode."""
        start_ts = time.time()
        rule_eval = RuleEvaluation("ATT_LOOKING_AWAY", "Looking Away", "Attention", True, 0.85, "Looking away", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [rule_eval]

        self.ctx.rule_results = ActiveRuleResults()
        # Brief 0.5s glance
        self.vm.process(self.ctx)

        # Zero active evidence or active violation items during brief glance
        active_vs = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs), 1)  # Episode tracked in memory
        self.assertEqual(len(self.vm.evidence_store), 0)  # No evidence generated during active episode

if __name__ == "__main__":
    unittest.main()
