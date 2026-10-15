"""
Unit Test Suite for Incident Intelligence Platform - Package 10.3 (Evidence Intelligence).
Verifies candidate model, deterministic ranking, deduplication, keyframe policy enforcement, clustering, and timeline ordering.
"""
import unittest
import time

from incident_intelligence.evidence import (
    EvidenceCandidate,
    EvidencePolicy,
    EvidenceRanker,
    EvidenceDeduplicator,
    EvidenceClusterer,
    EvidenceTimeline,
    EvidenceSelector
)
from incident_intelligence.domain import EvidenceReference

class TestEvidenceIntelligence(unittest.TestCase):

    def setUp(self):
        self.policy = EvidencePolicy(
            max_evidence_per_incident=5,
            min_keyframe_spacing_seconds=2.0,
            always_retain_start=True,
            always_retain_escalation=True,
            always_retain_resolution=True,
            min_importance_threshold=0.35
        )
        self.ranker = EvidenceRanker()
        self.deduplicator = EvidenceDeduplicator(self.ranker)
        self.clusterer = EvidenceClusterer()
        self.selector = EvidenceSelector(policy=self.policy)

    def test_01_deterministic_ranking(self):
        """Verify higher confidence, sharpness, and transition flags score higher deterministically."""
        ts = time.time()
        c_low = EvidenceCandidate(
            candidate_id="101",
            frame_number=10,
            timestamp=ts,
            confidence=0.40,
            sharpness_score=0.50,
            face_quality=0.50
        )
        c_high = EvidenceCandidate(
            candidate_id="102",
            frame_number=20,
            timestamp=ts + 1.0,
            confidence=0.95,
            sharpness_score=0.90,
            face_quality=0.95,
            is_transition_frame=True,
            state_tag="ESCALATED"
        )

        score_low = self.ranker.calculate_importance(c_low)
        score_high = self.ranker.calculate_importance(c_high)

        self.assertGreater(score_high, score_low, "High-quality transition frame must score higher")
        
        ranked = self.ranker.rank_candidates([c_low, c_high])
        self.assertEqual(ranked[0][0].candidate_id, "102")
        self.assertEqual(ranked[1][0].candidate_id, "101")

    def test_02_evidence_deduplication(self):
        """Verify deduplicator filters candidate frames within temporal spacing window."""
        ts = time.time()
        c1 = EvidenceCandidate("1", 10, ts, confidence=0.90, sharpness_score=0.80)
        c2 = EvidenceCandidate("2", 15, ts + 0.5, confidence=0.85, sharpness_score=0.70)  # Too close (0.5s < 2.0s)
        c3 = EvidenceCandidate("3", 40, ts + 3.0, confidence=0.88, sharpness_score=0.85)  # Far enough (3.0s > 2.0s)

        deduped = self.deduplicator.deduplicate([c1, c2, c3], self.policy)

        cand_ids = [c.candidate_id for c in deduped]
        self.assertIn("1", cand_ids)
        self.assertNotIn("2", cand_ids, "Close candidate should be deduplicated")
        self.assertIn("3", cand_ids)

    def test_03_keyframe_policy_and_mandatory_retention(self):
        """Verify mandatory transition frames (STARTED, ESCALATED, RESOLVED) are retained by policy."""
        ts = time.time()
        c_start = EvidenceCandidate("S", 1, ts, confidence=0.60, is_transition_frame=True, state_tag="STARTED")
        c_mid = EvidenceCandidate("M", 20, ts + 1.0, confidence=0.95, is_transition_frame=False, state_tag="ACTIVE")
        c_esc = EvidenceCandidate("E", 40, ts + 1.5, confidence=0.98, is_transition_frame=True, state_tag="ESCALATED")
        c_res = EvidenceCandidate("R", 80, ts + 5.0, confidence=0.50, is_transition_frame=True, state_tag="RESOLVED")

        refs = self.selector.select_evidence([c_start, c_mid, c_esc, c_res])
        ref_ids = [r.evidence_id for r in refs]

        self.assertIn("EV-S", ref_ids, "STARTED keyframe must be retained")
        self.assertIn("EV-E", ref_ids, "ESCALATED keyframe must be retained")
        self.assertIn("EV-R", ref_ids, "RESOLVED keyframe must be retained")

    def test_04_evidence_clustering(self):
        """Verify candidates are grouped chronologically into lifecycle phase clusters."""
        ts = time.time()
        c_start = EvidenceCandidate("1", 1, ts, confidence=0.80, state_tag="STARTED")
        c_mid = EvidenceCandidate("2", 30, ts + 3.0, confidence=0.85, state_tag="ACTIVE")
        c_esc = EvidenceCandidate("3", 50, ts + 4.0, confidence=0.98, state_tag="ESCALATED")
        c_rec = EvidenceCandidate("4", 70, ts + 6.0, confidence=0.70, state_tag="RECOVERING")
        c_res = EvidenceCandidate("5", 90, ts + 8.0, confidence=0.50, state_tag="RESOLVED")

        clusters = self.clusterer.cluster_evidence([c_start, c_mid, c_esc, c_rec, c_res])

        self.assertEqual(len(clusters["BEGINNING"]), 1)
        self.assertEqual(len(clusters["ESCALATION"]), 1)
        self.assertEqual(len(clusters["RECOVERY"]), 1)
        self.assertEqual(len(clusters["RESOLUTION"]), 1)

    def test_05_evidence_timeline(self):
        """Verify EvidenceTimeline orders selected EvidenceReference objects chronologically."""
        ts = time.time()
        c2 = EvidenceCandidate("2", 30, ts + 4.0, confidence=0.85)
        c1 = EvidenceCandidate("1", 10, ts + 1.0, confidence=0.90)

        timeline = self.selector.build_timeline("INC-2026-TEST", [c2, c1])
        refs = timeline.references

        self.assertEqual(len(refs), 2)
        self.assertLess(refs[0].timestamp, refs[1].timestamp, "Timeline must order references chronologically")
        self.assertEqual(refs[0].evidence_id, "EV-1")
        self.assertEqual(refs[1].evidence_id, "EV-2")

if __name__ == "__main__":
    unittest.main()
