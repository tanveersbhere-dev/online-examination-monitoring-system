from pydantic import BaseModel

class ExamRuntimePolicyConfig(BaseModel):
    """
    Part 10: Central Configurable Exam Runtime Policy.
    Universities and institutions can adjust execution parameters 
    without changing underlying business logic or model schemas.
    """
    prep_window_minutes: int = 15
    recovery_buffer_minutes: int = 30
    heartbeat_interval_seconds: int = 5
    heartbeat_miss_threshold: int = 6  # 6 consecutive misses (30s) before interruption logged
    max_recovery_count: int = 5
    suspension_timeout_seconds: int = 1800  # 30 minutes max suspension duration before session expiration
    recovery_window_seconds: int = 900
    device_match_required: bool = True
    browser_match_required: bool = True
    ai_pause_policy: str = "AUTO_PAUSE_ON_INTERRUPTION"
    offline_retry_policy: str = "EXPONENTIAL_BACKOFF"
    duplicate_runtime_policy: str = "LOCK_SECONDARY_TABS"

default_runtime_policy = ExamRuntimePolicyConfig()
