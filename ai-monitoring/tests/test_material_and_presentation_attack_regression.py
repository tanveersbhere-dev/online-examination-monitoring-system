"""Focused regressions for canonical material mapping and anti-spoofing confirmation."""

from types import SimpleNamespace

from ai_engine.core.enums import DetectedObjectType
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.yolo_detector import YOLODetector
from ai_engine.identity_protection.aggregator.identity_protection_aggregator import (
    IdentityProtectionAggregator,
)
from ai_engine.identity_protection.analyzers.temporal_consistency_analyzer import (
    TemporalConsistencyAnalyzer,
)
from ai_engine.identity_protection.interfaces.liveness_engine import LivenessResult
from ai_engine.intelligence.rule_engine.rules import ConfirmedPresentationAttackRule
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager


def _liveness_result(score):
    return LivenessResult(
        is_live=score >= 0.5,
        liveness_score=score,
        presentation_attack_type="PRESENTATION_ATTACK_SUSPECTED" if score < 0.5 else "NONE",
        confidence=0.95,
        reason="test liveness result",
    )


def _attack_rule_result(observation):
    return ConfirmedPresentationAttackRule().evaluate(
        SimpleNamespace(identity_protection=observation),
        None,
    )


def test_only_the_actual_coco_book_label_maps_to_material():
    detector = YOLODetector(ObjectDetectionConfig(enable_logging=False))

    assert detector._map_class_id(73) is DetectedObjectType.BOOK
    # COCO 75 is vase and 76 is scissors; they must not become material.
    assert detector._map_class_id(75) is DetectedObjectType.UNKNOWN
    assert detector._map_class_id(76) is DetectedObjectType.UNKNOWN


def test_normal_face_never_confirms_a_presentation_attack():
    temporal = TemporalConsistencyAnalyzer()
    observation = IdentityProtectionAggregator().aggregate(
        liveness_result=_liveness_result(0.95),
        temporal_result=temporal.process(0.95),
    )

    triggered, _, _ = _attack_rule_result(observation)
    assert observation.liveness_state == "LIVE"
    assert not triggered


def test_one_low_liveness_frame_after_live_history_is_only_suspected():
    temporal = TemporalConsistencyAnalyzer()
    temporal.process(0.95)
    observation = IdentityProtectionAggregator().aggregate(
        liveness_result=_liveness_result(0.10),
        temporal_result=temporal.process(0.10),
    )

    triggered, _, _ = _attack_rule_result(observation)
    assert observation.liveness_state == "SPOOF_SUSPECTED"
    assert not triggered


def test_sustained_low_liveness_still_confirms_presentation_attack():
    temporal = TemporalConsistencyAnalyzer()
    aggregator = IdentityProtectionAggregator()
    observation = None
    for _ in range(3):
        observation = aggregator.aggregate(
            liveness_result=_liveness_result(0.10),
            temporal_result=temporal.process(0.10),
        )

    assert observation is not None
    triggered, _, _ = _attack_rule_result(observation)
    assert observation.liveness_state == "SPOOF_CONFIRMED"
    assert triggered


def test_live_liveness_recovers_from_confirmed_attack_state():
    temporal = TemporalConsistencyAnalyzer()
    aggregator = IdentityProtectionAggregator()
    for _ in range(3):
        aggregator.aggregate(_liveness_result(0.10), temporal_result=temporal.process(0.10))
    recovered = aggregator.aggregate(_liveness_result(0.95), temporal_result=temporal.process(0.95))

    triggered, _, _ = _attack_rule_result(recovered)
    assert recovered.liveness_state == "LIVE"
    assert not triggered


def test_confirmed_attack_lifecycle_uses_one_started_and_one_resolved_event():
    timeline = ViolationTimelineManager(
        ViolationManagerConfig(
            enable_logging=False,
            min_confirming_frames=1,
            auto_close_timeout_seconds=0.5,
            per_violation_timeouts={"CONFIRMED_PRESENTATION_ATTACK": 0.5},
        )
    )
    events = []
    trigger = [{"rule_id": "CONFIRMED_PRESENTATION_ATTACK", "category": "Identity Protection", "confidence": 0.99}]
    for frame in range(10):
        events.extend(timeline.process_triggers(trigger, 90.0, "CRITICAL", [], frame * 0.1))
    events.extend(timeline.process_triggers([], 0.0, "NORMAL", [], 1.5))

    assert len([event for event in events if event.event_type == "STARTED"]) == 1
    assert len([event for event in events if event.event_type == "RESOLVED"]) == 1
    assert timeline.timeline.violations[0].status == "RESOLVED"
