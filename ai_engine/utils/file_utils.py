import logging
from pathlib import Path
from typing import Union

try:
    import cv2
except ImportError:
    cv2 = None

from ai_engine.camera.frame import Frame

logger = logging.getLogger("ai_engine.utils")

def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """Ensures a directory exists, creating all parent directories if necessary."""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_frame_to_disk(frame: Frame, output_path: Union[str, Path]) -> bool:
    """Saves a Frame's original image (BGR) to disk."""
    if cv2 is None:
        logger.error("OpenCV is not available. Cannot save frame to disk.")
        return False
    
    path = Path(output_path)
    ensure_dir(path.parent)
    try:
        # cv2.imwrite writes BGR images, which matches the original_frame format
        success = cv2.imwrite(str(path), frame.original_frame)
        return bool(success)
    except Exception as e:
        logger.error(f"Failed to save frame image to {path}: {e}")
        return False
