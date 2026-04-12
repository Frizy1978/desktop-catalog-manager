from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.db.session import SqlAlchemyDatabase
from app.integrations.woocommerce_client import (
    WooCommerceClient,
    WooCommerceClientError,
)
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sync_run_repository import SyncRunRepository


@dataclass(slots=True)
class ImportRunResult:
    success: bool
    counters: dict[str, int]
    errors: list[str]


logger = logging.getLogger(__name__)


class WooCommerceImportService:
    def __init__(
        self,
        database: SqlAlchemyDatabase,
        category_repository: CategoryRepository,
        product_repository: ProductRepository,
        sync_run_repository: SyncRunRepository,
        wc_client: WooCommerceClient,
    ) -> None:
        self._database = database
        self._category_repository = category_repository
        self._product_repository = product_repository
        self._sync_run_repository = sync_run_repository
        self._wc_client = wc_client

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
        }
        errors: list[str] = []

        try:
            self._emit_progress(progress_callback, 5, "Загрузка категорий из WooCommerce...")
            category_payloads = self._wc_client.fetch_categories(
                page_callback=lambda page, total: self._emit_progress(
                    progress_callback,
                    self._page_progress(5, 25, page, total),
                    f"Загрузка категорий: страница {page}"
                    + (f" из {total}" if total else ""),
                )
            )
            counters["categories_total"] = len(category_payloads)

            with self._database.session_scope() as session:
                total_categories = max(len(category_payloads), 1)
                for index, payload in enumerate(category_payloads, start=1):
                    _, created = self._category_repository.upsert_from_wc_payload(
                        session, payload
                    )
                    if created:
                        counters["categories_created"] += 1
                    else:
                        counters["categories_updated"] += 1
                    self._emit_progress(
                        progress_callback,
                        25 + int((index / total_categories) * 20),
                        f"Сохранение категорий: {index}/{len(category_payloads)}",
                    )
                self._category_repository.bind_parent_links_from_wc(
                    session,
                    category_payloads,
                )
            self._emit_progress(
                progress_callback, 47, "Связывание иерархии категорий завершено"
            )

            self._emit_progress(progress_callback, 50, "Загрузка товаров из WooCommerce...")
            product_payloads = self._wc_client.fetch_products(
                page_callback=lambda page, total: self._emit_progress(
                    progress_callback,
                    self._page_progress(50, 70, page, total),
                    f"Загрузка товаров: страница {page}"
                    + (f" из {total}" if total else ""),
                )
            )
            counters["products_total"] = len(product_payloads)

            with self._database.session_scope() as session:
                category_id_map = self._category_repository.external_to_local_id_map(
                    session
                )
                total_products = max(len(product_payloads), 1)
                for index, payload in enumerate(product_payloads, start=1):
                    product, created = self._product_repository.upsert_from_wc_payload(
                        session, payload
                    )
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
                        70 + int((index / total_products) * 25),
                        f"Сохранение товаров: {index}/{len(product_payloads)}",
                    )

            self._sync_run_repository.finish_run(
                run_id,
                status="success",
                counters=counters,
                errors=[],
            )
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
