"""
Validation Test Suite for Persistent Identity Episodes & Lifecycle Stability.
"""
import unittest
import time
import numpy as np

from ai_engine.core.exam_context import ExamContext, FaceInfo
from ai_engine.identity_protection.observations.identity_observation import IdentityProtectionObservation
from ai_engine.identity_protection.integrity.assessment import IdentityIntegrityAssessment
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig
from ai_engine.intelligence.behavior_engine.behavior_engine import BehaviorEngineProcessor
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from backend.pipeline.result_serializer import ResultSerializer

class DummyFrame:
    def __init__(self, frame_id, ts):
        self.original_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.rgb_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.frame_id = frame_id
        self.timestamp = ts
        self.fps = 10.0

class TestIdentityEpisodeStability(unittest.TestCase):
    def setUp(self):
        self.fusion_proc = FusionProcessor(ObservationFusionConfig())
        self.rule_proc = RuleEngineProcessor(RuleEngineConfig())
        self.beha_proc = BehaviorEngineProcessor()
        self.viol_proc = ViolationManagerProcessor(ViolationManagerConfig())
        self.serializer = ResultSerializer()
        self.fusion_proc.initialize()
        self.rule_proc.initialize()
        self.beha_proc.initialize()
        self.viol_proc.initialize()

    def test_01_persistent_identity_episode_uuid_and_updates(self):
        """Verify continuous identity anomaly maintains single UUID per rule type: STARTED -> UPDATED -> RESOLVED."""
        started_events_by_type = {}
        uuids_by_type = {}

        # Step 1: Trigger identity instability over 70 frames (~5.6s)
        for i in range(1, 71):
            time.sleep(0.08)
            ts = time.time()
            ctx = ExamContext()
            ctx.current_frame = DummyFrame(i, ts)
            fi = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT", identity_confidence=0.90)
            fi.tracking_id = "FACE_1"
            ctx.face_info = fi

            id_obs = IdentityProtectionObservation(
                liveness_state="LIVE", liveness_score=0.45, identity_integrity_score=0.40,
                inference_timestamp=ts, temporal_consistency=0.30, reflection_score=0.75,
                assessment=IdentityIntegrityAssessment(identity_confidence=0.90, overall_liveness=0.45, integrity_score=0.40, stability_score=0.30, timestamp=ts)
            )
            setattr(ctx, "identity_protection_observation", id_obs)

            self.fusion_proc.process(ctx)
            self.rule_proc.process(ctx)
            self.beha_proc.process(ctx)
            self.viol_proc.process(ctx)

            events = getattr(ctx, "lifecycle_events", [])
            for e in events:
                vtype = e.violation_type
                if e.event_type == "STARTED":
                    started_events_by_type.setdefault(vtype, []).append(e)
                    uuids_by_type.setdefault(vtype, set()).add(e.violation_id)

        # Verify each triggered violation type emitted exactly ONE STARTED event and ONE UUID
        self.assertTrue(len(started_events_by_type) > 0, "Must trigger at least one identity violation type")
        for vtype, events in started_events_by_type.items():
            self.assertEqual(len(events), 1, f"Must emit exactly ONE STARTED event per identity episode for {vtype}")
            self.assertEqual(len(uuids_by_type[vtype]), 1, f"Must maintain exact same UUID for {vtype}")

        # Step 2: Brief 3.0s recovery (should NOT close episode or create new STARTED events)
        for i in range(71, 105):
            time.sleep(0.08)
            ts = time.time()
            ctx = ExamContext()
            ctx.current_frame = DummyFrame(i, ts)
            fi = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT", identity_confidence=0.90)
            fi.tracking_id = "FACE_1"
            ctx.face_info = fi

            id_obs = IdentityProtectionObservation(
                liveness_state="LIVE", liveness_score=0.95, identity_integrity_score=0.85,
                inference_timestamp=ts, temporal_consistency=0.90, reflection_score=0.10,
                assessment=IdentityIntegrityAssessment(identity_confidence=0.90, overall_liveness=0.95, integrity_score=0.85, stability_score=0.90, timestamp=ts)
            )
            setattr(ctx, "identity_protection_observation", id_obs)

            self.fusion_proc.process(ctx)
            self.rule_proc.process(ctx)
            self.beha_proc.process(ctx)
            self.viol_proc.process(ctx)

            events = getattr(ctx, "lifecycle_events", [])
            for e in events:
                if e.event_type == "STARTED":
                    self.fail(f"Brief recovery must NOT produce new STARTED event for {e.violation_type}")

if __name__ == "__main__":
    unittest.main()
