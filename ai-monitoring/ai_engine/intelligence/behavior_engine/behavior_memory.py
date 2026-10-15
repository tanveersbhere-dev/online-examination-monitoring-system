"""
Bounded 60-Second Rolling Behavior Memory for Behavioral Intelligence Engine.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from ai_engine.intelligence.behavior_engine.behavior_event import BehaviorMemoryEntry

logger = logging.getLogger("ai_engine.behavior.memory")

class BehaviorMemory:
    """
    In-memory rolling buffer retaining atomic event entries for up to window_seconds (default: 60s).
    """
    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds: float = window_seconds
        self._entries: List[BehaviorMemoryEntry] = []

    def add_entry(self, entry: BehaviorMemoryEntry) -> None:
        self._entries.append(entry)
        self.prune_expired(entry.timestamp)

    def prune_expired(self, current_timestamp: float) -> None:
        cutoff = current_timestamp - self.window_seconds
        self._entries = [e for e in self._entries if e.timestamp >= cutoff]

    def get_recent(self, within_seconds: float = 60.0, current_timestamp: Optional[float] = None) -> List[BehaviorMemoryEntry]:
        ts = current_timestamp if current_timestamp is not None else time.time()
        cutoff = ts - within_seconds
        return [e for e in self._entries if e.timestamp >= cutoff]

    def get_entries_by_rule(self, rule_name: str, within_seconds: float = 60.0, current_timestamp: Optional[float] = None) -> List[BehaviorMemoryEntry]:
        recent = self.get_recent(within_seconds, current_timestamp)
        return [e for e in recent if e.rule_name == rule_name or rule_name in e.rule_name]

    def get_entries_by_object(self, object_type: str, within_seconds: float = 60.0, current_timestamp: Optional[float] = None) -> List[BehaviorMemoryEntry]:
        recent = self.get_recent(within_seconds, current_timestamp)
        return [e for e in recent if e.object_type == object_type]

    def clear(self) -> None:
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)
