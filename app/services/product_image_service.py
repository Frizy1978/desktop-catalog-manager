from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from app.core.paths import ensure_directory
from app.db.session import SqlAlchemyDatabase
from app.repositories.product_repository import ProductRepository
from app.repositories.product_image_repository import ProductImageRepository


class ProductImageService:
    def __init__(
        self,
        *,
        database: SqlAlchemyDatabase,
        repository: ProductImageRepository,
        product_repository: ProductRepository,
        media_root: Path,
    ) -> None:
        self._database = database
        self._repository = repository
        self._product_repository = product_repository
        self._media_root = media_root
        self._product_media_root = ensure_directory(media_root / "products")

    @property
    def product_media_root(self) -> Path:
        return self._product_media_root

    def list_product_images(self, product_id: int) -> list[dict]:
        with self._database.session_scope() as session:
            return self._repository.list_by_product(session, product_id)

    def add_local_image(self, product_id: int, source_path: str) -> dict:
        source_file = Path(source_path).expanduser()
        if not source_file.exists() or not source_file.is_file():
            raise ValueError("Файл изображения не найден.")

        suffix = source_file.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            raise ValueError("Поддерживаются только изображения: jpg, jpeg, png, webp, bmp, gif.")

        with self._database.session_scope() as session:
            if not self._repository.ensure_product_exists(session, product_id):
                raise ValueError("Товар не найден или находится в архиве.")

        product_dir = ensure_directory(self._product_media_root / str(product_id))
        target_name = f"{uuid4().hex}{suffix}"
        target_file = product_dir / target_name
        shutil.copy2(source_file, target_file)

        try:
            with self._database.session_scope() as session:
                image = self._repository.add_local_image(
                    session,
                    product_id=product_id,
                    original_path=str(source_file),
                    local_path=str(target_file),
                    metadata={
                        "original_filename": source_file.name,
                        "storage_kind": "local_file",
                    },
                )
                self._product_repository.mark_modified_local(session, product_id)
                return image
        except Exception:
            if target_file.exists() and target_file.is_file():
                target_file.unlink()
            raise

    def set_primary_image(self, product_id: int, image_id: int) -> bool:
        with self._database.session_scope() as session:
            updated = self._repository.set_primary(
                session,
                product_id=product_id,
                image_id=image_id,
            )
            if updated:
                self._product_repository.mark_modified_local(session, product_id)
            return updated

    def remove_image(self, product_id: int, image_id: int) -> bool:
        with self._database.session_scope() as session:
            removed = self._repository.remove_image(
                session,
                product_id=product_id,
                image_id=image_id,
            )
            if removed is not None:
                self._product_repository.mark_modified_local(session, product_id)
        if removed is None:
            return False

        local_path = removed.get("local_path")
        if isinstance(local_path, str) and local_path.strip():
            self._delete_managed_file(Path(local_path))
        return True

    def get_preview_path(self, image_row: dict) -> Path | None:
        local_path = str(image_row.get("local_path") or "").strip()
        if local_path:
            candidate = Path(local_path)
            if candidate.exists() and candidate.is_file():
                return candidate

        original_path = str(image_row.get("original_path") or "").strip()
        if not original_path:
            return None
        candidate = Path(original_path)
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def _delete_managed_file(self, file_path: Path) -> None:
        try:
            resolved_file = file_path.resolve(strict=False)
            resolved_root = self._product_media_root.resolve(strict=False)
        except Exception:
            return
        if resolved_root not in resolved_file.parents:
            return
        if resolved_file.exists() and resolved_file.is_file():
            resolved_file.unlink()
