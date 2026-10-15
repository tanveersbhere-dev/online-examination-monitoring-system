import unittest
import time

from ai_engine.utils.timer import Timer, time_function
from ai_engine.utils.fps import FPSTracker
from ai_engine.utils.helpers import parse_resolution, generate_uuid, get_current_timestamp

class TestUtils(unittest.TestCase):
    def test_timer_context_manager(self) -> None:
        """Verifies that Timer accurately captures code execution duration."""
        with Timer("Test Block") as t:
            time.sleep(0.02)
        self.assertIsNotNone(t.elapsed)
        self.assertGreaterEqual(t.elapsed, 0.015)

    def test_fps_tracker(self) -> None:
        """Verifies FPSTracker roll rate calculation."""
        tracker = FPSTracker(window_size=5)
        self.assertEqual(tracker.get_fps(), 0.0)

        tracker.update()
        time.sleep(0.01)
        tracker.update()

        fps = tracker.get_fps()
        self.assertGreater(fps, 0.0)

    def test_helpers(self) -> None:
        """Verifies helper utilities for parsing resolution and UUID/timestamp generations."""
        # Resolution parsing
        w, h = parse_resolution("1280x720")
        self.assertEqual(w, 1280)
        self.assertEqual(h, 720)

        with self.assertRaises(ValueError):
            parse_resolution("1280_720")

        # UUID generation
        uid = generate_uuid()
        self.assertEqual(len(uid), 36)

        # Timestamp generation
        ts = get_current_timestamp()
        self.assertGreater(ts, 0.0)
