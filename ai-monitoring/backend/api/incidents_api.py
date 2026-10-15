"""
FastAPI Incident Intelligence Platform Router
================================================
Provides REST API endpoints for Incident Intelligence Platform (Packages 10.1 - 10.9).
"""
import uuid
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from incident_intelligence.review import ReviewDecisionEnum
from incident_intelligence.export import ExportManifest, CasePackage, IntegrityHash

router = APIRouter(prefix="/api/incidents", tags=["Incident Intelligence"])

_integration_manager = None

def inject_dependencies(integration_manager) -> None:
    """Inject IncidentIntegrationManager dependency."""
    global _integration_manager
    _integration_manager = integration_manager

class ReviewDecisionRequest(BaseModel):
    decision: str
    notes: Optional[str] = None
    author: Optional[str] = "PROCTOR_REVIEWER"

@router.get("")
async def list_incidents(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
    """List all incident DTOs recorded in session."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    incidents = _integration_manager.incident_repository.list_all()
    if status:
        incidents = [i for i in incidents if i.status == status or (hasattr(i.status, 'value') and i.status.value == status)]
    if category:
        incidents = [i for i in incidents if i.metadata.category == category]

    incidents = incidents[-limit:]
    return {"incidents": [i.to_dto().to_dict() for i in incidents], "count": len(incidents)}

@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Get single incident DTO details."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    incident = _integration_manager.incident_repository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    return incident.to_dto().to_dict()

@router.get("/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str, projection: str = Query("human", regex="^(human|tech|rev)$")):
    """Get incident timeline projection (Package 10.4)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    incident = _integration_manager.incident_repository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    if projection == "human":
        proj = _integration_manager.timeline_projection.generate_human_projection(incident_id, incident.metadata.title)
    elif projection == "tech":
        proj = _integration_manager.timeline_projection.generate_technical_projection(incident_id)
    else:
        proj = _integration_manager.timeline_projection.generate_reviewer_projection(incident_id)

    return proj.to_dict()

@router.get("/{incident_id}/analytics")
async def get_incident_analytics(incident_id: str):
    """Get derived analytics snapshot DTO (Package 10.5)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    incident = _integration_manager.incident_repository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    snapshot = _integration_manager.analytics_repository.get_latest(incident_id)
    if not snapshot:
        snapshot = _integration_manager.analytics_engine.analyze_incident(
            incident, query_service=_integration_manager.timeline_query
        )

    return snapshot.to_dto().to_dict()

@router.get("/{incident_id}/explanation")
async def get_incident_explanation(incident_id: str):
    """Get reason codes and deterministic explanation package (Package 10.6)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    pkg = _integration_manager.explanation_repository.get_by_incident_id(incident_id)
    if not pkg:
        incident = _integration_manager.incident_repository.get_by_id(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        timeline_events = _integration_manager.timeline_query.get_complete_timeline(incident_id)
        snapshot = _integration_manager.analytics_repository.get_latest(incident_id)
        pkg = _integration_manager.narrative_builder.build_explanation_package(incident, timeline_events, snapshot)

    return pkg.to_dto().to_dict()

@router.get("/{incident_id}/review")
async def get_incident_review(incident_id: str):
    """Get ReviewPackage DTO for proctor workspace (Package 10.7)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    pkg = _integration_manager.review_repository.get_by_incident_id(incident_id)
    if not pkg:
        incident = _integration_manager.incident_repository.get_by_id(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
        human_proj = _integration_manager.timeline_projection.generate_human_projection(incident_id)
        snapshot = _integration_manager.analytics_repository.get_latest(incident_id)
        exp_pkg = _integration_manager.explanation_repository.get_by_incident_id(incident_id)
        pkg = _integration_manager.review_builder.build_review_package(
            incident=incident,
            human_timeline_projection=human_proj.to_dict(),
            analytics_snapshot=snapshot,
            explanation_package=exp_pkg
        )
        _integration_manager.review_repository.save(pkg)

    return pkg.to_dto().to_dict()

@router.post("/{incident_id}/review/decision")
async def submit_review_decision(incident_id: str, req: ReviewDecisionRequest):
    """Submit proctor review decision (Package 10.7)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    pkg = _integration_manager.review_repository.get_by_incident_id(incident_id)
    if not pkg:
        # Trigger review creation
        await get_incident_review(incident_id)
        pkg = _integration_manager.review_repository.get_by_incident_id(incident_id)

    if not pkg:
        raise HTTPException(status_code=404, detail=f"ReviewPackage for incident '{incident_id}' not found.")

    try:
        decision_enum = ReviewDecisionEnum(req.decision.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid decision '{req.decision}'. Accepted: CONFIRMED, DISMISSED, FALSE_POSITIVE, NEEDS_ESCALATION")

    ts = time.time()
    pkg.update_decision(decision_enum, ts, reason=req.notes or "Decision submitted via REST API")

    if req.notes:
        from incident_intelligence.review import ReviewNote
        note = ReviewNote(
            note_id=f"NOTE-{int(ts)}",
            timestamp=ts,
            author=req.author or "PROCTOR",
            text=req.notes
        )
        pkg.add_note(note)

    _integration_manager.review_repository.save(pkg)
    return pkg.to_dto().to_dict()

@router.get("/{incident_id}/replay")
async def get_replay_seek_data(incident_id: str, frame: int = Query(1, ge=1)):
    """Get replay seek target and overlay metadata (Package 10.8)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    incident = _integration_manager.incident_repository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    session = _integration_manager.replay_repository.get_by_incident_id(incident_id)
    if not session:
        session = ReplaySession(
            session_id=f"SESS-{incident_id}",
            incident_id=incident_id,
            current_frame_number=frame,
            current_timestamp=incident.start_time,
            incident_dto=incident.to_dto()
        )

        for f in range(1, 100):
            session.frame_index.add_entry(FrameIndexEntry(f, incident.start_time + (f * 0.1), incident_id))

        _integration_manager.replay_repository.save(session)

    entry = session.seek_to_frame(frame)
    if not entry:
        entry = FrameIndexEntry(frame, incident.start_time, incident_id)

    overlay = _integration_manager.overlay_generator.generate_overlay(incident, entry)
    return {
        "session": session.to_dto().to_dict(),
        "frame_entry": entry.to_dict(),
        "overlay": overlay.to_dict()
    }

def _build_case_package_helper(incident_id: str) -> CasePackage:
    incident = _integration_manager.incident_repository.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    inc_dto = incident.to_dto()
    ev_dtos = [ref.to_dto() for ref in incident.evidence_references]
    timeline = _integration_manager.timeline_query.get_complete_timeline(incident_id)
    tl_dtos = [e.to_dto() for e in timeline]

    analytics_snap = _integration_manager.analytics_repository.get_latest(incident_id)
    exp_pkg = _integration_manager.explanation_repository.get_by_incident_id(incident_id)
    rev_pkg = _integration_manager.review_repository.get_by_incident_id(incident_id)
    replay_sess = _integration_manager.replay_repository.get_by_incident_id(incident_id)

    payload_hash = {
        "incident": inc_dto.to_dict(),
        "evidence": [e.to_dict() for e in ev_dtos],
        "timeline": [t.to_dict() for t in tl_dtos]
    }
    digest = IntegrityHash.compute_hash(payload_hash)

    manifest = ExportManifest(
        package_uuid=f"PKG-{uuid.uuid4().hex[:8].upper()}",
        export_timestamp=time.time(),
        platform_version="IIP-2026-V1.0",
        schema_versions={"incident": "1.0.0", "timeline": "1.0.0"},
        incident_id=incident_id,
        replay_id=replay_sess.session_id if replay_sess else None,
        analytics_snapshot_id=analytics_snap.snapshot_id if analytics_snap else None,
        explanation_id=exp_pkg.incident_id if exp_pkg else None,
        review_id=rev_pkg.package_id if rev_pkg else None,
        evidence_count=len(ev_dtos),
        timeline_count=len(tl_dtos),
        integrity_hash=digest
    )

    return CasePackage(
        incident_dto=inc_dto,
        evidence_references=ev_dtos,
        timeline_events=tl_dtos,
        analytics_snapshot_dto=analytics_snap.to_dto() if analytics_snap else None,
        explanation_package_dto=exp_pkg.to_dto() if exp_pkg else None,
        review_package_dto=rev_pkg.to_dto() if rev_pkg else None,
        replay_session_dto=replay_sess.to_dto() if replay_sess else None,
        manifest=manifest,
        integrity_hash=digest
    )

@router.get("/{incident_id}/export/pdf")
async def export_incident_pdf(incident_id: str):
    """Download reviewer-friendly PDF/Text investigation report (Package 10.9)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    cp = _build_case_package_helper(incident_id)
    pdf_bytes = _integration_manager.pdf_exporter.export_pdf_bytes(cp)

    headers = {"Content-Disposition": f'attachment; filename="incident_report_{incident_id}.txt"'}
    return Response(content=pdf_bytes, media_type="text/plain", headers=headers)

@router.get("/{incident_id}/export/zip")
async def export_incident_zip(incident_id: str):
    """Download complete SHA-256 verified ZIP investigation CasePackage archive (Package 10.9)."""
    if not _integration_manager:
        raise HTTPException(status_code=503, detail="Incident Integration Manager not ready.")

    cp = _build_case_package_helper(incident_id)
    zip_bytes = _integration_manager.zip_exporter.export_zip_bytes(cp)

    headers = {"Content-Disposition": f'attachment; filename="case_package_{incident_id}.zip"'}
    return Response(content=zip_bytes, media_type="application/zip", headers=headers)
