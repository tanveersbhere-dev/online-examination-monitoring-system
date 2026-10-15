import time
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Union, Optional

@dataclass
class Frame:
    frame_id: int
    timestamp: float
    original_frame: np.ndarray
    rgb_frame: np.ndarray
    width: int
    height: int
    channels: int
    fps: float
    camera_id: Union[int, str]
    capture_timestamp: Optional[float] = None
    processing_timestamp: Optional[float] = None
    processing_latency: Optional[float] = None

    @classmethod
    def from_bgr_image(
        cls,
        bgr_image: np.ndarray,
        camera_id: Union[int, str] = "webrtc",
        fps: float = 30.0,
        frame_id: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> "Frame":
        """
        Authoritative factory method to construct a complete Frame instance from a BGR OpenCV image array.
        Derives width, height, channels, rgb_frame, timestamp, and frame_id if not explicitly provided.
        """
        if bgr_image is None or not isinstance(bgr_image, np.ndarray):
            raise ValueError("bgr_image must be a valid non-null numpy.ndarray")

        if bgr_image.ndim == 3:
            height, width, channels = bgr_image.shape
            rgb_frame = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        elif bgr_image.ndim == 2:
            height, width = bgr_image.shape
            channels = 1
            rgb_frame = cv2.cvtColor(bgr_image, cv2.COLOR_GRAY2RGB)
        else:
            raise ValueError(f"Unsupported image dimensions: {bgr_image.shape}")

        ts = timestamp if timestamp is not None else time.time()
        fid = frame_id if frame_id is not None else int(ts * 1000)

        return cls(
            frame_id=fid,
            timestamp=ts,
            original_frame=bgr_image,
            rgb_frame=rgb_frame,
            width=width,
            height=height,
            channels=channels,
            fps=fps,
            camera_id=camera_id
        )


