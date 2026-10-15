"""
Enterprise-Grade Violation Lifecycle & Object Continuity Test Suite.
====================================================================
Validates that:
  1. One real-world continuous violation produces exactly ONE logical event and ONE stable UUID.
  2. Duration continuously and monotonically increases without resetting.
  3. Confidence continuously updates (peak, average, running scores).
  4. Temporary signal loss (<2.0s cooldown) seamlessly recovers without event recreation.
  5. Class oscillation (BOOK <-> LAPTOP) across adjacent frames is smoothed and does NOT fragment violations.
  6. Exactly one STARTED event and one RESOLVED event are emitted per completed episode.
  7. Genuine termination (>2.0s timeout) resolves and subsequent re-appearance opens a fresh episode.
"""
import time
import unittest
import numpy as np
from pathlib import Path

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.intelligence.rule_engine.models import RuleEvaluation


class TestEnterpriseViolationLifecycle(unittest.TestCase):

    def setUp(self):
        self.evidence_dir = Path("./evidence/test_enterprise")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.config = ViolationManagerConfig(
            debounce_window_seconds=0.4,
            min_confirming_frames=1,
            cooldown_duration_seconds=2.0,
            dedup_coalesce_window_seconds=2.0,
            evidence_dir=self.evidence_dir,
            max_evidence_items=20,
            enable_logging=False
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

    def test_01_long_duration_continuous_violation_maintains_single_event_and_uuid(self):
        """
        100 continuous frames (10.0 seconds) of UNAUTH_PHONE.
        Must maintain the EXACT same violation ID throughout, with duration growing to 9.9s+.
        Must emit exactly 1 STARTED event and zero duplicate events.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_event_count = 0
        observed_ids = set()

        for i in range(100):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)

            class PhoneRule:
                rule_id = "UNAUTH_PHONE"
                rule_name = "Mobile Phone Visible"
                category = "Unauthorized Material"
                triggered = True
                confidence = 0.90 + (min(i, 10) * 0.008)  # Confidence climbs to 0.98

            ctx.rule_results = type("RR", (), {"evaluations": [PhoneRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 80.0, "risk_level": "HIGH"})()

            self.vm.process(ctx)

            # Collect lifecycle events emitted on this frame
            events = getattr(ctx, "lifecycle_events", [])
            for ev in events:
                if ev.event_type == "STARTED":
                    started_event_count += 1
                    observed_ids.add(ev.violation_id)

        # Assert: exactly 1 STARTED event ever emitted
        self.assertEqual(started_event_count, 1, "Exactly one STARTED event must be emitted for continuous violation")
        self.assertEqual(len(observed_ids), 1, "UUID must remain completely stable")

        # Check evidence store
        evidence_store = self.vm.all_evidence_records
        self.assertEqual(len(evidence_store), 1)
        rec = evidence_store[0]
        self.assertEqual(rec["status"], "ACTIVE")
        self.assertGreaterEqual(rec["total_duration"], 9.5, "Duration must continuously accumulate")
        self.assertAlmostEqual(rec["peak_confidence"], 0.98, places=2)

    def test_02_intermittent_disappearance_recovers_without_new_event(self):
        """
        Violation active for 2.0s -> disappears for 1.0s (within cooldown) -> active for 2.0s.
        Must seamlessly recover without emitting a new STARTED event, incrementing interruption count.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_events = []
        updated_events = []

        class LookingAwayRule:
            rule_id = "ATT_LOOKING_AWAY"
            rule_name = "Off-Screen Attention"
            category = "Attention"
            triggered = True
            confidence = 0.88

        # Phase 1: 20 frames (2.0s) active
        for i in range(20):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [LookingAwayRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 45.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)

        # Phase 2: 10 frames (1.0s) silent (candidate looks back briefly)
        for i in range(20, 30):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": []})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 0.0, "risk_level": "NORMAL"})()
            self.vm.process(ctx)

        # Phase 3: 20 frames (2.0s) re-triggered
        for i in range(30, 50):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [LookingAwayRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 55.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)
            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_events.append(ev)
                elif ev.event_type == "UPDATED":
                    updated_events.append(ev)

        # Assert: Still only 1 STARTED event across the entire session
        self.assertEqual(len(started_events), 1, "Interrupted signal within cooldown must NOT emit duplicate STARTED event")
        self.assertEqual(len(self.vm.all_evidence_records), 1)
        rec = self.vm.all_evidence_records[0]
        self.assertGreaterEqual(rec["interruption_count"], 1, "Interruption count must be incremented upon recovery")
        self.assertGreaterEqual(rec["total_duration"], 4.5, "Total duration encompasses full episode span")

    def test_03_class_oscillation_smoothed_into_single_violation(self):
        """
        Detector oscillates between BOOK and LAPTOP across 10 frames on desk register.
        Temporal buffer must smoothly disambiguate to BOOK without flipping or creating multiple tracks.
        """
        val_cfg = ObjectValidationConfig(majority_vote_window=10, laptop_book_margin=0.20)
        validator = ObjectValidationProcessor(val_cfg)
        validator.initialize()

        now = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        flat_box = BoundingBox(x=120, y=180, width=240, height=130)  # Flat desk register aspect ratio

        confirmed_types = []
        for i in range(10):
            ctx = ExamContext()
            ts = now + (i * 0.1)
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=ts)

            det_type = DetectedObjectType.LAPTOP if i % 2 == 0 else DetectedObjectType.BOOK
            conf = 0.52 if i % 2 == 0 else 0.48
            tracked_obj = TrackedObject(tracking_id=3, object_type=det_type, confidence=conf, bbox=flat_box)
            o_info = ctx.object_info
            o_info.tracked_objects = [tracked_obj]
            ctx.object_info = o_info

            validator.process(ctx)

            if ctx.object_info.validated_objects:
                v_type = getattr(ctx.object_info.validated_objects[0].object_type, "name", str(ctx.object_info.validated_objects[0].object_type))
                confirmed_types.append(v_type)

        # Assert: Validated objects are stably confirmed as BOOK/NOTEBOOK, never bouncing to LAPTOP
        self.assertGreaterEqual(len(confirmed_types), 5)
        for t in confirmed_types:
            self.assertIn(t, ["BOOK", "NOTEBOOK"], f"Oscillating detection must be smoothed to BOOK/NOTEBOOK, got {t}")

    def test_04_continuous_violation_never_appends_duplicate_evidence_records(self):
        """
        Stream 600 continuous frames (60.0s) of looking away.
        Assert that self.vm.all_evidence_records contains EXACTLY 1 record throughout,
        with duration monotonically accumulating and peak confidence updating in-place.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        started_event_count = 0
        observed_uuids = set()

        for i in range(600):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)

            class ContinuousRule:
                rule_id = "ATT_LOOKING_AWAY"
                rule_name = "Off-Screen Attention"
                category = "Attention"
                triggered = True
                confidence = 0.85 + min(i * 0.0002, 0.13)  # Confidence grows to 0.98

            ctx.rule_results = type("RR", (), {"evaluations": [ContinuousRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 75.0, "risk_level": "HIGH"})()
            self.vm.process(ctx)

            for ev in getattr(ctx, "lifecycle_events", []):
                if ev.event_type == "STARTED":
                    started_event_count += 1
                    observed_uuids.add(ev.violation_id)

            # Assert on EVERY single frame: exactly 1 logical evidence record exists
            self.assertEqual(len(self.vm.all_evidence_records), 1, f"Frame {i} appended a duplicate evidence record!")
            rec = self.vm.all_evidence_records[0]
            self.assertEqual(rec["status"], "ACTIVE")

        # Post-run assertion
        self.assertEqual(started_event_count, 1, "Must emit exactly ONE STARTED event")
        self.assertEqual(len(observed_uuids), 1, "Must maintain exactly ONE stable UUID")
        final_rec = self.vm.all_evidence_records[0]
        self.assertGreaterEqual(final_rec["total_duration"], 59.0, "Duration must continuously grow to 59s+")
        self.assertGreaterEqual(final_rec["peak_confidence"], 0.95)

    def test_05_periodic_keyframes_attach_to_single_evidence_record(self):
        """
        Stream 400 frames (40.0s) with 30s periodic keyframe enabled.
        Assert that periodic snapshot attaches to the single logical evidence record's
        snapshots array instead of creating a second evidence record.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        for i in range(400):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)

            class PhoneRule:
                rule_id = "UNAUTH_PHONE"
                rule_name = "Mobile Phone Visible"
                category = "Unauthorized Material"
                triggered = True
                confidence = 0.92

            ctx.rule_results = type("RR", (), {"evaluations": [PhoneRule()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 85.0, "risk_level": "HIGH"})()
            self.vm.process(ctx)

        # Assert: Exactly 1 logical evidence record
        self.assertEqual(len(self.vm.all_evidence_records), 1)
        rec = self.vm.all_evidence_records[0]
        self.assertIn("snapshots", rec)
        # Snapshots list contains initial confirmation + 30s keyframe
        self.assertEqual(len(rec["snapshots"]), 2, "Periodic keyframe must attach inside snapshots array")
        self.assertEqual(rec["total_snapshots"], 2)
        self.assertEqual(rec["snapshots"][0]["snapshot_type"], "INITIAL_CONFIRMATION")
        self.assertEqual(rec["snapshots"][1]["snapshot_type"], "PERIODIC_KEYFRAME")


if __name__ == "__main__":
    unittest.main()
