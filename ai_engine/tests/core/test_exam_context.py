import unittest
import threading
import time

from ai_engine.core.exam_context import ExamContext
from ai_engine.core.enums import ExamStatus

class TestExamContext(unittest.TestCase):
    def test_context_initial_state(self) -> None:
        """Ensures that ExamContext starts with the correct defaults."""
        context = ExamContext()
        self.assertEqual(context.system_state.status, ExamStatus.NOT_STARTED)
        self.assertIsNone(context.current_frame)
        self.assertEqual(context.camera_state.status, "OFFLINE")

    def test_context_thread_safety(self) -> None:
        """Spawns concurrent read and write threads to verify thread-safe operations on ExamContext."""
        context = ExamContext()
        errors = []

        def writer_thread(thread_id: int) -> None:
            try:
                for i in range(100):
                    with context.lock():
                        sess = context.session_info
                        sess.exam_id = f"t_{thread_id}_run_{i}"
                        context.session_info = sess
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reader_thread() -> None:
            try:
                for _ in range(100):
                    with context.lock():
                        _ = context.session_info
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer_thread, args=(1,)),
            threading.Thread(target=writer_thread, args=(2,)),
            threading.Thread(target=reader_thread),
            threading.Thread(target=reader_thread)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors occurred: {errors}")
        self.assertTrue(context.session_info.exam_id.startswith("t_"))

    def test_refinements(self) -> None:
        """Verifies enums and the new ExamContext sections (ObjectInfo, DetectionState, etc.)"""
        from ai_engine.core.enums import ModuleState, RiskLevel, SystemHealth
        from ai_engine.core.exam_context import (
            ObjectInfo, DetectionState, FeatureState, ViolationState, EvidenceState, Metadata
        )
        
        # Test new enums
        self.assertEqual(ModuleState.NOT_INITIALIZED.value, "NOT_INITIALIZED")
        self.assertEqual(RiskLevel.CRITICAL.value, "CRITICAL")
        self.assertEqual(SystemHealth.HEALTHY.value, "HEALTHY")

        context = ExamContext()

        # Check default initial values
        self.assertIsInstance(context.object_info, ObjectInfo)
        self.assertIsInstance(context.detection_state, DetectionState)
        self.assertIsInstance(context.feature_state, FeatureState)
        self.assertIsInstance(context.violation_state, ViolationState)
        self.assertIsInstance(context.evidence_state, EvidenceState)
        self.assertIsInstance(context.metadata, Metadata)

        # Set and get
        obj_info = ObjectInfo(items=[])
        context.object_info = obj_info
        self.assertEqual(len(context.object_info.items), 0)

        # Metadata dictionary compatibility setter
        context.metadata = {"session_hash": "abc"}
        self.assertEqual(context.metadata.data["session_hash"], "abc")

        # Metadata Metadata setter
        meta = Metadata(data={"key": "val"})
        context.metadata = meta
        self.assertEqual(context.metadata.data["key"], "val")

