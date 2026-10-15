"""
Unit Test Suite for Incident Intelligence Platform - Package 10.6 (Explainability Engine).
Verifies reason code generation, narrative determinism, reviewer summaries, technical traces, and machine explanations.
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
from incident_intelligence.analytics import AnalyticsEngine
from incident_intelligence.explainability import (
    ReasonCode,
    ReasonCodeEnum,
    ReasonCodeGenerator,
    TechnicalExplanation,
    ReviewerSummary,
    MachineExplanation,
    NarrativeBuilder,
    IncidentExplanationPackage,
    IncidentExplanationPackageDTO,
    InMemoryExplanationRepository
)

class TestExplainabilityEngine(unittest.TestCase):

    def setUp(self):
        self.tl_repository = InMemoryTimelineRepository()
        self.tl_builder = TimelineBuilder(repository=self.tl_repository)
        self.tl_query = TimelineQueryService(repository=self.tl_repository)
        self.analytics_engine = AnalyticsEngine()
        self.narrative_builder = NarrativeBuilder()
        self.explanation_repo = InMemoryExplanationRepository()

    def test_01_reason_code_generation(self):
        """Verify deterministic mapping of rules and timeline events to stable ReasonCode objects."""
        ts = time.time()
        metadata = IncidentMetadata(
            category="Security",
            title="Phone + Off-Screen Attention",
            triggered_rules=["UNAUTH_PHONE", "ATT_DOWNWARD_GAZE"]
        )
        incident = Incident(
            incident_id="INC-2026-EX01",
            episode_id="V-UUID-EX01",
            incident_type="COMPOSITE_PHONE_GAZE",
            start_time=ts,
            duration=6.0,
            metadata=metadata
        )

        gen = ReasonCodeGenerator()
        codes = gen.generate_reason_codes(incident)
        code_keys = [c.code for c in codes]

        self.assertIn(ReasonCodeEnum.PHONE_VISIBLE.value, code_keys)
        self.assertIn(ReasonCodeEnum.PHONE_LONG_DURATION.value, code_keys)
        self.assertIn(ReasonCodeEnum.DOWNWARD_GAZE.value, code_keys)
        self.assertIn(ReasonCodeEnum.COMPOSITE_BEHAVIOR.value, code_keys)

    def test_02_narrative_determinism(self):
        """Verify identical input data produces 100% identical narrative outputs."""
        ts = time.time()
        metadata = IncidentMetadata(
            category="Security",
            title="Unauthorized Phone",
            description="Cell phone detected in candidate hand",
            triggered_rules=["UNAUTH_PHONE"]
        )
        incident = Incident(
            incident_id="INC-2026-EX02",
            episode_id="V-UUID-EX02",
            incident_type="UNAUTH_PHONE",
            start_time=ts,
            duration=3.5,
            peak_confidence=0.92,
            metadata=metadata
        )

        pkg1 = self.narrative_builder.build_explanation_package(incident)
        pkg2 = self.narrative_builder.build_explanation_package(incident)

        self.assertEqual(pkg1.deterministic_narrative, pkg2.deterministic_narrative)
        self.assertEqual(pkg1.reviewer_summary.what_happened, pkg2.reviewer_summary.what_happened)

    def test_03_reviewer_summary_contents(self):
        """Verify ReviewerSummary fields (what happened, why it matters, duration, risk, evidence)."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-EX03",
            episode_id="V-UUID-EX03",
            incident_type="UNAUTH_BOOK",
            start_time=ts,
            duration=12.0,
            current_risk=70.0
        )
        incident.add_evidence_reference(EvidenceReference("EV-1", 10, ts, "/ev/1.jpg", 0.9))

        pkg = self.narrative_builder.build_explanation_package(incident)
        rev = pkg.reviewer_summary

        self.assertEqual(rev.incident_id, "INC-2026-EX03")
        self.assertIn("12.0 seconds", rev.duration_formatted)
        self.assertIn("1 keyframe", rev.supporting_evidence_summary)
        self.assertIn("70.0", rev.risk_assessment)

    def test_04_technical_and_machine_explanation(self):
        """Verify TechnicalExplanation and MachineExplanation generation."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-EX04",
            episode_id="V-UUID-EX04",
            incident_type="IDENTITY_INSTABILITY",
            start_time=ts,
            duration=4.0,
            peak_confidence=0.88
        )

        self.tl_builder.record_incident_created(incident, ts)
        self.tl_builder.record_state_changed("INC-2026-EX04", "STARTED", "ACTIVE", ts + 1.0)
        snapshot = self.analytics_engine.analyze_incident(incident, query_service=self.tl_query)

        pkg = self.narrative_builder.build_explanation_package(
            incident,
            timeline_events=self.tl_query.get_complete_timeline("INC-2026-EX04"),
            analytics_snapshot=snapshot
        )

        tech = pkg.technical_explanation
        mach = pkg.machine_explanation

        self.assertEqual(tech.incident_id, "INC-2026-EX04")
        self.assertEqual(len(tech.timeline_event_ids), 2)

        self.assertEqual(mach.incident_id, "INC-2026-EX04")
        self.assertEqual(mach.analytics_snapshot_id, snapshot.snapshot_id)
        self.assertIn("IDENTITY_INSTABILITY", mach.reason_codes)

    def test_05_explanation_package_dto_and_repository(self):
        """Verify IncidentExplanationPackage serialization and repository persistence."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-EX05",
            episode_id="V-UUID-EX05",
            incident_type="LOOKING_AWAY",
            start_time=ts
        )

        pkg = self.narrative_builder.build_explanation_package(incident)
        self.explanation_repo.save(pkg)

        fetched = self.explanation_repo.get_by_incident_id("INC-2026-EX05")
        self.assertIsNotNone(fetched)
        assert fetched is not None

        dto = fetched.to_dto()
        self.assertIsInstance(dto, IncidentExplanationPackageDTO)
        dto_dict = dto.to_dict()

        self.assertEqual(dto_dict["incident_id"], "INC-2026-EX05")
        self.assertIn("reviewer_summary", dto_dict)
        self.assertIn("technical_explanation", dto_dict)
        self.assertIn("machine_explanation", dto_dict)

if __name__ == "__main__":
    unittest.main()
