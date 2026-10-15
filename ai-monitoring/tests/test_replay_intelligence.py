"""
Unit Test Suite for Incident Intelligence Platform - Package 10.8 (Replay Intelligence Engine).
Verifies frame index lookup, bookmark management, timeline navigation, evidence navigation, overlay metadata, and repository persistence.
"""
import unittest
import time

from incident_intelligence.domain import (
    Incident,
    EvidenceReference
)
from incident_intelligence.timeline import TimelineEvent
from incident_intelligence.replay import (
    FrameIndexEntry,
    FrameIndex,
    TimelineNavigator,
    EvidenceNavigator,
    ReplayBookmark,
    BookmarkManager,
    ReplayOverlayMetadata,
    ReplayOverlayGenerator,
    ReplaySession,
    ReplaySessionDTO,
    InMemoryReplayRepository
)

class TestReplayIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryReplayRepository()
        self.timeline_navigator = TimelineNavigator()
        self.evidence_navigator = EvidenceNavigator()
        self.overlay_generator = ReplayOverlayGenerator()

    def test_01_frame_index_lookup(self):
        """Verify deterministic frame lookup by frame number, timestamp, timeline ID, and evidence ID."""
        ts = time.time()
        index = FrameIndex()

        e1 = FrameIndexEntry(1, ts, "INC-2026-RP01", "TLE-1", "EV-1")
        e2 = FrameIndexEntry(30, ts + 1.0, "INC-2026-RP01", "TLE-2", None)
        e3 = FrameIndexEntry(60, ts + 2.0, "INC-2026-RP01", "TLE-3", "EV-2")

        index.add_entry(e1)
        index.add_entry(e2)
        index.add_entry(e3)

        self.assertEqual(index.get_by_frame(30).timestamp, ts + 1.0)
        self.assertEqual(index.get_nearest_by_timestamp(ts + 0.9).frame_number, 30)
        self.assertEqual(index.get_by_timeline_event("TLE-3").frame_number, 60)
        self.assertEqual(index.get_by_evidence_ref("EV-1").frame_number, 1)

    def test_02_bookmark_management(self):
        """Verify immutable ReplayBookmark entries can be created, retrieved, and filtered."""
        ts = time.time()
        bm_mgr = BookmarkManager()

        b1 = ReplayBookmark("BM-1", ts, 10, "TIMELINE_EVENT", "TLE-101", "Incident Started")
        b2 = ReplayBookmark("BM-2", ts + 2.0, 60, "EVIDENCE", "EV-201", "Peak Keyframe")

        bm_mgr.add_bookmark(b1)
        bm_mgr.add_bookmark(b2)

        self.assertEqual(len(bm_mgr.list_all()), 2)
        self.assertEqual(bm_mgr.get_by_id("BM-2").label, "Peak Keyframe")
        self.assertEqual(len(bm_mgr.get_by_target_type("EVIDENCE")), 1)

    def test_03_timeline_navigation(self):
        """Verify TimelineNavigator seeks ReplaySession to incident milestones."""
        ts = time.time()
        session = ReplaySession("SESS-01", "INC-2026-RP03", 1, ts)

        # Build FrameIndex entries
        for f in range(1, 100):
            session.frame_index.add_entry(FrameIndexEntry(f, ts + (f * 0.1), "INC-2026-RP03"))

        timeline_events = [
            TimelineEvent("TLE-1", "INC-2026-RP03", ts + 0.1, "INCIDENT_CREATED", 1),
            TimelineEvent("TLE-2", "INC-2026-RP03", ts + 2.0, "STATE_CHANGED", 2, new_state="ESCALATED"),
            TimelineEvent("TLE-3", "INC-2026-RP03", ts + 3.0, "CONFIDENCE_UPDATED", 3, confidence=0.98),
            TimelineEvent("TLE-4", "INC-2026-RP03", ts + 5.0, "STATE_CHANGED", 4, new_state="RECOVERING"),
            TimelineEvent("TLE-5", "INC-2026-RP03", ts + 8.0, "RESOLVED", 5)
        ]

        # Jump to start
        entry = self.timeline_navigator.jump_to_incident_start(session, timeline_events)
        self.assertIsNotNone(entry)
        self.assertEqual(session.current_frame_number, 1)

        # Jump to escalation
        entry = self.timeline_navigator.jump_to_escalation(session, timeline_events)
        self.assertEqual(session.current_frame_number, 20)

        # Jump to peak confidence
        entry = self.timeline_navigator.jump_to_peak_confidence(session, timeline_events)
        self.assertEqual(session.current_frame_number, 30)

        # Jump to recovery
        entry = self.timeline_navigator.jump_to_recovery(session, timeline_events)
        self.assertEqual(session.current_frame_number, 50)

        # Jump to resolution
        entry = self.timeline_navigator.jump_to_resolution(session, timeline_events)
        self.assertEqual(session.current_frame_number, 80)

    def test_04_evidence_navigation(self):
        """Verify EvidenceNavigator seeks ReplaySession to next/prev/highest-ranked keyframes."""
        ts = time.time()
        session = ReplaySession("SESS-02", "INC-2026-RP04", 1, ts)

        for f in range(1, 100):
            session.frame_index.add_entry(FrameIndexEntry(f, ts + (f * 0.1), "INC-2026-RP04"))

        evidence_list = [
            EvidenceReference("EV-1", 10, ts + 1.0, "/ev/1.jpg", 0.60, crop_type="FULL_FRAME"),
            EvidenceReference("EV-2", 40, ts + 4.0, "/ev/2.jpg", 0.95, crop_type="FACE_CROP"),
            EvidenceReference("EV-3", 70, ts + 7.0, "/ev/3.jpg", 0.80, crop_type="FACE_CROP")
        ]

        # Seek session to ts + 2.0 (frame 20)
        session.seek_to_timestamp(ts + 2.0)

        # Next keyframe -> EV-2 at ts + 4.0
        next_e = self.evidence_navigator.next_keyframe(session, evidence_list)
        self.assertEqual(session.current_frame_number, 40)

        # Prev keyframe -> EV-1 at ts + 1.0
        prev_e = self.evidence_navigator.previous_keyframe(session, evidence_list)
        self.assertEqual(session.current_frame_number, 10)

        # Highest-ranked keyframe -> EV-2
        high_e = self.evidence_navigator.highest_ranked_keyframe(session, evidence_list)
        self.assertEqual(session.current_frame_number, 40)

        # Cluster keyframes by crop_type
        face_crops = self.evidence_navigator.evidence_cluster_keyframes(session, evidence_list, "FACE_CROP")
        self.assertEqual(len(face_crops), 2)

    def test_05_overlay_metadata_generation(self):
        """Verify ReplayOverlayGenerator constructs read-only overlay metadata without modifying frames."""
        ts = time.time()
        incident = Incident(incident_id="INC-2026-RP05", episode_id="V-UUID-RP05", incident_type="UNAUTH_PHONE", start_time=ts, current_confidence=0.91)
        entry = FrameIndexEntry(15, ts + 1.5, "INC-2026-RP05", "TLE-15")

        overlay = self.overlay_generator.generate_overlay(
            incident,
            entry,
            face_box=[100, 100, 250, 300],
            detected_objects=[{"label": "cell phone", "box": [120, 150, 180, 220]}]
        )

        self.assertIsInstance(overlay, ReplayOverlayMetadata)
        self.assertEqual(overlay.frame_number, 15)
        self.assertEqual(overlay.face_box, [100, 100, 250, 300])
        self.assertEqual(overlay.object_labels, ["cell phone"])
        self.assertEqual(overlay.confidence, 0.91)

    def test_06_replay_session_and_repository(self):
        """Verify ReplaySession serialization and repository persistence."""
        ts = time.time()
        session = ReplaySession("SESS-100", "INC-2026-RP06", 1, ts)
        session.add_bookmark(ReplayBookmark("BM-1", ts, 1, "TIMELINE_EVENT", "TLE-1", "Start"))

        self.repository.save(session)
        fetched = self.repository.get_by_session_id("SESS-100")
        self.assertIsNotNone(fetched)
        assert fetched is not None

        dto = fetched.to_dto()
        self.assertIsInstance(dto, ReplaySessionDTO)
        dto_dict = dto.to_dict()

        self.assertEqual(dto_dict["session_id"], "SESS-100")
        self.assertEqual(len(dto_dict["bookmarks"]), 1)

if __name__ == "__main__":
    unittest.main()
