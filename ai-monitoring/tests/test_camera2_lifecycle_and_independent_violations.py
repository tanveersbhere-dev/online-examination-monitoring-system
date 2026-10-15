"""
Test Suite: Camera 2 Violation Lifecycle & Independent Evidence Separation
===========================================================================
Verifies:
1. Camera 2 phone stays active across intermittent AI sample misses.
2. Phone genuine absence resolves after configured timeout.
3. Phone visible 30+ seconds stays active (no premature auto-close, no cross-camera track leakage).
4. Phone + off-screen attention at same frame/timestamp produce 2 independent violation types (no unwanted merging into composite).
5. Separate lifecycles (started, updated, resolved independently).
6. Evidence quota: up to 3 snapshots each for Phone and Attention independently (total 6 snapshots).
7. Shared frame underlying evidence associations remain independent.
8. Database persistence creates separate rows in SQLite violations and evidence tables.
9. Laptop + another violation remain independent.
"""
import os
import time
import uuid
import pytest
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, List

from ai_engine.core.exam_context import ExamContext, BoundingBox, TrackedObject, FaceInfo
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.violation_manager.models import (
    ViolationManagerConfig,
    LifecycleEvent,
)
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from backend.adapters.monitoring_persistence_adapter import MonitoringPersistenceAdapter
from backend.database.session_repository import session_repository


def _make_dummy_frame(camera_id: str = "camera_2", frame_id: int = 1, timestamp: Optional[float] = None) -> Frame:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, f"{camera_id.upper()} FRAME", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    ts = timestamp if timestamp is not None else time.time()
    return Frame.from_bgr_image(img, camera_id=camera_id, frame_id=frame_id, timestamp=ts)


def _make_context_with_rules(
    camera_id: str,
    rules: List[tuple],  # List of (rule_id, category, conf)
    frame_id: int = 1,
    timestamp: float = 100.0,
    has_phone_obj: bool = False,
    has_laptop_obj: bool = False,
) -> ExamContext:
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame(camera_id=camera_id, frame_id=frame_id, timestamp=timestamp)

    class DummyRuleResults:
        evaluations = [
            RuleEvaluation(
                rule_id=r_id,
                rule_name=r_id,
                category=r_cat,
                triggered=True,
                confidence=r_conf,
                supporting_observations=f"{r_id} on {camera_id}",
                evaluation_timestamp=timestamp,
                evaluation_duration=0.01,
            )
            for (r_id, r_cat, r_conf) in rules
        ]
    ctx.rule_results = DummyRuleResults()

    tracked_objs = []
    if has_phone_obj:
        tracked_objs.append(
            TrackedObject(
                tracking_id=1,
                object_type=DetectedObjectType.CELL_PHONE,
                bbox=BoundingBox(50, 50, 100, 150),
                confidence=0.92,
                current_state="TRACKED",
            )
        )
    if has_laptop_obj:
        tracked_objs.append(
            TrackedObject(
                tracking_id=2,
                object_type=DetectedObjectType.LAPTOP,
                bbox=BoundingBox(100, 200, 300, 180),
                confidence=0.90,
                current_state="TRACKED",
            )
        )
    ctx.object_info.validated_objects = tracked_objs
    return ctx


# ==============================================================================
# TEST 1: Camera 2 Phone Stays Active Across Intermittent Missed Samples
# ==============================================================================
def test_1_cam2_phone_stays_active_across_intermittent_missed_samples(tmp_path):
    """
    Verifies that when Camera 2 detects a phone, brief intermittent missed AI samples
    (e.g., dropped inferences or 1-2 missed frames) do NOT cause premature resolution.
    The episode must remain OPEN / ACTIVE.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=3.0,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Frame 1 (t=100.0): Phone detected on Camera 2 -> Starts violation
    ctx1 = _make_context_with_rules(
        "camera_2",
        [("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95)],
        frame_id=1,
        timestamp=100.0,
        has_phone_obj=True,
    )
    vm.process(ctx1)

    phone_eps = [v for v in vm._timeline_manager.timeline.violations if v.violation_type == "UNAUTH_PHONE"]
    assert len(phone_eps) == 1
    assert phone_eps[0].status in ("OPEN", "ACTIVE")

    # Frame 2 (t=100.5): Camera 1 frame (no phone)
    ctx2 = _make_context_with_rules("camera_1", [], frame_id=2, timestamp=100.5)
    vm.process(ctx2)
    assert phone_eps[0].status in ("OPEN", "ACTIVE"), "Camera 1 frame must not close Camera 2 phone violation"

    # Frame 3 (t=101.0): Camera 2 missed detection (intermittent sample miss)
    ctx3 = _make_context_with_rules("camera_2", [], frame_id=3, timestamp=101.0)
    vm.process(ctx3)
    assert phone_eps[0].status in ("OPEN", "ACTIVE"), "Single missed sample must not close Camera 2 phone violation"

    # Frame 4 (t=101.5): Phone detected again on Camera 2
    ctx4 = _make_context_with_rules(
        "camera_2",
        [("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.94)],
        frame_id=4,
        timestamp=101.5,
        has_phone_obj=True,
    )
    vm.process(ctx4)
    assert phone_eps[0].status in ("OPEN", "ACTIVE")

    # Frame 5 (t=102.2): Another transient miss
    ctx5 = _make_context_with_rules("camera_2", [], frame_id=5, timestamp=102.2)
    vm.process(ctx5)
    assert phone_eps[0].status in ("OPEN", "ACTIVE"), "Phone must remain active across intermittent misses"

    vm.stop()


# ==============================================================================
# TEST 2: Phone Genuine Absence Resolves After Configured Timeout
# ==============================================================================
def test_2_phone_genuine_absence_resolves_after_configured_timeout(tmp_path):
    """
    Verifies that when the phone is genuinely removed and stays absent longer than
    the auto-close absence timeout, the violation properly transitions to RESOLVED.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=1.0,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Step 1: Phone starts at t=100.0
    ctx1 = _make_context_with_rules(
        "camera_2",
        [("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95)],
        frame_id=1,
        timestamp=100.0,
        has_phone_obj=True,
    )
    vm.process(ctx1)

    phone_eps = [v for v in vm._timeline_manager.timeline.violations if v.violation_type == "UNAUTH_PHONE"]
    assert len(phone_eps) == 1
    assert phone_eps[0].status in ("OPEN", "ACTIVE")

    # Step 2: Continuous absence on Camera 2 past auto-close timeout
    # Default auto-close timeout in timeline manager is 6.0s for PROHIBITED_ITEMS
    t_absence = 100.0
    for i in range(1, 15):
        t_absence += 1.0  # up to t=114.0 (14 seconds of consecutive absence)
        ctx_abs = _make_context_with_rules("camera_2", [], frame_id=1 + i, timestamp=t_absence)
        vm.process(ctx_abs)

    assert phone_eps[0].status == "RESOLVED", f"Expected RESOLVED after 14s absence, got {phone_eps[0].status}"
    assert phone_eps[0].end_timestamp is not None
    vm.stop()


# ==============================================================================
# TEST 3: Phone Visible 30+ Seconds Stays Active (No Premature Auto-Close)
# ==============================================================================
def test_3_phone_visible_30_plus_seconds_stays_active(tmp_path):
    """
    Verifies that a phone visible on Camera 2 for 30+ seconds stays continuously
    active without prematurely closing, even when heavily interleaved with Camera 1 frames.
    Also verifies tracker camera partitioning prevents track loss.
    """
    # 1. Verify Tracker camera isolation
    from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
    from ai_engine.core.exam_context import FilteredObject
    tracker = ByteTrackTracker(ObjectTrackingConfig(tracking_confidence=0.22, max_lost_frames=15))
    tracker.initialize()
    tracker.start()

    # Camera 2 frame with phone
    ctx_c2 = ExamContext()
    ctx_c2.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_2", frame_id=1, timestamp=100.0)
    obj_info_c2 = ctx_c2.object_info
    obj_info_c2.filtered_detections = [
        FilteredObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.8, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=100.0)
    ]
    ctx_c2.object_info = obj_info_c2
    tracker.process(ctx_c2)
    assert len(ctx_c2.object_info.tracked_objects) == 1

    # Camera 1 receives 50 empty frames
    for i in range(50):
        ctx_c1 = ExamContext()
        ctx_c1.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_1", frame_id=2 + i, timestamp=100.0 + i * 0.1)
        tracker.process(ctx_c1)

    # Now check Camera 2: track must still be preserved and matched!
    ctx_c2_check = ExamContext()
    ctx_c2_check.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_2", frame_id=100, timestamp=105.0)
    obj_info_check = ctx_c2_check.object_info
    obj_info_check.filtered_detections = [
        FilteredObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.8, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=105.0)
    ]
    ctx_c2_check.object_info = obj_info_check
    tracker.process(ctx_c2_check)
    assert len(ctx_c2_check.object_info.tracked_objects) == 1
    assert ctx_c2_check.object_info.tracked_objects[0].tracking_id == 1, "Camera 2 track #1 must be preserved despite Cam 1 activity!"

    # 2. Verify Violation Timeline continuity
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=1.0,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    start_ts = 100.0
    curr_ts = start_ts
    # Simulate 35 seconds of physical time with interleaved Camera 1 and Camera 2 frames
    for second in range(35):
        curr_ts = start_ts + float(second)
        # Camera 1 frame (no phone)
        ctx_c1 = _make_context_with_rules("camera_1", [], frame_id=second * 2, timestamp=curr_ts)
        vm.process(ctx_c1)

        # Camera 2 frame (phone present)
        ctx_c2 = _make_context_with_rules(
            "camera_2",
            [("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95)],
            frame_id=second * 2 + 1,
            timestamp=curr_ts + 0.3,
            has_phone_obj=True,
        )
        vm.process(ctx_c2)

    phone_eps = [v for v in vm._timeline_manager.timeline.violations if v.violation_type == "UNAUTH_PHONE"]
    assert len(phone_eps) == 1
    assert phone_eps[0].status in ("OPEN", "ACTIVE"), f"Expected ACTIVE after 35s, got {phone_eps[0].status}"
    assert (phone_eps[0].last_updated_timestamp - phone_eps[0].start_timestamp) >= 34.0, "Violation episode duration must be >= 34 seconds"

    vm.stop()


# ==============================================================================
# TEST 4: Phone and Off-Screen Attention Same Timestamp Produce 2 Violations
# ==============================================================================
def test_4_phone_and_offscreen_attention_same_timestamp_produce_separate_violations(tmp_path):
    """
    CRITICAL DEFECT FIX:
    When phone detection (UNAUTH_PHONE) and off-screen attention (ATT_LOOKING_AWAY)
    occur simultaneously at the same timestamp/frame, they MUST NOT merge into
    COMPOSITE_PHONE_LOOKING_AWAY_TALKING or suppress each other.
    Both must exist as separate, distinct violations.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Frame contains BOTH rules simultaneously
    ctx = _make_context_with_rules(
        "camera_1",
        [
            ("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95),
            ("ATT_LOOKING_AWAY", "ATTENTION", 0.90),
        ],
        frame_id=1,
        timestamp=100.0,
        has_phone_obj=True,
    )
    vm.process(ctx)

    active_eps = [v for v in vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
    assert len(active_eps) == 2, f"Expected exactly 2 active violations, got {len(active_eps)}"

    active_types = {v.violation_type for v in active_eps}
    assert "UNAUTH_PHONE" in active_types
    assert "ATT_LOOKING_AWAY" in active_types
    assert "COMPOSITE_PHONE_LOOKING_AWAY_TALKING" not in active_types
    assert "PHONE_ATTENTION_COMPOSITE" not in active_types

    vm.stop()


# ==============================================================================
# TEST 5: Separate Lifecycles (Started, Updated, Resolved Independently)
# ==============================================================================
def test_5_separate_lifecycles_started_updated_resolved_independently(tmp_path):
    """
    Verifies that Phone and Attention maintain completely independent lifecycles:
    - ATT_LOOKING_AWAY starts at t=100.0
    - UNAUTH_PHONE starts at t=102.0
    - Candidate looks back to screen at t=105.0 -> ATT_LOOKING_AWAY resolves at t=112.0
    - Phone remains visible through t=120.0 -> UNAUTH_PHONE stays ACTIVE
    - Phone removed at t=120.0 -> UNAUTH_PHONE resolves at t=130.0
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # 1. t=100.0: ATT_LOOKING_AWAY starts
    ctx1 = _make_context_with_rules("camera_1", [("ATT_LOOKING_AWAY", "ATTENTION", 0.90)], frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    # 2. t=102.0: UNAUTH_PHONE also starts
    ctx2 = _make_context_with_rules(
        "camera_2",
        [
            ("ATT_LOOKING_AWAY", "ATTENTION", 0.90),
            ("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95),
        ],
        frame_id=2,
        timestamp=102.0,
        has_phone_obj=True,
    )
    vm.process(ctx2)

    active_types = {v.violation_type for v in vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")}
    assert active_types == {"ATT_LOOKING_AWAY", "UNAUTH_PHONE"}

    # 3. t=105.0 to 118.0: Candidate looks back to screen (Camera 1 has no rules), but Phone remains visible on Camera 2
    for ts in range(105, 118):
        # Camera 1 frame without ATT_LOOKING_AWAY
        ctx_c1 = _make_context_with_rules("camera_1", [], frame_id=ts * 2, timestamp=float(ts))
        vm.process(ctx_c1)
        # Camera 2 frame with phone
        ctx_c2 = _make_context_with_rules(
            "camera_2",
            [("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.95)],
            frame_id=ts * 2 + 1,
            timestamp=float(ts) + 0.1,
            has_phone_obj=True,
        )
        vm.process(ctx_c2)

    # Verify ATT_LOOKING_AWAY resolved while UNAUTH_PHONE is still ACTIVE
    att_ep = [v for v in vm._timeline_manager.timeline.violations if v.violation_type == "ATT_LOOKING_AWAY"][0]
    phone_ep = [v for v in vm._timeline_manager.timeline.violations if v.violation_type == "UNAUTH_PHONE"][0]

    assert att_ep.status == "RESOLVED", "ATT_LOOKING_AWAY must be resolved after candidate looks back"
    assert phone_ep.status in ("OPEN", "ACTIVE"), "UNAUTH_PHONE must remain ACTIVE while phone is still visible"

    # 4. t=120.0 to 135.0: Phone removed
    for ts in range(120, 136):
        ctx_abs = _make_context_with_rules("camera_2", [], frame_id=ts * 2, timestamp=float(ts))
        vm.process(ctx_abs)

    assert phone_ep.status == "RESOLVED", "UNAUTH_PHONE must resolve after removal"
    assert att_ep.end_timestamp < phone_ep.end_timestamp, "Attention resolved earlier than phone"

    vm.stop()


# ==============================================================================
# TEST 6: Evidence Quota: Up to 3 Snapshots Each Independently (Total 6)
# ==============================================================================
def test_6_evidence_quota_up_to_3_snapshots_each_independently(tmp_path):
    """
    Verifies that MAX_SNAPSHOTS_PER_VIOLATION = 3 applies INDEPENDENTLY to each
    violation episode. When UNAUTH_PHONE and ATT_LOOKING_AWAY run simultaneously,
    each collects up to 3 snapshots for a total of 6 snapshots across the two episodes.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    # Configure periodic resnapshot interval to 1.0s to allow multiple snapshots
    setattr(cfg, "periodic_resnapshot_interval_seconds", 1.0)
    setattr(cfg, "max_snapshots_per_violation", 3)

    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Feed frames at t=100.0, 102.0, 104.0, 106.0 with both rules active
    for step in range(5):
        ts = 100.0 + (step * 2.0)
        ctx = _make_context_with_rules(
            "camera_1",
            [
                ("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.90 + (step * 0.02)),
                ("ATT_LOOKING_AWAY", "ATTENTION", 0.85 + (step * 0.02)),
            ],
            frame_id=1 + step,
            timestamp=ts,
            has_phone_obj=True,
        )
        vm.process(ctx)

    records = vm.all_evidence_records
    assert len(records) == 2, f"Expected 2 evidence records, got {len(records)}"

    rec_by_type = {r["rule_id"]: r for r in records}
    assert "UNAUTH_PHONE" in rec_by_type
    assert "ATT_LOOKING_AWAY" in rec_by_type

    phone_snaps = rec_by_type["UNAUTH_PHONE"].get("snapshots", [])
    att_snaps = rec_by_type["ATT_LOOKING_AWAY"].get("snapshots", [])

    assert len(phone_snaps) == 3, f"Expected exactly 3 snapshots for UNAUTH_PHONE, got {len(phone_snaps)}"
    assert len(att_snaps) == 3, f"Expected exactly 3 snapshots for ATT_LOOKING_AWAY, got {len(att_snaps)}"
    assert len(phone_snaps) + len(att_snaps) == 6, "Total snapshots across both violations must be 6 (3 each)"

    vm.stop()


# ==============================================================================
# TEST 7: Shared Frame Underlying Evidence Associations Remain Independent
# ==============================================================================
def test_7_shared_frame_underlying_evidence_associations_remain_independent(tmp_path):
    """
    Verifies that on a shared frame containing multiple simultaneous violations:
    - The UNAUTH_PHONE evidence record has incident_title 'Unauthorized Cell Phone'
      and contains phone-specific contributing violations.
    - The ATT_LOOKING_AWAY evidence record has incident_title 'Off-Screen Attention'
      and contains attention-specific contributing violations.
    - Neither record cross-contaminates or overrides the other.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rules(
        "camera_1",
        [
            ("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.96),
            ("ATT_LOOKING_AWAY", "ATTENTION", 0.88),
        ],
        frame_id=1,
        timestamp=100.0,
        has_phone_obj=True,
    )
    vm.process(ctx)

    rec_phone = next(r for r in vm.all_evidence_records if r["rule_id"] == "UNAUTH_PHONE")
    rec_att = next(r for r in vm.all_evidence_records if r["rule_id"] == "ATT_LOOKING_AWAY")

    # Titles must be independent and specific
    assert "Phone" in rec_phone["incident_title"]
    assert "Attention" in rec_att["incident_title"]

    # Contributing violations must be scoped to their respective rules
    phone_rules = {cv["rule_id"] for cv in rec_phone["contributing_violations"]}
    att_rules = {cv["rule_id"] for cv in rec_att["contributing_violations"]}

    assert "UNAUTH_PHONE" in phone_rules
    assert "ATT_LOOKING_AWAY" not in phone_rules

    assert "ATT_LOOKING_AWAY" in att_rules
    assert "UNAUTH_PHONE" not in att_rules

    vm.stop()


# ==============================================================================
# TEST 8: Database Persistence Creates Separate Rows in SQLite Violations & Evidence
# ==============================================================================
def test_8_database_persistence_creates_separate_rows_in_sqlite(tmp_path):
    """
    Verifies end-to-end database persistence:
    Simultaneous UNAUTH_PHONE and ATT_LOOKING_AWAY result in 2 separate rows
    in the SQLite `violations` table, and separate rows in the `evidence` table.
    """
    session_id = f"sess_indep_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(
        session_id=session_id,
        student_id="student_simul",
        exam_id="exam_simul",
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

    ctx = _make_context_with_rules(
        "camera_2",
        [
            ("UNAUTH_PHONE", "PROHIBITED_ITEMS", 0.94),
            ("ATT_LOOKING_AWAY", "ATTENTION", 0.91),
        ],
        frame_id=1,
        timestamp=100.0,
        has_phone_obj=True,
    )
    vm.process(ctx)

    setattr(ctx, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx, session_id=session_id)

    report = session_repository.get_session_report(session_id)
    assert report is not None
    assert report["summary"]["total_violations"] == 2

    stored_types = {v["violation_type"] for v in report["violations"]}
    assert "UNAUTH_PHONE" in stored_types
    assert "ATT_LOOKING_AWAY" in stored_types

    assert len(report["evidence"]) >= 2
    ev_rules = {ev.get("metadata", {}).get("rule_id") for ev in report["evidence"] if isinstance(ev.get("metadata"), dict)}
    assert "UNAUTH_PHONE" in ev_rules
    assert "ATT_LOOKING_AWAY" in ev_rules

    vm.stop()


# ==============================================================================
# TEST 9: Laptop and Another Violation Remain Independent
# ==============================================================================
def test_9_laptop_and_another_violation_remain_independent(tmp_path):
    """
    Verifies that UNAUTH_LAPTOP and another violation (e.g. ATT_LOOKING_AWAY)
    triggered at the same time maintain independent lifecycles, separate
    incident titles, and independent evidence records.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rules(
        "camera_1",
        [
            ("UNAUTH_LAPTOP", "PROHIBITED_ITEMS", 0.88),
            ("ATT_LOOKING_AWAY", "ATTENTION", 0.92),
        ],
        frame_id=1,
        timestamp=100.0,
        has_laptop_obj=True,
    )
    vm.process(ctx)

    active_eps = [v for v in vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
    assert len(active_eps) == 2

    types = {v.violation_type for v in active_eps}
    assert "UNAUTH_LAPTOP" in types
    assert "ATT_LOOKING_AWAY" in types

    assert len(vm.all_evidence_records) == 2
    rec_laptop = next(r for r in vm.all_evidence_records if r["rule_id"] == "UNAUTH_LAPTOP")
    rec_att = next(r for r in vm.all_evidence_records if r["rule_id"] == "ATT_LOOKING_AWAY")

    assert "Laptop" in rec_laptop["incident_title"]
    assert "Attention" in rec_att["incident_title"]

    vm.stop()
