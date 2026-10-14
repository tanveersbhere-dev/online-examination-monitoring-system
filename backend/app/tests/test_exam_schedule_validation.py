import pytest
from datetime import datetime, timezone, timedelta
from app.services.exam_service import validate_schedule_rules

def format_duration_human(minutes: number if False else int) -> str:
    if minutes <= 0:
        return '0 minutes'
    hrs = minutes // 60
    mins = minutes % 60
    if hrs == 0:
        return f"{mins} minute{'s' if mins != 1 else ''}"
    if mins == 0:
        return f"{hrs} hour{'s' if hrs != 1 else ''}"
    return f"{hrs} hour{'s' if hrs != 1 else ''} {mins} minute{'s' if mins != 1 else ''}"

def test_case_1_start_in_past():
    """Case 1: Start time yesterday should be rejected with exact past message."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    end = yesterday + timedelta(hours=2)

    with pytest.raises(ValueError) as exc:
        validate_schedule_rules(yesterday, end)
    assert "Exam start time cannot be scheduled in the past." in str(exc.value)

def test_case_2_end_before_start():
    """Case 2: End time before start time should be rejected."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = now + timedelta(days=1, hours=18, minutes=30) # 6:30 PM

    with pytest.raises(ValueError) as exc:
        validate_schedule_rules(start, end)
    assert "End time must be after the start time." in str(exc.value)

def test_case_3_duration_less_than_10_minutes():
    """Case 3: Duration 5 min < 10 min should be rejected."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = now + timedelta(days=1, hours=19, minutes=5) # 7:05 PM

    with pytest.raises(ValueError) as exc:
        validate_schedule_rules(start, end)
    assert "Exam duration must be at least 10 minutes." in str(exc.value)

def test_case_4_duration_10_minutes():
    """Case 4: Duration exactly 10 min should be accepted."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = now + timedelta(days=1, hours=19, minutes=10) # 7:10 PM

    duration = validate_schedule_rules(start, end)
    assert duration == 10
    assert format_duration_human(duration) == "10 minutes"

def test_case_5_duration_1_hour_45_minutes():
    """Case 5: Duration 1 hr 45 min (105 min) should be accepted."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = now + timedelta(days=1, hours=20, minutes=45) # 8:45 PM

    duration = validate_schedule_rules(start, end)
    assert duration == 105
    assert format_duration_human(duration) == "1 hour 45 minutes"

def test_case_6_automatic_duration_recalculation():
    """Case 6: Modify end time repeatedly and verify duration recalculates automatically."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM

    # End 7:30 PM (30 min)
    end1 = start + timedelta(minutes=30)
    dur1 = validate_schedule_rules(start, end1)
    assert dur1 == 30
    assert format_duration_human(dur1) == "30 minutes"

    # Modify End to 9:00 PM (120 min)
    end2 = start + timedelta(minutes=120)
    dur2 = validate_schedule_rules(start, end2)
    assert dur2 == 120
    assert format_duration_human(dur2) == "2 hours"

    # Modify End to 9:15 PM (135 min)
    end3 = start + timedelta(minutes=135)
    dur3 = validate_schedule_rules(start, end3)
    assert dur3 == 135
    assert format_duration_human(dur3) == "2 hours 15 minutes"

def test_max_duration_5_hours_accepted():
    """Start 7:00 PM, End 12:00 AM (5 hours = 300 min) -> Accepted."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = start + timedelta(hours=5) # 12:00 AM (300 min)

    duration = validate_schedule_rules(start, end)
    assert duration == 300
    assert format_duration_human(duration) == "5 hours"

def test_max_duration_exceeded_rejected():
    """Start 7:00 PM, End 12:01 AM (5 hours 1 min = 301 min) -> Rejected with exact message."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1, hours=19) # 7:00 PM
    end = start + timedelta(hours=5, minutes=1) # 12:01 AM (301 min)

    with pytest.raises(ValueError) as exc:
        validate_schedule_rules(start, end)
    assert "Exam duration cannot exceed 5 hours." in str(exc.value)
