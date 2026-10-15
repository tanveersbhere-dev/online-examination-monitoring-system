import logging
from typing import Optional

from ai_engine.core.enums import EventType
from ai_engine.core.types import EventCallback
from ai_engine.events.event_bus import EventBus

logger = logging.getLogger("ai_engine.events")

class Subscriber:
    def __init__(self, event_bus: EventBus, callback: EventCallback, event_type: Optional[EventType] = None) -> None:
        self._event_bus = event_bus
        self._callback = callback
        self._event_type = event_type
        self._subscribed = False

    def subscribe(self) -> None:
        """Registers this subscriber callback with the EventBus."""
        if not self._subscribed:
            self._event_bus.subscribe(self._event_type, self._callback)
            self._subscribed = True

    def unsubscribe(self) -> None:
        """Unregisters this subscriber callback from the EventBus."""
        if self._subscribed:
            self._event_bus.unsubscribe(self._event_type, self._callback)
            self._subscribed = False

    @property
    def is_subscribed(self) -> bool:
        return self._subscribed
