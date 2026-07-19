"""Application logging configuration."""
from __future__ import annotations

import logging
from pathlib import Path


def configure_logging() -> None:
    """Configure file and console logging for the desktop application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "application.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
