from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.database.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def check_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint to verify backend status, DB connectivity, and AI Engine status placeholder.
    """
    # Check DB
    db_status = "offline"
    try:
        if not settings.TESTING:
            result = await db.execute(text("SELECT 1"))
            if result.scalar() == 1:
                db_status = "online"
        else:
            # During isolated tests where DB might not be fully up
            db_status = "online (test mode)"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    return {
        "status": "online",
        "version": "1.0.0",
        "database": db_status,
        "ai_engine": "enabled" if settings.AI_ENGINE_ENABLED else "disabled",
        "environment": "debug" if settings.DEBUG else "production"
    }
