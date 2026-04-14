from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.session import SqlAlchemyDatabase
from app.integrations.wp_media_client import (
    WordPressMediaClient,
    WordPressMediaClientError,
)
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_image_repository import ProductImageRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CategoryImageResolveResult:
    image_src: str | None
    uploaded: int
    reused: int


@dataclass(slots=True)
class ProductImagesResolveResult:
    images_payload: list[dict[str, Any]]
    uploaded: int
    reused: int


class WooMediaPublishService:
    def __init__(
        self,
        *,
        database: SqlAlchemyDatabase,
        category_repository: CategoryRepository,
        product_image_repository: ProductImageRepository,
        wp_media_client: WordPressMediaClient | None = None,
    ) -> None:
        self._database = database
        self._category_repository = category_repository
        self._product_image_repository = product_image_repository
        self._wp_media_client = wp_media_client

    def resolve_category_image(
        self,
        *,
        category_id: int,
        image_source_url: str | None,
        image_local_path: str | None,
    ) -> CategoryImageResolveResult:
        source_url = (image_source_url or "").strip()
        local_path = (image_local_path or "").strip()

        if local_path:
            candidate = Path(local_path)
            if source_url and self._is_remote_url(source_url):
                return CategoryImageResolveResult(image_src=source_url, uploaded=0, reused=1)
            if not candidate.exists() or not candidate.is_file():
                raise ValueError(f"Файл изображения категории не найден: {candidate}")

            uploaded = self._upload_local_file(candidate)
            uploaded_source_url = str(uploaded.get("source_url") or "").strip()
            media_id = int(uploaded.get("id") or 0)
            if not uploaded_source_url:
                raise WordPressMediaClientError(
                    "WordPress не вернул URL загруженного изображения категории.",
                    technical_message=f"category_media_upload_missing_source_url: {uploaded}",
                )

            with self._database.session_scope() as session:
                self._category_repository.set_published_image_source_url(
                    session,
                    category_id=category_id,
                    source_url=uploaded_source_url,
                )

            logger.info(
                "Category image uploaded: category_id=%s media_id=%s source_url=%s",
                category_id,
                media_id,
                uploaded_source_url,
            )
            return CategoryImageResolveResult(image_src=uploaded_source_url, uploaded=1, reused=0)

        if source_url and self._is_remote_url(source_url):
            return CategoryImageResolveResult(image_src=source_url, uploaded=0, reused=1)
        return CategoryImageResolveResult(image_src=None, uploaded=0, reused=0)

    def resolve_product_images(self, *, product_id: int) -> ProductImagesResolveResult:
        with self._database.session_scope() as session:
            image_rows = self._product_image_repository.list_for_publish(session, product_id)

        if not image_rows:
            return ProductImagesResolveResult(images_payload=[], uploaded=0, reused=0)

        payload: list[dict[str, Any]] = []
        uploaded_count = 0
        reused_count = 0

        for position, image_row in enumerate(image_rows):
            image_id = int(image_row["id"])
            source_url = self._resolve_single_product_image(image_row=image_row)
            if source_url is None:
                continue

            if bool(image_row.get("_uploaded_now")):
                uploaded_count += 1
            else:
                reused_count += 1
            payload.append({"src": source_url, "position": position})

            uploaded_meta = image_row.get("_uploaded_meta")
            if isinstance(uploaded_meta, dict):
                with self._database.session_scope() as session:
                    self._product_image_repository.set_wc_media_mapping(
                        session,
                        image_id=image_id,
                        wc_media_id=int(uploaded_meta.get("media_id") or 0),
                        wc_source_url=str(uploaded_meta.get("source_url") or ""),
                    )

        return ProductImagesResolveResult(
            images_payload=payload,
            uploaded=uploaded_count,
            reused=reused_count,
        )

    def _resolve_single_product_image(self, *, image_row: dict[str, Any]) -> str | None:
        metadata = image_row.get("metadata") or {}
        if isinstance(metadata, dict):
            meta_source_url = str(metadata.get("wc_source_url") or "").strip()
            if meta_source_url and self._is_remote_url(meta_source_url):
                image_row["_uploaded_now"] = False
                return meta_source_url

        source_type = str(image_row.get("source_type") or "").strip()
        original_path = str(image_row.get("original_path") or "").strip()
        local_path = str(image_row.get("local_path") or "").strip()

        if source_type == "wc_url" and self._is_remote_url(original_path):
            image_row["_uploaded_now"] = False
            return original_path

        if local_path:
            local_file = Path(local_path)
            if local_file.exists() and local_file.is_file():
                uploaded = self._upload_local_file(local_file)
                uploaded_source_url = str(uploaded.get("source_url") or "").strip()
                media_id = int(uploaded.get("id") or 0)
                if not uploaded_source_url:
                    raise WordPressMediaClientError(
                        "WordPress не вернул URL загруженного изображения товара.",
                        technical_message=f"product_media_upload_missing_source_url: {uploaded}",
                    )
                image_row["_uploaded_now"] = True
                image_row["_uploaded_meta"] = {
                    "media_id": media_id,
                    "source_url": uploaded_source_url,
                }
                return uploaded_source_url

        if self._is_remote_url(original_path):
            image_row["_uploaded_now"] = False
            return original_path

        if original_path:
            original_file = Path(original_path)
            if original_file.exists() and original_file.is_file():
                uploaded = self._upload_local_file(original_file)
                uploaded_source_url = str(uploaded.get("source_url") or "").strip()
                media_id = int(uploaded.get("id") or 0)
                if not uploaded_source_url:
                    raise WordPressMediaClientError(
                        "WordPress не вернул URL загруженного изображения товара.",
                        technical_message=f"product_original_upload_missing_source_url: {uploaded}",
                    )
                image_row["_uploaded_now"] = True
                image_row["_uploaded_meta"] = {
                    "media_id": media_id,
                    "source_url": uploaded_source_url,
                }
                return uploaded_source_url

        raise ValueError(
            f"Изображение товара #{int(image_row.get('id') or 0)} не имеет доступного пути/URL для публикации"
        )

    def _upload_local_file(self, file_path: Path) -> dict[str, Any]:
        if self._wp_media_client is None:
            raise WordPressMediaClientError(
                "Не настроен отдельный WordPress media-клиент. Заполните wp_base_url, wp_username и wp_application_password.",
                technical_message="wp_media_client_not_configured",
            )
        return self._wp_media_client.upload_media(file_path)

    def _is_remote_url(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered.startswith("http://") or lowered.startswith("https://")
