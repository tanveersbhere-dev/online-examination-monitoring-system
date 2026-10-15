"""
Unit Tests for Incident Intelligence Platform - Package 10.1 (Incident Domain Core).
Verifies aggregate root creation, history immutability, DTO serialization, and schema versioning.
"""
import unittest
import time
from dataclasses import FrozenInstanceError

from incident_intelligence.domain import (
    Incident,
    IncidentDTO,
    IncidentState,
    IncidentSeverity,
    IncidentPriority,
    IncidentMetadata,
    EvidenceReference,
    EvidenceReferenceDTO,
    ConfidenceHistoryEntry,
    RiskHistoryEntry,
    StateHistoryEntry,
    INCIDENT_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION
)

class TestIncidentDomainCore(unittest.TestCase):

    def test_01_incident_aggregate_creation(self):
        """Verify Incident aggregate root instantiates with correct defaults and schema version."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-0001",
            episode_id="V-UUID-0001",
            incident_type="PHONE_USAGE",
            start_time=ts
        )

        self.assertEqual(incident.incident_id, "INC-2026-0001")
        self.assertEqual(incident.episode_id, "V-UUID-0001")
        self.assertEqual(incident.incident_type, "PHONE_USAGE")
        self.assertEqual(incident.status, IncidentState.STARTED)
        self.assertEqual(incident.severity, IncidentSeverity.MEDIUM)
        self.assertEqual(incident.priority, IncidentPriority.P3_MEDIUM)
        self.assertEqual(incident.schema_version, INCIDENT_SCHEMA_VERSION)
        self.assertEqual(len(incident.confidence_history), 0)
        self.assertEqual(len(incident.evidence_references), 0)

    def test_02_append_history_and_metrics_update(self):
        """Verify append_confidence, append_risk, and transition_state update metrics correctly."""
        ts = time.time()
        incident = Incident(
            incident_id="INC-2026-0002",
            episode_id="V-UUID-0002",
            incident_type="LOOKING_AWAY",
            start_time=ts
        )

        # Append confidence entries
        incident.append_confidence(ts + 1.0, 0.70, 10)
        incident.append_confidence(ts + 2.0, 0.90, 20)

        self.assertEqual(len(incident.confidence_history), 2)
        self.assertEqual(incident.current_confidence, 0.90)
        self.assertEqual(incident.peak_confidence, 0.90)
        self.assertEqual(incident.average_confidence, 0.80)
        self.assertEqual(incident.duration, 2.0)

        # Append risk entry
        incident.append_risk(ts + 2.0, 45.0, 20)
        self.assertEqual(len(incident.risk_history), 1)
        self.assertEqual(incident.current_risk, 45.0)

        # State transition
        incident.transition_state(ts + 3.0, IncidentState.ACTIVE, "Confidence sustained > threshold")
        self.assertEqual(incident.status, IncidentState.ACTIVE)
        self.assertEqual(len(incident.state_history), 1)
        self.assertEqual(incident.state_history[0].previous_state, "STARTED")
        self.assertEqual(incident.state_history[0].new_state, "ACTIVE")

    def test_03_history_entry_immutability(self):
        """Verify history entries are immutable and raise error on attribute modification."""
        c_entry = ConfidenceHistoryEntry(time.time(), 0.85, 15)
        r_entry = RiskHistoryEntry(time.time(), 50.0, 15)
        s_entry = StateHistoryEntry(time.time(), "STARTED", "ACTIVE", "Sustained detection")

        with self.assertRaises(FrozenInstanceError):
            c_entry.confidence_value = 0.99  # type: ignore

        with self.assertRaises(FrozenInstanceError):
            r_entry.risk_score_value = 100.0  # type: ignore

        with self.assertRaises(FrozenInstanceError):
            s_entry.new_state = "RESOLVED"  # type: ignore

    def test_04_evidence_reference_and_dto(self):
        """Verify EvidenceReference immutability and conversion to DTO."""
        ts = time.time()
        ev_ref = EvidenceReference(
            evidence_id="EV-1001",
            frame_number=42,
            timestamp=ts,
            uri="/static/evidence/ev_1001.jpg",
            importance=0.95,
            crop_type="OBJECT_CROP"
        )

        self.assertEqual(ev_ref.evidence_id, "EV-1001")
        self.assertEqual(ev_ref.schema_version, EVIDENCE_SCHEMA_VERSION)

        with self.assertRaises(FrozenInstanceError):
            ev_ref.importance = 0.50  # type: ignore

        dto = ev_ref.to_dto()
        self.assertIsInstance(dto, EvidenceReferenceDTO)
        dto_dict = dto.to_dict()
        self.assertEqual(dto_dict["evidence_id"], "EV-1001")
        self.assertEqual(dto_dict["importance"], 0.95)

    def test_05_incident_dto_serialization(self):
        """Verify complete Incident Aggregate Root serialization to DTO and Dictionary."""
        ts = time.time()
        metadata = IncidentMetadata(
            category="Security",
            title="Phone + Off-Screen Attention",
            description="Cell phone detected while looking away",
            triggered_rules=["UNAUTH_PHONE", "ATT_DOWNWARD_GAZE"]
        )

        incident = Incident(
            incident_id="INC-2026-0005",
            episode_id="V-UUID-0005",
            incident_type="COMPOSITE_PHONE_GAZE",
            start_time=ts,
            metadata=metadata
        )

        incident.append_confidence(ts + 1.0, 0.92, 100)
        incident.append_risk(ts + 1.0, 75.0, 100)
        incident.add_evidence_reference(
            EvidenceReference("EV-5001", 100, ts + 1.0, "/evidence/ev_5001.jpg", 0.90)
        )

        dto = incident.to_dto()
        self.assertIsInstance(dto, IncidentDTO)

        dto_dict = dto.to_dict()
        self.assertEqual(dto_dict["incident_id"], "INC-2026-0005")
        self.assertEqual(dto_dict["episode_id"], "V-UUID-0005")
        self.assertEqual(dto_dict["metadata"]["category"], "Security")
        self.assertEqual(dto_dict["metadata"]["title"], "Phone + Off-Screen Attention")
        self.assertEqual(len(dto_dict["history"]["confidence_history"]), 1)
        self.assertEqual(len(dto_dict["evidence_references"]), 1)
        self.assertEqual(dto_dict["schema_version"], INCIDENT_SCHEMA_VERSION)

if __name__ == "__main__":
    unittest.main()
