"""
Health API
==========
GET /health — full system + pipeline health snapshot.

Returns processor statuses, model loading state, and system resource usage.
Used by the frontend Status Bar and Pipeline Debugger.
"""
import time
import logging

import psutil
from fastapi import APIRouter

logger = logging.getLogger("playground.health")

router = APIRouter(tags=["health"])

_orchestrator_ref = None
_start_time = time.time()


def inject_dependencies(orchestrator):
    global _orchestrator_ref
    _orchestrator_ref = orchestrator


@router.get("/health")
async def health():
    proc = psutil.Process()
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    pipeline_health = {}
    avg_ms = 0.0
    total_frames = 0

    if _orchestrator_ref:
        pipeline_health = _orchestrator_ref.processor_health()
        avg_ms = _orchestrator_ref.avg_pipeline_ms
        total_frames = _orchestrator_ref.total_frames_processed

    ready_count = sum(1 for v in pipeline_health.values() if v["status"] == "READY")
    failed_count = sum(1 for v in pipeline_health.values() if v["status"] == "FAILED")
    total_count = len(pipeline_health)

    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "system": {
            "cpu_percent": cpu_percent,
            "ram_percent": mem.percent,
            "ram_used_mb": round(mem.used / 1024 / 1024, 1),
            "ram_total_mb": round(mem.total / 1024 / 1024, 1),
        },
        "pipeline": {
            "processors": pipeline_health,
            "ready": ready_count,
            "failed": failed_count,
            "total": total_count,
            "avg_latency_ms": avg_ms,
            "total_frames_processed": total_frames,
        },
    }
