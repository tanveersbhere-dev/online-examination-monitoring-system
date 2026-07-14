import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request durations and statuses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        
        # Log format: METHOD PATH - STATUS - DURATION
        logger.info(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - "
            f"{process_time:.4f}s"
        )
        
        return response
