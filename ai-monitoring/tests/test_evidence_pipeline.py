"""
Unit tests for Composite Evidence Generation and Object Re-appearance Temporal Reasoning.
"""
import time
import numpy as np
import pytest

from ai_engine.core.exam_context import ExamContext, BoundingBox, TrackedObject
from ai_engine.core.enums import DetectedObjectType
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig, LifecycleEvent
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from backend.pipeline.result_serializer import ResultSerializer


def test_composite_evidence_capture_preserves_all_violations(tmp_path):
    """Test that when multiple violations occur simultaneously, all violations, objects, and faces are saved."""
    config = ViolationManagerConfig(evidence_dir=tmp_path, enable_logging=False)
    vm = ViolationManagerProcessor(config)
    vm.initialize()
    vm.start()

    ctx = ExamContext()
    # Create dummy original frame
    class DummyFrame:
        original_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_id = 42
    ctx.current_frame = DummyFrame()

    # Attach face_info (Identity Mismatch)
    class DummyFaceInfo:
        face_detected = True
        confidence = 0.95
        face_count = 1
        bbox = [100, 100, 200, 200]
        identity_consistent = False
        identity_confidence = 0.25
        similarity_score = 0.25
        presence_state = "PRESENT"
    ctx.face_info = DummyFaceInfo()

    phone = TrackedObject(tracking_id=1, object_type=DetectedObjectType.CELL_PHONE, bbox=BoundingBox(10, 10, 50, 80), confidence=0.94, current_state="TRACKED")
    book = TrackedObject(tracking_id=2, object_type=DetectedObjectType.BOOK, bbox=BoundingBox(300, 200, 120, 150), confidence=0.91, current_state="TRACKED")
    obj_info = ctx.object_info
    obj_info.validated_objects = [phone, book]
    obj_info.tracked_objects = [phone, book]
    ctx.object_info = obj_info

    # Attach multiple rule results
    class DummyRuleResults:
        evaluations = [
            RuleEvaluation("ID_MISMATCH", "Identity Mismatch", "Identity", True, 0.95, "Identity mismatch", time.time(), 0.01),
            RuleEvaluation("UNAUTH_PHONE", "Mobile Phone Visible", "Unauthorized Material", True, 0.94, "Phone visible", time.time(), 0.01),
            RuleEvaluation("UNAUTH_BOOK", "Book Visible", "Unauthorized Material", True, 0.91, "Book visible", time.time(), 0.01),
        ]
    ctx.rule_results = DummyRuleResults()

    # Process initial frame to start episode
    vm.process(ctx)

    # Fast-forward time past auto-close resolution timeout (1.5s later)
    time.sleep(1.2)
    class EmptyRuleResults:
        evaluations = []
    ctx.rule_results = EmptyRuleResults()
    vm.process(ctx)

    evidence_store = vm.evidence_store
    assert len(evidence_store) >= 1, "Evidence store should capture single summarized record on RESOLVED episode completion"

    # Inspect the composite records
    all_v_ids = [r["rule_id"] for r in evidence_store]
    assert "ID_MISMATCH" in all_v_ids
    assert "UNAUTH_PHONE" in all_v_ids
    assert "UNAUTH_BOOK" in all_v_ids

    rec = evidence_store[-1]

    # Verify detected objects with confidence
    assert len(rec["detected_objects"]) == 2
    obj_types = [o["type"] for o in rec["detected_objects"]]
    assert "CELL_PHONE" in obj_types
    assert "BOOK" in obj_types
    for o in rec["detected_objects"]:
        if o["type"] == "CELL_PHONE":
            assert o["confidence"] == 0.94
        if o["type"] == "BOOK":
            assert o["confidence"] == 0.91

    # Verify identity verification result
    assert rec["identity_verification_result"]["consistent"] is False
    assert rec["identity_verification_result"]["confidence"] == 0.25

    # Verify serializer output
    serializer = ResultSerializer()
    serialized = serializer.to_dict(ctx, {}, 42, 10.0, evidence_store)
    assert "evidence" in serialized
    assert len(serialized["evidence"]) >= 1
    assert serialized["evidence"][-1]["contributing_violations"] == rec["contributing_violations"]

    vm.cleanup()


def test_object_reappearance_instant_reconfirmation():
    """Test that when an object disappears briefly and reappears, it is re-confirmed without delay."""
    cfg = ObjectValidationConfig(max_missing_frames_to_expire=30)
    buffer = TemporalConfirmationBuffer(cfg)

    now = time.time()
    bbox = BoundingBox(10, 10, 50, 50)

    # Frame 1: first seen
    confirmed, f_cnt, _, _ = buffer.update_and_evaluate(1, "BOOK", 0.9, now, bbox)
    assert not confirmed

    # Frame 2: confirmed
    confirmed, f_cnt, _, _ = buffer.update_and_evaluate(1, "BOOK", 0.9, now + 0.03, bbox)
    assert confirmed

    # Object disappears for 10 frames
    for i in range(10):
        buffer.age_missing_tracks(active_keys_seen=set())

    # Object reappears on Frame 13
    confirmed, f_cnt, _, _ = buffer.update_and_evaluate(1, "BOOK", 0.9, now + 0.5, bbox)
    assert confirmed, "Reappearing object within grace window should re-confirm immediately"
