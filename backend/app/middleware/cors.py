from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

def setup_cors(app: FastAPI) -> None:
    """Configure CORS for the FastAPI application."""
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
    str(origin).rstrip("/")
    for origin in settings.BACKEND_CORS_ORIGINS
],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
