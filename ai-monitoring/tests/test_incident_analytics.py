"""
Unit Test Suite for Incident Intelligence Platform - Package 10.5 (Incident Intelligence Analytics Engine).
Verifies read-only analytics calculation, statistical metrics, timeline statistics, risk velocity, and repository persistence.
"""
import unittest
import time

from incident_intelligence.domain import (
    Incident,
    IncidentMetadata,
    EvidenceReference,
    IncidentState
)
from incident_intelligence.timeline import (
    TimelineBuilder,
    InMemoryTimelineRepository,
    TimelineQueryService
)
from incident_intelligence.analytics import (
    AnalyticsEngine,
    InMemoryAnalyticsRepository,
    IncidentAnalyticsSnapshot,
    IncidentAnalyticsSnapshotDTO,
    ConfidenceAnalysis,
    RiskAnalysis,
    BehaviorAnalysis,
    TimelineStatistics
)

class TestIncidentAnalyticsEngine(unittest.TestCase):

    def setUp(self):
        self.tl_repository = InMemoryTimelineRepository()
        self.tl_builder = TimelineBuilder(repository=self.tl_repository)
        self.tl_query = TimelineQueryService(repository=self.tl_repository)

        self.analytics_repository = InMemoryAnalyticsRepository()
        self.analytics_engine = AnalyticsEngine(repository=self.analytics_repository)

    def test_01_confidence_statistical_analysis(self):
        """Verify confidence analysis computes peak, mean, median, std_dev, slope, and trend."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-AN01",
            episode_id="V-UUID-AN01",
            incident_type="UNAUTH_PHONE",
            start_time=ts
        )

        incident.append_confidence(ts, 0.40, 1)
        incident.append_confidence(ts + 1.0, 0.70, 10)
        incident.append_confidence(ts + 2.0, 0.90, 20)

        snapshot = self.analytics_engine.analyze_incident(incident)

        conf_a = snapshot.confidence_analysis
        self.assertEqual(conf_a.current, 0.90)
        self.assertEqual(conf_a.peak, 0.90)
        self.assertEqual(conf_a.average, 0.6667)
        self.assertEqual(conf_a.median, 0.70)
        self.assertGreater(conf_a.slope, 0.0)
        self.assertEqual(conf_a.trend, "INCREMENTAL")

    def test_02_risk_trajectory_analysis(self):
        """Verify risk analysis computes current/peak/average risk, velocity (dR/dt), and stability."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-AN02",
            episode_id="V-UUID-AN02",
            incident_type="IDENTITY_INSTABILITY",
            start_time=ts
        )

        incident.append_risk(ts, 20.0, 1)
        incident.append_risk(ts + 2.0, 60.0, 20)
        incident.append_risk(ts + 4.0, 80.0, 40)

        snapshot = self.analytics_engine.analyze_incident(incident)

        risk_a = snapshot.risk_analysis
        self.assertEqual(risk_a.current_risk, 80.0)
        self.assertEqual(risk_a.peak_risk, 80.0)
        self.assertEqual(risk_a.average_risk, 53.33)
        self.assertEqual(risk_a.risk_escalation_count, 2)
        self.assertGreater(risk_a.risk_velocity, 0.0)

    def test_03_timeline_statistics_and_duration_splits(self):
        """Verify timeline statistics compute time in states, transition counts, and longest active period."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-AN03",
            episode_id="V-UUID-AN03",
            incident_type="COMPOSITE_PHONE_GAZE",
            start_time=ts
        )

        self.tl_builder.record_incident_created(incident, ts)
        self.tl_builder.record_state_changed("INC-2026-AN03", "STARTED", "ACTIVE", ts + 1.0)
        self.tl_builder.record_state_changed("INC-2026-AN03", "ACTIVE", "ESCALATED", ts + 4.0)
        self.tl_builder.record_state_changed("INC-2026-AN03", "ESCALATED", "RECOVERING", ts + 6.0)
        self.tl_builder.record_resolved("INC-2026-AN03", ts + 8.0)

        snapshot = self.analytics_engine.analyze_incident(incident, query_service=self.tl_query)

        metrics = snapshot.metrics
        tl_stats = snapshot.timeline_statistics

        self.assertEqual(metrics.total_duration_seconds, 8.0)
        self.assertEqual(metrics.escalation_count, 1)
        self.assertEqual(metrics.recovery_count, 1)
        self.assertGreater(tl_stats.longest_active_period_seconds, 0.0)
        self.assertEqual(tl_stats.transition_count, 5)

    def test_04_behavior_analysis_aggregation(self):
        """Verify behavior analysis aggregates rule frequencies and composite counts."""
        ts = time.time()
        metadata = IncidentMetadata(triggered_rules=["UNAUTH_PHONE", "ATT_DOWNWARD_GAZE"])
        incident = Incident(
            incident_id="INC-2026-AN04",
            episode_id="V-UUID-AN04",
            incident_type="COMPOSITE_PHONE_GAZE",
            start_time=ts,
            metadata=metadata
        )

        snapshot = self.analytics_engine.analyze_incident(incident)
        b_analysis = snapshot.behavior_analysis

        self.assertEqual(b_analysis.triggered_rules_frequency.get("UNAUTH_PHONE"), 1)
        self.assertEqual(b_analysis.triggered_rules_frequency.get("ATT_DOWNWARD_GAZE"), 1)
        self.assertEqual(b_analysis.composite_frequency.get("COMPOSITE_PHONE_GAZE"), 1)

    def test_05_analytics_repository_and_dto_serialization(self):
        """Verify snapshot saving, querying, and conversion to pure DTO dictionary."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-AN05",
            episode_id="V-UUID-AN05",
            incident_type="UNAUTH_BOOK",
            start_time=ts
        )

        snapshot = self.analytics_engine.analyze_incident(incident)

        # Query repository
        latest = self.analytics_repository.get_latest("INC-2026-AN05")
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.snapshot_id, snapshot.snapshot_id)

        # DTO Serialization
        dto = snapshot.to_dto()
        self.assertIsInstance(dto, IncidentAnalyticsSnapshotDTO)
        dto_dict = dto.to_dict()

        self.assertEqual(dto_dict["incident_id"], "INC-2026-AN05")
        self.assertIn("metrics", dto_dict)
        self.assertIn("confidence_analysis", dto_dict)
        self.assertIn("risk_analysis", dto_dict)
        self.assertIn("timeline_statistics", dto_dict)

if __name__ == "__main__":
    unittest.main()
