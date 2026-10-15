"""
Regression Test Suite for Single Violation Episode Lifecycle & Deduplication.
Validates that:
  Scenario A: 10 consecutive frames with OFF-SCREEN ATTENTION active -> 1 episode, 1 UUID, 1 STARTED event.
  Scenario B: OFF-SCREEN active for 5 frames -> inactive for 5 frames -> active for 5 frames -> 2 episodes, 2 distinct UUIDs.
  Scenario C: Continuous normal gaze -> 0 episodes, 0 UUIDs.
  Scenario D: Mixed attention sub-rules (looking away, downward gaze, head rotation) -> 1 episode, 1 UUID, no duplicate episodes.
"""
import time
import unittest
import numpy as np
from pathlib import Path

from ai_engine.core.exam_context import ExamContext
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager


class TestDuplicateViolationEpisodes(unittest.TestCase):

    def setUp(self):
        self.evidence_dir = Path("./evidence/test_dedup")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.config = ViolationManagerConfig(
            debounce_window_seconds=0.3,
            min_confirming_frames=1,
            auto_close_timeout_seconds=0.6,
            evidence_dir=self.evidence_dir,
            max_evidence_items=20,
            enable_logging=False,
        )
        self.vm = ViolationManagerProcessor(self.config)
        self.vm.initialize()
        self.vm.start()

    def tearDown(self):
        self.vm.stop()
        self.vm.cleanup()
        for f in self.evidence_dir.glob("*.jpg"):
            try:
                f.unlink()
            except Exception:
                pass

    def test_scenario_a_continuous_off_screen_single_episode_single_uuid(self):
        """
        Scenario A: 10 consecutive frames with OFF-SCREEN ATTENTION active.
        Expected:
          - Exactly 1 violation episode
          - Exactly 1 UUID
          - Exactly 1 STARTED lifecycle event
          - Exactly 1 active evidence record accumulating duration
          - NOT 10 violations.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_events = []
        observed_uuids = set()

        class LookingAwayRule:
            rule_id = "ATT_LOOKING_AWAY"
            rule_name = "Off-Screen Attention"
            category = "Attention"
            triggered = True
            confidence = 0.90

        for i in range(10):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [LookingAwayRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 40.0, "risk_level": "MEDIUM"})()

            self.vm.process(ctx)

            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)
                    observed_uuids.add(ev.violation_id)

        # Assertions
        self.assertEqual(len(started_events), 1, "Must emit exactly ONE STARTED event for continuous episode")
        self.assertEqual(len(observed_uuids), 1, "Must maintain exactly ONE stable UUID throughout")
        self.assertEqual(len(self.vm._timeline_manager.timeline.violations), 1)

        # Check evidence store
        evidence_store = self.vm.all_evidence_records
        self.assertEqual(len(evidence_store), 1, "Must have exactly 1 evidence record")
        rec = evidence_store[0]
        self.assertEqual(rec["status"], "ACTIVE")
        self.assertEqual(rec["violation_id"], list(observed_uuids)[0])
        self.assertGreaterEqual(rec["total_duration"], 0.8, "Duration must accumulate across the 10 frames")

    def test_scenario_b_active_inactive_active_two_distinct_episodes(self):
        """
        Scenario B:
          - OFF-SCREEN active for 5 frames (0.0s - 0.4s)
          - inactive for 10 frames (0.5s - 1.4s, crosses 0.6s auto-close timeout -> RESOLVES Episode 1)
          - active for 5 frames (1.5s - 1.9s -> CREATES Episode 2)
        Expected:
          - Exactly 2 violation episodes
          - Exactly 2 distinct UUIDs
          - Exactly 2 STARTED events and 1 RESOLVED event.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_events = []
        resolved_events = []
        observed_uuids = set()

        class LookingAwayRule:
            rule_id = "ATT_LOOKING_AWAY"
            rule_name = "Off-Screen Attention"
            category = "Attention"
            triggered = True
            confidence = 0.92

        # Phase 1: 5 frames active (0.0s to 0.4s)
        for i in range(5):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [LookingAwayRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 40.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)
                    observed_uuids.add(ev.violation_id)

        self.assertEqual(len(started_events), 1, "Phase 1 must start Episode 1")
        ep1_uuid = started_events[0].violation_id

        # Phase 2: 10 frames inactive (0.5s to 1.4s, inactive for 1.0s > 0.6s timeout)
        for i in range(5, 15):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": []})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 0.0, "risk_level": "NORMAL"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "RESOLVED":
                    resolved_events.append(ev)

        self.assertEqual(len(resolved_events), 1, "Episode 1 must be resolved after inactivity timeout")
        self.assertEqual(resolved_events[0].violation_id, ep1_uuid)

        # Phase 3: 5 frames active again (1.5s to 1.9s)
        for i in range(15, 20):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [LookingAwayRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 45.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)
                    observed_uuids.add(ev.violation_id)

        # Assertions
        self.assertEqual(len(started_events), 2, "Must emit exactly 2 STARTED events for 2 separate episodes")
        self.assertEqual(len(observed_uuids), 2, "Must have exactly 2 distinct UUIDs")
        ep2_uuid = started_events[1].violation_id
        self.assertNotEqual(ep1_uuid, ep2_uuid, "Episode 2 UUID must be different from Episode 1 UUID")

    def test_scenario_c_continuous_normal_gaze_zero_violations(self):
        """
        Scenario C: Continuous normal gaze (no rules triggered).
        Expected: 0 violation episodes, 0 UUIDs, 0 STARTED events.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_events = []

        for i in range(20):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": []})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 0.0, "risk_level": "NORMAL"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)

        self.assertEqual(len(started_events), 0, "No violations should be created during normal gaze")
        self.assertEqual(len(self.vm.all_evidence_records), 0)

    def test_scenario_d_mixed_attention_signals_maintain_single_episode(self):
        """
        Scenario D: Candidate looks away, looks downward, and turns head simultaneously across 10 frames.
        Expected:
          - Exactly 1 logical episode
          - Exactly 1 UUID
          - All signals merged without duplicate simultaneous cards.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_events = []
        observed_uuids = set()

        class LookingAwayRule:
            rule_id = "ATT_LOOKING_AWAY"
            rule_name = "Off-Screen Attention"
            category = "Attention"
            triggered = True
            confidence = 0.92

        class DownwardGazeRule:
            rule_id = "ATT_DOWNWARD_GAZE"
            rule_name = "Downward Gaze"
            category = "Attention"
            triggered = True
            confidence = 0.88

        class HeadRotationRule:
            rule_id = "ATT_HEAD_ROTATION"
            rule_name = "Head Rotation"
            category = "Attention"
            triggered = True
            confidence = 0.85

        for i in range(10):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [
                LookingAwayRule(),
                DownwardGazeRule(),
                HeadRotationRule()
            ]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 50.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)

            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)
                    observed_uuids.add(ev.violation_id)

        self.assertEqual(len(started_events), 1, "Simultaneous attention sub-signals must emit exactly ONE STARTED event")
        self.assertEqual(len(observed_uuids), 1, "Must maintain exactly ONE UUID for the entire attention episode")
        self.assertEqual(len(self.vm.all_evidence_records), 1, "Must have exactly ONE evidence record in store")


if __name__ == "__main__":
    unittest.main()
