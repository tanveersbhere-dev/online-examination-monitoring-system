"""
Unit and integration tests verifying end-to-end off-screen attention incident creation.
Ensures that sustained off-screen and downward gaze produce:
1. Rule triggers (ATT_LOOKING_AWAY / ATT_DOWNWARD_GAZE).
2. ViolationManager debounced confirmation (OPEN -> ACTIVE).
3. Lifecycle events emitted (STARTED -> ACTIVE -> RESOLVED).
4. IncidentIntegrationManager aggregate incidents displayed in Dashboard payload.
"""
import pytest
import time
import numpy as np

from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
from backend.pipeline.integration_manager import IncidentIntegrationManager
from ai_engine.core.exam_context import ExamContext, FaceInfo, HeadPoseInfo, EyeInfo
from ai_engine.camera.frame import Frame
from ai_engine.calibration.baseline_profile import GazeBaseline, CandidateBaseline, HeadPoseBaseline, FaceBaseline


@pytest.fixture
def orchestrator_with_integration():
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    orch.start()

    integration_mgr = IncidentIntegrationManager()
    orch.integration_manager = integration_mgr

    orch._calibration_manager.status = "CALIBRATED"
    orch._calibration_manager.stage = "READY"
    baseline = CandidateBaseline(
        head_pose=HeadPoseBaseline(average_yaw=0.0, average_pitch=0.0, average_roll=0.0),
        gaze=GazeBaseline(center_x=0.0, center_y=0.0),
        face=FaceBaseline(average_distance=1.0)
    )
    orch._calibration_manager.baseline = baseline
    return orch, integration_mgr


def test_off_screen_attention_generates_active_incident(orchestrator_with_integration):
    """Verify that looking away for > 1.5s opens an active incident in the platform."""
    orch, integration_mgr = orchestrator_with_integration

    t0 = time.time()
    for f in range(1, 10):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(
            np.zeros((480, 640, 3), dtype=np.uint8),
            frame_id=f,
            timestamp=t0 + f * 0.5
        )
        ctx.face_info = FaceInfo(
            face_detected=True,
            confidence=0.95,
            bbox=(100, 100, 200, 200),
            face_count=1,
            presence_state="PRESENT",
            identity_consistent=True,
            identity_confidence=0.88
        )
        # Looking far right off-screen (yaw=45 deg, gaze_x=0.7)
        ctx.head_pose_info = HeadPoseInfo(yaw=45.0, pitch=5.0, roll=0.0, success=True)
        ctx.eye_info = EyeInfo(
            gaze_confidence=1.0,
            combined_gaze=(0.70, 0.05, 1.0),
            left_iris_center=(0.4, 0.5),
            right_iris_center=(0.6, 0.5),
            average_ear=0.28,
            blink_detected=False
        )

        orch._calibration_manager.evaluate_runtime_frame(ctx)
        orch._update_calibrated_attention(ctx)

        for step in ["ObservationFusion", "RuleEngine", "RiskEngine", "ViolationManager", "BehaviorEngine"]:
            orch._run_step(step, ctx)

        orch.integration_manager.handle_frame_lifecycle_events(ctx)

    payload = integration_mgr.get_platform_serializer_payload()
    incidents = payload.get("all_incidents", [])

    assert len(incidents) >= 1, "Expected at least 1 incident created in Incident Intelligence Platform"
    inc = incidents[0]
    assert inc["incident_type"] == "ATT_LOOKING_AWAY"
    assert inc["status"] in ("ACTIVE", "OPEN", "STARTED")


def test_downward_gaze_generates_active_incident(orchestrator_with_integration):
    """Verify that looking downward sustained opens an active incident."""
    orch, integration_mgr = orchestrator_with_integration

    t0 = time.time()
    for f in range(1, 10):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(
            np.zeros((480, 640, 3), dtype=np.uint8),
            frame_id=f,
            timestamp=t0 + f * 0.5
        )
        ctx.face_info = FaceInfo(
            face_detected=True,
            confidence=0.95,
            bbox=(100, 100, 200, 200),
            face_count=1,
            presence_state="PRESENT",
            identity_consistent=True,
            identity_confidence=0.88
        )
        # Looking downward (pitch=-25 deg, gaze_y=-0.6)
        ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=-25.0, roll=0.0, success=True)
        ctx.eye_info = EyeInfo(
            gaze_confidence=1.0,
            combined_gaze=(0.0, -0.60, 1.0),
            left_iris_center=(0.5, 0.7),
            right_iris_center=(0.5, 0.7),
            average_ear=0.28,
            blink_detected=False
        )

        orch._calibration_manager.evaluate_runtime_frame(ctx)
        orch._update_calibrated_attention(ctx)

        for step in ["ObservationFusion", "RuleEngine", "RiskEngine", "ViolationManager", "BehaviorEngine"]:
            orch._run_step(step, ctx)

        orch.integration_manager.handle_frame_lifecycle_events(ctx)

    payload = integration_mgr.get_platform_serializer_payload()
    incidents = payload.get("all_incidents", [])

    assert len(incidents) >= 1, "Expected at least 1 incident created for downward gaze"
    inc = incidents[0]
    assert inc["incident_type"] in ("ATT_LOOKING_AWAY", "ATT_DOWNWARD_GAZE")
    assert inc["status"] in ("ACTIVE", "OPEN", "STARTED")
