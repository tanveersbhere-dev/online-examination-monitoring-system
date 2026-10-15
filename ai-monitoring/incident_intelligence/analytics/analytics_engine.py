"""
Incident Intelligence Analytics Engine (IIAE).
Computes read-only analytics snapshots derived entirely from Incident state and Timeline query results.
"""
from typing import Optional, List, Dict, Any
import time
import uuid

from incident_intelligence.domain.incident import Incident
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.timeline.timeline_query import TimelineQueryService
from incident_intelligence.analytics.incident_metrics import IncidentMetrics
from incident_intelligence.analytics.confidence_analysis import ConfidenceAnalysis, analyze_confidence_stream
from incident_intelligence.analytics.risk_analysis import RiskAnalysis, analyze_risk_stream
from incident_intelligence.analytics.behavior_analysis import BehaviorAnalysis
from incident_intelligence.analytics.timeline_statistics import TimelineStatistics
from incident_intelligence.analytics.analytics_repository import (
    InMemoryAnalyticsRepository,
    IncidentAnalyticsSnapshot
)

class AnalyticsEngine:
    """Read-only analytics calculator and snapshot engine."""

    def __init__(self, repository: Optional[InMemoryAnalyticsRepository] = None):
        self.repository = repository or InMemoryAnalyticsRepository()

    def analyze_incident(
        self,
        incident: Incident,
        query_service: Optional[TimelineQueryService] = None
    ) -> IncidentAnalyticsSnapshot:
        """
        Compute complete analytics snapshot from Incident aggregate and optional Timeline query service.
        Returns immutable IncidentAnalyticsSnapshot object.
        """
        ts_now = time.time()

        # Fetch timeline events if query service available
        timeline_events: List[TimelineEvent] = []
        if query_service:
            timeline_events = query_service.get_complete_timeline(incident.incident_id)

        # 1. Compute Confidence Analysis
        conf_vals = [e.confidence_value for e in incident.confidence_history]
        conf_ts = [e.timestamp for e in incident.confidence_history]
        if not conf_vals and timeline_events:
            conf_vals = [e.confidence for e in timeline_events if e.confidence is not None]
            conf_ts = [e.timestamp for e in timeline_events if e.confidence is not None]

        conf_analysis = analyze_confidence_stream(conf_vals, conf_ts)

        # 2. Compute Risk Analysis
        risk_vals = [e.risk_score_value for e in incident.risk_history]
        risk_ts = [e.timestamp for e in incident.risk_history]
        if not risk_vals and timeline_events:
            risk_vals = [e.risk for e in timeline_events if e.risk is not None]
            risk_ts = [e.timestamp for e in timeline_events if e.risk is not None]

        risk_analysis = analyze_risk_stream(risk_vals, risk_ts)

        # 3. Compute Behavior Analysis
        rule_freq: Dict[str, int] = {}
        for r in incident.metadata.triggered_rules:
            rule_freq[r] = rule_freq.get(r, 0) + 1

        comp_freq: Dict[str, int] = {}
        if "COMPOSITE" in incident.incident_type:
            comp_freq[incident.incident_type] = 1

        behavior_analysis = BehaviorAnalysis(
            triggered_rules_frequency=rule_freq,
            composite_frequency=comp_freq,
            behavior_recurrence_count=max(0, len(incident.confidence_history) - 1),
            behavior_persistence_seconds=incident.duration
        )

        # 4. Compute Timeline Statistics
        time_in_states: Dict[str, float] = {}
        longest_active = 0.0
        longest_recovery = 0.0
        escalation_cnt = 0
        recovery_cnt = 0
        active_dur = 0.0
        recovery_dur = 0.0

        if timeline_events:
            last_ts = timeline_events[0].timestamp
            last_state = timeline_events[0].new_state or "STARTED"

            for i in range(1, len(timeline_events)):
                ev = timeline_events[i]
                dur = max(0.0, ev.timestamp - last_ts)
                time_in_states[last_state] = time_in_states.get(last_state, 0.0) + dur

                if last_state in ("ACTIVE", "ESCALATED"):
                    active_dur += dur
                    longest_active = max(longest_active, dur)
                elif last_state == "RECOVERING":
                    recovery_dur += dur
                    longest_recovery = max(longest_recovery, dur)

                if ev.event_type == "STATE_CHANGED":
                    if ev.new_state == "ESCALATED":
                        escalation_cnt += 1
                    elif ev.new_state == "RECOVERING":
                        recovery_cnt += 1

                last_ts = ev.timestamp
                if ev.new_state:
                    last_state = ev.new_state
        else:
            # Fallback based on aggregate state history
            for entry in incident.state_history:
                if entry.new_state == "ESCALATED":
                    escalation_cnt += 1
                elif entry.new_state == "RECOVERING":
                    recovery_cnt += 1

        total_dur = round(timeline_events[-1].timestamp - timeline_events[0].timestamp, 2) if (timeline_events and len(timeline_events) > 1) else max(0.0, incident.duration)
        if active_dur == 0.0 and total_dur > 0.0:
            active_dur = total_dur

        trans_cnt = len(timeline_events) if timeline_events else len(incident.state_history)
        trans_freq = round((trans_cnt / max(0.1, total_dur)) * 60.0, 2)

        timeline_stats = TimelineStatistics(
            time_in_states_seconds=time_in_states,
            longest_active_period_seconds=round(longest_active, 2),
            longest_recovery_period_seconds=round(longest_recovery, 2),
            transition_count=trans_cnt,
            transition_frequency_per_minute=trans_freq
        )

        # 5. Compute Overall Incident Metrics
        ev_count = len(incident.evidence_references)
        ev_density = round((ev_count / max(0.1, total_dur)) * 60.0, 2)

        metrics = IncidentMetrics(
            total_duration_seconds=round(total_dur, 2),
            active_duration_seconds=round(active_dur, 2),
            recovery_duration_seconds=round(recovery_dur, 2),
            escalation_count=escalation_cnt,
            recovery_count=recovery_cnt,
            resolution_time=incident.resolved_time,
            evidence_count=ev_count,
            evidence_density_per_minute=ev_density,
            keyframe_count=ev_count
        )

        # 6. Create Immutable Snapshot
        snapshot = IncidentAnalyticsSnapshot(
            snapshot_id=f"ANS-{uuid.uuid4().hex[:8].upper()}",
            incident_id=incident.incident_id,
            timestamp=ts_now,
            metrics=metrics,
            confidence_analysis=conf_analysis,
            risk_analysis=risk_analysis,
            behavior_analysis=behavior_analysis,
            timeline_statistics=timeline_stats
        )

        self.repository.save(snapshot)
        return snapshot
