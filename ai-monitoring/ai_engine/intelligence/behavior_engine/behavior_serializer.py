"""
Behavior Serializer for Behavioral Intelligence Engine output payload.
"""
from typing import Dict, Any, List
from ai_engine.intelligence.behavior_engine.behavior_event import (
    CandidateBehaviorProfile, CompositeBehaviorInstance, BehaviorTimelineEvent, BehaviorSessionSummary
)

class BehaviorSerializer:
    """
    Serializes behavior profile, composite instances, timeline events, and session summaries.
    """
    @staticmethod
    def serialize_profile(profile: CandidateBehaviorProfile) -> Dict[str, Any]:
        return {
            "state": profile.state,
            "behavior_score": profile.behavior_score,
            "trend": profile.trend,
            "last_escalation": profile.last_escalation,
            "last_recovery": profile.last_recovery,
            "active_composite_behaviors": [
                BehaviorSerializer.serialize_composite_instance(b) for b in profile.active_composite_behaviors
            ]
        }

    @staticmethod
    def serialize_composite_instance(instance: CompositeBehaviorInstance) -> Dict[str, Any]:
        return {
            "name": instance.name,
            "title": instance.title,
            "confidence": instance.confidence,
            "supporting_events": instance.supporting_events,
            "supporting_violations": instance.supporting_violations,
            "start_time": instance.start_time,
            "last_update": instance.last_update,
            "duration_seconds": instance.duration_seconds,
            "resolved": instance.resolved,
            "explainability": instance.explainability,
        }

    @staticmethod
    def serialize_timeline_events(events: List[BehaviorTimelineEvent]) -> List[Dict[str, Any]]:
        return [
            {
                "id": e.id,
                "type": e.type,
                "transition": e.transition,
                "confidence": e.confidence,
                "timestamp": e.timestamp,
                "description": e.description,
                "duration_seconds": e.duration_seconds,
            }
            for e in events
        ]

    @staticmethod
    def serialize_summary(summary: BehaviorSessionSummary) -> Dict[str, Any]:
        return {
            "behavior_score": summary.behavior_score,
            "highest_risk_state": summary.highest_risk_state,
            "composite_behaviors_detected": summary.composite_behaviors_detected,
            "total_escalations": summary.total_escalations,
            "avg_confidence": summary.avg_confidence,
            "peak_confidence": summary.peak_confidence,
            "longest_suspicious_period_sec": summary.longest_suspicious_period_sec,
            "recovered_behaviors_count": summary.recovered_behaviors_count,
            "overall_integrity_assessment": summary.overall_integrity_assessment,
        }
