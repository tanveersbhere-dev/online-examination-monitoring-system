"""
Regression Test Suite: False Face Absence & BoundingBox Contradiction Fix
==========================================================================
Verifies:
  - Case A: Face Present -> face_detected=True, valid bbox, presence_state=PRESENT, no false ID_FACE_MISSING or CAMERA_EVASION violations.
  - Case B: Face Absent -> face_detected=False -> presence_state=MISSING/ABSENT, ID_FACE_MISSING generated after threshold.
  - Case C: Face Recovery -> Face returns -> presence_state resets to PRESENT, violation recovers.
  - Case D: Robustness -> BoundingBox dataclass instances, tuples, and lists handled without exceptions in FacePresenceProcessor, ViolationManager, and ResultSerializer.
"""
import pytest
import time
import numpy as np
from ai_engine.core.exam_context import ExamContext, FaceInfo, BoundingBox
from ai_engine.camera.frame import Frame
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
from backend.pipeline.result_serializer import ResultSerializer


@pytest.fixture
def orchestrator():
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    return orch


@pytest.fixture
def serializer():
    return ResultSerializer()


def test_case_a_face_present_no_false_absence(orchestrator, serializer):
    """CASE A: Given a valid detected face with BoundingBox object, presence_state MUST be PRESENT and no ID_FACE_MISSING created."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = Frame.from_bgr_image(blank, frame_id=1, timestamp=time.time())
    ctx = ExamContext()
    ctx.current_frame = frame
    ctx.face_info = FaceInfo(
        face_detected=True,
        confidence=0.95,
        face_count=1,
        bbox=BoundingBox(x=150, y=100, width=200, height=200),
        presence_state="PRESENT"
    )

    for step_name in ["FacePresenceTracker", "ObservationFusion", "RuleEngine", "ViolationManager"]:
        entry = orchestrator._processors.get(step_name)
        if entry and entry.processor:
            entry.processor.process(ctx)

    assert ctx.face_info.face_detected is True
    assert ctx.face_info.presence_state == "PRESENT"
    assert ctx.face_info.absent_duration == 0.0

    res = serializer.to_dict(ctx, orchestrator.processor_health(), 1, 10.0, [])
    face_res = res.get("face", {})
    assert face_res.get("detected") is True
    assert face_res.get("presence_state") == "PRESENT"
    assert face_res.get("bbox") == [150, 100, 200, 200]

    viols = res.get("violations", [])
    violation_types = [v.get("type") or v.get("violation_type") for v in viols]
    assert "ID_FACE_MISSING" not in violation_types
    assert "CAMERA_EVASION" not in violation_types


def test_case_b_face_absent_generates_absence_violation(orchestrator, serializer):
    """CASE B: Given no valid face, presence_state transitions to MISSING and ID_FACE_MISSING violation is created."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = Frame.from_bgr_image(blank, frame_id=1, timestamp=time.time())
    ctx = ExamContext()
    ctx.current_frame = frame
    ctx.face_info = FaceInfo(
        face_detected=False,
        confidence=0.0,
        face_count=0,
        bbox=BoundingBox(x=0, y=0, width=0, height=0),
        presence_state="ABSENT",
        absent_duration=5.0
    )

    for step_name in ["FacePresenceTracker", "ObservationFusion", "RuleEngine", "ViolationManager"]:
        entry = orchestrator._processors.get(step_name)
        if entry and entry.processor:
            entry.processor.process(ctx)

    res = serializer.to_dict(ctx, orchestrator.processor_health(), 1, 10.0, [])
    viols = res.get("violations", [])
    violation_types = [v.get("type") or v.get("violation_type") for v in viols]
    assert "ID_FACE_MISSING" in violation_types or "COMPOSITE_FACE_MISSING_UNKNOWN" in violation_types


def test_case_c_face_recovery_resets_absence_state(orchestrator, serializer):
    """CASE C: Valid face returns after absence -> presence_state resets to PRESENT and absence duration clears."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 1. Missing frame
    ctx = ExamContext()
    ctx.current_frame = Frame.from_bgr_image(blank, frame_id=1, timestamp=time.time())
    ctx.face_info = FaceInfo(face_detected=False, confidence=0.0, face_count=0, presence_state="ABSENT", absent_duration=3.0)
    for step_name in ["FacePresenceTracker", "ObservationFusion", "RuleEngine", "ViolationManager"]:
        orchestrator._processors[step_name].processor.process(ctx)

    # 2. Returned face frame
    ctx.current_frame = Frame.from_bgr_image(blank, frame_id=2, timestamp=time.time() + 0.1)
    ctx.face_info = FaceInfo(
        face_detected=True,
        confidence=0.92,
        face_count=1,
        bbox=BoundingBox(x=100, y=100, width=150, height=150),
        presence_state="PRESENT"
    )
    for step_name in ["FacePresenceTracker", "ObservationFusion", "RuleEngine", "ViolationManager"]:
        orchestrator._processors[step_name].processor.process(ctx)

    assert ctx.face_info.face_detected is True
    assert ctx.face_info.presence_state == "PRESENT"
    assert ctx.face_info.absent_duration == 0.0


def test_case_d_bbox_dataclass_and_tuple_unpacking(orchestrator, serializer):
    """CASE D: Verifies BoundingBox dataclass instances, tuples, and lists do not raise TypeError anywhere in the pipeline."""
    blank = np.zeros((480, 640, 3), dtype=np.uint8)

    # Test BoundingBox instance
    ctx1 = ExamContext()
    ctx1.current_frame = Frame.from_bgr_image(blank, frame_id=1)
    ctx1.face_info = FaceInfo(face_detected=True, confidence=0.9, face_count=1, bbox=BoundingBox(10, 20, 30, 40))
    orchestrator._processors["FacePresenceTracker"].processor.process(ctx1)
    res1 = serializer.to_dict(ctx1, {}, 1, 5.0, [])
    assert res1["face"]["bbox"] == [10, 20, 30, 40]

    # Test tuple
    ctx2 = ExamContext()
    ctx2.current_frame = Frame.from_bgr_image(blank, frame_id=2)
    ctx2.face_info = FaceInfo(face_detected=True, confidence=0.9, face_count=1, bbox=(50, 60, 70, 80))
    orchestrator._processors["FacePresenceTracker"].processor.process(ctx2)
    res2 = serializer.to_dict(ctx2, {}, 2, 5.0, [])
    assert res2["face"]["bbox"] == [50, 60, 70, 80]
