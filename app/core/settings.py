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
        # Runtime settings must reflect latest saved .env values immediately.
        os.environ[key] = value


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


def _read_int_env(key: str, default: int) -> int:
    raw_value = _read_env(key, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(slots=True)
class AppSettings:
    app_name: str
    app_data_dir: Path
    db_path: Path
    media_dir: Path
    logs_dir: Path
    default_admin_username: str
    default_admin_password: str
    wc_base_url: str
    wc_consumer_key: str
    wc_consumer_secret: str
    wp_base_url: str
    wp_username: str
    wp_application_password: str
    wc_timeout_seconds: int
    wc_verify_ssl: bool
    log_max_bytes: int
    log_backup_count: int

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
            wc_base_url=_read_env("FISHOLHA_WC_BASE_URL", "https://fisholha.ru/"),
            wc_consumer_key=_read_env("FISHOLHA_WC_CONSUMER_KEY", ""),
            wc_consumer_secret=_read_env("FISHOLHA_WC_CONSUMER_SECRET", ""),
            wp_base_url=_read_env("FISHOLHA_WP_BASE_URL", "https://fisholha.ru/"),
            wp_username=_read_env("FISHOLHA_WP_USERNAME", ""),
            wp_application_password=_read_env("FISHOLHA_WP_APPLICATION_PASSWORD", ""),
            wc_timeout_seconds=_read_int_env("FISHOLHA_WC_TIMEOUT_SECONDS", 20),
            wc_verify_ssl=_read_env("FISHOLHA_WC_VERIFY_SSL", "true").lower()
            in {"1", "true", "yes", "on"},
            log_max_bytes=max(1024 * 1024, _read_int_env("FISHOLHA_LOG_MAX_BYTES", 5 * 1024 * 1024)),
            log_backup_count=max(1, _read_int_env("FISHOLHA_LOG_BACKUP_COUNT", 10)),
        )
