"""Focused regression coverage for canonical violation episode lifecycles.

These tests exercise the timeline directly: detectors may evaluate per frame,
but the timeline must emit lifecycle transitions only when an episode changes.
"""
from types import SimpleNamespace

import pytest
import numpy as np

from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from backend.pipeline.result_serializer import ResultSerializer


def _timeline():
    return ViolationTimelineManager(
        ViolationManagerConfig(
            enable_logging=False,
            min_confirming_frames=1,
            auto_close_timeout_seconds=0.5,
            per_violation_timeouts={
                "UNAUTH_PHONE": 0.5,
                "ATT_LOOKING_AWAY": 0.5,
                "ENV_BOOK_DETECTED": 0.5,
            },
        )
    )


def _trigger(rule_id, category="Attention", confidence=0.9):
    return {"rule_id": rule_id, "category": category, "confidence": confidence}


def _advance(timeline, timestamp, *triggers):
    return timeline.process_triggers(
        triggered_rules=list(triggers),
        risk_score=50.0 if triggers else 0.0,
        risk_level="MEDIUM" if triggers else "NORMAL",
        evidence_refs=[],
        current_time=timestamp,
    )


def _events_for_frames(timeline, rule, count, start=0.0, step=0.1):
    events = []
    for index in range(count):
        events.extend(_advance(timeline, start + index * step, rule))
    return events


def test_twenty_phone_frames_are_one_episode_and_one_started_event():
    timeline = _timeline()

    events = _events_for_frames(timeline, _trigger("UNAUTH_PHONE", "Unauthorized Device"), 20)

    started = [event for event in events if event.event_type == "STARTED"]
    assert len(timeline.timeline.violations) == 1
    assert len(started) == 1
    assert timeline.timeline.violations[0].violation_id == started[0].violation_id
    assert timeline.timeline.violations[0].last_updated_timestamp == pytest.approx(1.9)


def test_phone_disappearance_resolves_the_same_episode_once():
    timeline = _timeline()
    events = _events_for_frames(timeline, _trigger("UNAUTH_PHONE", "Unauthorized Device"), 3)
    started = [event for event in events if event.event_type == "STARTED"]

    events.extend(_advance(timeline, 0.8))
    events.extend(_advance(timeline, 1.4))

    resolved = [event for event in events if event.event_type == "RESOLVED"]
    assert len(started) == 1
    assert len(resolved) == 1
    assert resolved[0].violation_id == started[0].violation_id
    assert timeline.timeline.violations[0].status == "RESOLVED"
    assert timeline.timeline.violations[0].end_timestamp == 0.2


def test_phone_reappearance_after_resolution_is_a_new_uuid():
    timeline = _timeline()
    events = _events_for_frames(timeline, _trigger("UNAUTH_PHONE", "Unauthorized Device"), 2)
    events.extend(_advance(timeline, 0.7))
    events.extend(_advance(timeline, 0.8, _trigger("UNAUTH_PHONE", "Unauthorized Device")))

    started = [event for event in events if event.event_type == "STARTED"]
    resolved = [event for event in events if event.event_type == "RESOLVED"]
    assert len(started) == 2
    assert len(resolved) == 1
    assert started[0].violation_id != started[1].violation_id


def test_attention_family_is_one_episode_with_one_started_event():
    timeline = _timeline()
    events = []
    for index in range(10):
        events.extend(
            _advance(
                timeline,
                index * 0.1,
                _trigger("ATT_LOOKING_AWAY"),
                _trigger("ATT_DOWNWARD_GAZE"),
                _trigger("ATT_HEAD_ROTATION"),
            )
        )

    started = [event for event in events if event.event_type == "STARTED"]
    assert len(timeline.timeline.violations) == 1
    assert len(started) == 1
    assert timeline.timeline.violations[0].violation_type == "ATT_LOOKING_AWAY"


def test_attention_and_phone_are_independent_single_episodes():
    timeline = _timeline()
    events = []
    for index in range(10):
        events.extend(
            _advance(
                timeline,
                index * 0.1,
                _trigger("ATT_LOOKING_AWAY"),
                _trigger("UNAUTH_PHONE", "Unauthorized Device"),
            )
        )

    started = [event for event in events if event.event_type == "STARTED"]
    assert len(timeline.timeline.violations) == 2
    assert {event.violation_type for event in started} == {"ATT_LOOKING_AWAY", "UNAUTH_PHONE"}
    assert len({event.violation_id for event in started}) == 2


def test_material_family_merges_without_a_parallel_material_episode():
    timeline = _timeline()
    events = _events_for_frames(
        timeline,
        _trigger("ENV_BOOK_DETECTED", "Unauthorized Material"),
        1,
    )
    for index in range(1, 10):
        events.extend(
            _advance(
                timeline,
                index * 0.1,
                _trigger("ENV_BOOK_DETECTED", "Unauthorized Material"),
                _trigger("UNAUTH_BOOK", "Unauthorized Material"),
                _trigger("UNAUTH_NOTEBOOK", "Unauthorized Material"),
            )
        )

    assert len(timeline.timeline.violations) == 1
    assert len([event for event in events if event.event_type == "STARTED"]) == 1
    assert timeline.timeline.violations[0].violation_type == "ENV_BOOK_DETECTED"


def test_normal_frames_never_create_an_episode():
    timeline = _timeline()
    events = []
    for index in range(20):
        events.extend(_advance(timeline, index * 0.1))

    assert timeline.timeline.violations == []
    assert [event for event in events if event.event_type == "STARTED"] == []


def test_brief_dropout_merges_back_into_the_active_phone_episode():
    timeline = _timeline()
    events = _events_for_frames(timeline, _trigger("UNAUTH_PHONE", "Unauthorized Device"), 2)
    events.extend(_advance(timeline, 0.2))
    events.extend(_advance(timeline, 0.3, _trigger("UNAUTH_PHONE", "Unauthorized Device")))

    assert len(timeline.timeline.violations) == 1
    assert len([event for event in events if event.event_type == "STARTED"]) == 1
    assert len([event for event in events if event.event_type == "RESOLVED"]) == 0


def test_serializer_preserves_one_lifecycle_event_per_backend_transition():
    timeline = _timeline()
    started = _advance(timeline, 0.0, _trigger("UNAUTH_PHONE", "Unauthorized Device"))
    assert len(started) == 1

    serializer = ResultSerializer()
    context = SimpleNamespace(lifecycle_events=started)
    payload = serializer._lifecycle_events(context)

    assert len(payload) == 1
    assert payload[0]["transition"] == "STARTED"
    assert payload[0]["violation_id"] == started[0].violation_id


def test_duplicate_callback_is_idempotent_and_preserves_one_episode():
    timeline = _timeline()
    trigger = _trigger("UNAUTH_PHONE", "Unauthorized Device", 0.82)

    first = _advance(timeline, 10.0, trigger)
    duplicate = _advance(timeline, 10.0, trigger)
    later = _advance(timeline, 10.1, _trigger("UNAUTH_PHONE", "Unauthorized Device", 0.96))

    violation = timeline.timeline.violations[0]
    assert [event.event_type for event in first] == ["STARTED"]
    assert duplicate == []
    assert later == []
    assert len(timeline.timeline.violations) == 1
    assert violation.detection_count == 2
    assert violation.current_confidence == pytest.approx(0.96)
    assert violation.peak_confidence == pytest.approx(0.96)


def test_snapshot_retention_keeps_primary_and_two_strongest_candidates(tmp_path):
    from ai_engine.camera.frame import Frame
    from ai_engine.core.exam_context import ExamContext
    from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor

    manager = ViolationManagerProcessor(
        ViolationManagerConfig(
            evidence_dir=tmp_path,
            enable_logging=False,
            min_confirming_frames=1,
            periodic_resnapshot_interval_seconds=0.1,
            max_snapshots_per_violation=3,
        )
    )
    manager.initialize()
    frame = np.zeros((32, 32, 3), dtype=np.uint8)

    for index, confidence in enumerate((0.82, 0.87, 0.91, 0.88, 0.96)):
        timestamp = 20.0 + (index * 0.11)
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(frame, frame_id=index + 1, timestamp=timestamp)
        rule = type("PhoneRule", (), {
            "rule_id": "UNAUTH_PHONE", "rule_name": "Mobile Phone Visible",
            "category": "Unauthorized Device", "triggered": True, "confidence": confidence,
        })()
        context.rule_results = type("Rules", (), {"evaluations": [rule]})()
        context.risk_assessment = type("Risk", (), {"overall_score": 50.0, "risk_level": "MEDIUM"})()
        manager.process(context)

    record = manager.all_evidence_records[0]
    confidences = [snapshot["confidence"] for snapshot in record["snapshots"]]
    assert len(record["snapshots"]) == 3
    assert confidences[0] == pytest.approx(0.82)  # primary stays stable
    assert 0.91 in confidences
    assert 0.96 in confidences
