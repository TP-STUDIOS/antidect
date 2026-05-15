import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path(__file__).parent / "antidect.log"

_configured = False

def get(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=512 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root = logging.getLogger("antidect")
        root.setLevel(logging.INFO)
        root.addHandler(handler)
        root.propagate = False
        _configured = True
    return logging.getLogger(f"antidect.{name}")
