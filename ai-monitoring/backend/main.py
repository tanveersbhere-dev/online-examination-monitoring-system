"""
AI Monitoring Unit Host — FastAPI Application
==============================================
Entry point for the standalone / PPR-attachable AI Monitoring Unit Host.

Architecture:
  Browser WebSocket → /ws/monitor → ContextBuilder → Pipeline Orchestrator → ResultSerializer → JSON response
  GET /evidence      → Evidence files & keyframe images
  GET /health        → System + pipeline diagnostics
  GET /session       → Session identity & mode (standalone / ppr)
  REST /api/incidents → Incident intelligence platform endpoints (review, replay, export)
"""
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
_WORKSPACE = Path(__file__).resolve().parent.parent
_DESKTOP = _WORKSPACE.parent

if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))
if str(_DESKTOP) not in sys.path:
    sys.path.insert(0, str(_DESKTOP))

# ── Imports ────────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .pipeline.orchestrator import MonitoringPipelineOrchestrator
from .pipeline.context_builder import ContextBuilder
from .pipeline.result_serializer import ResultSerializer
from .pipeline.integration_manager import IncidentIntegrationManager
from .adapters.session_context import MonitoringSessionContext
from .api import ws_handler, evidence_api, health_api, incidents_api, calibration_api, monitoring_api

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("playground.main")

# ── PyTorch Thread Optimization ───────────────────────────────────────
# Limit PyTorch CPU threads (default 4) to eliminate CPU core starvation under concurrent dual-camera load
import os
try:
    import torch
    _target_threads = int(os.environ.get("PYTORCH_NUM_THREADS", "4"))
    torch.set_num_threads(_target_threads)
    logger.info(f"PyTorch CPU worker threads configured to: {torch.get_num_threads()}")
except Exception as _e:
    logger.debug(f"PyTorch thread configuration skipped: {_e}")

# ── Session & Singletons (created once per process) ─────────────────────
session_context = MonitoringSessionContext.from_env()
orchestrator = MonitoringPipelineOrchestrator()
integration_manager = IncidentIntegrationManager()
orchestrator.integration_manager = integration_manager
context_builder = ContextBuilder(session_context=session_context)
serializer = ResultSerializer()


# ── Lifespan ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting Monitoring Unit Host [mode={session_context.mode}, "
        f"session={session_context.monitoring_session_id}, "
        f"student={session_context.student_id}]..."
    )

    # Auto-create initial active monitoring session in database
    from backend.database.session_repository import session_repository
    from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
    initial_sess = session_repository.create_session(
        session_id=session_context.monitoring_session_id,
        student_id=session_context.student_id,
        exam_id=session_context.exam_id,
        attempt_id=session_context.attempt_id,
    )
    monitoring_persistence_adapter.active_session_id = initial_sess["id"]

    # Wire dependencies into API modules
    ws_handler.inject_dependencies(orchestrator, context_builder, serializer)
    evidence_api.inject_dependencies(orchestrator.EVIDENCE_DIR, lambda: orchestrator.evidence_store)
    health_api.inject_dependencies(orchestrator)
    incidents_api.inject_dependencies(integration_manager)
    calibration_api.inject_dependencies(orchestrator)

    # Connect Camera 2 AI processor callback to MultiCameraManager
    from backend.camera.multi_camera_manager import multi_camera_manager

    def process_camera2_frame(camera_id: str, jpeg_bytes: bytes, session_id: str):
        """Asynchronous AI sampling processor for Camera 2 frames."""
        try:
            # Decode JPEG and construct Frame with camera_id="camera_2"
            frame = context_builder.decode_and_inject(jpeg_bytes, camera_id="camera_2")
            if frame is None:
                return

            context = context_builder.get_context(camera_id="camera_2")
            # Process sampled Camera 2 frame through camera-aware orchestrator
            pipeline_ms = orchestrator.process(context)

            # Persist Camera 2 lifecycle events & evidence with same session_id
            from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
            effective_sid = session_id or monitoring_persistence_adapter.active_session_id
            monitoring_persistence_adapter.handle_frame_lifecycle(context, session_id=effective_sid)
        except Exception as e:
            logger.error(f"[Camera2 AI] Error processing sampled frame: {e}", exc_info=True)

    multi_camera_manager.set_ai_pipeline_processor(process_camera2_frame)
    multi_camera_manager.start_background_workers()

    # Initialize the full AI pipeline (blocking — models load here)
    try:
        orchestrator.initialize()
        # Start processor lifecycle.
        orchestrator.start()
        logger.info("Pipeline initialized. Ready to receive frames.")
    except Exception as e:
        logger.critical(f"Pipeline initialization failed: {e}", exc_info=True)
        # Continue anyway — individual processor failures are handled gracefully

    # Start dedicated background AudioDetectionWorker & VoiceActivityWorker
    try:
        from ai_engine.audio_detection.audio_worker import audio_detection_worker
        if not audio_detection_worker.detector.is_available:
            audio_detection_worker.initialize()
        loop = asyncio.get_running_loop()
        audio_detection_worker.start(loop=loop)
        logger.info("Dedicated AudioDetectionWorker started.")
    except Exception as e:
        logger.error(f"Failed to start AudioDetectionWorker: {e}", exc_info=True)

    try:
        from ai_engine.audio_detection.voice_vad_worker import voice_vad_worker
        voice_vad_worker.start()
        logger.info("Dedicated VoiceActivityWorker started.")
    except Exception as e:
        logger.error(f"Failed to start VoiceActivityWorker: {e}", exc_info=True)

    yield  # ← application runs here

    logger.info("Shutting down pipeline...")
    try:
        from ai_engine.audio_detection.audio_worker import audio_detection_worker
        audio_detection_worker.stop()
    except Exception:
        pass
    try:
        from ai_engine.audio_detection.voice_vad_worker import voice_vad_worker
        voice_vad_worker.stop()
    except Exception:
        pass
    orchestrator.shutdown()
    integration_manager.clear()
    multi_camera_manager.stop_background_workers()
    ws_handler.shutdown_cam1_executor()
    logger.info("Shutdown complete.")


# ── Application ────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Monitoring Unit Host",
    description="Standalone AI Monitoring Application Host.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server and LAN mobile devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(ws_handler.router)
app.include_router(monitoring_api.router)
app.include_router(evidence_api.router)
app.include_router(health_api.router)
app.include_router(incidents_api.router)
app.include_router(calibration_api.router)


@app.get("/session")
@app.get("/api/session")
async def get_session():
    """Return active monitoring session identity and mode."""
    return session_context.to_dict()


@app.get("/")
async def root():
    return {
        "service": "AI Monitoring Unit Host",
        "version": "1.0.0",
        "mode": session_context.mode,
        "session_id": session_context.monitoring_session_id,
        "student_id": session_context.student_id,
        "websocket": "ws://localhost:8000/ws/monitor",
        "evidence": "/evidence",
        "health": "/health",
        "session": "/session",
    }
