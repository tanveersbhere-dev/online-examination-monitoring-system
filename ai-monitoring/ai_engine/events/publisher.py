import logging
from ai_engine.core.exam_context import ExamContext
from ai_engine.core.enums import EventPriority
from ai_engine.interfaces.event_publisher import EventPublisher
from ai_engine.events.event_bus import EventBus
from ai_engine.events.event import Event

logger = logging.getLogger("ai_engine.events")

class Publisher(EventPublisher):
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._initialized = False
        self._running = False

    def initialize(self) -> None:
        logger.info("Initializing Event Publisher...")
        self._initialized = True

    def start(self) -> None:
        if not self._initialized:
            self.initialize()
        logger.info("Starting Event Publisher...")
        self._running = True

    def process(self, context: ExamContext) -> None:
        """Process exam context events (optional hook for publisher buffering or logs)."""
        pass

    def stop(self) -> None:
        logger.info("Stopping Event Publisher...")
        self._running = False

    def cleanup(self) -> None:
        logger.info("Cleaning up Event Publisher...")
        self._initialized = False

    def publish(self, event: Event, priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publishes an event to the underlying EventBus."""
        if not self._running:
            logger.warning("Attempted to publish event while Publisher is not running.")
        self._event_bus.publish(event, priority)

    def broadcast(self, event: Event, priority: EventPriority = EventPriority.NORMAL) -> None:
        """Broadcasts an event to the underlying EventBus."""
        if not self._running:
            logger.warning("Attempted to broadcast event while Publisher is not running.")
        self._event_bus.broadcast(event, priority)
