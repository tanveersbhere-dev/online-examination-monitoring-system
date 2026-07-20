from datetime import datetime, timezone
import zoneinfo
from app.core.config import settings

def get_utc_now() -> datetime:
    """
    Returns a timezone-naive datetime representing the current UTC time.
    This serves as the single datetime strategy for all internal backend logic
    to avoid offset-aware vs offset-naive mixing issues with asyncpg.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def to_presentation_tz(dt_naive_utc: datetime) -> datetime:
    """
    Converts a naive UTC datetime to a timezone-aware datetime in the APP_TIMEZONE.
    Useful for formatting dates in emails or API responses.
    """
    # First, make it aware in UTC
    dt_aware_utc = dt_naive_utc.replace(tzinfo=timezone.utc)
    
    # Convert to the target timezone
    try:
        target_tz = zoneinfo.ZoneInfo(settings.APP_TIMEZONE)
    except Exception:
        # Fallback to UTC if timezone is invalid
        target_tz = timezone.utc
        
    return dt_aware_utc.astimezone(target_tz)
