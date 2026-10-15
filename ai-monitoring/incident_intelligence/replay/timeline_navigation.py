"""
TimelineNavigator for Replay Intelligence Engine.
Provides deterministic jump navigation based on canonical timeline milestones.
"""
from typing import Optional, List
from incident_intelligence.timeline.timeline_event import TimelineEvent
from incident_intelligence.replay.replay_session import ReplaySession
from incident_intelligence.replay.frame_index import FrameIndexEntry

class TimelineNavigator:
    """Navigation service seeking ReplaySession to timeline milestone events."""

    def jump_to_incident_start(
        self,
        session: ReplaySession,
        timeline_events: List[TimelineEvent]
    ) -> Optional[FrameIndexEntry]:
        """Jump to initial INCIDENT_CREATED timeline event."""
        start_events = [e for e in timeline_events if e.event_type == "INCIDENT_CREATED"]
        if start_events:
            return session.seek_to_timestamp(start_events[0].timestamp)
        elif timeline_events:
            return session.seek_to_timestamp(timeline_events[0].timestamp)
        return None

    def jump_to_escalation(
        self,
        session: ReplaySession,
        timeline_events: List[TimelineEvent]
    ) -> Optional[FrameIndexEntry]:
        """Jump to first ESCALATED state transition event."""
        esc_events = [e for e in timeline_events if e.event_type == "STATE_CHANGED" and e.new_state == "ESCALATED"]
        if esc_events:
            return session.seek_to_timestamp(esc_events[0].timestamp)
        return None

    def jump_to_peak_confidence(
        self,
        session: ReplaySession,
        timeline_events: List[TimelineEvent]
    ) -> Optional[FrameIndexEntry]:
        """Jump to timeline event with peak confidence value."""
        conf_events = [e for e in timeline_events if e.confidence is not None]
        if conf_events:
            peak_ev = max(conf_events, key=lambda e: e.confidence)
            return session.seek_to_timestamp(peak_ev.timestamp)
        return None

    def jump_to_recovery(
        self,
        session: ReplaySession,
        timeline_events: List[TimelineEvent]
    ) -> Optional[FrameIndexEntry]:
        """Jump to first RECOVERING state transition event."""
        rec_events = [e for e in timeline_events if e.event_type == "STATE_CHANGED" and e.new_state == "RECOVERING"]
        if rec_events:
            return session.seek_to_timestamp(rec_events[0].timestamp)
        return None

    def jump_to_resolution(
        self,
        session: ReplaySession,
        timeline_events: List[TimelineEvent]
    ) -> Optional[FrameIndexEntry]:
        """Jump to final RESOLVED timeline event."""
        res_events = [e for e in timeline_events if e.event_type == "RESOLVED"]
        if res_events:
            return session.seek_to_timestamp(res_events[-1].timestamp)
        return None
