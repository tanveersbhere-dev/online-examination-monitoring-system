from datetime import datetime, timezone, timedelta
import zoneinfo
from app.core.config import settings

def get_utc_now() -> datetime:
    """
    Returns a timezone-naive datetime representing the current UTC time.
    This serves as the single datetime strategy for all internal backend logic
    to avoid offset-aware vs offset-naive mixing issues with asyncpg.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def to_presentation_tz(dt: datetime) -> datetime:
    """
    Converts a naive or aware UTC datetime to a timezone-aware datetime in the APP_TIMEZONE.
    Useful for formatting dates in emails or API responses.
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        dt_aware_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_aware_utc = dt.astimezone(timezone.utc)
    
    # Convert to target timezone (with fallback to UTC+5 for Asia/Karachi on Windows if tzdata missing)
    try:
        target_tz = zoneinfo.ZoneInfo(settings.APP_TIMEZONE)
    except Exception:
        if settings.APP_TIMEZONE in ["Asia/Karachi", "PKT"]:
            target_tz = timezone(timedelta(hours=5), name="PKT")
        else:
            target_tz = timezone.utc
        
    return dt_aware_utc.astimezone(target_tz)
