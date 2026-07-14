import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union

class SystemLogFilter(logging.Filter):
    """Filters out camera and event specific logs from the system.log."""
    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name.startswith("ai_engine.camera") or record.name.startswith("ai_engine.events"))

_logging_configured = False

def setup_logging(
    log_dir: Union[str, Path] = "logs",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    level: str = "INFO"
) -> None:
    global _logging_configured
    if _logging_configured:
        return
        
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Format pattern
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(threadName)s] - %(message)s"
    )
    
    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing root handlers to prevent duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # 1. Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. errors.log Handler (Filters WARNING and higher logs from all loggers)
    errors_handler = RotatingFileHandler(
        filename=log_path / "errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    errors_handler.setLevel(logging.WARNING)
    errors_handler.setFormatter(formatter)
    root_logger.addHandler(errors_handler)
    
    # 3. system.log Handler (Filters general messages excluding camera and events)
    system_handler = RotatingFileHandler(
        filename=log_path / "system.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    system_handler.setLevel(numeric_level)
    system_handler.setFormatter(formatter)
    system_handler.addFilter(SystemLogFilter())
    root_logger.addHandler(system_handler)
    
    # 4. camera.log Handler (Dedicated camera activity logger)
    camera_logger = logging.getLogger("ai_engine.camera")
    camera_logger.setLevel(numeric_level)
    camera_logger.propagate = True  # Propagates warning/error to errors.log and console
    
    # Clear existing handlers to prevent duplication
    camera_logger.handlers.clear()
    
    camera_handler = RotatingFileHandler(
        filename=log_path / "camera.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    camera_handler.setLevel(numeric_level)
    camera_handler.setFormatter(formatter)
    camera_logger.addHandler(camera_handler)
    
    # 5. events.log Handler (Dedicated events activity logger)
    events_logger = logging.getLogger("ai_engine.events")
    events_logger.setLevel(numeric_level)
    events_logger.propagate = True  # Propagates warning/error to errors.log and console
    
    # Clear existing handlers to prevent duplication
    events_logger.handlers.clear()
    
    events_handler = RotatingFileHandler(
        filename=log_path / "events.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    events_handler.setLevel(numeric_level)
    events_handler.setFormatter(formatter)
    events_logger.addHandler(events_handler)
    
    _logging_configured = True
    logging.info("Logging system configured successfully.")
