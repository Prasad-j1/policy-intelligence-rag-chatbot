import logging
from pathlib import Path
from backend.config import LOGS_PATH, LOG_LEVEL

# Make sure the logs/ folder actually exists before we try to write to it
Path(LOGS_PATH).mkdir(parents=True, exist_ok=True)

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Track which loggers we've already configured, so calling get_logger()
# multiple times for the same module doesn't attach duplicate handlers
_configured_loggers = set()


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger configured to write to both:
      - logs/app.log     (everything: INFO and above)
      - logs/errors.log  (only ERROR and above)
    and also print to the console during local development.

    Usage in any file:
        from backend.utils.logger import get_logger
        logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if name in _configured_loggers:
        return logger  # already set up, avoid duplicate handlers

    logger.setLevel(LOG_LEVEL)

    formatter = logging.Formatter(_LOG_FORMAT)

    # General log file — everything at LOG_LEVEL and above
    app_file_handler = logging.FileHandler(f"{LOGS_PATH}/app.log", encoding="utf-8")
    app_file_handler.setLevel(LOG_LEVEL)
    app_file_handler.setFormatter(formatter)

    # Error-only log file — makes it fast to find what broke without
    # scrolling through normal INFO noise
    error_file_handler = logging.FileHandler(f"{LOGS_PATH}/errors.log", encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    # Console output — so you can see logs live while running locally
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    logger.addHandler(app_file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)

    _configured_loggers.add(name)

    return logger