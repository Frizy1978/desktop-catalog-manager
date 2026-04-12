from __future__ import annotations

import logging
from pathlib import Path

from app.core.paths import ensure_directory


def configure_logging(logs_dir: Path) -> None:
    ensure_directory(logs_dir)
    log_file = logs_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
