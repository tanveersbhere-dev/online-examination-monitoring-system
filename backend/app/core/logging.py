import logging
import sys

def setup_logging(debug: bool = False):
    """Setup standard logging for the application."""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Suppress verbose third-party loggers if not in debug mode
    if not debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
