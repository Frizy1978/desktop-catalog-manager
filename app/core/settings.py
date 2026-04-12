from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import ensure_directory


def _load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _default_app_data_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "FishOlhaCatalogManager"
    return Path.home() / ".fisholha_catalog_manager"


def _read_env(key: str, default: str) -> str:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    value = raw_value.strip()
    return value if value else default


@dataclass(slots=True)
class AppSettings:
    app_name: str
    app_data_dir: Path
    db_path: Path
    media_dir: Path
    logs_dir: Path
    default_admin_username: str
    default_admin_password: str

    @classmethod
    def load(cls) -> "AppSettings":
        _load_env_file(Path(".env"))

        app_data_dir = Path(
            _read_env("FISHOLHA_APP_DATA_DIR", str(_default_app_data_dir()))
        )
        db_path = Path(_read_env("FISHOLHA_DB_PATH", str(app_data_dir / "catalog.db")))

        media_dir = app_data_dir / "media"
        logs_dir = app_data_dir / "logs"

        ensure_directory(app_data_dir)
        ensure_directory(media_dir)
        ensure_directory(logs_dir)
        ensure_directory(db_path.parent)

        return cls(
            app_name="Fish Olha Desktop Catalog Manager",
            app_data_dir=app_data_dir,
            db_path=db_path,
            media_dir=media_dir,
            logs_dir=logs_dir,
            default_admin_username=_read_env("FISHOLHA_DEFAULT_ADMIN_USERNAME", "admin"),
            default_admin_password=_read_env(
                "FISHOLHA_DEFAULT_ADMIN_PASSWORD", "admin123"
            ),
        )
