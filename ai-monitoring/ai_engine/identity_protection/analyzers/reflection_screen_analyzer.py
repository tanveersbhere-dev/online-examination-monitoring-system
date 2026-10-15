"""
Reflection and Screen Analyzer evaluating Moiré high-frequency screen grid energy and specular reflection artifacts.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Dict

logger = logging.getLogger("ai_engine.identity_protection.reflection_screen")

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

@dataclass
class ReflectionAnalysisResult:
    """
    Measurement result from Reflection & Screen Analysis.
    """
    moire_pattern_score: float = 0.0      # [0.0 - 1.0] High energy indicates screen grid Moiré pattern
    specular_reflection_score: float = 0.0 # [0.0 - 1.0] High energy indicates screen glare artifacts
    screen_edge_score: float = 0.0
    confidence: float = 1.0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ReflectionScreenAnalyzer:
    """
    Analyzes face crop for presentation attack artifacts (screen Moiré patterns & specular reflections).
    Produces raw measurements without classifying attacks directly.
    """

    def process(self, frame_bgr: Any, face_bbox: Optional[Any] = None) -> ReflectionAnalysisResult:
        """
        Evaluates 2D FFT Moiré high-frequency spectral grid energy and specular reflection brightness.
        """
        start_time = time.perf_counter()

        if frame_bgr is None or cv2 is None or np is None:
            return ReflectionAnalysisResult(
                moire_pattern_score=0.0,
                specular_reflection_score=0.0,
                screen_edge_score=0.0,
                confidence=0.5,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                metadata={"reason": "Frame is empty or OpenCV/NumPy unavailable"}
            )

        try:
            h_img, w_img = frame_bgr.shape[:2]

            # Extract face crop
            if face_bbox is not None:
                if isinstance(face_bbox, (tuple, list)) and len(face_bbox) == 4:
                    x, y, w, h = [int(v) for v in face_bbox]
                elif hasattr(face_bbox, "x") and hasattr(face_bbox, "width"):
                    x = int(getattr(face_bbox, "x", 0))
                    y = int(getattr(face_bbox, "y", 0))
                    w = int(getattr(face_bbox, "width", w_img))
                    h = int(getattr(face_bbox, "height", h_img))
                else:
                    x, y, w, h = 0, 0, w_img, h_img
                
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(w_img, x + w), min(h_img, y + h)
                crop = frame_bgr[y1:y2, x1:x2]
            else:
                crop = frame_bgr

            if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
                return ReflectionAnalysisResult(
                    moire_pattern_score=0.0,
                    specular_reflection_score=0.0,
                    screen_edge_score=0.0,
                    confidence=0.5,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    metadata={"reason": "Crop too small"}
                )

            # Convert to grayscale
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

            # 1. Moiré Pattern Analysis using 2D Fast Fourier Transform (FFT)
            # High-frequency periodic screen grid lines produce concentrated high-frequency spectral energy.
            fft = np.fft.fft2(gray)
            fft_shift = np.fft.fftshift(fft)
            magnitude_spectrum = 20 * np.log(np.abs(fft_shift) + 1e-5)

            # High-frequency outer ring energy ratio
            h, w = gray.shape
            cy, cx = h // 2, w // 2
            r = min(h, w) // 4
            
            # Mask out DC low-frequency components at center
            high_freq_spectrum = magnitude_spectrum.copy()
            high_freq_spectrum[max(0, cy - r):min(h, cy + r), max(0, cx - r):min(w, cx + r)] = 0
            
            high_freq_energy = float(np.mean(high_freq_spectrum))
            # Normalize Moiré pattern score into [0.0, 1.0].
            # Threshold calibration: webcam JPEG compression produces spectral energy in
            # the 45–65 range; genuine Moiré screen-grid patterns exceed 70.
            moire_score = float(np.clip((high_freq_energy - 70.0) / 30.0, 0.0, 1.0))

            # 2. Specular Reflection Analysis (over-saturated pixels near 255)
            over_exposed_pixels = float(np.sum(gray >= 250))
            total_pixels = float(gray.size)
            specular_ratio = over_exposed_pixels / total_pixels
            specular_score = float(np.clip(specular_ratio / 0.05, 0.0, 1.0))

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return ReflectionAnalysisResult(
                moire_pattern_score=round(moire_score, 4),
                specular_reflection_score=round(specular_score, 4),
                screen_edge_score=0.0,
                confidence=0.85,
                latency_ms=round(elapsed_ms, 2),
                metadata={
                    "high_freq_energy": round(high_freq_energy, 2),
                    "specular_pixel_ratio": round(specular_ratio, 4)
                }
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Error in ReflectionScreenAnalyzer: {e}")
            return ReflectionAnalysisResult(
                moire_pattern_score=0.0,
                specular_reflection_score=0.0,
                screen_edge_score=0.0,
                confidence=0.5,
                latency_ms=round(elapsed_ms, 2),
                metadata={"error": str(e)}
            )
