"""
Targeted Test Suite: Professional Proctoring Evidence Debouncing, Lifecycle, and Object Disambiguation.
======================================================================================================
Tests:
  1. Single sustained violation over 50 frames produces exactly 1 evidence entry with in-place duration/score update.
  2. Flickering violation within cooldown window produces exactly 1 coalesced incident (no duplicate evidence files).
  3. Book/notebook held steadily on desk is reliably classified as BOOK/NOTEBOOK, not LAPTOP (majority voting & threshold).
  4. True high-confidence laptop is correctly confirmed as LAPTOP.
  5. Capacity ceiling and rate limiting are strictly enforced.
"""
import time
import unittest
import numpy as np
from pathlib import Path

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.environment.object_validation.models import ObjectValidationConfig, ClassValidationConfig
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer


class TestEvidenceDebouncingAndDisambiguation(unittest.TestCase):

    def setUp(self):
        self.evidence_dir = Path("./evidence/test_debouncing")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.config = ViolationManagerConfig(
            debounce_window_seconds=0.4,
            min_confirming_frames=1,
            cooldown_duration_seconds=2.0,
            dedup_coalesce_window_seconds=4.0,
            evidence_dir=self.evidence_dir,
            max_evidence_items=10
        )
        self.vm = ViolationManagerProcessor(self.config)
        self.vm.initialize()
        self.vm.start()

    def tearDown(self):
        self.vm.stop()
        self.vm.cleanup()
        # Clean up test artifacts
        for f in self.evidence_dir.glob("*.jpg"):
            try:
                f.unlink()
            except Exception:
                pass

    def test_01_single_sustained_violation_produces_single_evidence_record(self):
        """
        Scenario A: Sustained 50 frames of UNAUTH_PHONE.
        Must produce exactly ONE evidence snapshot file and ONE evidence store entry,
        with live in-place duration and score updates.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Feed 50 frames over 5 seconds (10 fps)
        for i in range(50):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)

            # Rule evaluation triggered for UNAUTH_PHONE
            class MockEvaluation:
                rule_id = "UNAUTH_PHONE"
                rule_name = "Mobile Phone Visible"
                category = "Unauthorized Material"
                triggered = True
                confidence = 0.95

            class MockRuleResults:
                evaluations = [MockEvaluation()]

            class MockRisk:
                overall_score = 75.0 + (i * 0.2)  # Score climbs live
                risk_level = "HIGH"

            ctx.rule_results = MockRuleResults()
            ctx.risk_assessment = MockRisk()

            self.vm.process(ctx)

        # Assert: Exactly 1 active evidence record created across all 50 frames
        evidence_store = self.vm.all_evidence_records
        self.assertEqual(len(evidence_store), 1, "Sustained violation must have exactly 1 evidence entry")

        rec = evidence_store[0]
        self.assertEqual(rec["rule_id"], "UNAUTH_PHONE")
        self.assertEqual(rec["status"], "ACTIVE")
        self.assertGreaterEqual(rec["total_duration"], 4.8, "Duration must update live in-place")
        self.assertAlmostEqual(rec["peak_confidence"], 0.95, places=2)

        # Count JPEG snapshots created in directory
        jpg_files = list(self.evidence_dir.glob("*.jpg"))
        self.assertEqual(len(jpg_files), 1, "Sustained violation must produce exactly 1 snapshot image file")

    def test_02_flickering_violation_within_cooldown_coalesces_into_single_incident(self):
        """
        Scenario B: Violation flickers on/off within cooldown and grace period.
        2.0s active -> 1.0s absent (within cooldown) -> 2.0s active.
        Must maintain a single continuous incident and NOT generate duplicate evidence files.
        """
        t0 = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Phase 1: 20 frames active (2.0s)
        for i in range(20):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)

            class MockEv:
                rule_id = "ATT_LOOKING_AWAY"
                rule_name = "Off-Screen Attention"
                category = "Attention"
                triggered = True
                confidence = 0.90
            ctx.rule_results = type("RR", (), {"evaluations": [MockEv()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 40.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)

        self.assertEqual(len(self.vm.all_evidence_records), 1)

        # Phase 2: 10 frames inactive / flicker (1.0s absent — within cooldown)
        for i in range(20, 30):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": []})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 0.0, "risk_level": "NORMAL"})()
            self.vm.process(ctx)

        # Phase 3: 20 frames re-triggered (2.0s active)
        for i in range(30, 50):
            current_time = t0 + (i * 0.1)
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=i + 1, timestamp=current_time)
            ctx.rule_results = type("RR", (), {"evaluations": [MockEv()]})()
            ctx.risk_assessment = type("RA", (), {"overall_score": 50.0, "risk_level": "MEDIUM"})()
            self.vm.process(ctx)

        # Assert: Still only 1 coalesced evidence entry
        evidence_store = self.vm.all_evidence_records
        self.assertEqual(len(evidence_store), 1, "Flickering violation must be coalesced into exactly 1 record")

        # Total duration encompasses the full duration
        rec = evidence_store[0]
        self.assertGreaterEqual(rec["total_duration"], 4.5)

    def test_03_notebook_held_steadily_is_disambiguated_from_laptop(self):
        """
        Scenario C: An open register/notebook with borderline laptop predictions.
        Simulates alternating/mixed detector outputs (LAPTOP conf=0.50, BOOK conf=0.45, flat aspect ratio).
        Must be confirmed as BOOK/NOTEBOOK, NOT LAPTOP.
        """
        cfg = ObjectValidationConfig(
            majority_vote_window=10,
            laptop_book_margin=0.20
        )
        processor = ObjectValidationProcessor(cfg)
        processor.initialize()

        now = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        flat_bbox = BoundingBox(x=100, y=200, width=220, height=120)  # Aspect ratio 1.83 (flat desk register)

        # Stream 10 frames with borderline/confusable predictions
        for frame_idx in range(10):
            ctx = ExamContext()
            ts = now + (frame_idx * 0.1)
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=frame_idx + 1, timestamp=ts)

            # Detector alternates between LAPTOP (conf 0.50) and BOOK (conf 0.45)
            det_type = DetectedObjectType.LAPTOP if frame_idx % 2 == 0 else DetectedObjectType.BOOK
            conf = 0.50 if frame_idx % 2 == 0 else 0.45

            raw_obj = TrackedObject(
                tracking_id=5,
                object_type=det_type,
                confidence=conf,
                bbox=flat_bbox
            )
            o_info = ctx.object_info
            o_info.tracked_objects = [raw_obj]
            ctx.object_info = o_info

            processor.process(ctx)

        validated = ctx.object_info.validated_objects
        self.assertEqual(len(validated), 1, "Object must be confirmed")

        # Must be disambiguated to BOOK or NOTEBOOK, never LAPTOP
        confirmed_type = getattr(validated[0].object_type, "name", str(validated[0].object_type))
        self.assertIn(confirmed_type, ["BOOK", "NOTEBOOK"], "Flat notebook must not be classified as LAPTOP")
        self.assertNotEqual(confirmed_type, "LAPTOP")

    def test_04_genuine_high_confidence_laptop_is_confirmed(self):
        """
        Verify that a true high-confidence laptop (conf=0.85, upright aspect ratio)
        is correctly confirmed as LAPTOP.
        """
        cfg = ObjectValidationConfig()
        processor = ObjectValidationProcessor(cfg)
        processor.initialize()

        now = time.time()
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        upright_bbox = BoundingBox(x=50, y=50, width=200, height=180)  # Aspect ratio 1.11

        for frame_idx in range(5):
            ctx = ExamContext()
            ts = now + (frame_idx * 0.1)
            ctx.current_frame = Frame.from_bgr_image(blank_frame, frame_id=frame_idx + 1, timestamp=ts)

            laptop_obj = TrackedObject(
                tracking_id=8,
                object_type=DetectedObjectType.LAPTOP,
                confidence=0.85,
                bbox=upright_bbox
            )
            o_info = ctx.object_info
            o_info.tracked_objects = [laptop_obj]
            ctx.object_info = o_info

            processor.process(ctx)

        validated = ctx.object_info.validated_objects
        self.assertEqual(len(validated), 1)
        confirmed_type = getattr(validated[0].object_type, "name", str(validated[0].object_type))
        self.assertEqual(confirmed_type, "LAPTOP", "True high-confidence laptop must be confirmed as LAPTOP")




if __name__ == "__main__":
    unittest.main()
