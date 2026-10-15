"""
Temporal Consistency Analyzer tracking stability across recent frame windows.
"""
import time
import logging
import collections
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

logger = logging.getLogger("ai_engine.identity_protection.temporal")

try:
    import numpy as np
except ImportError:
    np = None

@dataclass
class TemporalConsistencyResult:
    """
    Measurement result from Temporal Consistency Analysis.
    """
    liveness_trend_score: float = 1.0        # Stability of liveness score over recent window
    landmark_continuity_score: float = 1.0  # Smooth movement without artificial jumps
    motion_continuity_score: float = 1.0
    confidence: float = 1.0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class TemporalConsistencyAnalyzer:
    """
    Tracks rolling liveness and motion metrics over recent frames (max window = 10 frames).
    Maintains a small, lightweight in-memory deque with zero long-term storage.
    """

    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._liveness_history = collections.deque(maxlen=window_size)
        self._bbox_history = collections.deque(maxlen=window_size)

    def process(self, liveness_score: float, face_bbox: Optional[Any] = None) -> TemporalConsistencyResult:
        """
        Evaluates liveness score trend and bounding box displacement continuity across rolling history.
        """
        start_time = time.perf_counter()

        self._liveness_history.append(liveness_score)
        
        # Bounding box center extraction
        center = None
        if face_bbox is not None:
            if isinstance(face_bbox, (tuple, list)) and len(face_bbox) == 4:
                center = (face_bbox[0] + face_bbox[2] / 2.0, face_bbox[1] + face_bbox[3] / 2.0)
            elif hasattr(face_bbox, "x") and hasattr(face_bbox, "width"):
                center = (
                    getattr(face_bbox, "x", 0) + getattr(face_bbox, "width", 0) / 2.0,
                    getattr(face_bbox, "y", 0) + getattr(face_bbox, "height", 0) / 2.0
                )
        
        if center is not None:
            self._bbox_history.append(center)

        if len(self._liveness_history) < 2 or np is None:
            return TemporalConsistencyResult(
                liveness_trend_score=1.0,
                landmark_continuity_score=1.0,
                motion_continuity_score=1.0,
                confidence=0.5,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                metadata={"history_length": len(self._liveness_history)}
            )

        try:
            # Liveness score trend stability (1.0 - standard deviation of scores)
            scores_array = np.array(self._liveness_history, dtype=np.float32)
            std_liveness = float(np.std(scores_array))
            mean_liveness = float(np.mean(scores_array))
            liveness_trend_score = float(np.clip(mean_liveness - std_liveness, 0.0, 1.0))

            # Bounding box motion displacement continuity
            motion_continuity = 1.0
            if len(self._bbox_history) >= 2:
                centers = np.array(self._bbox_history, dtype=np.float32)
                displacements = np.linalg.norm(np.diff(centers, axis=0), axis=1)
                max_disp = float(np.max(displacements))
                # Unnatural sudden frame jumps (>150px displacement) lower motion continuity score
                if max_disp > 150.0:
                    motion_continuity = float(np.clip(1.0 - (max_disp - 150.0) / 200.0, 0.0, 1.0))

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return TemporalConsistencyResult(
                liveness_trend_score=round(liveness_trend_score, 4),
                landmark_continuity_score=round(motion_continuity, 4),
                motion_continuity_score=round(motion_continuity, 4),
                confidence=0.90,
                latency_ms=round(elapsed_ms, 2),
                metadata={
                    "window_size": len(self._liveness_history),
                    "score_std": round(std_liveness, 4),
                    "mean_liveness": round(mean_liveness, 4)
                }
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Error in TemporalConsistencyAnalyzer: {e}")
            return TemporalConsistencyResult(
                liveness_trend_score=1.0,
                landmark_continuity_score=1.0,
                motion_continuity_score=1.0,
                confidence=0.5,
                latency_ms=round(elapsed_ms, 2),
                metadata={"error": str(e)}
            )
