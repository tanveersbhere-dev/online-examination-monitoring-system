"""
Monitoring Session & Report API Router
======================================
REST API endpoints for starting sessions, submitting/ending monitoring,
and retrieving comprehensive monitoring reports.
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from backend.database.session_repository import session_repository
from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring Lifecycle & Reports"])


class CreateSessionRequest(BaseModel):
    student_id: Optional[str] = "local_student"
    examiner_id: Optional[str] = "local_examiner"
    exam_id: Optional[str] = "local_exam"
    attempt_id: Optional[str] = "attempt_1"
    metadata: Optional[Dict[str, Any]] = None


@router.post("/sessions")
async def create_monitoring_session(payload: Optional[CreateSessionRequest] = None):
    """Create a new independent monitoring session and mark it active."""
    req = payload or CreateSessionRequest()
    session = session_repository.create_session(
        student_id=req.student_id or "local_student",
        examiner_id=req.examiner_id,
        exam_id=req.exam_id,
        attempt_id=req.attempt_id,
        metadata=req.metadata,
    )
    # Set as active session in persistence adapter
    monitoring_persistence_adapter.active_session_id = session["id"]
    return {
        "success": True,
        "session_id": session["id"],
        "session": session,
    }


@router.get("/sessions")
async def list_monitoring_sessions(limit: int = Query(20, ge=1, le=100)):
    """List recent monitoring sessions."""
    sessions = session_repository.list_sessions(limit=limit)
    return {
        "sessions": sessions,
        "count": len(sessions),
        "active_session_id": monitoring_persistence_adapter.active_session_id,
    }


@router.get("/sessions/{session_id}")
async def get_monitoring_session(session_id: str):
    """Get metadata for a specific monitoring session."""
    session = session_repository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Monitoring session '{session_id}' not found.")
    return {
        "session": session,
    }


@router.post("/sessions/{session_id}/submit")
async def submit_monitoring_session(session_id: str):
    # Flush any in-memory evidence snapshots to session repository
    try:
        from backend.api import ws_handler
        orch = getattr(ws_handler, "_orchestrator", None)
        if orch and hasattr(orch, "evidence_store"):
            for rec in orch.evidence_store:
                if not isinstance(rec, dict):
                    continue
                v_id = rec.get("violation_id") or rec.get("episode_id")
                if not v_id:
                    continue
                snapshots = rec.get("snapshots")
                if isinstance(snapshots, list) and snapshots:
                    for snap in snapshots:
                        s_fname = snap.get("filename")
                        s_fpath = snap.get("filepath")
                        if s_fname and s_fpath:
                            meta = dict(rec)
                            meta["snapshot"] = snap
                            session_repository.record_evidence(
                                session_id=session_id,
                                violation_id=v_id,
                                filename=s_fname,
                                filepath=s_fpath,
                                timestamp=float(snap.get("timestamp", rec.get("timestamp", 0.0))),
                                confidence=float(snap.get("confidence", rec.get("confidence", 0.0))),
                                duration=float(snap.get("duration", rec.get("total_duration", 0.0))),
                                metadata=meta,
                            )
                else:
                    fname = rec.get("filename") or rec.get("latest_filename")
                    fpath = rec.get("filepath")
                    if fname and fpath:
                        session_repository.record_evidence(
                            session_id=session_id,
                            violation_id=v_id,
                            filename=fname,
                            filepath=fpath,
                            timestamp=float(rec.get("timestamp", 0.0)),
                            confidence=float(rec.get("confidence", rec.get("peak_confidence", 0.0))),
                            duration=float(rec.get("total_duration", 0.0)),
                            metadata=rec,
                        )
    except Exception:
        pass

    session = session_repository.finalize_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Monitoring session '{session_id}' not found.")

    # Reset active session if submitting current session
    if monitoring_persistence_adapter.active_session_id == session_id:
        monitoring_persistence_adapter.active_session_id = None

    return {
        "success": True,
        "session_id": session_id,
        "status": session["status"],
        "duration_seconds": session["total_duration"],
        "session": session,
        "report_url": f"/monitoring/report/{session_id}",
    }


@router.get("/sessions/{session_id}/report")
async def get_session_report(session_id: str):
    """Retrieve full audit report for an exact monitoring session."""
    report = session_repository.get_session_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Monitoring report for session '{session_id}' not found.")
    return report
