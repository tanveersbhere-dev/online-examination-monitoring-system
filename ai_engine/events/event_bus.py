import queue
import logging
import threading
from typing import Dict, List, Optional, Tuple

from ai_engine.core.enums import EventType, EventPriority
from ai_engine.core.types import EventCallback
from ai_engine.events.event import Event

logger = logging.getLogger("ai_engine.events")

class EventBus:
    def __init__(self, async_dispatch: bool = True, queue_size: int = 100) -> None:
        self._async_dispatch = async_dispatch
        self._subscribers: Dict[Optional[EventType], List[EventCallback]] = {}
        self._global_subscribers: List[EventCallback] = []
        self._lock = threading.RLock()
        
        # Priority Queue for async dispatch
        # Items are: (-priority_value, sequence_number, event, is_broadcast)
        self._queue = queue.PriorityQueue(maxsize=queue_size)
        self._counter = 0
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def subscribe(self, event_type: Optional[EventType], callback: EventCallback) -> None:
        """Subscribes a callback to a specific EventType, or to all events if event_type is None."""
        with self._lock:
            if event_type is None:
                if callback not in self._global_subscribers:
                    self._global_subscribers.append(callback)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                if callback not in self._subscribers[event_type]:
                    self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed callback to EventType: {event_type}")

    def unsubscribe(self, event_type: Optional[EventType], callback: EventCallback) -> None:
        """Unsubscribes a callback from an EventType."""
        with self._lock:
            if event_type is None:
                if callback in self._global_subscribers:
                    self._global_subscribers.remove(callback)
            else:
                if event_type in self._subscribers and callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed callback from EventType: {event_type}")

    def start(self) -> None:
        """Starts the asynchronous event dispatch thread if enabled."""
        if not self._async_dispatch:
            return
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(target=self._dispatch_loop, name="EventBusWorkerThread", daemon=True)
            self._worker_thread.start()
            logger.info("Event Bus async worker thread started.")

    def stop(self) -> None:
        """Stops the asynchronous event dispatch thread."""
        if not self._async_dispatch:
            return
        with self._lock:
            if not self._running:
                return
            self._running = False
            # Push poison pill to unblock the queue
            # (highest priority to stop immediately, i.e., -9999)
            self._queue.put((-9999, 0, None, False))
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=3.0)
            self._worker_thread = None
        logger.info("Event Bus async worker thread stopped.")

    def publish(self, event: Event, priority: EventPriority = EventPriority.NORMAL) -> None:
        """Publishes an event to the bus. Routes asynchronously or synchronously."""
        if self._async_dispatch:
            with self._lock:
                self._counter += 1
                cnt = self._counter
            try:
                # -priority.value because higher priority should be popped first
                self._queue.put_nowait((-priority.value, cnt, event, False))
            except queue.Full:
                logger.error("Event Bus queue is full! Dropping event.")
        else:
            self._dispatch_event(event, is_broadcast=False)

    def broadcast(self, event: Event, priority: EventPriority = EventPriority.NORMAL) -> None:
        """Broadcasts an event to all subscribers regardless of their specific type subscription."""
        if self._async_dispatch:
            with self._lock:
                self._counter += 1
                cnt = self._counter
            try:
                self._queue.put_nowait((-priority.value, cnt, event, True))
            except queue.Full:
                logger.error("Event Bus queue is full! Dropping broadcast event.")
        else:
            self._dispatch_event(event, is_broadcast=True)

    def _dispatch_event(self, event: Event, is_broadcast: bool) -> None:
        callbacks_to_invoke = []
        with self._lock:
            # Always invoke global subscribers
            callbacks_to_invoke.extend(self._global_subscribers)
            
            if is_broadcast:
                # Invoke everyone else as well
                for cb_list in self._subscribers.values():
                    for cb in cb_list:
                        if cb not in callbacks_to_invoke:
                            callbacks_to_invoke.append(cb)
            else:
                # Invoke specific subscribers for this type
                if event.event_type in self._subscribers:
                    for cb in self._subscribers[event.event_type]:
                        if cb not in callbacks_to_invoke:
                            callbacks_to_invoke.append(cb)

        for callback in callbacks_to_invoke:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}", exc_info=True)

    def _dispatch_loop(self) -> None:
        while self._running:
            try:
                _, _, event, is_broadcast = self._queue.get()
                if event is None:  # Poison pill
                    break
                self._dispatch_event(event, is_broadcast)
            except Exception as e:
                logger.error(f"Error in Event Bus dispatch loop: {e}", exc_info=True)
