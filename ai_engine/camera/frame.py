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

