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
    )
    
    # 3. Setup middleware
    setup_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    setup_exception_handlers(app)
    
    # 4. Include REST routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # 5. Include WebSocket router
    from app.websocket.websocket_router import router as ws_router
    app.include_router(ws_router, prefix="/ws/monitoring", tags=["WebSocket Monitoring"])
    
    return app

# The main application instance for uvicorn
app = create_app()
