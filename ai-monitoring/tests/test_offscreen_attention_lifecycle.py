"""Focused lifecycle regression coverage for OFF-SCREEN ATTENTION only."""

import pytest

from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager


ATTENTION_FAMILY = (
    "ATT_LOOKING_AWAY",
    "ATT_DOWNWARD_GAZE",
    "ATT_SIDE_GAZE",
    "ATT_HEAD_ROTATION",
)


def _timeline():
    return ViolationTimelineManager(
        ViolationManagerConfig(
            enable_logging=False,
            min_confirming_frames=1,
            auto_close_timeout_seconds=0.5,
            per_violation_timeouts={rule: 0.5 for rule in ATTENTION_FAMILY},
        )
    )


def _trigger(rule_id, category="Attention"):
    return {"rule_id": rule_id, "category": category, "confidence": 0.9}


def _advance(timeline, timestamp, *rules):
    return timeline.process_triggers(
        triggered_rules=[_trigger(rule) for rule in rules],
        risk_score=50.0 if rules else 0.0,
        risk_level="MEDIUM" if rules else "NORMAL",
        evidence_refs=[],
        current_time=timestamp,
    )


def _events_for_frames(timeline, count, start=0.0, step=0.1):
    events = []
    for index in range(count):
        events.extend(_advance(timeline, start + index * step, "ATT_LOOKING_AWAY"))
    return events


def _events_of_type(events, event_type):
    return [event for event in events if event.event_type == event_type]


def test_ten_consecutive_attention_observations_are_one_episode():
    timeline = _timeline()
    events = _events_for_frames(timeline, 10)

    started = _events_of_type(events, "STARTED")
    assert len(timeline.timeline.violations) == 1
    assert len(started) == 1
    assert timeline.timeline.violations[0].violation_id == started[0].violation_id


def test_thirty_consecutive_attention_observations_accumulate_duration():
    timeline = _timeline()
    events = _events_for_frames(timeline, 30)

    violation = timeline.timeline.violations[0]
    assert len(_events_of_type(events, "STARTED")) == 1
    assert violation.last_updated_timestamp == pytest.approx(2.9)
    assert violation.last_updated_timestamp - violation.start_timestamp == pytest.approx(2.9)


def test_attention_resolves_once_after_normal_gaze():
    timeline = _timeline()
    events = _events_for_frames(timeline, 3)
    events.extend(_advance(timeline, 0.8))
    events.extend(_advance(timeline, 1.2))

    assert len(_events_of_type(events, "STARTED")) == 1
    assert len(_events_of_type(events, "RESOLVED")) == 1
    assert timeline.timeline.violations[0].status == "RESOLVED"


def test_attention_after_resolution_creates_a_distinct_episode():
    timeline = _timeline()
    events = _events_for_frames(timeline, 2)
    events.extend(_advance(timeline, 0.7))
    events.extend(_advance(timeline, 0.8, "ATT_LOOKING_AWAY"))

    started = _events_of_type(events, "STARTED")
    resolved = _events_of_type(events, "RESOLVED")
    assert len(started) == 2
    assert len(resolved) == 1
    assert started[0].violation_id != started[1].violation_id


def test_simultaneous_attention_subsignals_collapse_to_one_episode():
    timeline = _timeline()
    events = []
    for index in range(10):
        events.extend(_advance(timeline, index * 0.1, *ATTENTION_FAMILY))

    assert len(timeline.timeline.violations) == 1
    assert len(_events_of_type(events, "STARTED")) == 1


def test_subtype_switch_at_expiry_does_not_fragment_attention_episode():
    """A current attention signal keeps its family episode alive for merging."""
    timeline = _timeline()
    events = _advance(timeline, 0.0, "ATT_LOOKING_AWAY")
    events.extend(_advance(timeline, 0.6, "ATT_DOWNWARD_GAZE"))

    assert len(timeline.timeline.violations) == 1
    assert len(_events_of_type(events, "STARTED")) == 1
    assert _events_of_type(events, "RESOLVED") == []


def test_phone_and_attention_remain_independent_episodes():
    timeline = _timeline()
    events = []
    for index in range(10):
        events.extend(_advance(timeline, index * 0.1, "ATT_LOOKING_AWAY", "UNAUTH_PHONE"))

    started = _events_of_type(events, "STARTED")
    assert len(timeline.timeline.violations) == 2
    assert {event.violation_type for event in started} == {"ATT_LOOKING_AWAY", "UNAUTH_PHONE"}


def test_normal_gaze_creates_no_attention_episode():
    timeline = _timeline()
    events = []
    for index in range(20):
        events.extend(_advance(timeline, index * 0.1))

    assert timeline.timeline.violations == []
    assert _events_of_type(events, "STARTED") == []
