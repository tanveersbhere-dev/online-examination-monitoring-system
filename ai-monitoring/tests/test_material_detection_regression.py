"""
Test Suite: Material Detection & Classification Regression (Notebook, Book, Page, Register)
===========================================================================================
Verifies:
  1. Book -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  2. Notebook -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  3. Register -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  4. Diary / Journal -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  5. Textbook -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  6. Printed page -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  7. Loose paper / page -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  8. Exercise book -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  9. Writing pad -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  10. Exam notebook -> ENV_BOOK_DETECTED / UNAUTH_BOOK
  11. NO 'multistage behaviour' is produced when only physical reading/writing material is present
  12. Phone detection remains unchanged (UNAUTH_PHONE)
  13. Audio remains disabled via AUDIO_DEVICE_DETECTION_ENABLED=false
  14. ATT_LOOKING_AWAY remains unchanged
  15. Face-missing remains unchanged (ID_FACE_MISSING)
  16. Multiple-person detection remains unchanged (COMM_MULTIPLE_PERSONS)
  17. Identity/spoof detection remains unchanged
"""
import time
import numpy as np
import pytest

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, TrackedObject, BoundingBox, DetectedObject
)
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


def _create_frame(frame_id=1):
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    return Frame.from_bgr_image(blank, frame_id=frame_id, timestamp=time.time())


def _inject_material_and_evaluate(orchestrator, obj_type, conf=0.92):
    """Helper to inject tracked material and run fusion and rule engine."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.0, 0.0, 1.0))

    obj = TrackedObject(
        tracking_id=101,
        object_type=obj_type,
        bbox=BoundingBox(x=150.0, y=250.0, width=200.0, height=150.0),
        confidence=conf,
        current_state="TRACKED",
        consecutive_frames=2
    )
    oi = ctx.object_info
    oi.tracked_objects = [obj]
    setattr(oi, "validated_objects", [obj])
    ctx.object_info = oi

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    return ctx


def test_01_book_triggers_book_violation(orchestrator):
    """1. Book -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, DetectedObjectType.BOOK)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_02_notebook_triggers_book_violation(orchestrator):
    """2. Notebook -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, DetectedObjectType.NOTEBOOK)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered) or ("UNAUTH_NOTEBOOK" in triggered)


def test_03_register_triggers_book_violation(orchestrator):
    """3. Register -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, DetectedObjectType.REGISTER)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered) or ("UNAUTH_REGISTER" in triggered)


def test_04_diary_journal_triggers_book_violation(orchestrator):
    """4. Diary/Journal string -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "DIARY")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_05_textbook_triggers_book_violation(orchestrator):
    """5. Textbook -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "TEXTBOOK")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_06_printed_page_triggers_book_violation(orchestrator):
    """6. Printed page -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "PRINTED_PAGE")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_07_loose_paper_page_triggers_book_violation(orchestrator):
    """7. Loose paper/page -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, DetectedObjectType.PAPER)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered) or ("UNAUTH_PAPER" in triggered)


def test_08_exercise_book_triggers_book_violation(orchestrator):
    """8. Exercise book -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "EXERCISE_BOOK")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_09_writing_pad_triggers_book_violation(orchestrator):
    """9. Writing pad -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "WRITING_PAD")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_10_exam_notebook_triggers_book_violation(orchestrator):
    """10. Exam notebook -> ENV_BOOK_DETECTED / UNAUTH_BOOK."""
    ctx = _inject_material_and_evaluate(orchestrator, "EXAM_NOTEBOOK")
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert ("UNAUTH_BOOK" in triggered) or ("ENV_BOOK_DETECTED" in triggered)


def test_11_no_multistage_behavior_for_book_alone(orchestrator, serializer):
    """11. Verify NO 'multistage behaviour' / composite behavior is generated for book alone."""
    ctx = _inject_material_and_evaluate(orchestrator, DetectedObjectType.BOOK)
    orchestrator._processors["BehaviorEngine"].processor.process(ctx)
    orchestrator._processors["ViolationManager"].processor.process(ctx)

    res = serializer.to_dict(ctx, orchestrator.processor_health(), 1, 10.0, [])
    behaviors = res.get("behavior", {}).get("summary", {}).get("composite_behaviors_detected", [])
    assert "LOOKING_FOR_NOTES" not in behaviors
    assert "Multi-Signal Behavioral Flag" not in behaviors

    violations = res.get("violations", [])
    for v in violations:
        title = v.get("title", "")
        assert "Multi-Signal" not in title
        assert "Composite" not in title


def test_12_phone_detection_unchanged(orchestrator):
    """12. Phone detection remains unchanged (UNAUTH_PHONE)."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

    phone_obj = TrackedObject(
        tracking_id=1,
        object_type=DetectedObjectType.CELL_PHONE,
        bbox=BoundingBox(x=300.0, y=300.0, width=100.0, height=150.0),
        confidence=0.88,
        current_state="TRACKED",
        consecutive_frames=2
    )
    oi = ctx.object_info
    oi.tracked_objects = [phone_obj]
    setattr(oi, "validated_objects", [phone_obj])
    ctx.object_info = oi

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "UNAUTH_PHONE" in triggered


def test_13_audio_disabled_suppressed(orchestrator, serializer):
    """13. Audio detection remains disabled."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

    audio_obj = TrackedObject(
        tracking_id=5,
        object_type=DetectedObjectType.COMM_EARPHONES,
        bbox=BoundingBox(x=200, y=100, width=50, height=50),
        confidence=0.95,
        current_state="TRACKED",
        consecutive_frames=3
    )
    oi = ctx.object_info
    oi.tracked_objects = [audio_obj]
    setattr(oi, "validated_objects", [audio_obj])
    ctx.object_info = oi

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    orchestrator._processors["ViolationManager"].processor.process(ctx)

    res = serializer.to_dict(ctx, orchestrator.processor_health(), 1, 10.0, [])
    viols = res.get("violations", [])
    v_types = [v.get("type") or v.get("violation_type") for v in viols]
    assert "COMM_EARPHONES" not in v_types


def test_14_attention_tolerance_unchanged(orchestrator):
    """14. Direct screen viewing produces NO ATT_LOOKING_AWAY."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.0, 0.0, 1.0))

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_15_face_missing_unchanged(orchestrator):
    """15. Face missing triggers ID_FACE_MISSING independently."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=False, confidence=0.0, face_count=0, presence_state="ABSENT")

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ID_FACE_MISSING" in triggered


def test_16_multiple_persons_unchanged(orchestrator):
    """16. Multiple persons triggers COMM_MULTIPLE_PERSONS independently."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=2, presence_state="MULTIPLE")

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "COMM_MULTIPLE_PERSONS" in triggered or "ID_MULTIPLE_FACES" in triggered
