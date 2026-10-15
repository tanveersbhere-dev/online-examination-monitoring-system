"""
Unit tests for Object Re-Detection Reliability and Composite Incident Descriptive Titling.
Verifies that:
1. Re-appearing objects (books, phones) create new active episodes without being blocked by previous completed episodes.
2. Composite incident titles dynamically format as 'Phone + Looking Down', 'Book + Looking Away', 'Identity Mismatch + Phone', etc.
"""
import time
import unittest
import numpy as np

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
from backend.pipeline.result_serializer import ResultSerializer

class TestRedetectionAndTitling(unittest.TestCase):

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

    def test_01_object_redetection_after_episode_resolution(self):
        """Verify object (Book) creates a new active episode when reappearing after previous episode resolved."""
        start_ts = time.time()
        book_eval = RuleEvaluation("UNAUTH_BOOK", "Book Visible", "Unauthorized Material", True, 0.92, "Book detected", start_ts, 0.01)

        # First appearance: Book detected
        class ActiveRuleResults:
            evaluations = [book_eval]
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        active_vs = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs), 1)
        first_id = active_vs[0].violation_id

        # Book disappears and time fast-forwards past resolution timeout
        time.sleep(1.2)
        class InactiveRuleResults:
            evaluations = []
        self.ctx.rule_results = InactiveRuleResults()
        self.vm.process(self.ctx)

        # Episode 1 resolved
        self.assertEqual(len(self.vm.evidence_store), 1)

        # Second appearance: Book reappears 20 seconds later (past 15s coalesce window)
        start_ts2 = time.time() + 20.0
        book_eval2 = RuleEvaluation("UNAUTH_BOOK", "Book Visible", "Unauthorized Material", True, 0.95, "Book detected again", start_ts2, 0.01)
        class ActiveRuleResults2:
            evaluations = [book_eval2]
        self.ctx.rule_results = ActiveRuleResults2()
        self.vm.process(self.ctx)

        # New episode created immediately without being blocked
        active_vs2 = [v for v in self.vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
        self.assertEqual(len(active_vs2), 1)
        second_id = active_vs2[0].violation_id
        self.assertNotEqual(first_id, second_id, "Re-appeared object must start a new episode ID")

    def test_02_descriptive_composite_incident_titles(self):
        """Verify title generator produces descriptive combined labels matching user specifications."""
        t1 = format_composite_incident_title("PHONE_USAGE", ["UNAUTH_PHONE", "ATT_DOWNWARD_GAZE"])
        self.assertEqual(t1, "Phone + Off-Screen Attention")

        t2 = format_composite_incident_title("LOOKING_FOR_NOTES", ["UNAUTH_BOOK", "ATT_LOOKING_AWAY"])
        self.assertEqual(t2, "Book + Off-Screen Attention")

        t3 = format_composite_incident_title("SECURITY_ALERT", ["ID_MISMATCH", "UNAUTH_PHONE"])
        self.assertEqual(t3, "Identity Mismatch + Phone")

        t4 = format_composite_incident_title("COMMUNICATION", ["COMM_MULTIPLE_PERSONS", "MAR"])
        self.assertEqual(t4, "Multiple Person + Conversation")

        t5 = format_composite_incident_title("COMMUNICATION", ["UNAUTH_PHONE", "COMM_EARPHONES"])
        self.assertEqual(t5, "Phone + Earpods")

    def test_03_serializer_outputs_descriptive_titles(self):
        """Verify serializer outputs descriptive title fields in JSON FrameResult payload."""
        start_ts = time.time()
        phone_eval = RuleEvaluation("UNAUTH_PHONE", "Mobile Phone Visible", "Unauthorized Material", True, 0.94, "Phone visible", start_ts, 0.01)
        gaze_eval = RuleEvaluation("ATT_DOWNWARD_GAZE", "Downward Gaze", "Attention", True, 0.88, "Looking down at phone", start_ts, 0.01)

        class ActiveRuleResults:
            evaluations = [phone_eval, gaze_eval]
        self.ctx.rule_results = ActiveRuleResults()
        self.vm.process(self.ctx)

        serializer = ResultSerializer()
        serialized = serializer.to_dict(self.ctx, {}, 1, 10.0, self.vm.evidence_store)

        active_viols = serialized.get("violations", [])
        self.assertGreaterEqual(len(active_viols), 1)
        # Verify title is descriptive (e.g. Phone + Looking Down)
        titles = [v["title"] for v in active_viols]
        self.assertTrue(any("Phone" in t for t in titles))

if __name__ == "__main__":
    unittest.main()
