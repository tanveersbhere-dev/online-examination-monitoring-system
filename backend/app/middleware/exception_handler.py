import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the application."""
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error due to database operation."}
        )
        
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(f"Value error: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)}
        )
