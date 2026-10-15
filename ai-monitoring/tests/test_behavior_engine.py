"""
Automated Test Suite for Phase 5 — Behavioral Intelligence & Temporal Reasoning Engine.
"""
import unittest
import time
import numpy as np

from ai_engine.core.exam_context import ExamContext, FaceInfo, MouthInfo, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.behavior_engine.behavior_event import BehaviorMemoryEntry
from ai_engine.intelligence.behavior_engine.behavior_memory import BehaviorMemory
from ai_engine.intelligence.behavior_engine.sequence_detector import SequenceDetector
from ai_engine.intelligence.behavior_engine.composite_behavior import CompositeBehaviorEvaluator
from ai_engine.intelligence.behavior_engine.confidence_engine import ConfidenceEngine
from ai_engine.intelligence.behavior_engine.behavior_profile import BehaviorProfileManager
from ai_engine.intelligence.behavior_engine.behavior_engine import BehaviorEngineProcessor
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator

class TestBehaviorEngine(unittest.TestCase):

    def setUp(self):
        self.orchestrator = MonitoringPipelineOrchestrator()
        self.orchestrator.initialize()
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_01_behavior_memory_pruning(self):
        """Test rolling memory retention window (60s) and automatic entry expiry pruning."""
        memory = BehaviorMemory(window_seconds=60.0)
        now = 1000.0

        # Add 3 entries within 60s window (t=950s, 970s, 995s)
        memory.add_entry(BehaviorMemoryEntry(timestamp=950.0, rule_name="UNAUTH_PHONE", violation_id="V1", severity="HIGH", confidence=0.9))
        memory.add_entry(BehaviorMemoryEntry(timestamp=970.0, rule_name="ATT_LOOKING_AWAY", violation_id="V2", severity="MEDIUM", confidence=0.8))
        memory.add_entry(BehaviorMemoryEntry(timestamp=995.0, rule_name="MAR", violation_id="V3", severity="LOW", confidence=0.7))

        self.assertEqual(memory.size, 3)

        # Prune with current_timestamp = 1020.0 (cutoff = 960.0)
        memory.prune_expired(now + 20.0)
        # Entry at t=950.0 should be pruned
        self.assertEqual(memory.size, 2)
        recent_rules = [e.rule_name for e in memory.get_recent(60.0, now + 20.0)]
        self.assertNotIn("UNAUTH_PHONE", recent_rules)
        self.assertIn("ATT_LOOKING_AWAY", recent_rules)

    def test_02_sequence_detector(self):
        """Test ordered multi-step sequence detection (Phone -> Looking Away -> Talking)."""
        now = 1000.0
        entries = [
            BehaviorMemoryEntry(timestamp=990.0, rule_name="UNAUTH_PHONE", violation_id="V1", severity="HIGH", confidence=0.9, object_type="CELL_PHONE"),
            BehaviorMemoryEntry(timestamp=993.0, rule_name="ATT_LOOKING_AWAY", violation_id="V2", severity="MEDIUM", confidence=0.8),
            BehaviorMemoryEntry(timestamp=996.0, rule_name="MAR", violation_id="V3", severity="LOW", confidence=0.8, talking=True),
        ]

        seq = ["UNAUTH_PHONE", "ATT_LOOKING_AWAY", "MAR"]
        found, matched = SequenceDetector.detect_sequence(entries, seq, window_seconds=10.0, current_timestamp=now)
        self.assertTrue(found)
        self.assertEqual(len(matched), 3)

    def test_03_composite_behavior_phone_usage(self):
        """Test PHONE_USAGE composite behavior evaluation and explainability generation."""
        now = 1000.0
        entries = [
            BehaviorMemoryEntry(timestamp=999.5, rule_name="UNAUTH_PHONE", violation_id="V1", severity="HIGH", confidence=0.9, phone_present=True, object_type="CELL_PHONE"),
            BehaviorMemoryEntry(timestamp=999.7, rule_name="ATT_LOOKING_AWAY", violation_id="V2", severity="MEDIUM", confidence=0.8),
        ]

        comp = CompositeBehaviorEvaluator.evaluate_phone_usage(entries, current_ts=now)
        self.assertIsNotNone(comp)
        self.assertEqual(comp.name, "PHONE_USAGE")
        self.assertIn("UNAUTH_PHONE", comp.supporting_events)
        self.assertGreater(len(comp.explainability), 0)

    def test_04_confidence_buildup_and_decay(self):
        """Test gradual confidence buildup on support and decay when activity ceases."""
        engine = ConfidenceEngine(decay_rate_per_sec=5.0)
        now = 1000.0

        comp = CompositeBehaviorEvaluator.evaluate_phone_usage([
            BehaviorMemoryEntry(timestamp=999.5, rule_name="UNAUTH_PHONE", violation_id="V1", severity="HIGH", confidence=0.9, phone_present=True, object_type="CELL_PHONE"),
            BehaviorMemoryEntry(timestamp=999.6, rule_name="ATT_LOOKING_AWAY", violation_id="V2", severity="MEDIUM", confidence=0.8),
        ], current_ts=now)

        # 1. Initial confidence calculation
        c1 = engine.calculate_confidence(comp, current_ts=now, is_actively_supported=True)
        self.assertGreaterEqual(c1, 50.0)

        # 2. Support continues 2 seconds later -> Buildup
        c2 = engine.calculate_confidence(comp, current_ts=now + 2.0, is_actively_supported=True)
        self.assertGreater(c2, c1)

        # 3. Activity stops 5 seconds later -> Temporal Decay
        c3 = engine.calculate_confidence(comp, current_ts=now + 7.0, is_actively_supported=False)
        self.assertLess(c3, c2)

    def test_05_behavior_profile_state_transitions(self):
        """Test candidate behavior profile state transitions and trend updates."""
        manager = BehaviorProfileManager()
        now = 1000.0

        # Normal empty state
        p0 = manager.update_profile([], current_ts=now)
        self.assertEqual(p0.state, "NORMAL")
        self.assertEqual(p0.behavior_score, 0.0)

        # Active composite behavior with 75% confidence -> HIGH_RISK state
        comp = CompositeBehaviorEvaluator.evaluate_phone_usage([
            BehaviorMemoryEntry(timestamp=999.5, rule_name="UNAUTH_PHONE", violation_id="V1", severity="HIGH", confidence=0.9, phone_present=True, object_type="CELL_PHONE")
        ], current_ts=now)
        comp.confidence = 75.0

        p1 = manager.update_profile([comp], current_ts=now + 1.0)
        self.assertIn(p1.state, ["SUSPICIOUS", "HIGH_RISK"])

    def test_06_orchestrator_step18_integration(self):
        """Test full pipeline orchestrator runs BehaviorEngine processor as Step 18."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

        pipeline_ms = self.orchestrator.process(context)
        self.assertGreater(pipeline_ms, 0.0)

        # Check behavior_result output attached to context
        b_res = getattr(context, "behavior_result", None)
        self.assertIsNotNone(b_res)
        self.assertIn("profile", b_res)
        self.assertIn("summary", b_res)

if __name__ == "__main__":
    unittest.main()
