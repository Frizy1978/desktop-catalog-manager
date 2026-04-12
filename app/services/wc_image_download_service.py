from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

from app.core.paths import ensure_directory
from app.db.session import SqlAlchemyDatabase
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_image_repository import ProductImageRepository

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/gif": ".gif",
}


@dataclass(slots=True)
class ImageDownloadResult:
    total_pending: int
    downloaded: int
    reused_existing: int
    failed: int
    errors: list[str]
    legacy_deleted: int = 0
    directories_deleted: int = 0


class WooImageDownloadService:
    def __init__(
        self,
        *,
        database: SqlAlchemyDatabase,
        product_repository: ProductImageRepository,
        category_repository: CategoryRepository,
        media_root: Path,
        timeout_seconds: int = 20,
        verify_ssl: bool = True,
        retries: int = 2,
    ) -> None:
        self._database = database
        self._product_repository = product_repository
        self._category_repository = category_repository
        self._timeout_seconds = max(5, int(timeout_seconds))
        self._verify_ssl = bool(verify_ssl)
        self._retries = max(0, int(retries))
        self._product_media_root = ensure_directory(media_root / "products")
        self._category_media_root = ensure_directory(media_root / "categories")

    # Backward-compatible alias.
    def download_missing_images(self) -> ImageDownloadResult:
        return self.download_all_missing_product_images()

    def download_all_missing_product_images(self) -> ImageDownloadResult:
        with self._database.session_scope() as session:
            pending_rows = self._product_repository.list_wc_images_without_local_path(session)
            existing_rows = self._product_repository.list_wc_images(session)

        logger.info(
            "Product images download started: pending=%s existing=%s",
            len(pending_rows),
            len(existing_rows),
        )

        existing_local_by_url = self._existing_local_by_url(
            rows=existing_rows,
            source_key="source_url",
            local_key="local_path",
        )
        result = self._download_missing_entities(
            pending_rows=pending_rows,
            existing_local_by_url=existing_local_by_url,
            source_key="source_url",
            id_key="id",
            build_target_path=lambda row, ext: self._build_product_target_path(
                product_id=int(row["product_id"]),
                image_id=int(row["id"]),
                extension=ext,
            ),
            update_local_path=lambda row, path: self._set_product_local_path(
                image_id=int(row["id"]),
                local_path=path,
            ),
            entity_label="product_image",
        )

        files_deleted, dirs_deleted = self._cleanup_product_media()
        result.legacy_deleted += files_deleted
        result.directories_deleted += dirs_deleted
        logger.info(
            "Product images download finished: downloaded=%s reused=%s failed=%s cleaned_files=%s cleaned_dirs=%s",
            result.downloaded,
            result.reused_existing,
            result.failed,
            files_deleted,
            dirs_deleted,
        )
        return result

    def download_all_missing_category_images(self) -> ImageDownloadResult:
        with self._database.session_scope() as session:
            pending_rows = self._category_repository.list_categories_missing_local_image(session)
            existing_rows = self._category_repository.list_categories_with_local_image(session)

        logger.info(
            "Category images download started: pending=%s existing=%s",
            len(pending_rows),
            len(existing_rows),
        )

        existing_local_by_url = self._existing_local_by_url(
            rows=existing_rows,
            source_key="source_url",
            local_key="local_path",
        )
        result = self._download_missing_entities(
            pending_rows=pending_rows,
            existing_local_by_url=existing_local_by_url,
            source_key="source_url",
            id_key="category_id",
            build_target_path=lambda row, ext: self._build_category_target_path(
                category_id=int(row["category_id"]),
                extension=ext,
            ),
            update_local_path=lambda row, path: self._set_category_local_path(
                category_id=int(row["category_id"]),
                local_path=path,
            ),
            entity_label="category_image",
        )

        files_deleted, dirs_deleted = self._cleanup_category_media()
        result.legacy_deleted += files_deleted
        result.directories_deleted += dirs_deleted
        logger.info(
            "Category images download finished: downloaded=%s reused=%s failed=%s cleaned_files=%s cleaned_dirs=%s",
            result.downloaded,
            result.reused_existing,
            result.failed,
            files_deleted,
            dirs_deleted,
        )
        return result

    def _download_missing_entities(
        self,
        *,
        pending_rows: list[dict],
        existing_local_by_url: dict[str, Path],
        source_key: str,
        id_key: str,
        build_target_path: Callable[[dict, str], Path],
        update_local_path: Callable[[dict, Path], bool],
        entity_label: str,
    ) -> ImageDownloadResult:
        downloaded = 0
        reused_existing = 0
        failed = 0
        errors: list[str] = []
        local_cache_by_url: dict[str, Path] = {}

        for row in pending_rows:
            source_url = str(row.get(source_key) or "").strip()
            if not source_url:
                continue
            row_id = int(row[id_key])

            preferred_ext = self._resolve_extension_from_url(source_url)
            target_path = build_target_path(row, preferred_ext)

            try:
                if target_path.exists() and target_path.is_file():
                    if not update_local_path(row, target_path):
                        raise ValueError(f"record #{row_id} not found")
                    local_cache_by_url[source_url] = target_path
                    reused_existing += 1
                    continue

                reusable = self._resolve_reusable_source(
                    source_url=source_url,
                    existing_local_by_url=existing_local_by_url,
                    local_cache_by_url=local_cache_by_url,
                )
                if reusable is not None:
                    ensure_directory(target_path.parent)
                    if reusable.resolve(strict=False) != target_path.resolve(strict=False):
                        shutil.copy2(reusable, target_path)
                    if not update_local_path(row, target_path):
                        raise ValueError(f"record #{row_id} not found")
                    local_cache_by_url[source_url] = target_path
                    reused_existing += 1
                    continue

                payload, response_ext = self._download_binary_with_retries(source_url)
                if response_ext != preferred_ext:
                    target_path = build_target_path(row, response_ext)
                ensure_directory(target_path.parent)
                target_path.write_bytes(payload)

                if not update_local_path(row, target_path):
                    raise ValueError(f"record #{row_id} not found")
                local_cache_by_url[source_url] = target_path
                downloaded += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                logger.exception(
                    "Failed to process %s id=%s url=%s",
                    entity_label,
                    row_id,
                    source_url,
                )
                if len(errors) < 25:
                    errors.append(f"{entity_label} #{row_id}: {exc}")

        if failed > len(errors):
            errors.append(f"Дополнительно ошибок: {failed - len(errors)}.")

        logger.info(
            "%s processed: total=%s downloaded=%s reused=%s failed=%s",
            entity_label,
            len(pending_rows),
            downloaded,
            reused_existing,
            failed,
        )
        return ImageDownloadResult(
            total_pending=len(pending_rows),
            downloaded=downloaded,
            reused_existing=reused_existing,
            failed=failed,
            errors=errors,
        )

    def _resolve_reusable_source(
        self,
        *,
        source_url: str,
        existing_local_by_url: dict[str, Path],
        local_cache_by_url: dict[str, Path],
    ) -> Path | None:
        candidate = local_cache_by_url.get(source_url) or existing_local_by_url.get(source_url)
        if candidate is None:
            return None
        if not candidate.exists() or not candidate.is_file():
            return None
        return candidate

    def _existing_local_by_url(
        self,
        *,
        rows: list[dict],
        source_key: str,
        local_key: str,
    ) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for row in rows:
            source_url = str(row.get(source_key) or "").strip()
            local_path = str(row.get(local_key) or "").strip()
            if not source_url or not local_path:
                continue
            candidate = Path(local_path)
            if not candidate.exists() or not candidate.is_file():
                continue
            if source_url not in result:
                result[source_url] = candidate
        return result

    def _download_binary_with_retries(self, source_url: str) -> tuple[bytes, str]:
        attempts = self._retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(
                    source_url,
                    timeout=self._timeout_seconds,
                    verify=self._verify_ssl,
                )
                if response.status_code >= 400:
                    raise ValueError(f"server returned HTTP {response.status_code}")
                payload = response.content
                if not payload:
                    raise ValueError("empty response while downloading image")
                ext = self._resolve_extension_from_response(response.headers.get("Content-Type", ""))
                return payload, ext
            except (requests.Timeout, requests.ConnectionError, requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < attempts:
                    logger.warning(
                        "Retry %s/%s for image url=%s due to: %s",
                        attempt + 1,
                        attempts,
                        source_url,
                        exc,
                    )
                    continue

        if last_error is None:
            raise ValueError("unknown image download error")
        raise last_error

    def _build_product_target_path(self, *, product_id: int, image_id: int, extension: str) -> Path:
        product_dir = ensure_directory(self._product_media_root / str(product_id))
        return product_dir / f"{image_id}{extension}"

    def _build_category_target_path(self, *, category_id: int, extension: str) -> Path:
        category_dir = ensure_directory(self._category_media_root / str(category_id))
        return category_dir / f"{category_id}{extension}"

    def _set_product_local_path(self, *, image_id: int, local_path: Path) -> bool:
        with self._database.session_scope() as session:
            return self._product_repository.set_local_path(
                session,
                image_id=image_id,
                local_path=str(local_path),
            )

    def _set_category_local_path(self, *, category_id: int, local_path: Path) -> bool:
        with self._database.session_scope() as session:
            return self._category_repository.set_category_image_local_path(
                session,
                category_id=category_id,
                local_path=str(local_path),
            )

    def _cleanup_product_media(self) -> tuple[int, int]:
        with self._database.session_scope() as session:
            image_rows = self._product_repository.list_wc_images(session)
            existing_product_ids = self._product_repository.list_existing_product_ids(session)

        referenced = {
            Path(str(row.get("local_path") or "").strip()).resolve(strict=False)
            for row in image_rows
            if str(row.get("local_path") or "").strip()
        }
        return self._cleanup_media_root(
            root=self._product_media_root,
            referenced_files=referenced,
            existing_numeric_ids=existing_product_ids,
            is_managed_file=lambda path, _entity_id: (
                path.suffix.lower() in _ALLOWED_EXTENSIONS and path.stem.isdigit()
            ),
        )

    def _cleanup_category_media(self) -> tuple[int, int]:
        with self._database.session_scope() as session:
            image_rows = self._category_repository.list_categories_with_local_image(session)
            existing_category_ids = self._category_repository.list_existing_category_ids(session)

        referenced = {
            Path(str(row.get("local_path") or "").strip()).resolve(strict=False)
            for row in image_rows
            if str(row.get("local_path") or "").strip()
        }
        return self._cleanup_media_root(
            root=self._category_media_root,
            referenced_files=referenced,
            existing_numeric_ids=existing_category_ids,
            is_managed_file=lambda path, entity_id: (
                path.suffix.lower() in _ALLOWED_EXTENSIONS and path.stem == str(entity_id)
            ),
        )

    def _cleanup_media_root(
        self,
        *,
        root: Path,
        referenced_files: set[Path],
        existing_numeric_ids: set[int],
        is_managed_file: Callable[[Path, int], bool],
    ) -> tuple[int, int]:
        if not root.exists() or not root.is_dir():
            return 0, 0

        files_deleted = 0
        dirs_deleted = 0
        for entity_dir in sorted(root.iterdir()):
            if not entity_dir.exists() or not entity_dir.is_dir() or not entity_dir.name.isdigit():
                continue
            entity_id = int(entity_dir.name)

            if entity_id not in existing_numeric_ids:
                try:
                    shutil.rmtree(entity_dir)
                    dirs_deleted += 1
                except OSError:
                    logger.warning("Cannot remove orphan media directory: %s", entity_dir)
                continue

            for file_path in list(entity_dir.rglob("*")):
                if not file_path.exists() or not file_path.is_file():
                    continue
                if not is_managed_file(file_path, entity_id):
                    continue
                resolved = file_path.resolve(strict=False)
                if resolved in referenced_files:
                    continue
                try:
                    file_path.unlink()
                    files_deleted += 1
                except OSError:
                    logger.warning("Cannot delete unreferenced media file: %s", file_path)

            for nested in sorted(entity_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if not nested.exists() or not nested.is_dir():
                    continue
                try:
                    next(nested.iterdir())
                except StopIteration:
                    try:
                        nested.rmdir()
                        dirs_deleted += 1
                    except OSError:
                        logger.warning("Cannot remove empty media directory: %s", nested)

            if entity_dir.exists() and entity_dir.is_dir():
                try:
                    next(entity_dir.iterdir())
                except StopIteration:
                    try:
                        entity_dir.rmdir()
                        dirs_deleted += 1
                    except OSError:
                        logger.warning("Cannot remove empty media directory: %s", entity_dir)

        return files_deleted, dirs_deleted

    def _resolve_extension_from_url(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix in _ALLOWED_EXTENSIONS:
            return suffix
        return ".jpg"

    def _resolve_extension_from_response(self, content_type: str) -> str:
        normalized = content_type.split(";")[0].strip().lower()
        return _CONTENT_TYPE_EXTENSIONS.get(normalized, ".jpg")
