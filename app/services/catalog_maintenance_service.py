from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.paths import ensure_directory


class CatalogMaintenanceService:
    def __init__(self, db_path: Path, backups_dir: Path) -> None:
        self._db_path = db_path
        self._backups_dir = backups_dir
        ensure_directory(backups_dir)

    def clear_catalog_with_backup(self) -> Path:
        if not self._db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self._db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self._backups_dir / f"catalog_backup_{timestamp}.db"

        source = sqlite3.connect(self._db_path)
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.executescript(
                """
                DELETE FROM product_image_versions;
                DELETE FROM product_categories;
                DELETE FROM product_images;
                DELETE FROM products;
                DELETE FROM categories;
                DELETE FROM sync_runs;
                DELETE FROM publish_jobs;
                """
            )
            connection.commit()
        finally:
            connection.close()

        return backup_path
