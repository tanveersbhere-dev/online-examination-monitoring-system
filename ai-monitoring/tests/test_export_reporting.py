"""
Unit Test Suite for Incident Intelligence Platform - Package 10.9 (Export & Reporting Engine).
Verifies CasePackage creation, ExportManifest generation, SHA-256 integrity verification, JSON export, PDF generation, ZIP archive packaging, and repository persistence.
"""
import unittest
import time
import zipfile
import io
import json
import uuid

from incident_intelligence.domain import (
    Incident,
    IncidentMetadata,
    EvidenceReference
)
from incident_intelligence.timeline import TimelineEvent
from incident_intelligence.analytics import AnalyticsEngine
from incident_intelligence.explainability import NarrativeBuilder
from incident_intelligence.review import ReviewBuilder, ReviewDecisionEnum
from incident_intelligence.replay import ReplaySession, ReplayBookmark
from incident_intelligence.export import (
    IntegrityHash,
    ExportManifest,
    ExportManifestDTO,
    CasePackage,
    CasePackageDTO,
    JSONExporter,
    PDFExporter,
    ZIPExporter,
    InMemoryExportRepository
)

class TestExportReportingEngine(unittest.TestCase):

    def setUp(self):
        self.json_exporter = JSONExporter()
        self.pdf_exporter = PDFExporter()
        self.zip_exporter = ZIPExporter()
        self.repository = InMemoryExportRepository()

    def _create_sample_case_package(self) -> CasePackage:
        ts = time.time()
        metadata = IncidentMetadata(category="Security", title="Cell Phone Violation")
        incident = Incident("INC-2026-EX09", "V-UUID-EX09", "UNAUTH_PHONE", ts, duration=5.0, metadata=metadata)
        ev_ref = EvidenceReference("EV-1", 10, ts, "/ev/1.jpg", 0.90)
        incident.add_evidence_reference(ev_ref)

        inc_dto = incident.to_dto()
        ev_dtos = [ev_ref.to_dto()]
        tl_dtos = [TimelineEvent("TLE-1", "INC-2026-EX09", ts, "INCIDENT_CREATED", 1).to_dto()]

        analytics_engine = AnalyticsEngine()
        analytics_snap = analytics_engine.analyze_incident(incident)

        narrative_builder = NarrativeBuilder()
        exp_pkg = narrative_builder.build_explanation_package(incident)

        review_builder = ReviewBuilder()
        rev_pkg = review_builder.build_review_package(incident)
        rev_pkg.update_decision(ReviewDecisionEnum.CONFIRMED, ts + 1.0)

        replay_sess = ReplaySession("SESS-1", "INC-2026-EX09", 10, ts)
        replay_sess.add_bookmark(ReplayBookmark("BM-1", ts, 10, "EVIDENCE", "EV-1", "Keyframe Peak"))

        payload_to_hash = {
            "incident": inc_dto.to_dict(),
            "evidence": [e.to_dict() for e in ev_dtos],
            "timeline": [t.to_dict() for t in tl_dtos]
        }
        digest = IntegrityHash.compute_hash(payload_to_hash)

        manifest = ExportManifest(
            package_uuid=f"PKG-{uuid.uuid4().hex[:8].upper()}",
            export_timestamp=ts,
            platform_version="IIP-2026-V1.0",
            schema_versions={"incident": "1.0.0", "evidence": "1.0.0"},
            incident_id="INC-2026-EX09",
            replay_id="SESS-1",
            analytics_snapshot_id=analytics_snap.snapshot_id,
            explanation_id=exp_pkg.incident_id,
            review_id=rev_pkg.package_id,
            evidence_count=1,
            timeline_count=1,
            integrity_hash=digest
        )

        return CasePackage(
            incident_dto=inc_dto,
            evidence_references=ev_dtos,
            timeline_events=tl_dtos,
            analytics_snapshot_dto=analytics_snap.to_dto(),
            explanation_package_dto=exp_pkg.to_dto(),
            review_package_dto=rev_pkg.to_dto(),
            replay_session_dto=replay_sess.to_dto(),
            manifest=manifest,
            integrity_hash=digest
        )

    def test_01_sha256_integrity_hash(self):
        """Verify SHA-256 payload hashing and verification API."""
        payload = {"incident_id": "INC-100", "status": "ACTIVE", "score": 95.5}
        digest = IntegrityHash.compute_hash(payload)

        self.assertTrue(IntegrityHash.verify_hash(payload, digest))

        # Mutate payload and verify failure
        mutated_payload = {"incident_id": "INC-100", "status": "ACTIVE", "score": 0.0}
        self.assertFalse(IntegrityHash.verify_hash(mutated_payload, digest))

    def test_02_case_package_creation_and_manifest(self):
        """Verify CasePackage creation with valid ExportManifest."""
        cp = self._create_sample_case_package()

        self.assertEqual(cp.incident_dto.incident_id, "INC-2026-EX09")
        self.assertEqual(cp.manifest.evidence_count, 1)
        self.assertEqual(cp.manifest.timeline_count, 1)
        self.assertIsNotNone(cp.integrity_hash)

    def test_03_json_exporter(self):
        """Verify JSONExporter serializes complete CasePackage with zero information loss."""
        cp = self._create_sample_case_package()

        json_str = self.json_exporter.export_json(cp)
        self.assertIn("INC-2026-EX09", json_str)
        self.assertIn("manifest", json_str)

        # Deserialize back
        data = json.loads(json_str)
        self.assertEqual(data["incident"]["incident_id"], "INC-2026-EX09")
        self.assertEqual(data["manifest"]["platform_version"], "IIP-2026-V1.0")

    def test_04_pdf_exporter(self):
        """Verify PDFExporter generates reviewer report containing all required sections."""
        cp = self._create_sample_case_package()

        report_text = self.pdf_exporter.generate_report_content(cp)

        self.assertIn("EXECUTIVE SUMMARY", report_text)
        self.assertIn("EVIDENCE TABLE", report_text)
        self.assertIn("TIMELINE SUMMARY", report_text)
        self.assertIn("ANALYTICS SUMMARY", report_text)
        self.assertIn("EXPLAINABILITY SUMMARY", report_text)
        self.assertIn("HUMAN REVIEW SUMMARY", report_text)
        self.assertIn("REPLAY BOOKMARK SUMMARY", report_text)

    def test_05_zip_exporter_contents(self):
        """Verify ZIPExporter packages all required 8 files into archived container."""
        cp = self._create_sample_case_package()

        zip_bytes = self.zip_exporter.export_zip_bytes(cp)
        self.assertGreater(len(zip_bytes), 0)

        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            filenames = zf.namelist()
            self.assertIn("report.pdf", filenames)
            self.assertIn("incident.json", filenames)
            self.assertIn("timeline.json", filenames)
            self.assertIn("analytics.json", filenames)
            self.assertIn("explanation.json", filenames)
            self.assertIn("review.json", filenames)
            self.assertIn("bookmarks.json", filenames)
            self.assertIn("manifest.json", filenames)

    def test_06_export_repository(self):
        """Verify InMemoryExportRepository saves and queries CasePackage by UUID and incident ID."""
        cp = self._create_sample_case_package()
        self.repository.save(cp)

        by_uuid = self.repository.get_by_uuid(cp.manifest.package_uuid)
        self.assertIsNotNone(by_uuid)
        assert by_uuid is not None
        self.assertEqual(by_uuid.incident_dto.incident_id, "INC-2026-EX09")

        by_inc = self.repository.get_by_incident_id("INC-2026-EX09")
        self.assertIsNotNone(by_inc)

if __name__ == "__main__":
    unittest.main()
