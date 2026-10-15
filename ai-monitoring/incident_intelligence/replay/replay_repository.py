"""
InMemoryReplayRepository for Replay Intelligence Engine.
Stores active ReplaySession objects in memory.
"""
from typing import Dict, Any, Optional, List
from incident_intelligence.replay.replay_session import ReplaySession

class InMemoryReplayRepository:
    """In-memory storage adapter for ReplaySession objects."""

    def __init__(self):
        self._sessions: Dict[str, ReplaySession] = {}
        self._incident_map: Dict[str, str] = {}

    def save(self, session: ReplaySession) -> None:
        """Save a replay session."""
        self._sessions[session.session_id] = session
        self._incident_map[session.incident_id] = session.session_id

    def get_by_session_id(self, session_id: str) -> Optional[ReplaySession]:
        """Fetch replay session by session_id."""
        return self._sessions.get(session_id)

    def get_by_incident_id(self, incident_id: str) -> Optional[ReplaySession]:
        """Fetch replay session by incident_id."""
        session_id = self._incident_map.get(incident_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def list_all(self) -> List[ReplaySession]:
        """List all stored replay sessions."""
        return list(self._sessions.values())

    def clear(self) -> None:
        """Clear repository."""
        self._sessions.clear()
        self._incident_map.clear()
