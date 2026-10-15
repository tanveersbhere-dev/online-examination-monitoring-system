"""
Unit Test Suite for Incident Intelligence Platform - Package 10.2 (Incident Orchestration Engine).
Verifies event routing, deterministic matching, aggregate updates, state transitions, and repository adapter.
"""
import unittest
import time
from unittest.mock import MagicMock

from incident_intelligence.domain import (
    Incident,
    IncidentState,
    IncidentSeverity,
    EvidenceReference
)
from incident_intelligence.orchestration import (
    InMemoryIncidentRepository,
    IncidentFactory,
    IncidentLifecycleManager,
    IncidentMatchingEngine,
    IncidentEventRouter,
    IncidentOrchestrator
)

class TestIncidentOrchestrationEngine(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryIncidentRepository()
        self.orchestrator = IncidentOrchestrator(repository=self.repository)

    def test_01_create_new_incident_on_started_event(self):
        """Verify STARTED lifecycle event creates a new Incident aggregate root."""
        ts = time.time()
        event_data = {
            "event_type": "STARTED",
            "violation_id": "V-UUID-1001",
            "violation_type": "UNAUTH_PHONE",
            "violation_category": "Security",
            "title": "Phone Detected",
            "description": "Cell phone detected in hand",
            "timestamp": ts,
            "confidence": 0.92,
            "risk_score": 80.0,
            "frame_number": 42
        }

        incident = self.orchestrator.process_lifecycle_event(event_data)
        self.assertIsNotNone(incident)
        assert incident is not None
        self.assertEqual(incident.episode_id, "V-UUID-1001")
        self.assertEqual(incident.incident_type, "UNAUTH_PHONE")
        self.assertEqual(incident.status, IncidentState.STARTED)
        self.assertEqual(incident.current_confidence, 0.92)
        self.assertEqual(incident.current_risk, 80.0)

        # Check repository persistence
        fetched = self.repository.get_by_episode_id("V-UUID-1001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.incident_id, incident.incident_id)

    def test_02_update_existing_incident_on_updated_event(self):
        """Verify UPDATED lifecycle event updates existing Incident aggregate root."""
        ts = time.time()
        start_event = {
            "event_type": "STARTED",
            "violation_id": "V-UUID-1002",
            "violation_type": "ATT_LOOKING_AWAY",
            "timestamp": ts,
            "confidence": 0.70
        }
        inc1 = self.orchestrator.process_lifecycle_event(start_event)
        assert inc1 is not None

        # Send UPDATED event
        update_event = {
            "event_type": "UPDATED",
            "violation_id": "V-UUID-1002",
            "violation_type": "ATT_LOOKING_AWAY",
            "timestamp": ts + 1.5,
            "confidence": 0.95,
            "risk_score": 50.0,
            "frame_number": 80
        }
        inc2 = self.orchestrator.process_lifecycle_event(update_event)
        assert inc2 is not None

        self.assertEqual(inc2.incident_id, inc1.incident_id)
        self.assertEqual(inc2.current_confidence, 0.95)
        self.assertEqual(inc2.peak_confidence, 0.95)
        self.assertEqual(len(inc2.confidence_history), 2)

    def test_03_escalate_and_resolve_incident(self):
        """Verify ESCALATED and RESOLVED lifecycle state transitions."""
        ts = time.time()
        self.orchestrator.process_lifecycle_event({
            "event_type": "STARTED",
            "violation_id": "V-UUID-1003",
            "violation_type": "IDENTITY_INSTABILITY",
            "timestamp": ts
        })

        # Send ESCALATED event
        inc_esc = self.orchestrator.process_lifecycle_event({
            "event_type": "ESCALATED",
            "violation_id": "V-UUID-1003",
            "timestamp": ts + 2.0,
            "confidence": 0.98
        })
        assert inc_esc is not None
        self.assertEqual(inc_esc.status, IncidentState.ESCALATED)

        # Send RESOLVED event
        inc_res = self.orchestrator.process_lifecycle_event({
            "event_type": "RESOLVED",
            "violation_id": "V-UUID-1003",
            "timestamp": ts + 8.0,
            "description": "Identity stabilized"
        })
        assert inc_res is not None
        self.assertEqual(inc_res.status, IncidentState.RESOLVED)
        self.assertIsNotNone(inc_res.resolved_time)
        self.assertEqual(inc_res.duration, 8.0)

    def test_04_duplicate_started_event_ignored(self):
        """Verify duplicate STARTED event for active episode updates existing aggregate without creating new ID."""
        ts = time.time()
        event_data = {
            "event_type": "STARTED",
            "violation_id": "V-UUID-1004",
            "violation_type": "UNAUTH_BOOK",
            "timestamp": ts
        }

        inc1 = self.orchestrator.process_lifecycle_event(event_data)
        inc2 = self.orchestrator.process_lifecycle_event(event_data)

        assert inc1 is not None and inc2 is not None
        self.assertEqual(inc1.incident_id, inc2.incident_id)

    def test_05_unknown_update_handled_safely(self):
        """Verify UPDATED event received without prior STARTED creates aggregate safely."""
        ts = time.time()
        event_data = {
            "event_type": "UPDATED",
            "violation_id": "V-UUID-UNKNOWN",
            "violation_type": "COMM_MULTIPLE_PERSONS",
            "timestamp": ts,
            "confidence": 0.85
        }

        inc = self.orchestrator.process_lifecycle_event(event_data)
        self.assertIsNotNone(inc)
        assert inc is not None
        self.assertEqual(inc.episode_id, "V-UUID-UNKNOWN")

    def test_06_attach_evidence_reference(self):
        """Verify attaching evidence reference updates incident aggregate and logs domain event."""
        ts = time.time()
        inc = self.orchestrator.process_lifecycle_event({
            "event_type": "STARTED",
            "violation_id": "V-UUID-1006",
            "violation_type": "UNAUTH_PHONE",
            "timestamp": ts
        })
        assert inc is not None

        ev_ref = EvidenceReference("EV-9001", 50, ts + 1.0, "/evidence/ev_9001.jpg", 0.95)
        success = self.orchestrator.add_evidence_to_incident(inc.incident_id, ev_ref)

        self.assertTrue(success)
        fetched = self.orchestrator.get_incident(inc.incident_id)
        assert fetched is not None
        self.assertEqual(len(fetched.evidence_references), 1)
        self.assertEqual(fetched.evidence_references[0].evidence_id, "EV-9001")
        self.assertTrue(any(e["event_type"] == "EvidenceAttached" for e in fetched.domain_events))

if __name__ == "__main__":
    unittest.main()
