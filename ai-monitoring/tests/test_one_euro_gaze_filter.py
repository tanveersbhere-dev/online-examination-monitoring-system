"""
Test Suite: One-Euro Gaze Filter and Two-Eye Robustness (Phase 1)
================================================================
Verifies that:
1. Stationary gaze eliminates high-frequency MediaPipe iris micro-jitter.
2. Fast gaze saccades respond dynamically without excessive lag.
3. Two-eye outlier mitigation prevents asymmetric single-eye landmark glitches.
4. Filter resets cleanly across tracking loss and new sessions without state leakage.
5. Raw and filtered vectors are both preserved.
"""
import time
import math
import random
import pytest

from ai_engine.features.eye_gaze.models import EyeGazeConfig
from ai_engine.features.eye_gaze.mediapipe_gaze_extractor import (
    OneEuroFilter1D, OneEuroFilter2D, MediaPipeEyeGazeExtractor, _normalized_eye_gaze
)
from ai_engine.camera.frame import Frame
import numpy as np


class TestOneEuroGazeFilter:
    """Unit tests for One-Euro filter math and MediaPipeEyeGazeExtractor integration."""

    def test_01_stationary_gaze_jitter_reduction(self):
        """Stationary fixation with Gaussian noise should have significantly lower variance after filtering."""
        filter_1d = OneEuroFilter1D(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        
        base_val = 0.05
        raw_samples = []
        filtered_samples = []
        
        t = 1000.0
        random.seed(42)
        for _ in range(60):  # 60 frames (~6 seconds at 10 FPS)
            noise = random.gauss(0.0, 0.04)  # High-frequency iris noise
            x = base_val + noise
            raw_samples.append(x)
            
            x_filtered = filter_1d.filter(x, timestamp=t)
            filtered_samples.append(x_filtered)
            t += 0.10  # 100ms interval (10 FPS)

        raw_var = np.var(raw_samples[10:])
        filtered_var = np.var(filtered_samples[10:])

        # Filtered variance must be at least 60% lower than noisy raw input
        assert filtered_var < raw_var * 0.40, f"Filtered var ({filtered_var}) should be < 40% of raw ({raw_var})"
        # Mean should remain centered around true value
        assert abs(np.mean(filtered_samples[10:]) - base_val) < 0.015

    def test_02_fast_saccade_responsiveness(self):
        """Fast intentional gaze shift should dynamically adapt cutoff and follow within 2-3 frames without lag."""
        filter_1d = OneEuroFilter1D(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        
        t = 1000.0
        # Initialize at center (0.0)
        for _ in range(10):
            filter_1d.filter(0.0, timestamp=t)
            t += 0.10
            
        # Fast saccade to looking away at right (0.60)
        target = 0.60
        lag_samples = []
        for _ in range(5):
            val = filter_1d.filter(target, timestamp=t)
            lag_samples.append(val)
            t += 0.10
            
        # Within 2 frames (200ms), filter should reach > 55% of target
        assert lag_samples[1] > 0.35, f"Frame 2 reached {lag_samples[1]}, expected > 0.35 (responsive saccade)"
        # Within 4 frames (400ms), filter should reach > 85% of target
        assert lag_samples[3] > 0.50, f"Frame 4 reached {lag_samples[3]}, expected > 0.50"


    def test_03_dual_channel_2d_filter(self):
        """OneEuroFilter2D filters gx and gy independently."""
        filter_2d = OneEuroFilter2D(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        
        t = 100.0
        fx, fy = filter_2d.filter(0.10, -0.20, timestamp=t)
        assert fx == 0.10
        assert fy == -0.20

        t += 0.10
        fx, fy = filter_2d.filter(0.12, -0.18, timestamp=t)
        assert abs(fx - 0.11) < 0.02
        assert abs(fy - (-0.19)) < 0.02

    def test_04_session_and_tracking_loss_reset(self):
        """Large time gap or explicit reset must clear historical momentum immediately."""
        filter_1d = OneEuroFilter1D(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
        
        # High value at t=100
        filter_1d.filter(0.80, timestamp=100.0)
        filter_1d.filter(0.80, timestamp=100.1)
        
        # Tracking loss: gap > 1.0s (e.g. 5 seconds face absent)
        # Next frame at t=105.1 with new candidate looking center (0.0)
        val_after_gap = filter_1d.filter(0.0, timestamp=105.1)
        
        # Must immediately snap to new reading (0.0) without smoothing from stale 0.80
        assert val_after_gap == 0.0

        # Explicit reset test
        filter_1d.filter(0.90, timestamp=106.0)
        filter_1d.reset()
        val_after_reset = filter_1d.filter(-0.30, timestamp=106.1)
        assert val_after_reset == -0.30

    def test_05_two_eye_asymmetric_outlier_rejection(self):
        """If one eye experiences an abnormal single-frame landmark glitch, the stable eye protects the combined signal."""
        config = EyeGazeConfig(enable_smoothing=True)
        extractor = MediaPipeEyeGazeExtractor(config=config)
        extractor.initialize()
        extractor.start()

        # Build mock landmarks: left eye centered, right eye centered
        def _make_landmarks(left_iris_x=0.45, right_iris_x=0.55):
            lm = [(0.5, 0.5, 0.0)] * 480
            # Left eye corners & lids (width=0.08, height=0.04, center_x=0.45, center_y=0.40)
            lm[33] = (0.41, 0.40, 0.0)
            lm[133] = (0.49, 0.40, 0.0)
            lm[159] = (0.45, 0.38, 0.0)
            lm[145] = (0.45, 0.42, 0.0)
            lm[468] = (left_iris_x, 0.40, 0.0)  # Left iris

            # Right eye corners & lids (width=0.08, height=0.04, center_x=0.55, center_y=0.40)
            lm[362] = (0.51, 0.40, 0.0)
            lm[263] = (0.59, 0.40, 0.0)
            lm[386] = (0.55, 0.38, 0.0)
            lm[374] = (0.55, 0.42, 0.0)
            lm[473] = (right_iris_x, 0.40, 0.0)  # Right iris
            return [lm]

        frame = Frame.from_bgr_image(
            np.zeros((480, 640, 3), dtype=np.uint8),
            frame_id=1, timestamp=100.0
        )


        # 1. Warm up with stable center gaze (gx ≈ 0.0)
        res1 = extractor.extract(frame, _make_landmarks(0.45, 0.55))
        assert abs(res1.primary_gaze.combined_gaze_vector[0]) < 0.05

        # 2. Inject single-eye glitch: left eye stays center (0.45 -> gx=0.0), right eye spikes far right (0.58 -> gx=0.75)
        frame.timestamp = 100.1
        frame.frame_id = 2
        res2 = extractor.extract(frame, _make_landmarks(0.45, 0.58))
        
        # Outlier rejection weights the stable left eye more (80%) -> combined raw < 0.25 (instead of 0.375)
        primary = res2.primary_gaze
        assert primary.raw_gaze_vector is not None
        assert primary.filtered_gaze_vector is not None
        assert primary.combined_gaze_vector[0] < 0.20, f"Glitch mitigated: {primary.combined_gaze_vector[0]}"
