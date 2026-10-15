"""
Evidence API
============
GET /evidence          — list all evidence records (metadata only)
GET /evidence/{fname}  — serve the actual JPEG image file
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger("playground.evidence")

router = APIRouter(prefix="/evidence", tags=["evidence"])

_evidence_dir: Path = None
_evidence_store_ref = None


def inject_dependencies(evidence_dir: Path, evidence_store_ref):
    global _evidence_dir, _evidence_store_ref
    _evidence_dir = evidence_dir
    _evidence_store_ref = evidence_store_ref


@router.get("", response_model=List[Dict[str, Any]])
async def list_evidence():
    """Return all evidence records collected during the session."""
    if _evidence_store_ref is None:
        return []
    store = _evidence_store_ref() if callable(_evidence_store_ref) else _evidence_store_ref
    return list(reversed(store))  # newest first


@router.get("/{filepath:path}")
async def get_evidence_file(filepath: str):
    """Serve a specific evidence file (image or replay video) by path."""
    if _evidence_dir is None:
        raise HTTPException(status_code=503, detail="Evidence directory not configured")

    target_path = (_evidence_dir / filepath).resolve()
    try:
        # Prevent path traversal outside evidence directory
        if not str(target_path).startswith(str(_evidence_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid path")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail=f"Evidence file not found: {filepath}")

    ext = target_path.suffix.lower()
    if ext == ".mp4":
        media_type = "video/mp4"
    elif ext == ".webm":
        media_type = "video/webm"
    elif ext == ".webp":
        media_type = "image/webp"
    elif ext == ".avi":
        media_type = "video/x-msvideo"
    elif ext in (".png",):
        media_type = "image/png"
    elif ext == ".wav":
        media_type = "audio/wav"
    else:
        media_type = "image/jpeg"

    return FileResponse(str(target_path), media_type=media_type)
