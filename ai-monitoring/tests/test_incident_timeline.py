"""
Unit Test Suite for Incident Intelligence Platform - Package 10.4 (Incident Timeline Engine).
Verifies timeline event creation, sequence numbering, append-only immutability, query service, and projections.
"""
import unittest
import time
from dataclasses import FrozenInstanceError

from incident_intelligence.domain import (
    Incident,
    EvidenceReference,
    IncidentState
)
from incident_intelligence.timeline import (
    TimelineEvent,
    TimelineEventDTO,
    TimelineBuilder,
    InMemoryTimelineRepository,
    TimelineQueryService,
    TimelineProjectionService,
    HumanTimelineProjection,
    TechnicalTimelineProjection,
    ReviewerTimelineProjection
)

class TestIncidentTimelineEngine(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryTimelineRepository()
        self.builder = TimelineBuilder(repository=self.repository)
        self.query_service = TimelineQueryService(repository=self.repository)
        self.projection_service = TimelineProjectionService(query_service=self.query_service)

    def test_01_timeline_event_creation_and_sequence(self):
        """Verify timeline events append sequentially with incremental sequence numbers."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-TL01",
            episode_id="V-UUID-TL01",
            incident_type="UNAUTH_PHONE",
            start_time=ts
        )

        e1 = self.builder.record_incident_created(incident, ts)
        e2 = self.builder.record_confidence_updated("INC-2026-TL01", 0.90, ts + 1.0, 10)
        e3 = self.builder.record_risk_updated("INC-2026-TL01", 75.0, ts + 1.0, 10)

        self.assertEqual(e1.sequence_number, 1)
        self.assertEqual(e2.sequence_number, 2)
        self.assertEqual(e3.sequence_number, 3)

        timeline = self.query_service.get_complete_timeline("INC-2026-TL01")
        self.assertEqual(len(timeline), 3)

    def test_02_append_only_immutability(self):
        """Verify TimelineEvent properties are immutable."""
        e = TimelineEvent(
            event_id="TLE-1001",
            incident_id="INC-2026-TL02",
            timestamp=time.time(),
            event_type="INCIDENT_CREATED",
            sequence_number=1
        )

        with self.assertRaises(FrozenInstanceError):
            e.event_type = "MODIFIED"  # type: ignore

    def test_03_state_transition_and_evidence_recording(self):
        """Verify recording state transitions and evidence keyframes."""
        ts = time.time()
        self.builder.record_state_changed("INC-2026-TL03", "STARTED", "ACTIVE", ts, "Sustained detection")
        
        ev_ref = EvidenceReference("EV-7001", 30, ts + 0.5, "/evidence/ev_7001.jpg", 0.92)
        self.builder.record_evidence_added("INC-2026-TL03", ev_ref, ts + 0.5)

        self.builder.record_resolved("INC-2026-TL03", ts + 5.0, "Behavior ended")

        ev_events = self.query_service.get_evidence_events("INC-2026-TL03")
        self.assertEqual(len(ev_events), 1)
        self.assertEqual(ev_events[0].evidence_reference.evidence_id, "EV-7001")

    def test_04_query_filters(self):
        """Verify get_events_by_type, get_events_by_time_range, and get_confidence_history."""
        ts = time.time()
        self.builder.record_confidence_updated("INC-2026-TL04", 0.70, ts, 1)
        self.builder.record_confidence_updated("INC-2026-TL04", 0.95, ts + 2.0, 20)
        self.builder.record_risk_updated("INC-2026-TL04", 80.0, ts + 2.0, 20)

        conf_events = self.query_service.get_events_by_type("INC-2026-TL04", "CONFIDENCE_UPDATED")
        self.assertEqual(len(conf_events), 2)

        range_events = self.query_service.get_events_by_time_range("INC-2026-TL04", ts + 1.0, ts + 3.0)
        self.assertEqual(len(range_events), 2)

        conf_history = self.query_service.get_confidence_history("INC-2026-TL04")
        self.assertEqual(len(conf_history), 2)
        self.assertEqual(conf_history[1][1], 0.95)

    def test_05_projections_generation(self):
        """Verify Human, Technical, and Reviewer timeline projection DTO generation."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-TL05",
            episode_id="V-UUID-TL05",
            incident_type="COMPOSITE_PHONE_GAZE",
            start_time=ts
        )

        self.builder.record_incident_created(incident, ts)
        self.builder.record_state_changed("INC-2026-TL05", "STARTED", "ESCALATED", ts + 2.0, "High severity")
        ev_ref = EvidenceReference("EV-8001", 40, ts + 2.0, "/evidence/ev_8001.jpg", 0.98)
        self.builder.record_evidence_added("INC-2026-TL05", ev_ref, ts + 2.0)
        self.builder.record_resolved("INC-2026-TL05", ts + 6.0, "Episode closed")

        # Human Projection
        human_proj = self.projection_service.generate_human_projection("INC-2026-TL05", "Phone + Off-Screen")
        self.assertIsInstance(human_proj, HumanTimelineProjection)
        self.assertEqual(len(human_proj.event_summaries), 4)

        # Technical Projection
        tech_proj = self.projection_service.generate_technical_projection("INC-2026-TL05")
        self.assertIsInstance(tech_proj, TechnicalTimelineProjection)
        self.assertEqual(tech_proj.total_events, 4)

        # Reviewer Projection
        rev_proj = self.projection_service.generate_reviewer_projection("INC-2026-TL05")
        self.assertIsInstance(rev_proj, ReviewerTimelineProjection)
        self.assertEqual(len(rev_proj.keyframe_evidence), 1)
        self.assertEqual(len(rev_proj.escalation_events), 1)

if __name__ == "__main__":
    unittest.main()
