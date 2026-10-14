import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.routes import api_router
from app.middleware.cors import setup_cors
from app.middleware.request_logger import RequestLoggingMiddleware
from app.middleware.exception_handler import setup_exception_handlers

from typing import Optional
from contextlib import asynccontextmanager
import asyncio
import logging

logger = logging.getLogger(__name__)
lifecycle_task: Optional[asyncio.Task] = None

async def _periodic_exam_lifecycle_runner():
    """Background task running every 15s to auto-complete expired exams and sync state."""
    from app.database.session import async_session_factory
    from app.services.exam_lifecycle_service import ExamLifecycleService
    
    while True:
        try:
            await asyncio.sleep(15)
            async with async_session_factory() as db:
                service = ExamLifecycleService(db)
                count = await service.process_expired_exams()
                if count > 0:
                    logger.info(f"[LIFECYCLE SCHEDULER] Auto-completed {count} expired exam(s).")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error in background lifecycle runner: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global lifecycle_task
    logger.info("Starting Exam Lifecycle Scheduler background task...")
    lifecycle_task = asyncio.create_task(_periodic_exam_lifecycle_runner())
    yield
    logger.info("Stopping Exam Lifecycle Scheduler background task...")
    if lifecycle_task:
        lifecycle_task.cancel()
        try:
            await lifecycle_task
        except asyncio.CancelledError:
            pass

def create_app() -> FastAPI:
    """
    Application factory for creating the FastAPI app instance.
    Sets up configuration, logging, middleware, and routes.
    """
    # 1. Setup logging
    setup_logging(debug=settings.DEBUG)
    
    # 2. Create app instance
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="Backend API Foundation for Online Examination Monitoring System",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 3. Setup middleware
    setup_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    setup_exception_handlers(app)
    
    # 4. Include REST routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # 5. Include WebSocket router (Secure token-authenticated)
    from app.api.v1.routes.ws import router as ws_router
    app.include_router(ws_router, prefix="/ws/monitoring", tags=["WebSocket Monitoring"])
    
    # 6. Mount Secure Authenticated File Serving for Uploads / Evidence
    from app.api.v1.routes.uploads import router as uploads_router
    upload_dir = settings.UPLOAD_DIR or "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    app.include_router(uploads_router, prefix="/uploads", tags=["Secure File Access"])
    app.include_router(uploads_router, prefix="/evidence", tags=["Secure File Access"])
    
    return app

# The main application instance for uvicorn
app = create_app()
