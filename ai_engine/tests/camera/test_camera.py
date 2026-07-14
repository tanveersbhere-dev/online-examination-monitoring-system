import unittest
import numpy as np
import time

from ai_engine.camera.frame import Frame
from ai_engine.camera.frame_queue import FrameQueue

class TestCamera(unittest.TestCase):
    def test_frame_properties(self) -> None:
        """Verifies frame initialization properties."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = Frame(
            frame_id=123,
            timestamp=1234567.89,
            original_frame=img,
            rgb_frame=img,
            width=640,
            height=480,
            channels=3,
            fps=29.97,
            camera_id="cam_0"
        )
        self.assertEqual(frame.frame_id, 123)
        self.assertEqual(frame.width, 640)
        self.assertEqual(frame.height, 480)
        self.assertEqual(frame.camera_id, "cam_0")

    def test_frame_queue_drop_policy(self) -> None:
        """Verifies that the oldest frames are dropped when queue is full."""
        queue = FrameQueue(max_size=3)
        img = np.zeros((10, 10, 3), dtype=np.uint8)

        def create_frame(fid: int) -> Frame:
            return Frame(
                frame_id=fid,
                timestamp=time.time(),
                original_frame=img,
                rgb_frame=img,
                width=10,
                height=10,
                channels=3,
                fps=30.0,
                camera_id=0
            )

        # Fill queue
        queue.put(create_frame(1))
        queue.put(create_frame(2))
        queue.put(create_frame(3))

        self.assertEqual(queue.size, 3)
        self.assertEqual(queue.dropped_count, 0)

        # Pushing a 4th frame should drop the 1st frame (oldest)
        dropped = queue.put(create_frame(4))
        self.assertTrue(dropped)
        self.assertEqual(queue.size, 3)
        self.assertEqual(queue.dropped_count, 1)

        # Retrieve frames - should be 2, 3, and 4
        f1 = queue.get(timeout=0.1)
        self.assertIsNotNone(f1)
        self.assertEqual(f1.frame_id, 2)

        f2 = queue.get(timeout=0.1)
        self.assertIsNotNone(f2)
        self.assertEqual(f2.frame_id, 3)

        f3 = queue.get(timeout=0.1)
        self.assertIsNotNone(f3)
        self.assertEqual(f3.frame_id, 4)

        # Queue is empty now
        self.assertIsNone(queue.get(timeout=0.01))

    def test_frame_new_properties(self) -> None:
        """Verifies that frame captures optional timestamps and latency."""
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        frame = Frame(
            frame_id=1,
            timestamp=100.0,
            original_frame=img,
            rgb_frame=img,
            width=10,
            height=10,
            channels=3,
            fps=30.0,
            camera_id=0,
            capture_timestamp=100.1,
            processing_timestamp=100.2,
            processing_latency=0.1
        )
        self.assertEqual(frame.capture_timestamp, 100.1)
        self.assertEqual(frame.processing_timestamp, 100.2)
        self.assertEqual(frame.processing_latency, 0.1)

        # Check default values
        frame_default = Frame(
            frame_id=2,
            timestamp=200.0,
            original_frame=img,
            rgb_frame=img,
            width=10,
            height=10,
            channels=3,
            fps=30.0,
            camera_id=0
        )
        self.assertIsNone(frame_default.capture_timestamp)
        self.assertIsNone(frame_default.processing_timestamp)
        self.assertIsNone(frame_default.processing_latency)

    def test_camera_manager_health(self) -> None:
        """Verifies CameraManager.health() diagnostics output."""
        from ai_engine.camera.camera_manager import CameraManager, CameraHealth
        manager = CameraManager(camera_id="test_cam")
        manager.initialize()
        
        # Check initial health state before starting
        h = manager.health()
        self.assertIsInstance(h, CameraHealth)
        self.assertFalse(h.camera_connected)
        self.assertFalse(h.camera_running)
        self.assertEqual(h.dropped_frames, 0)
        self.assertEqual(h.uptime, 0.0)
        self.assertEqual(h.last_frame_timestamp, 0.0)

