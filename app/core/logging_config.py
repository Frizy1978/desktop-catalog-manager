from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.paths import ensure_directory


def configure_logging(
    logs_dir: Path,
    *,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 10,
) -> None:
    ensure_directory(logs_dir)
    log_file = logs_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Reconfigure handlers explicitly so settings are always applied.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001
            pass

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s %(threadName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rotating_handler = RotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes=max(1024 * 1024, int(max_bytes)),
        backupCount=max(1, int(backup_count)),
        encoding="utf-8",
    )
    rotating_handler.setLevel(logging.INFO)
    rotating_handler.setFormatter(formatter)
    root_logger.addHandler(rotating_handler)
