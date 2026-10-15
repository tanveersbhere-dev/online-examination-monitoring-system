"""
Unit tests for Enterprise AI Proctoring Behavioral Reasoning Engine Redesign.
"""
import time
import unittest
from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.behavior_engine.behavior_engine import BehaviorEngineProcessor
from ai_engine.intelligence.behavior_engine.temporal_state_machine import BehaviorStateMachineManager, BehaviorState

class TestProctoringBehaviorEngine(unittest.TestCase):

    def setUp(self):
        self.engine = BehaviorEngineProcessor()
        self.engine.initialize()
        self.engine.start()

    def test_01_brief_look_away_ignored(self):
        """Verify brief natural glance away (<0.8s) stays in OBSERVED/MONITORING and does NOT trigger active violation."""
        manager = BehaviorStateMachineManager()
        start_ts = time.time()

        # Frame 0 at 0.0s
        manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts)

        # Frame 1: 0.5s glance away -> OBSERVED
        state, conf, is_active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts + 0.5)
        self.assertEqual(state, BehaviorState.OBSERVED)
        self.assertFalse(is_active)
        self.assertLess(conf, 35.0)

    def test_02_sustained_look_away_activates_violation(self):
        """Verify sustained look away (>3.0s) smoothly transitions NORMAL -> OBSERVED -> MONITORING -> WARNING -> CONFIRMED -> ACTIVE."""
        manager = BehaviorStateMachineManager()
        start_ts = time.time()

        # 0.0s -> Start observation
        manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts)

        # 0.5s -> OBSERVED
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts + 0.5)
        self.assertEqual(state, BehaviorState.OBSERVED)
        self.assertFalse(active)

        # 1.2s -> MONITORING
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts + 1.2)
        self.assertIn(state, [BehaviorState.MONITORING, BehaviorState.WARNING])
        self.assertFalse(active)

        # 2.0s -> WARNING
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts + 2.0)
        self.assertIn(state, [BehaviorState.WARNING, BehaviorState.CONFIRMED])
        self.assertFalse(active)

        # 3.2s -> ACTIVE violation
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=start_ts + 3.2)
        self.assertEqual(state, BehaviorState.ACTIVE)
        self.assertTrue(active)
        self.assertGreaterEqual(conf, 80.0)

    def test_03_hysteresis_resolution(self):
        """Verify behavior decays gradually and resolves only after confidence drops below hysteresis threshold (30%)."""
        manager = BehaviorStateMachineManager()
        start_ts = time.time()

        # Activate violation across 3.2s
        for t in [0.0, 0.5, 1.2, 2.0, 2.8, 3.3]:
            manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=start_ts + t)

        tracker = manager.get_tracker("ATT_LOOKING_AWAY", start_ts + 3.3)
        self.assertEqual(tracker.state, BehaviorState.ACTIVE)

        # Behavior stops at 3.4s (decay begins)
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=start_ts + 3.5)
        # Still in decay phase, not immediately resolved
        self.assertGreater(conf, 30.0)

        # 5.0s (decayed below 30%) -> RESOLVED
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=start_ts + 5.2)
        self.assertEqual(state, BehaviorState.RESOLVED)
        self.assertFalse(active)

    def test_04_recurrent_behavior_acceleration(self):
        """Verify repeated occurrences within 60s accelerate confidence buildup."""
        manager = BehaviorStateMachineManager()
        start_ts = time.time()

        # First activation cycle
        for t in [0.0, 0.5, 1.2, 2.0, 3.3]:
            manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=start_ts + t)

        tracker = manager.get_tracker("ATT_LOOKING_AWAY", start_ts + 3.3)
        self.assertGreaterEqual(len(tracker.occurrences_60s), 1)

        # Behavior resolves
        manager.update_frame("ATT_LOOKING_AWAY", observed=False, raw_confidence=0.0, current_ts=start_ts + 5.5)

        # Second activation cycle 10 seconds later
        start_ts2 = start_ts + 15.0
        # Accelerated buildup reaches active faster
        state2, conf2, active2 = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=start_ts2 + 1.8)
        self.assertGreaterEqual(conf2, 60.0)

    def test_05_adaptive_calibration_baseline_integration(self):
        """Verify baseline head motion metrics adjust ignore thresholds dynamically per candidate."""
        manager = BehaviorStateMachineManager()
        start_ts = time.time()

        calibration_info = {
            "status": "CALIBRATED",
            "runtime_deltas": {
                "head_pose_yaw_dev": 20.0 # Candidate with high baseline head motion
            }
        }

        # 0.9s glance for high baseline candidate stays OBSERVED (threshold expanded by +0.3s)
        manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts, calibration_info=calibration_info)
        state, conf, active = manager.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.9, current_ts=start_ts + 0.9, calibration_info=calibration_info)
        self.assertEqual(state, BehaviorState.OBSERVED)
        self.assertFalse(active)

if __name__ == "__main__":
    unittest.main()
