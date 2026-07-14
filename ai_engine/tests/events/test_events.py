import unittest
import time
from typing import List

from ai_engine.core.enums import EventType, Severity, EventPriority
from ai_engine.events.event import Event
from ai_engine.events.event_bus import EventBus
from ai_engine.events.publisher import Publisher
from ai_engine.events.subscriber import Subscriber

class TestEvents(unittest.TestCase):
    def test_event_dataclass(self) -> None:
        """Verifies event creation and its properties."""
        event = Event(
            event_id="evt_101",
            event_type=EventType.TALKING_DETECTED,
            timestamp=123.456,
            severity=Severity.HIGH,
            source_module="audio_vad",
            confidence=0.85,
            payload={"dB": -12.4},
            frame_id=987,
            session_id="sess_1",
            student_id="std_1"
        )
        self.assertEqual(event.event_id, "evt_101")
        self.assertEqual(event.event_type, EventType.TALKING_DETECTED)
        self.assertEqual(event.payload["dB"], -12.4)

    def test_event_bus_sync_dispatch(self) -> None:
        """Verifies that events are delivered synchronously to subscribers when async_dispatch is False."""
        bus = EventBus(async_dispatch=False)
        received_events: List[Event] = []

        def callback(event: Event) -> None:
            received_events.append(event)

        # Wildcard subscription
        bus.subscribe(None, callback)

        event = Event("e1", EventType.SYSTEM_INFO, time.time(), Severity.INFO, "test", 1.0)
        bus.publish(event)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_id, "e1")

        # Unsubscribe and check
        bus.unsubscribe(None, callback)
        bus.publish(event)
        self.assertEqual(len(received_events), 1)

    def test_event_bus_priority_queueing(self) -> None:
        """Ensures that the EventBus priority queue correctly sorts pending events based on Priority level."""
        bus = EventBus(async_dispatch=True, queue_size=10)
        
        event_low = Event("1", EventType.SYSTEM_INFO, time.time(), Severity.INFO, "src", 1.0)
        event_high = Event("2", EventType.DEVICE_TAMPERING, time.time(), Severity.HIGH, "src", 1.0)
        event_crit = Event("3", EventType.FACE_ABSENT, time.time(), Severity.CRITICAL, "src", 1.0)
        event_normal = Event("4", EventType.TALKING_DETECTED, time.time(), Severity.MEDIUM, "src", 1.0)
        
        # Publish in non-sorted order (without starting the worker thread)
        bus.publish(event_low, EventPriority.LOW)
        bus.publish(event_crit, EventPriority.CRITICAL)
        bus.publish(event_normal, EventPriority.NORMAL)
        bus.publish(event_high, EventPriority.HIGH)
        
        # Retrieve raw items from queue to test ordering directly
        # Format in queue: (-priority.value, counter, event, is_broadcast)
        item1 = bus._queue.get()
        self.assertEqual(item1[2].event_id, "3")  # CRITICAL (highest priority)
        
        item2 = bus._queue.get()
        self.assertEqual(item2[2].event_id, "2")  # HIGH
        
        item3 = bus._queue.get()
        self.assertEqual(item3[2].event_id, "4")  # NORMAL
        
        item4 = bus._queue.get()
        self.assertEqual(item4[2].event_id, "1")  # LOW (lowest priority)

    def test_event_correlation_id(self) -> None:
        """Verifies event creation with correlation_id."""
        event_with_corr = Event(
            event_id="e1",
            event_type=EventType.SYSTEM_INFO,
            timestamp=time.time(),
            severity=Severity.INFO,
            source_module="test",
            confidence=1.0,
            correlation_id="corr_999"
        )
        self.assertEqual(event_with_corr.correlation_id, "corr_999")
        
        event_without_corr = Event(
            event_id="e2",
            event_type=EventType.SYSTEM_INFO,
            timestamp=time.time(),
            severity=Severity.INFO,
            source_module="test",
            confidence=1.0
        )
        self.assertIsNone(event_without_corr.correlation_id)

