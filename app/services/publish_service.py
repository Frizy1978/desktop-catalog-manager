from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from app.db.session import SqlAlchemyDatabase
from app.integrations.woocommerce_client import WooCommerceClient, WooCommerceClientError
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publish_job_repository import PublishJobRepository
from app.repositories.sync_run_repository import SyncRunRepository
from app.services.wc_media_publish_service import WooMediaPublishService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PublishRunResult:
    success: bool
    counters: dict[str, int]
    errors: list[str]


class WooCommercePublishService:
    def __init__(
        self,
        *,
        database: SqlAlchemyDatabase,
        category_repository: CategoryRepository,
        product_repository: ProductRepository,
        sync_run_repository: SyncRunRepository,
        publish_job_repository: PublishJobRepository,
        wc_client: WooCommerceClient,
        media_publish_service: WooMediaPublishService | None = None,
    ) -> None:
        self._database = database
        self._category_repository = category_repository
        self._product_repository = product_repository
        self._sync_run_repository = sync_run_repository
        self._publish_job_repository = publish_job_repository
        self._wc_client = wc_client
        self._media_publish_service = media_publish_service

    def run_publish(
        self,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> PublishRunResult:
        self._emit_progress(progress_callback, 0, "Подготовка публикации...")
        run_id = self._sync_run_repository.start_run("publish_to_wc")

        with self._database.session_scope() as session:
            categories = self._category_repository.list_categories_for_publish(session)
            products = self._product_repository.list_products_for_publish(session)

        entities_payload = {
            "categories": [int(row["id"]) for row in categories],
            "products": [int(row["id"]) for row in products],
        }
        publish_job_id = self._publish_job_repository.start_job(
            target="wc",
            entities=entities_payload,
        )

        counters = {
            "categories_total": len(categories),
            "categories_created": 0,
            "categories_updated": 0,
            "categories_failed": 0,
            "category_images_uploaded": 0,
            "category_images_reused": 0,
            "category_images_failed": 0,
            "products_total": len(products),
            "products_created": 0,
            "products_updated": 0,
            "products_failed": 0,
            "product_images_uploaded": 0,
            "product_images_reused": 0,
            "product_images_failed": 0,
        }
        errors: list[str] = []
        details: dict[str, list[dict[str, Any]]] = {"categories": [], "products": []}

        logger.info(
            "Publish run started: run_id=%s job_id=%s categories=%s products=%s",
            run_id,
            publish_job_id,
            len(categories),
            len(products),
        )

        if not categories and not products:
            self._finish_run(
                run_id=run_id,
                publish_job_id=publish_job_id,
                counters=counters,
                errors=[],
                details=details,
            )
            self._emit_progress(progress_callback, 100, "Нет изменений для публикации")
            return PublishRunResult(success=True, counters=counters, errors=[])

        self._publish_categories(
            categories=categories,
            counters=counters,
            errors=errors,
            details=details["categories"],
            progress_callback=progress_callback,
        )
        self._publish_products(
            products=products,
            counters=counters,
            errors=errors,
            details=details["products"],
            progress_callback=progress_callback,
        )

        self._finish_run(
            run_id=run_id,
            publish_job_id=publish_job_id,
            counters=counters,
            errors=errors,
            details=details,
        )
        if errors:
            self._emit_progress(progress_callback, 100, "Публикация завершена с ошибками")
            return PublishRunResult(success=False, counters=counters, errors=errors)

        self._emit_progress(progress_callback, 100, "Публикация завершена успешно")
        return PublishRunResult(success=True, counters=counters, errors=[])

    def _publish_categories(
        self,
        *,
        categories: list[dict[str, Any]],
        counters: dict[str, int],
        errors: list[str],
        details: list[dict[str, Any]],
        progress_callback: Callable[[int, str], None] | None,
    ) -> None:
        ordered_categories = self._order_categories_for_publish(categories)
        with self._database.session_scope() as session:
            category_wc_map = self._category_repository.category_wc_mapping_by_local_id(
                session
            )

        total = max(1, len(ordered_categories))
        for index, row in enumerate(ordered_categories, start=1):
            category_id = int(row["id"])
            category_name = str(row.get("name") or "")
            self._emit_progress(
                progress_callback,
                5 + int((index / total) * 40),
                f"Публикация категорий: {index}/{len(ordered_categories)}",
            )

            with self._database.session_scope() as session:
                self._category_repository.set_publish_pending(session, category_id)

            try:
                category_image_src: str | None = None
                media_warning: str | None = None
                if self._media_publish_service is not None:
                    try:
                        image_result = self._media_publish_service.resolve_category_image(
                            category_id=category_id,
                            image_source_url=row.get("image_source_url"),
                            image_local_path=row.get("image_local_path"),
                        )
                        category_image_src = image_result.image_src
                        counters["category_images_uploaded"] += image_result.uploaded
                        counters["category_images_reused"] += image_result.reused
                    except Exception as media_exc:  # noqa: BLE001
                        counters["category_images_failed"] += 1
                        media_warning = self._error_message(media_exc)
                        raw_image_src = str(row.get("image_source_url") or "").strip()
                        if self._is_remote_url(raw_image_src):
                            category_image_src = raw_image_src
                            counters["category_images_reused"] += 1
                        logger.warning(
                            "Category image publish skipped for category_id=%s: %s",
                            category_id,
                            media_warning,
                        )
                else:
                    raw_image_src = str(row.get("image_source_url") or "").strip()
                    category_image_src = raw_image_src if self._is_remote_url(raw_image_src) else None

                payload = self._build_category_payload(
                    row,
                    category_wc_map=category_wc_map,
                    image_src=category_image_src,
                )
                external_wc_id = row.get("external_wc_id")
                response: dict[str, Any]
                action: str
                if external_wc_id is None:
                    response = self._wc_client.create_category(payload)
                    action = "created"
                else:
                    try:
                        response = self._wc_client.update_category(int(external_wc_id), payload)
                        action = "updated"
                    except WooCommerceClientError as exc:
                        if exc.status_code == 404:
                            response = self._wc_client.create_category(payload)
                            action = "created_missing_remote"
                        else:
                            raise

                resolved_wc_id = int(response.get("id") or external_wc_id or 0)
                if resolved_wc_id <= 0:
                    raise ValueError("WooCommerce не вернул id категории")

                with self._database.session_scope() as session:
                    self._category_repository.mark_publish_success(
                        session,
                        category_id=category_id,
                        external_wc_id=resolved_wc_id,
                    )
                category_wc_map[category_id] = resolved_wc_id

                if action.startswith("created"):
                    counters["categories_created"] += 1
                else:
                    counters["categories_updated"] += 1
                details.append(
                    {
                        "id": category_id,
                        "wc_id": resolved_wc_id,
                        "name": category_name,
                        "action": action,
                        "status": "success",
                        "media_warning": media_warning,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                message = (
                    f"Категория #{category_id} '{category_name}': "
                    f"{self._error_message(exc)}"
                )
                logger.exception("Category publish failed: %s", message)
                errors.append(message)
                counters["categories_failed"] += 1
                with self._database.session_scope() as session:
                    self._category_repository.mark_publish_error(session, category_id)
                details.append(
                    {
                        "id": category_id,
                        "name": category_name,
                        "status": "error",
                        "error": self._error_message(exc),
                    }
                )

    def _publish_products(
        self,
        *,
        products: list[dict[str, Any]],
        counters: dict[str, int],
        errors: list[str],
        details: list[dict[str, Any]],
        progress_callback: Callable[[int, str], None] | None,
    ) -> None:
        total = max(1, len(products))
        for index, row in enumerate(products, start=1):
            product_id = int(row["id"])
            product_name = str(row.get("name") or "")
            self._emit_progress(
                progress_callback,
                50 + int((index / total) * 45),
                f"Публикация товаров: {index}/{len(products)}",
            )

            with self._database.session_scope() as session:
                self._product_repository.set_publish_pending(session, product_id)

            try:
                with self._database.session_scope() as session:
                    category_wc_ids, missing_category_ids = (
                        self._product_repository.get_product_category_wc_ids(
                            session,
                            product_id=product_id,
                        )
                    )
                if missing_category_ids:
                    raise ValueError(
                        "не опубликованы категории товара: "
                        + ", ".join(str(value) for value in missing_category_ids)
                    )

                product_images_payload: list[dict[str, Any]] = []
                media_warning: str | None = None
                if self._media_publish_service is not None:
                    try:
                        images_result = self._media_publish_service.resolve_product_images(
                            product_id=product_id
                        )
                        product_images_payload = images_result.images_payload
                        counters["product_images_uploaded"] += images_result.uploaded
                        counters["product_images_reused"] += images_result.reused
                    except Exception as media_exc:  # noqa: BLE001
                        counters["product_images_failed"] += 1
                        media_warning = self._error_message(media_exc)
                        logger.warning(
                            "Product images publish skipped for product_id=%s: %s",
                            product_id,
                            media_warning,
                        )
                        product_images_payload = []

                payload = self._build_product_payload(
                    row,
                    category_wc_ids=category_wc_ids,
                    images_payload=product_images_payload,
                )
                external_wc_id = row.get("external_wc_id")
                response: dict[str, Any]
                action: str
                if external_wc_id is None:
                    response = self._wc_client.create_product(payload)
                    action = "created"
                else:
                    try:
                        response = self._wc_client.update_product(int(external_wc_id), payload)
                        action = "updated"
                    except WooCommerceClientError as exc:
                        if exc.status_code == 404:
                            response = self._wc_client.create_product(payload)
                            action = "created_missing_remote"
                        else:
                            raise

                resolved_wc_id = int(response.get("id") or external_wc_id or 0)
                if resolved_wc_id <= 0:
                    raise ValueError("WooCommerce не вернул id товара")

                with self._database.session_scope() as session:
                    self._product_repository.mark_publish_success(
                        session,
                        product_id=product_id,
                        external_wc_id=resolved_wc_id,
                    )

                if action.startswith("created"):
                    counters["products_created"] += 1
                else:
                    counters["products_updated"] += 1
                details.append(
                    {
                        "id": product_id,
                        "wc_id": resolved_wc_id,
                        "name": product_name,
                        "action": action,
                        "status": "success",
                        "media_warning": media_warning,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                message = f"Товар #{product_id} '{product_name}': {self._error_message(exc)}"
                logger.exception("Product publish failed: %s", message)
                errors.append(message)
                counters["products_failed"] += 1
                with self._database.session_scope() as session:
                    self._product_repository.mark_publish_error(session, product_id)
                details.append(
                    {
                        "id": product_id,
                        "name": product_name,
                        "status": "error",
                        "error": self._error_message(exc),
                    }
                )

    def _build_category_payload(
        self,
        row: dict[str, Any],
        *,
        category_wc_map: dict[int, int],
        image_src: str | None,
    ) -> dict[str, Any]:
        parent_local_id = row.get("parent_id")
        parent_wc_id = 0
        if parent_local_id is not None:
            parent_wc_id = int(category_wc_map.get(int(parent_local_id)) or 0)
            if parent_wc_id <= 0:
                raise ValueError(
                    f"родительская категория #{int(parent_local_id)} не опубликована"
                )

        payload: dict[str, Any] = {
            "name": str(row.get("name") or "").strip(),
            "slug": str(row.get("slug") or "").strip(),
            "description": str(row.get("description") or "").strip(),
            "parent": parent_wc_id,
        }
        if image_src:
            payload["image"] = {"src": image_src}
        return payload

    def _build_product_payload(
        self,
        row: dict[str, Any],
        *,
        category_wc_ids: list[int],
        images_payload: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": str(row.get("name") or "").strip(),
            "slug": str(row.get("slug") or "").strip(),
            "description": str(row.get("description") or "").strip(),
            "short_description": str(row.get("short_description") or "").strip(),
            "status": self._normalize_wc_status(str(row.get("published_state") or "draft")),
            "catalog_visibility": str(row.get("visibility") or "visible"),
            "categories": [{"id": category_id} for category_id in category_wc_ids],
        }

        sku = row.get("sku")
        if sku:
            payload["sku"] = str(sku).strip()

        price = self._decimal_to_price_string(
            row.get("regular_price") if row.get("regular_price") is not None else row.get("price")
        )
        payload["regular_price"] = price

        sale_price = self._decimal_to_price_string(row.get("sale_price"))
        if sale_price:
            payload["sale_price"] = sale_price

        price_unit = str(row.get("price_unit") or "").strip()
        if price_unit:
            payload["meta_data"] = [{"key": "_price_unit", "value": price_unit}]

        if images_payload:
            payload["images"] = images_payload

        return payload

    def _finish_run(
        self,
        *,
        run_id: int,
        publish_job_id: int,
        counters: dict[str, int],
        errors: list[str],
        details: dict[str, list[dict[str, Any]]],
    ) -> None:
        run_status = "success" if not errors else "error"
        self._sync_run_repository.finish_run(
            run_id,
            status=run_status,
            counters=counters,
            errors=errors,
        )
        self._publish_job_repository.finish_job(
            publish_job_id,
            status=run_status,
            result={
                "counters": counters,
                "errors": errors,
                "details": details,
            },
        )
        logger.info(
            "Publish run finished: run_id=%s job_id=%s status=%s counters=%s errors=%s",
            run_id,
            publish_job_id,
            run_status,
            counters,
            len(errors),
        )

    def _order_categories_for_publish(
        self,
        categories: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pending = {int(row["id"]): row for row in categories}
        ordered: list[dict[str, Any]] = []
        processed_ids: set[int] = set()

        while pending:
            progress_made = False
            for category_id, row in list(pending.items()):
                parent_id = row.get("parent_id")
                if parent_id is None or int(parent_id) not in pending:
                    ordered.append(row)
                    processed_ids.add(category_id)
                    del pending[category_id]
                    progress_made = True
                    continue
                if int(parent_id) in processed_ids:
                    ordered.append(row)
                    processed_ids.add(category_id)
                    del pending[category_id]
                    progress_made = True
            if not progress_made:
                ordered.extend(pending.values())
                break
        return ordered

    def _normalize_wc_status(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"publish", "draft", "pending", "private"}:
            return normalized
        if normalized == "published":
            return "publish"
        return "draft"

    def _decimal_to_price_string(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, Decimal):
            raw = format(value, "f")
        else:
            raw = str(value).strip()
        if not raw:
            return ""
        if "." in raw:
            raw = raw.rstrip("0").rstrip(".")
        return raw or "0"

    def _error_message(self, exc: Exception) -> str:
        if isinstance(exc, WooCommerceClientError):
            return exc.user_message
        message = str(exc).strip()
        return message if message else exc.__class__.__name__

    def _emit_progress(
        self,
        progress_callback: Callable[[int, str], None] | None,
        percent: int,
        message: str,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(max(0, min(100, int(percent))), message)

    def _is_remote_url(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered.startswith("http://") or lowered.startswith("https://")
