"""
Unit Test Suite for Incident Intelligence Platform - Package 10.7 (Review Intelligence Engine).
Verifies ReviewPackage creation, decision transitions, reviewer notes, audit trail integrity, DTO serialization, and repository persistence.
"""
import unittest
import time

from incident_intelligence.domain import (
    Incident,
    IncidentMetadata,
    EvidenceReference
)
from incident_intelligence.review import (
    ReviewPackage,
    ReviewPackageDTO,
    ReviewStatusEnum,
    ReviewDecisionEnum,
    ReviewNote,
    ReviewAuditEntry,
    ReviewBuilder,
    InMemoryReviewRepository
)

class TestReviewIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        self.builder = ReviewBuilder()
        self.repository = InMemoryReviewRepository()

    def test_01_review_package_creation(self):
        """Verify ReviewBuilder creates ReviewPackage with read-only DTOs and initial audit entry."""
        ts = time.time()
        metadata = IncidentMetadata(category="Security", title="Phone Usage", description="Phone detected")
        incident = Incident(
            incident_id="INC-2026-RV01",
            episode_id="V-UUID-RV01",
            incident_type="UNAUTH_PHONE",
            start_time=ts,
            metadata=metadata
        )

        ev_ref = EvidenceReference("EV-100", 20, ts, "/ev/100.jpg", 0.90)
        incident.add_evidence_reference(ev_ref)

        pkg = self.builder.build_review_package(incident)

        self.assertEqual(pkg.incident_id, "INC-2026-RV01")
        self.assertEqual(pkg.review_status, ReviewStatusEnum.UNREVIEWED)
        self.assertEqual(pkg.review_decision, ReviewDecisionEnum.NO_DECISION)
        self.assertEqual(len(pkg.evidence_references), 1)
        self.assertEqual(len(pkg.audit_trail), 1)
        self.assertEqual(pkg.audit_trail[0].action, "REVIEW_STARTED")

    def test_02_decision_update_and_audit_trail(self):
        """Verify updating decision sets status to REVIEWED and appends DECISION_CHANGED audit entry."""
        ts = time.time()
        incident = Incident(incident_id="INC-2026-RV02", episode_id="V-UUID-RV02", incident_type="LOOKING_AWAY", start_time=ts)
        pkg = self.builder.build_review_package(incident)

        pkg.set_under_review(ts + 1.0)
        self.assertEqual(pkg.review_status, ReviewStatusEnum.UNDER_REVIEW)

        pkg.update_decision(ReviewDecisionEnum.CONFIRMED, ts + 2.0, "Verified phone usage in video crop")
        self.assertEqual(pkg.review_status, ReviewStatusEnum.REVIEWED)
        self.assertEqual(pkg.review_decision, ReviewDecisionEnum.CONFIRMED)

        # Audit trail should have 3 entries: REVIEW_STARTED, REVIEW_STARTED, DECISION_CHANGED
        actions = [a.action for a in pkg.audit_trail]
        self.assertIn("REVIEW_STARTED", actions)
        self.assertIn("DECISION_CHANGED", actions)

    def test_03_adding_reviewer_notes(self):
        """Verify adding ReviewNote appends to notes list and logs NOTE_ADDED audit entry."""
        ts = time.time()
        incident = Incident(incident_id="INC-2026-RV03", episode_id="V-UUID-RV03", incident_type="ID_MISMATCH", start_time=ts)
        pkg = self.builder.build_review_package(incident)

        note = ReviewNote(note_id="N-1", timestamp=ts + 1.0, author="PROCTOR_AUDITOR_1", text="Secondary reviewer requested")
        pkg.add_note(note)

        self.assertEqual(len(pkg.notes), 1)
        self.assertEqual(pkg.notes[0].author, "PROCTOR_AUDITOR_1")
        self.assertTrue(any(a.action == "NOTE_ADDED" for a in pkg.audit_trail))

    def test_04_repository_and_status_filtering(self):
        """Verify saving to InMemoryReviewRepository and querying by status."""
        ts = time.time()
        inc1 = Incident(incident_id="INC-2026-RV04A", episode_id="V-UUID-04A", incident_type="UNAUTH_PHONE", start_time=ts)
        inc2 = Incident(incident_id="INC-2026-RV04B", episode_id="V-UUID-04B", incident_type="UNAUTH_BOOK", start_time=ts)

        pkg1 = self.builder.build_review_package(inc1)
        pkg2 = self.builder.build_review_package(inc2)
        pkg2.update_decision(ReviewDecisionEnum.FALSE_POSITIVE, ts + 1.0)

        self.repository.save(pkg1)
        self.repository.save(pkg2)

        unreviewed = self.repository.list_by_status(ReviewStatusEnum.UNREVIEWED)
        reviewed = self.repository.list_by_status(ReviewStatusEnum.REVIEWED)

        self.assertEqual(len(unreviewed), 1)
        self.assertEqual(unreviewed[0].incident_id, "INC-2026-RV04A")
        self.assertEqual(len(reviewed), 1)
        self.assertEqual(reviewed[0].incident_id, "INC-2026-RV04B")

    def test_05_dto_serialization(self):
        """Verify ReviewPackage conversion to DTO and dictionary payload."""
        ts = time.time()
        incident = Incident(incident_id="INC-2026-RV05", episode_id="V-UUID-RV05", incident_type="PRESENTATION_ATTACK", start_time=ts)
        pkg = self.builder.build_review_package(incident)

        dto = pkg.to_dto()
        self.assertIsInstance(dto, ReviewPackageDTO)
        dto_dict = dto.to_dict()

        self.assertEqual(dto_dict["package_id"], pkg.package_id)
        self.assertEqual(dto_dict["incident_id"], "INC-2026-RV05")
        self.assertEqual(dto_dict["review_status"], "UNREVIEWED")
        self.assertEqual(dto_dict["review_decision"], "NO_DECISION")
        self.assertIn("incident", dto_dict)
        self.assertIn("audit_trail", dto_dict)

if __name__ == "__main__":
    unittest.main()
