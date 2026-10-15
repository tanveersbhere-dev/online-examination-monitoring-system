"""
Test Suite: Laptop Detection Preservation & UNAUTH_LAPTOP Violation Integration
================================================================================
Comprehensive verification that:
1. Genuine LAPTOP detections with flat/desk geometry (width >= 1.2 * height, y > 200)
   and confidence in 0.35-0.65 are preserved as LAPTOP and never converted to REGISTER/BOOK.
2. Genuinely ambiguous cases with coexisting paper votes still disambiguate properly.
3. ObjectValidationProcessor validates and confirms LAPTOP objects.
4. ObservationFusionProcessor sets environment.laptop_present = True.
5. LaptopVisibleRule evaluates correctly.
6. RuleEngineProcessor produces RuleEvaluation("UNAUTH_LAPTOP").
7. ViolationManagerProcessor debounces and opens UNAUTH_LAPTOP lifecycle episode.
8. Evidence engine stores snapshot and links to UNAUTH_LAPTOP.
9. ResultSerializer serializes UNAUTH_LAPTOP with title "Unauthorized Laptop".
10. Composite behavior titling formats standalone and combined laptop incidents.
11. Camera 1 detects UNAUTH_LAPTOP.
12. Camera 2 detects UNAUTH_LAPTOP via CAMERA_2_APPROVED_RULES.
13. SQLite database persistence stores and fetches UNAUTH_LAPTOP with evidence.
"""
import os
import time
import uuid
import pytest
import numpy as np
import cv2
from pathlib import Path
from typing import Optional

from ai_engine.core.exam_context import ExamContext, BoundingBox, TrackedObject, FaceInfo
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_validation.models import (
    ObjectValidationConfig, ClassValidationConfig, ValidationReason
)
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.intelligence.observation_fusion.models import (
    ObservationFusionConfig, EnvironmentObservation, UnifiedObservation
)
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.rule_engine.models import RuleEvaluation, RuleEngineConfig
from ai_engine.intelligence.rule_engine.rules import LaptopVisibleRule
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig, LifecycleEvent
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
from backend.adapters.monitoring_persistence_adapter import MonitoringPersistenceAdapter
from backend.database.session_repository import session_repository
from backend.pipeline.result_serializer import ResultSerializer


def _make_dummy_frame(camera_id: str = "camera_1", frame_id: int = 1, timestamp: Optional[float] = None) -> Frame:
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    ts = timestamp if timestamp is not None else time.time()
    return Frame.from_bgr_image(img, camera_id=camera_id, frame_id=frame_id, timestamp=ts)


# ==============================================================================
# TEST 1: Mandatory Bug Regression: YOLO LAPTOP with Desk Geometry Preserved
# ==============================================================================
def test_1_regression_yolo_laptop_with_desk_geometry_preserved_as_laptop():
    """
    REGRESSION ROOT CAUSE VERIFICATION:
    In the previous code, temporal_buffer converted ANY LAPTOP to REGISTER if
    aspect_ratio >= 1.20 or y > 200.0, even with 0 paper votes!
    Here, a laptop with aspect_ratio=1.8 (desk view) and confidence=0.45
    MUST be preserved as LAPTOP.
    """
    config = ObjectValidationConfig()
    buffer = TemporalConfirmationBuffer(config)
    
    # Flat horizontal bbox matching real laptop placed on a desk: 360 wide x 200 high (aspect ratio = 1.8), y = 250
    bbox = BoundingBox(x=100.0, y=250.0, width=360.0, height=200.0)
    
    t0 = 100.0
    for i in range(5):
        confirmed, count, dur, reason = buffer.update_and_evaluate(
            track_id=1,
            object_type="LAPTOP",
            confidence=0.45,
            current_ts=t0 + i * 0.1,
            bbox=bbox
        )
    
    resolved_type = buffer.get_resolved_type("trk_1", default="UNKNOWN")
    resolved_conf = buffer.get_resolved_confidence("trk_1", default=0.45)
    
    # MUST BE LAPTOP, NEVER REGISTER OR BOOK!
    assert resolved_type == "LAPTOP", f"Expected LAPTOP but got {resolved_type}!"
    assert resolved_conf == pytest.approx(0.45, abs=0.01)


# ==============================================================================
# TEST 2: Genuine Paper/Book Votes Still Disambiguate Appropriately
# ==============================================================================
def test_2_disambiguation_when_paper_votes_coexist():
    """
    When genuine paper/register votes coexist in history and confidence is below
    laptop threshold, disambiguation to REGISTER/BOOK should still take place.
    """
    config = ObjectValidationConfig()
    buffer = TemporalConfirmationBuffer(config)
    
    bbox = BoundingBox(x=100.0, y=250.0, width=300.0, height=200.0)
    t0 = 100.0
    
    # Simulate ambiguous detections: alternating BOOK / REGISTER / weak LAPTOP
    buffer.update_and_evaluate(1, "BOOK", 0.80, t0, bbox)
    buffer.update_and_evaluate(1, "REGISTER", 0.82, t0 + 0.1, bbox)
    buffer.update_and_evaluate(1, "LAPTOP", 0.50, t0 + 0.2, bbox)
    
    resolved_type = buffer.get_resolved_type("trk_1", default="UNKNOWN")
    assert resolved_type in ("REGISTER", "BOOK", "NOTEBOOK")


# ==============================================================================
# TEST 3: ObjectValidationProcessor Accepts and Confirms LAPTOP
# ==============================================================================
def test_3_object_validation_layer_accepts_laptop():
    """
    ObjectValidationProcessor passes and accepts LAPTOP candidates with
    confidence >= 0.28 across consecutive frames.
    """
    config = ObjectValidationConfig()
    processor = ObjectValidationProcessor(config)
    processor.initialize()
    
    t0 = 100.0
    bbox = BoundingBox(x=50.0, y=220.0, width=280.0, height=160.0)
    
    accepted_items = []
    for frame_id in range(1, 5):
        ctx = ExamContext()
        ctx.current_frame = _make_dummy_frame(frame_id=frame_id, timestamp=t0 + frame_id * 0.1)
        raw_obj = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.LAPTOP,
            bbox=bbox,
            confidence=0.55,
            current_state="TRACKED",
            consecutive_frames=frame_id
        )
        o_info = ctx.object_info
        o_info.tracked_objects = [raw_obj]
        ctx.object_info = o_info
        
        processor.process(ctx)
        validated = getattr(ctx.object_info, "validated_objects", [])
        if validated:
            accepted_items.extend(validated)
            
    assert len(accepted_items) > 0
    assert accepted_items[-1].object_type == DetectedObjectType.LAPTOP
    assert accepted_items[-1].confidence >= 0.28


# ==============================================================================
# TEST 4: ObservationFusionProcessor Sets laptop_present = True
# ==============================================================================
def test_4_observation_fusion_populates_laptop_present():
    """
    ObservationFusionProcessor extracts LAPTOP from validated objects
    and sets laptop_present = True on EnvironmentObservation.
    """
    fusion = FusionProcessor(ObservationFusionConfig(enable_face=False, enable_environment=True))
    fusion.initialize()
    
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame()
    
    laptop_item = TrackedObject(
        tracking_id=1,
        object_type=DetectedObjectType.LAPTOP,
        bbox=BoundingBox(x=50, y=50, width=200, height=120),
        confidence=0.62,
        current_state="TRACKED",
    )
    o_info = ctx.object_info
    o_info.validated_objects = [laptop_item]
    ctx.object_info = o_info
    
    fusion.process(ctx)
    obs = getattr(ctx, "observation", None)
    
    assert obs is not None
    assert obs.environment is not None
    assert obs.environment.laptop_present is True
    assert any(e.get("type") == "LAPTOP" for e in obs.environment.tracked_entities_summary)


# ==============================================================================
# TEST 5: LaptopVisibleRule Evaluates Correctly
# ==============================================================================
def test_5_laptop_visible_rule_evaluates_correctly():
    """
    LaptopVisibleRule triggers with high confidence when laptop_present is True.
    """
    rule = LaptopVisibleRule()
    config = RuleEngineConfig()
    
    # 1. Negative test: no laptop
    obs_clean = UnifiedObservation(timestamp=100.0, environment=EnvironmentObservation(laptop_present=False))
    trig, conf, reason = rule.evaluate(obs_clean, config)
    assert trig is False
    
    # 2. Positive test: laptop present
    obs_laptop = UnifiedObservation(
        timestamp=100.0,
        environment=EnvironmentObservation(
            laptop_present=True,
            tracked_entities_summary=[{"id": 1, "type": "LAPTOP", "conf": 0.88}]
        )
    )
    trig, conf, reason = rule.evaluate(obs_laptop, config)
    assert trig is True
    assert conf >= 0.85
    assert "laptop" in reason.lower()


# ==============================================================================
# TEST 6: RuleEngineProcessor Triggers UNAUTH_LAPTOP
# ==============================================================================
def test_6_rule_engine_processor_triggers_unauth_laptop():
    """
    RuleEngineProcessor evaluates LaptopVisibleRule when enabled
    and records RuleEvaluation with rule_id == "UNAUTH_LAPTOP".
    """
    cfg = RuleEngineConfig()
    engine = RuleEngineProcessor(cfg)
    engine.initialize()
    
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame("camera_1")
    ctx.observation = UnifiedObservation(
        timestamp=100.0,
        environment=EnvironmentObservation(
            laptop_present=True,
            tracked_entities_summary=[{"id": 1, "type": "LAPTOP", "conf": 0.85}]
        )
    )
    
    engine.process(ctx)
    evals = ctx.rule_results.evaluations
    laptop_evals = [e for e in evals if e.rule_id == "UNAUTH_LAPTOP" and e.triggered]
    assert len(laptop_evals) == 1
    assert laptop_evals[0].category == "Electronic Device"


# ==============================================================================
# TEST 7: ViolationManager Debounces and Opens UNAUTH_LAPTOP Episode
# ==============================================================================
def test_7_violation_manager_debounces_and_opens_unauth_laptop_episode(tmp_path):
    """
    ViolationManagerProcessor debounces UNAUTH_LAPTOP and fires LifecycleEvent("STARTED").
    """
    vm_cfg = ViolationManagerConfig(
        debounce_window_seconds=1.5,
        min_confirming_frames=3,
        evidence_dir=tmp_path
    )
    vm = ViolationManagerProcessor(vm_cfg)
    vm.initialize()
    
    t0 = 100.0
    started_events = []
    
    # Feed frames spanning 2.0 seconds (> debounce window of 1.5s, >= 3 frames)
    for i in range(10):
        t = t0 + i * 0.25
        ctx = ExamContext()
        ctx.current_frame = _make_dummy_frame("camera_1", frame_id=i+1, timestamp=t)
        
        class DummyRuleResults:
            evaluations = [
                RuleEvaluation(
                    rule_id="UNAUTH_LAPTOP",
                    rule_name="Laptop Visible",
                    category="Electronic Device",
                    triggered=True,
                    confidence=0.88,
                    supporting_observations="Unauthorized laptop detected",
                    evaluation_timestamp=t,
                    evaluation_duration=1.0
                )
            ]
        ctx.rule_results = DummyRuleResults()
        
        vm.process(ctx)
        events = getattr(ctx, "lifecycle_events", [])
        for e in events:
            if e.event_type == "STARTED" and e.violation_type == "UNAUTH_LAPTOP":
                started_events.append(e)
                
    assert len(started_events) == 1
    assert started_events[0].violation_type == "UNAUTH_LAPTOP"
    assert started_events[0].camera_id == "camera_1"


# ==============================================================================
# TEST 8: Evidence Engine Captures Snapshot for UNAUTH_LAPTOP
# ==============================================================================
def test_8_evidence_engine_captures_snapshot_for_unauth_laptop(tmp_path):
    """
    Evidence capture creates a physical snapshot JPEG file on disk for UNAUTH_LAPTOP.
    """
    vm_cfg = ViolationManagerConfig(
        debounce_window_seconds=0.1,
        min_confirming_frames=1,
        evidence_dir=tmp_path
    )
    vm = ViolationManagerProcessor(vm_cfg)
    vm.initialize()
    vm.start()
    
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame("camera_1", frame_id=1, timestamp=100.0)
    class DummyRuleResults:
        evaluations = [
            RuleEvaluation(
                rule_id="UNAUTH_LAPTOP",
                rule_name="Laptop Visible",
                category="Electronic Device",
                triggered=True,
                confidence=0.92,
                supporting_observations="Laptop detected",
                evaluation_timestamp=100.0,
                evaluation_duration=1.0
            )
        ]
    ctx.rule_results = DummyRuleResults()
    vm.process(ctx)
    
    assert len(vm.all_evidence_records) >= 1
    rec = vm.all_evidence_records[0]
    assert rec["rule_id"] == "UNAUTH_LAPTOP"
    assert rec["camera_id"] == "camera_1"
    assert Path(rec["filepath"]).exists()
    vm.stop()


# ==============================================================================
# TEST 9: ResultSerializer Serializes UNAUTH_LAPTOP Correctly
# ==============================================================================
def test_9_result_serializer_serializes_unauth_laptop():
    """
    ResultSerializer outputs UNAUTH_LAPTOP with title 'Unauthorized Laptop'.
    """
    serializer = ResultSerializer()
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame()
    
    v_event = LifecycleEvent(
        event_type="STARTED",
        violation_id="V-LAPTOP-001",
        violation_type="UNAUTH_LAPTOP",
        violation_category="Electronic Device",
        severity="HIGH",
        risk_score=75.0,
        triggered_rules=["UNAUTH_LAPTOP"],
        timestamp=100.0,
        start_timestamp=100.0,
        camera_id="camera_1"
    )
    setattr(ctx, "lifecycle_events", [v_event])
    
    payload = serializer.to_dict(
        ctx,
        processor_health={},
        frame_counter=1,
        pipeline_ms=2.0,
        evidence_store=[]
    )
    assert "lifecycle_events" in payload
    assert len(payload["lifecycle_events"]) == 1
    
    event_dict = payload["lifecycle_events"][0]
    assert event_dict["type"] == "UNAUTH_LAPTOP"
    assert event_dict["title"] == "Unauthorized Laptop"


# ==============================================================================
# TEST 10: Composite Behavior Titling for Laptop
# ==============================================================================
def test_10_composite_behavior_titling_for_laptop():
    """
    format_composite_incident_title formats standalone and combined laptop violations.
    """
    # 1. Standalone
    title_single = format_composite_incident_title("UNAUTH_LAPTOP", ["UNAUTH_LAPTOP"])
    assert title_single == "Unauthorized Laptop"
    
    # 2. Combined with downward gaze
    title_combined_down = format_composite_incident_title(
        "UNAUTH_LAPTOP", ["UNAUTH_LAPTOP", "ATT_DOWNWARD_GAZE"]
    )
    assert title_combined_down == "Laptop + Off-Screen Attention"
    
    # 3. Combined with looking away
    title_combined_away = format_composite_incident_title(
        "UNAUTH_LAPTOP", ["UNAUTH_LAPTOP", "ATT_LOOKING_AWAY"]
    )
    assert title_combined_away == "Laptop + Off-Screen Attention"


# ==============================================================================
# TEST 11: Multi-Camera Routing: Camera 1 Detects UNAUTH_LAPTOP
# ==============================================================================
def test_11_multicamera_routing_camera_1_unauth_laptop():
    """
    Camera 1 frame evaluates full rules including UNAUTH_LAPTOP.
    """
    engine = RuleEngineProcessor(RuleEngineConfig())
    engine.initialize()
    
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame("camera_1")
    ctx.observation = UnifiedObservation(
        timestamp=100.0,
        environment=EnvironmentObservation(laptop_present=True)
    )
    
    engine.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "UNAUTH_LAPTOP" in triggered


# ==============================================================================
# TEST 12: Multi-Camera Routing: Camera 2 Detects UNAUTH_LAPTOP
# ==============================================================================
def test_12_multicamera_routing_camera_2_unauth_laptop():
    """
    Camera 2 frame successfully evaluates UNAUTH_LAPTOP because it is in
    CAMERA_2_APPROVED_RULES.
    """
    assert "UNAUTH_LAPTOP" in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
    
    engine = RuleEngineProcessor(RuleEngineConfig())
    engine.initialize()
    
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame("camera_2")
    ctx.observation = UnifiedObservation(
        timestamp=100.0,
        environment=EnvironmentObservation(laptop_present=True)
    )
    
    engine.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "UNAUTH_LAPTOP" in triggered
    
    # Verify non-approved Camera 2 rules (e.g. ATT_LOOKING_AWAY) are NOT evaluated on Camera 2
    evaluated_ids = [e.rule_id for e in ctx.rule_results.evaluations]
    assert "ATT_LOOKING_AWAY" not in evaluated_ids
    assert "ID_MISMATCH" not in evaluated_ids


# ==============================================================================
# TEST 13: SQLite Database Persistence for UNAUTH_LAPTOP
# ==============================================================================
def test_13_database_persistence_unauth_laptop(tmp_path):
    """
    MonitoringPersistenceAdapter and session_repository record UNAUTH_LAPTOP
    violations and evidence in the SQLite database and retrieve them accurately.
    """
    session_id = f"sess_laptop_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(
        session_id=session_id,
        student_id="student_laptop",
        exam_id="exam_laptop",
    )
    adapter = MonitoringPersistenceAdapter(active_session_id=session_id)
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame("camera_2", frame_id=1, timestamp=100.0)
    class DummyRuleResults:
        evaluations = [
            RuleEvaluation(
                rule_id="UNAUTH_LAPTOP",
                rule_name="Laptop Visible",
                category="Electronic Device",
                triggered=True,
                confidence=0.92,
                supporting_observations="Laptop detected",
                evaluation_timestamp=100.0,
                evaluation_duration=1.0
            )
        ]
    ctx.rule_results = DummyRuleResults()
    vm.process(ctx)
    setattr(ctx, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx, session_id=session_id)

    report = session_repository.get_session_report(session_id)
    assert report is not None
    assert report["summary"]["session_id"] == session_id
    assert report["summary"]["total_violations"] == 1

    violations = report["violations"]
    assert len(violations) == 1
    assert violations[0]["violation_type"] == "UNAUTH_LAPTOP"

    evidence_list = report.get("evidence", [])
    assert len(evidence_list) >= 1
    assert evidence_list[0]["metadata"]["camera_id"] == "camera_2"
    vm.stop()

