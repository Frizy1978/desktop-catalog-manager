from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.db.session import SqlAlchemyDatabase
from app.integrations.woocommerce_client import WooCommerceClient, WooCommerceClientError
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sync_run_repository import SyncRunRepository
from app.services.wc_image_download_service import WooImageDownloadService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportRunResult:
    success: bool
    counters: dict[str, int]
    errors: list[str]


class WooCommerceImportService:
    def __init__(
        self,
        database: SqlAlchemyDatabase,
        category_repository: CategoryRepository,
        product_repository: ProductRepository,
        sync_run_repository: SyncRunRepository,
        wc_client: WooCommerceClient,
        image_download_service: WooImageDownloadService | None = None,
    ) -> None:
        self._database = database
        self._category_repository = category_repository
        self._product_repository = product_repository
        self._sync_run_repository = sync_run_repository
        self._wc_client = wc_client
        self._image_download_service = image_download_service

    def run_initial_import(
        self,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> ImportRunResult:
        self._emit_progress(progress_callback, 0, "Подготовка импорта...")
        run_id = self._sync_run_repository.start_run("import_from_wc")
        counters = {
            "categories_total": 0,
            "categories_created": 0,
            "categories_updated": 0,
            "products_total": 0,
            "products_created": 0,
            "products_updated": 0,
            "product_category_links": 0,
            "product_images": 0,
            "images_downloaded": 0,
            "images_reused_existing": 0,
            "images_failed": 0,
            "images_legacy_deleted": 0,
            "images_dirs_deleted": 0,
            "category_images_downloaded": 0,
            "category_images_reused_existing": 0,
            "category_images_failed": 0,
            "category_images_deleted": 0,
            "category_images_dirs_deleted": 0,
        }
        errors: list[str] = []
        logger.info("Import run started: run_id=%s", run_id)

        try:
            self._emit_progress(progress_callback, 5, "Загрузка категорий из WooCommerce...")
            category_payloads = self._wc_client.fetch_categories(
                page_callback=lambda page, total: self._emit_progress(
                    progress_callback,
                    self._page_progress(5, 25, page, total),
                    f"Загрузка категорий: страница {page}" + (f" из {total}" if total else ""),
                )
            )
            counters["categories_total"] = len(category_payloads)
            logger.info("Fetched categories from WooCommerce: %s", len(category_payloads))

            with self._database.session_scope() as session:
                total_categories = max(len(category_payloads), 1)
                for index, payload in enumerate(category_payloads, start=1):
                    _, created = self._category_repository.upsert_from_wc_payload(session, payload)
                    if created:
                        counters["categories_created"] += 1
                    else:
                        counters["categories_updated"] += 1
                    self._emit_progress(
                        progress_callback,
                        25 + int((index / total_categories) * 20),
                        f"Сохранение категорий: {index}/{len(category_payloads)}",
                    )
                self._category_repository.bind_parent_links_from_wc(session, category_payloads)
            logger.info(
                "Categories upsert finished: created=%s updated=%s",
                counters["categories_created"],
                counters["categories_updated"],
            )
            self._emit_progress(progress_callback, 47, "Иерархия категорий сохранена")

            self._emit_progress(progress_callback, 50, "Загрузка товаров из WooCommerce...")
            product_payloads = self._wc_client.fetch_products(
                page_callback=lambda page, total: self._emit_progress(
                    progress_callback,
                    self._page_progress(50, 70, page, total),
                    f"Загрузка товаров: страница {page}" + (f" из {total}" if total else ""),
                )
            )
            counters["products_total"] = len(product_payloads)
            logger.info("Fetched products from WooCommerce: %s", len(product_payloads))

            with self._database.session_scope() as session:
                category_id_map = self._category_repository.external_to_local_id_map(session)
                total_products = max(len(product_payloads), 1)
                for index, payload in enumerate(product_payloads, start=1):
                    product, created = self._product_repository.upsert_from_wc_payload(session, payload)
                    session.flush()
                    if created:
                        counters["products_created"] += 1
                    else:
                        counters["products_updated"] += 1

                    linked_categories = self._resolve_product_categories(
                        payload=payload,
                        category_id_map=category_id_map,
                    )
                    self._product_repository.replace_category_links(
                        session,
                        product_id=product.id,
                        category_ids=linked_categories,
                    )
                    counters["product_category_links"] += len(set(linked_categories))

                    images_count = self._product_repository.replace_images_from_wc_payload(
                        session,
                        product_id=product.id,
                        images=self._read_images(payload),
                    )
                    counters["product_images"] += images_count
                    self._emit_progress(
                        progress_callback,
                        70 + int((index / total_products) * 20),
                        f"Сохранение товаров: {index}/{len(product_payloads)}",
                    )
            logger.info(
                "Products upsert finished: created=%s updated=%s product_images=%s",
                counters["products_created"],
                counters["products_updated"],
                counters["product_images"],
            )

            if self._image_download_service is not None:
                self._emit_progress(progress_callback, 90, "Скачивание изображений товаров...")
                product_image_result = self._image_download_service.download_all_missing_product_images()
                counters["images_downloaded"] = product_image_result.downloaded
                counters["images_reused_existing"] = product_image_result.reused_existing
                counters["images_failed"] = product_image_result.failed
                counters["images_legacy_deleted"] = product_image_result.legacy_deleted
                counters["images_dirs_deleted"] = product_image_result.directories_deleted
                if product_image_result.errors:
                    errors.extend(product_image_result.errors)

                self._emit_progress(progress_callback, 96, "Скачивание изображений категорий...")
                category_image_result = self._image_download_service.download_all_missing_category_images()
                counters["category_images_downloaded"] = category_image_result.downloaded
                counters["category_images_reused_existing"] = category_image_result.reused_existing
                counters["category_images_failed"] = category_image_result.failed
                counters["category_images_deleted"] = category_image_result.legacy_deleted
                counters["category_images_dirs_deleted"] = category_image_result.directories_deleted
                if category_image_result.errors:
                    errors.extend(category_image_result.errors)

                logger.info(
                    "Image stages finished: products(downloaded=%s reused=%s failed=%s) categories(downloaded=%s reused=%s failed=%s)",
                    counters["images_downloaded"],
                    counters["images_reused_existing"],
                    counters["images_failed"],
                    counters["category_images_downloaded"],
                    counters["category_images_reused_existing"],
                    counters["category_images_failed"],
                )

            run_status = "success" if not errors else "error"
            self._sync_run_repository.finish_run(
                run_id,
                status=run_status,
                counters=counters,
                errors=errors,
            )
            logger.info("Import run finished: run_id=%s status=%s counters=%s", run_id, run_status, counters)

            if errors:
                self._emit_progress(progress_callback, 100, "Импорт завершен с частичными ошибками")
                return ImportRunResult(success=False, counters=counters, errors=errors)

            self._emit_progress(progress_callback, 100, "Импорт завершен успешно")
            return ImportRunResult(success=True, counters=counters, errors=[])
        except WooCommerceClientError as exc:
            logger.exception(
                "WooCommerce import failed due to API/client error: %s",
                exc.technical_message,
            )
            errors.append(exc.user_message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("WooCommerce import failed unexpectedly")
            errors.append(f"Unexpected import failure: {exc}")

        self._sync_run_repository.finish_run(
            run_id,
            status="error",
            counters=counters,
            errors=errors,
        )
        logger.error("Import run failed: run_id=%s errors=%s", run_id, errors)
        self._emit_progress(progress_callback, 100, "Импорт завершен с ошибкой")
        return ImportRunResult(success=False, counters=counters, errors=errors)

    def _resolve_product_categories(
        self,
        *,
        payload: dict[str, Any],
        category_id_map: dict[int, int],
    ) -> list[int]:
        category_ids: list[int] = []
        for category_payload in payload.get("categories") or []:
            if not isinstance(category_payload, dict):
                continue
            external_id = int(category_payload.get("id") or 0)
            if external_id <= 0:
                continue
            local_id = category_id_map.get(external_id)
            if local_id is not None:
                category_ids.append(local_id)
        return category_ids

    def _read_images(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        images = payload.get("images")
        if not isinstance(images, list):
            return []
        return [item for item in images if isinstance(item, dict)]

    def _emit_progress(
        self,
        progress_callback: Callable[[int, str], None] | None,
        percent: int,
        message: str,
    ) -> None:
        if progress_callback is None:
            return
        safe_percent = max(0, min(100, int(percent)))
        progress_callback(safe_percent, message)

    def _page_progress(
        self,
        start: int,
        end: int,
        page: int,
        total_pages: int | None,
    ) -> int:
        if total_pages is None or total_pages <= 0:
            return start
        clamped_page = max(1, min(page, total_pages))
        ratio = clamped_page / total_pages
        return start + int((end - start) * ratio)
