import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "app.log"
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on reload/re-import.
    for existing in root_logger.handlers:
        if isinstance(existing, TimedRotatingFileHandler) and str(existing.baseFilename) == str(log_file):
            return

    root_logger.addHandler(handler)
