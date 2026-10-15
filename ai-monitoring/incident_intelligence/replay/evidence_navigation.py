"""
EvidenceNavigator for Replay Intelligence Engine.
Provides keyframe and evidence cluster navigation.
"""
from typing import Optional, List
from incident_intelligence.domain.evidence_reference import EvidenceReference
from incident_intelligence.replay.replay_session import ReplaySession
from incident_intelligence.replay.frame_index import FrameIndexEntry

class EvidenceNavigator:
    """Navigation service seeking ReplaySession between evidence keyframe targets."""

    def next_keyframe(
        self,
        session: ReplaySession,
        evidence_list: List[EvidenceReference]
    ) -> Optional[FrameIndexEntry]:
        """Navigate to next keyframe after current timestamp."""
        sorted_ev = sorted(evidence_list, key=lambda e: e.timestamp)
        future_ev = [e for e in sorted_ev if e.timestamp > session.current_timestamp]
        if future_ev:
            return session.seek_to_timestamp(future_ev[0].timestamp)
        return None

    def previous_keyframe(
        self,
        session: ReplaySession,
        evidence_list: List[EvidenceReference]
    ) -> Optional[FrameIndexEntry]:
        """Navigate to previous keyframe before current timestamp."""
        sorted_ev = sorted(evidence_list, key=lambda e: e.timestamp, reverse=True)
        past_ev = [e for e in sorted_ev if e.timestamp < session.current_timestamp]
        if past_ev:
            return session.seek_to_timestamp(past_ev[0].timestamp)
        return None

    def highest_ranked_keyframe(
        self,
        session: ReplaySession,
        evidence_list: List[EvidenceReference]
    ) -> Optional[FrameIndexEntry]:
        """Navigate to keyframe with highest importance score."""
        if not evidence_list:
            return None
        best_ev = max(evidence_list, key=lambda e: e.importance)
        return session.seek_to_timestamp(best_ev.timestamp)

    def evidence_cluster_keyframes(
        self,
        session: ReplaySession,
        evidence_list: List[EvidenceReference],
        crop_type: str
    ) -> List[FrameIndexEntry]:
        """Filter keyframe entries by crop_type category."""
        matching = [e for e in evidence_list if e.crop_type == crop_type]
        results = []
        for ev in matching:
            entry = session.frame_index.get_nearest_by_timestamp(ev.timestamp)
            if entry:
                results.append(entry)
        return results
