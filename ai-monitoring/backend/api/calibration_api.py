"""
Calibration Control API
=======================
REST endpoints for Adaptive Baseline Calibration Engine control.

Endpoints:
  POST /calibration/start   â€” Begin a 30-second calibration session
  POST /calibration/reset   â€” Abort calibration and request recalibration
  GET  /calibration/status  â€” Return current calibration state (REST alternative to WS stream)

The calibration status is also embedded in every WS frame result under the
'calibration' key â€” so this REST interface is supplementary (used by button clicks).

Design:
  - All state lives in the CalibrationManager, which is owned by the Orchestrator.
  - This module is purely a thin HTTP shim over the Orchestrator's public API.
  - No business logic here.
"""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("playground.calibration_api")

router = APIRouter(prefix="/calibration", tags=["Calibration"])

# Injected at startup by main.py
_orchestrator_ref = None


def inject_dependencies(orchestrator) -> None:
    """Called once at app startup to inject the shared orchestrator instance."""
    global _orchestrator_ref
    _orchestrator_ref = orchestrator


@router.post("/start")
async def start_calibration():
    """
    Begin a 30-second adaptive baseline calibration session.
    The candidate must look naturally at the centre of the exam screen during this window.
    Calibration progress is streamed back via the WebSocket frame result
    under the 'calibration' key (status, quality_score, elapsed_seconds).
    """
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready.")

    calib_manager = getattr(_orchestrator_ref, "calibration_manager", None)
    if calib_manager is None:
        raise HTTPException(status_code=503, detail="Calibration manager not available.")

    current_status = getattr(calib_manager, "status", "NOT_STARTED")
    if current_status == "CALIBRATING":
        return {"status": "ALREADY_CALIBRATING", "message": "Calibration is already in progress."}

    try:
        _orchestrator_ref.start_calibration()
        logger.info("Calibration started via REST API.")
        return {
            "status": "STARTED",
            "message": "Centre-screen calibration started. Look naturally at the centre of the exam screen and keep your face visible.",
        }
    except Exception as e:
        logger.error(f"Failed to start calibration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start calibration: {e}")


@router.post("/reset")
async def reset_calibration():
    """
    Abort any in-progress calibration and mark the session as
    RECALIBRATION_REQUIRED. The user may then start a fresh calibration.
    """
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready.")

    try:
        _orchestrator_ref.reset_calibration(reason="Manual reset requested via UI.")
        logger.info("Calibration reset via REST API.")
        return {
            "status": "RESET",
            "message": "Calibration has been reset. Click 'Start Calibration' to begin again.",
        }
    except Exception as e:
        logger.error(f"Failed to reset calibration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset calibration: {e}")


@router.get("/status")
async def get_calibration_status():
    """
    Return current calibration state snapshot.
    This is the same data embedded in every WS frame under 'calibration',
    but available over REST for one-shot reads (e.g. on modal open).
    """
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready.")

    calib_manager = getattr(_orchestrator_ref, "calibration_manager", None)
    if calib_manager is None:
        return {"status": "NOT_STARTED", "quality_rating": "UNKNOWN", "quality_score": 0.0}

    status = getattr(calib_manager, "status", "NOT_STARTED")
    baseline = getattr(calib_manager, "baseline", None)

    return {
        "status": status,
        "quality_rating": getattr(baseline, "quality_rating", "UNKNOWN") if baseline else "UNKNOWN",
        "quality_score": getattr(baseline, "quality_score", 0.0) if baseline else 0.0,
        "message": _status_message(status),
    }


def _status_message(status: str) -> str:
    return {
        "NOT_STARTED": "No calibration performed yet. Click 'Start Calibration' to begin.",
        "CALIBRATING": "Calibration in progress. Please sit still.",
        "CALIBRATED": "Baseline calibrated. Adaptive thresholds are active.",
        "FAILED": "Calibration failed. Please try again with better lighting.",
        "RECALIBRATION_REQUIRED": "Recalibration required. Click 'Start Calibration'.",
    }.get(status, "Unknown calibration state.")
