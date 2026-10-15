import time
import numpy as np
from typing import Union, Tuple, Optional

try:
    import cv2
except ImportError:
    # Set cv2 to None to handle systems where opencv is not installed or when mock testing
    cv2 = None

from ai_engine.core.exceptions import CameraError

class Webcam:
    def __init__(self, camera_id: Union[int, str] = 0, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None

    def open(self) -> bool:
        """Opens the camera device in local hardware mode, or returns False in decoupled mode."""
        if cv2 is None:
            # In headless browser-owned media mode, OpenCV capture is bypassed
            return False
        
        if self._cap is not None:
            self.close()

        # If camera_id is a string that represents an integer, convert it
        cam_id = self.camera_id
        if isinstance(cam_id, str):
            try:
                cam_id = int(cam_id)
            except ValueError:
                pass  # Keep as string for video file paths or stream URLs

        try:
            self._cap = cv2.VideoCapture(cam_id)
            if not self._cap or not self._cap.isOpened():
                self._cap = None
                return False

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            return True
        except Exception:
            self._cap = None
            return False

    def close(self) -> None:
        """Releases the camera device."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    def is_opened(self) -> bool:
        """Returns True if the camera device is currently opened."""
        return self._cap is not None and self._cap.isOpened()

    def read(self) -> Optional[Tuple[float, np.ndarray]]:
        """Reads a frame from the camera. Returns (timestamp, frame_image) or None."""
        if not self.is_opened() or self._cap is None:
            return None
        
        try:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                return None
            return time.time(), frame
        except Exception as e:
            # Let the manager handle errors / reconnections
            return None
