from __future__ import annotations

import difflib
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Category, Product, ProductCategoryLink, ProductImage


class ProductRepository:
    _ALLOWED_PUBLISHED_STATES = {"draft", "publish", "pending", "private"}
    _ALLOWED_VISIBILITY_VALUES = {"visible", "catalog", "search", "hidden"}
    _ALLOWED_STOCK_STATUSES = {"instock", "outofstock", "onbackorder"}

    def upsert_from_wc_payload(
        self,
        session: Session,
        payload: dict[str, Any],
    ) -> tuple[Product, bool]:
        wc_id = int(payload["id"])
        product = session.scalar(select(Product).where(Product.external_wc_id == wc_id))
        created = product is None
        if product is None:
            product = Product(external_wc_id=wc_id)
            session.add(product)

        product.name = str(payload.get("name") or f"Товар {wc_id}")
        product.slug = str(payload.get("slug") or f"wc-product-{wc_id}")
        product.sku = payload.get("sku") or None
        product.description = payload.get("description")
        product.short_description = payload.get("short_description")
        product.price = self._to_decimal(payload.get("price"))
        product.regular_price = self._to_decimal(payload.get("regular_price"))
        product.sale_price = self._to_decimal(payload.get("sale_price"))
        product.price_unit = self._extract_price_unit(payload.get("meta_data"))
        product.is_featured = bool(payload.get("featured", False))
        product.visibility = str(payload.get("catalog_visibility") or "visible")
        product.stock_status = self._normalize_stock_status(payload.get("stock_status"))
        product.published_state = str(payload.get("status") or "draft")
        product.sync_status = "synced"
        product.is_archived = False
        return product, created

    def replace_category_links(
        self,
        session: Session,
        *,
        product_id: int,
        category_ids: list[int],
    ) -> None:
        session.execute(
            delete(ProductCategoryLink).where(ProductCategoryLink.product_id == product_id)
        )
        for category_id in sorted(set(category_ids)):
            session.add(
                ProductCategoryLink(
                    product_id=product_id,
                    category_id=category_id,
                )
            )

    def replace_images_from_wc_payload(
        self,
        session: Session,
        *,
        product_id: int,
        images: list[dict[str, Any]],
    ) -> int:
        prepared: list[tuple[str, int, bool]] = []
        for image in images:
            src = str(image.get("src") or "").strip()
            if not src:
                continue
            position = int(image.get("position") or 0)
            preferred_primary = position == 0
            prepared.append((src, position, preferred_primary))

        all_existing_images = session.scalars(
            select(ProductImage).where(ProductImage.product_id == product_id)
        ).all()
        existing_wc_images = [
            image_row
            for image_row in all_existing_images
            if image_row.source_type == "wc_url"
        ]
        has_non_wc_primary = any(
            bool(image_row.is_primary) and image_row.source_type != "wc_url"
            for image_row in all_existing_images
        )
        existing_by_src: dict[str, list[ProductImage]] = {}
        for image_row in existing_wc_images:
            key = str(image_row.original_path or "").strip()
            if not key:
                continue
            existing_by_src.setdefault(key, []).append(image_row)
        for image_rows in existing_by_src.values():
            image_rows.sort(key=lambda row: int(row.id))

        if not prepared:
            for image_row in existing_wc_images:
                session.delete(image_row)
            return 0

        prepared.sort(key=lambda item: item[1])
        primary_index = 0
        for index, item in enumerate(prepared):
            if item[2]:
                primary_index = index
                break

        # Preserve a user-selected local primary image if it exists.
        # Otherwise, reset WC primary markers before assigning the new one so
        # SQLite's partial unique index on product_images(product_id)
        # WHERE is_primary = 1 is not violated during the import update.
        if not has_non_wc_primary:
            for image_row in existing_wc_images:
                image_row.is_primary = False
            if existing_wc_images:
                session.flush()

        used_ids: set[int] = set()
        active_count = 0
        for index, (src, position, _preferred_primary) in enumerate(prepared):
            candidates = existing_by_src.get(src) or []
            target_row: ProductImage | None = None
            for candidate in candidates:
                if int(candidate.id) not in used_ids:
                    target_row = candidate
                    break

            if target_row is None:
                target_row = ProductImage(
                    product_id=product_id,
                    original_path=src,
                    local_path=None,
                    source_type="wc_url",
                    metadata_json=None,
                    is_primary=False,
                    sort_order=position,
                )
                session.add(target_row)
                session.flush()
            else:
                target_row.original_path = src
                target_row.source_type = "wc_url"
                target_row.sort_order = position

            target_row.is_primary = (not has_non_wc_primary) and index == primary_index
            used_ids.add(int(target_row.id))
            active_count += 1

        for image_row in existing_wc_images:
            if int(image_row.id) not in used_ids:
                session.delete(image_row)
        return active_count

    def list_products_for_table(
        self,
        session: Session,
        *,
        page: int,
        page_size: int,
        category_id: int | None = None,
        search_query: str = "",
        sync_status_filter: str = "",
        published_state_filter: str = "",
        visibility_filter: str = "",
        is_featured_filter: str = "",
        stock_status_filter: str = "",
    ) -> tuple[list[dict], int]:
        filtered_items = self._list_products_for_table_items(
            session,
            category_id=category_id,
            search_query=search_query,
            sync_status_filter=sync_status_filter,
            published_state_filter=published_state_filter,
            visibility_filter=visibility_filter,
            is_featured_filter=is_featured_filter,
            stock_status_filter=stock_status_filter,
        )
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        total_items = len(filtered_items)
        offset = (safe_page - 1) * safe_page_size
        paged_items = filtered_items[offset : offset + safe_page_size]
        items = [
            {
                "id": item["id"],
                "name": item["name"],
                "sku": item["sku"],
                "price": item["price"],
                "price_unit": item["price_unit"],
                "status": item["status"],
                "visibility": item["visibility"],
                "is_featured": item["is_featured"],
                "stock_status": item["stock_status"],
                "sync_status": item["sync_status"],
                "categories": item["categories"],
            }
            for item in paged_items
        ]
        return items, total_items

    def list_product_ids_for_table_selection(
        self,
        session: Session,
        *,
        category_id: int | None = None,
        search_query: str = "",
        sync_status_filter: str = "",
        published_state_filter: str = "",
        visibility_filter: str = "",
        is_featured_filter: str = "",
        stock_status_filter: str = "",
    ) -> list[int]:
        filtered_items = self._list_products_for_table_items(
            session,
            category_id=category_id,
            search_query=search_query,
            sync_status_filter=sync_status_filter,
            published_state_filter=published_state_filter,
            visibility_filter=visibility_filter,
            is_featured_filter=is_featured_filter,
            stock_status_filter=stock_status_filter,
        )
        return [int(item["id"]) for item in filtered_items]

    def _list_products_for_table_items(
        self,
        session: Session,
        *,
        category_id: int | None = None,
        search_query: str = "",
        sync_status_filter: str = "",
        published_state_filter: str = "",
        visibility_filter: str = "",
        is_featured_filter: str = "",
        stock_status_filter: str = "",
    ) -> list[dict[str, Any]]:
        normalized_search = search_query.strip()
        normalized_sync_status = sync_status_filter.strip().lower()
        normalized_published_state = published_state_filter.strip().lower()
        normalized_visibility = visibility_filter.strip().lower()
        normalized_is_featured = is_featured_filter.strip().lower()
        normalized_stock_status = stock_status_filter.strip().lower()

        stmt = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                Product.price,
                Product.price_unit,
                Product.published_state,
                Product.sync_status,
                Product.visibility,
                Product.is_featured,
                Product.stock_status,
                Product.updated_at,
                func.group_concat(func.distinct(Category.name)).label("categories"),
            )
            .select_from(Product)
            .join(
                ProductCategoryLink,
                ProductCategoryLink.product_id == Product.id,
                isouter=True,
            )
            .join(Category, ProductCategoryLink.category_id == Category.id, isouter=True)
            .where(Product.is_archived.is_(False))
        )
        if category_id is not None:
            stmt = stmt.where(
                Product.id.in_(
                    select(ProductCategoryLink.product_id).where(
                        ProductCategoryLink.category_id == category_id
                    )
                )
            )

        rows = session.execute(
            stmt.group_by(Product.id).order_by(Product.updated_at.desc(), Product.id.desc())
        ).all()

        all_items = [
            {
                "id": row.id,
                "name": row.name,
                "sku": row.sku,
                "price": row.price,
                "price_unit": row.price_unit,
                "status": row.published_state,
                "sync_status": row.sync_status,
                "visibility": row.visibility,
                "is_featured": bool(row.is_featured),
                "stock_status": row.stock_status,
                "categories": row.categories or "",
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

        filtered_items = [
            item
            for item in all_items
            if self._matches_product_table_filters(
                item,
                search_query=normalized_search,
                sync_status_filter=normalized_sync_status,
                published_state_filter=normalized_published_state,
                visibility_filter=normalized_visibility,
                is_featured_filter=normalized_is_featured,
                stock_status_filter=normalized_stock_status,
            )
        ]
        return filtered_items

    def get_product_details(self, session: Session, product_id: int) -> dict | None:
        product = self._get_active_product(session, product_id)
        if product is None:
            return None

        category_rows = session.execute(
            select(ProductCategoryLink.category_id).where(
                ProductCategoryLink.product_id == product.id
            )
        ).all()
        image_rows = session.execute(
            select(ProductImage.original_path)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
        ).all()

        return {
            "id": int(product.id),
            "name": product.name,
            "description": product.description or "",
            "price": str(product.price) if product.price is not None else "",
            "price_unit": product.price_unit or "",
            "sku": product.sku or "",
            "status": product.published_state,
            "published_state": product.published_state,
            "sync_status": product.sync_status,
            "visibility": product.visibility or "visible",
            "is_featured": bool(product.is_featured),
            "stock_status": product.stock_status or "instock",
            "category_ids": [int(row.category_id) for row in category_rows],
            "image_urls": [str(row.original_path) for row in image_rows if row.original_path],
        }

    def create_product(
        self,
        session: Session,
        *,
        name: str,
        description: str | None,
        price: str | Decimal | None,
        price_unit: str | None,
        sku: str | None,
        published_state: str | None,
        visibility: str | None,
        is_featured: bool,
        stock_status: str | None,
        category_ids: list[int],
        image_urls: list[str] | None = None,
    ) -> int:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название товара не может быть пустым.")

        self._validate_unique_sku(session, sku=sku, exclude_product_id=None)

        base_slug = self._normalize_slug(normalized_name, fallback="product")
        slug = self._ensure_unique_slug(session, base_slug, exclude_product_id=None)

        normalized_price = self._to_decimal(price)
        normalized_description = (description or "").strip() or None
        normalized_sku = (sku or "").strip() or None
        normalized_price_unit = (price_unit or "").strip() or None
        normalized_published_state = self._normalize_published_state(published_state)
        normalized_visibility = self._normalize_visibility(visibility)
        normalized_stock_status = self._normalize_stock_status(stock_status)

        product = Product(
            name=normalized_name,
            slug=slug,
            sku=normalized_sku,
            description=normalized_description,
            short_description=None,
            price=normalized_price,
            regular_price=normalized_price,
            sale_price=None,
            price_unit=normalized_price_unit,
            is_featured=bool(is_featured),
            visibility=normalized_visibility,
            stock_status=normalized_stock_status,
            published_state=normalized_published_state,
            sync_status="new_local",
            external_wc_id=None,
            is_archived=False,
        )
        session.add(product)
        session.flush()

        self.replace_category_links(
            session,
            product_id=int(product.id),
            category_ids=category_ids,
        )
        if image_urls is not None:
            self._replace_images_from_urls(
                session,
                product_id=int(product.id),
                image_urls=image_urls,
            )
        return int(product.id)

    def update_product(
        self,
        session: Session,
        *,
        product_id: int,
        name: str,
        description: str | None,
        price: str | Decimal | None,
        price_unit: str | None,
        sku: str | None,
        published_state: str | None,
        visibility: str | None,
        is_featured: bool,
        stock_status: str | None,
        category_ids: list[int],
        image_urls: list[str] | None = None,
    ) -> None:
        product = self._get_active_product(session, product_id)
        if product is None:
            raise ValueError("Товар не найден.")

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название товара не может быть пустым.")

        self._validate_unique_sku(
            session,
            sku=sku,
            exclude_product_id=int(product.id),
        )
        if not product.slug:
            base_slug = self._normalize_slug(normalized_name, fallback="product")
            product.slug = self._ensure_unique_slug(
                session,
                base_slug,
                exclude_product_id=int(product.id),
            )

        product.name = normalized_name
        product.description = (description or "").strip() or None
        product.price = self._to_decimal(price)
        product.regular_price = product.price
        product.price_unit = (price_unit or "").strip() or None
        product.sku = (sku or "").strip() or None
        product.published_state = self._normalize_published_state(published_state)
        product.visibility = self._normalize_visibility(visibility)
        product.is_featured = bool(is_featured)
        product.stock_status = self._normalize_stock_status(stock_status)
        product.is_archived = False
        if product.sync_status != "new_local":
            product.sync_status = "modified_local"

        self.replace_category_links(
            session,
            product_id=int(product.id),
            category_ids=category_ids,
        )
        if image_urls is not None:
            self._replace_images_from_urls(
                session,
                product_id=int(product.id),
                image_urls=image_urls,
            )

    def archive_product(self, session: Session, product_id: int) -> bool:
        product = self._get_active_product(session, product_id)
        if product is None:
            return False
        product.is_archived = True
        if product.external_wc_id is not None:
            product.sync_status = "archived"
        return True

    def bulk_update_price_unit(
        self,
        session: Session,
        *,
        product_ids: list[int],
        price_unit: str | None,
    ) -> int:
        normalized_price_unit = (price_unit or "").strip() or None
        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if (product.price_unit or None) == normalized_price_unit:
                continue
            product.price_unit = normalized_price_unit
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_update_price(
        self,
        session: Session,
        *,
        product_ids: list[int],
        price: str | Decimal,
    ) -> int:
        normalized_price = self._to_decimal(price)
        if normalized_price is None:
            raise ValueError("Цена должна быть указана корректно.")

        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if (
                product.price == normalized_price
                and product.regular_price == normalized_price
                and product.sale_price is None
            ):
                continue
            product.price = normalized_price
            product.regular_price = normalized_price
            product.sale_price = None
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_replace_category(
        self,
        session: Session,
        *,
        product_ids: list[int],
        category_id: int,
    ) -> int:
        category = session.scalar(
            select(Category).where(
                Category.id == category_id,
                Category.is_archived.is_(False),
            )
        )
        if category is None:
            raise ValueError("Категория для массового изменения не найдена.")

        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            current_category_ids = [
                int(link.category_id)
                for link in sorted(
                    product.category_links,
                    key=lambda link: int(link.category_id),
                )
            ]
            if current_category_ids == [int(category_id)]:
                continue
            self.replace_category_links(
                session,
                product_id=int(product.id),
                category_ids=[int(category_id)],
            )
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_update_published_state(
        self,
        session: Session,
        *,
        product_ids: list[int],
        published_state: str,
    ) -> int:
        normalized_state = str(published_state or "").strip().lower()
        if normalized_state not in self._ALLOWED_PUBLISHED_STATES:
            raise ValueError("Некорректный статус публикации для массового изменения.")

        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if (product.published_state or "draft") == normalized_state:
                continue
            product.published_state = normalized_state
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_update_visibility(
        self,
        session: Session,
        *,
        product_ids: list[int],
        visibility: str,
    ) -> int:
        normalized_visibility = str(visibility or "").strip().lower()
        if normalized_visibility not in self._ALLOWED_VISIBILITY_VALUES:
            raise ValueError("Некорректная видимость каталога для массового изменения.")

        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if (product.visibility or "visible") == normalized_visibility:
                continue
            product.visibility = normalized_visibility
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_update_featured(
        self,
        session: Session,
        *,
        product_ids: list[int],
        is_featured: bool,
    ) -> int:
        normalized_featured = bool(is_featured)
        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if bool(product.is_featured) == normalized_featured:
                continue
            product.is_featured = normalized_featured
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_update_stock_status(
        self,
        session: Session,
        *,
        product_ids: list[int],
        stock_status: str,
    ) -> int:
        normalized_stock_status = str(stock_status or "").strip().lower()
        if normalized_stock_status not in self._ALLOWED_STOCK_STATUSES:
            raise ValueError("Некорректное наличие для массового изменения.")

        updated_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if (product.stock_status or "instock") == normalized_stock_status:
                continue
            product.stock_status = normalized_stock_status
            if product.sync_status != "new_local":
                product.sync_status = "modified_local"
            updated_count += 1
        return updated_count

    def bulk_archive_products(
        self,
        session: Session,
        *,
        product_ids: list[int],
    ) -> int:
        archived_count = 0
        for product in self._get_active_products_by_ids(session, product_ids):
            if self.archive_product(session, int(product.id)):
                archived_count += 1
        return archived_count

    def list_products_for_publish(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(
                Product.id,
                Product.name,
                Product.slug,
                Product.sku,
                Product.description,
                Product.short_description,
                Product.price,
                Product.regular_price,
                Product.sale_price,
                Product.price_unit,
                Product.visibility,
                Product.stock_status,
                Product.is_featured,
                Product.published_state,
                Product.external_wc_id,
                Product.sync_status,
            )
            .where(
                Product.is_archived.is_(False),
                Product.sync_status.in_(
                    ["new_local", "modified_local", "publish_error", "publish_pending"]
                ),
            )
            .order_by(Product.id.asc())
        ).all()
        return [
            {
                "id": int(row.id),
                "name": str(row.name or ""),
                "slug": str(row.slug or ""),
                "sku": str(row.sku or "").strip() or None,
                "description": str(row.description or "").strip(),
                "short_description": str(row.short_description or "").strip(),
                "price": row.price,
                "regular_price": row.regular_price,
                "sale_price": row.sale_price,
                "price_unit": str(row.price_unit or "").strip() or None,
                "visibility": str(row.visibility or "visible"),
                "stock_status": str(row.stock_status or "instock"),
                "is_featured": bool(row.is_featured),
                "published_state": str(row.published_state or "draft"),
                "external_wc_id": int(row.external_wc_id)
                if row.external_wc_id is not None
                else None,
                "sync_status": str(row.sync_status or ""),
            }
            for row in rows
        ]

    def list_products_publish_preview(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(
                Product.id,
                Product.name,
                Product.sku,
                Product.sync_status,
                Product.external_wc_id,
                func.group_concat(func.distinct(Category.name)).label("categories"),
            )
            .select_from(Product)
            .join(
                ProductCategoryLink,
                ProductCategoryLink.product_id == Product.id,
                isouter=True,
            )
            .join(Category, ProductCategoryLink.category_id == Category.id, isouter=True)
            .where(
                Product.is_archived.is_(False),
                Product.sync_status.in_(
                    ["new_local", "modified_local", "publish_error", "publish_pending"]
                ),
            )
            .group_by(Product.id)
            .order_by(Product.updated_at.desc(), Product.id.desc())
        ).all()
        return [
            {
                "id": int(row.id),
                "name": str(row.name or ""),
                "sku": str(row.sku or "").strip(),
                "sync_status": str(row.sync_status or ""),
                "external_wc_id": int(row.external_wc_id)
                if row.external_wc_id is not None
                else None,
                "categories": str(row.categories or ""),
            }
            for row in rows
        ]

    def get_product_category_wc_ids(
        self,
        session: Session,
        *,
        product_id: int,
    ) -> tuple[list[int], list[int]]:
        rows = session.execute(
            select(Category.id, Category.external_wc_id)
            .join(
                ProductCategoryLink,
                ProductCategoryLink.category_id == Category.id,
            )
            .where(
                ProductCategoryLink.product_id == product_id,
                Category.is_archived.is_(False),
            )
            .order_by(Category.id.asc())
        ).all()
        wc_ids: list[int] = []
        missing_local_ids: list[int] = []
        for row in rows:
            local_category_id = int(row.id)
            if row.external_wc_id is None:
                missing_local_ids.append(local_category_id)
                continue
            wc_ids.append(int(row.external_wc_id))
        return sorted(set(wc_ids)), sorted(set(missing_local_ids))

    def set_publish_pending(self, session: Session, product_id: int) -> bool:
        product = self._get_active_product(session, product_id)
        if product is None:
            return False
        product.sync_status = "publish_pending"
        return True

    def mark_publish_success(
        self,
        session: Session,
        *,
        product_id: int,
        external_wc_id: int,
    ) -> bool:
        product = self._get_active_product(session, product_id)
        if product is None:
            return False
        product.external_wc_id = int(external_wc_id)
        product.sync_status = "synced"
        product.is_archived = False
        return True

    def mark_publish_error(self, session: Session, product_id: int) -> bool:
        product = self._get_active_product(session, product_id)
        if product is None:
            return False
        product.sync_status = "publish_error"
        return True

    def mark_modified_local(self, session: Session, product_id: int) -> bool:
        product = self._get_active_product(session, product_id)
        if product is None:
            return False
        if product.sync_status != "new_local":
            product.sync_status = "modified_local"
        return True

    def _extract_price_unit(self, meta_data: Any) -> str | None:
        if not isinstance(meta_data, list):
            return None
        for meta in meta_data:
            if not isinstance(meta, dict):
                continue
            if str(meta.get("key")) == "_price_unit":
                value = meta.get("value")
                return str(value).strip() if value is not None else None
        return None

    def _to_decimal(self, raw: Any) -> Decimal | None:
        if raw is None:
            return None
        value = str(raw).strip()
        if not value:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    def _normalize_published_state(self, value: Any) -> str:
        normalized = str(value or "").strip().lower() or "draft"
        if normalized not in self._ALLOWED_PUBLISHED_STATES:
            raise ValueError("Некорректный статус публикации товара.")
        return normalized

    def _normalize_visibility(self, value: Any) -> str:
        normalized = str(value or "").strip().lower() or "visible"
        if normalized not in self._ALLOWED_VISIBILITY_VALUES:
            raise ValueError("Некорректная видимость товара.")
        return normalized

    def _normalize_stock_status(self, value: Any) -> str:
        normalized = str(value or "").strip().lower() or "instock"
        if normalized not in self._ALLOWED_STOCK_STATUSES:
            return "instock"
        return normalized

    def _replace_images_from_urls(
        self,
        session: Session,
        *,
        product_id: int,
        image_urls: list[str],
    ) -> None:
        prepared: list[dict[str, Any]] = []
        for index, url in enumerate(image_urls):
            normalized = url.strip()
            if not normalized:
                continue
            prepared.append(
                {
                    "src": normalized,
                    "position": index,
                }
            )
        self.replace_images_from_wc_payload(
            session,
            product_id=product_id,
            images=prepared,
        )

    def _normalize_slug(self, value: str, *, fallback: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or fallback

    def _ensure_unique_slug(
        self,
        session: Session,
        base_slug: str,
        *,
        exclude_product_id: int | None,
    ) -> str:
        candidate = base_slug
        suffix = 2
        while self._slug_exists(
            session,
            slug=candidate,
            exclude_product_id=exclude_product_id,
        ):
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate

    def _slug_exists(
        self,
        session: Session,
        *,
        slug: str,
        exclude_product_id: int | None,
    ) -> bool:
        stmt = select(func.count(Product.id)).where(Product.slug == slug)
        if exclude_product_id is not None:
            stmt = stmt.where(Product.id != exclude_product_id)
        count = session.execute(stmt).scalar_one()
        return int(count) > 0

    def _validate_unique_sku(
        self,
        session: Session,
        *,
        sku: str | None,
        exclude_product_id: int | None,
    ) -> None:
        normalized_sku = (sku or "").strip()
        if not normalized_sku:
            return
        stmt = select(func.count(Product.id)).where(Product.sku == normalized_sku)
        if exclude_product_id is not None:
            stmt = stmt.where(Product.id != exclude_product_id)
        count = session.execute(stmt).scalar_one()
        if int(count) > 0:
            raise ValueError("Товар с таким SKU уже существует.")

    def _matches_search(self, query: str, fields: list[str]) -> bool:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return True

        query_compact = self._compact_text(normalized_query)
        for field in fields:
            lowered = field.lower()
            if normalized_query in lowered:
                return True
            compact_field = self._compact_text(lowered)
            if query_compact and query_compact in compact_field:
                return True

            words = [word for word in compact_field.split(" ") if word]
            for word in words:
                ratio = difflib.SequenceMatcher(None, query_compact, word).ratio()
                if ratio >= 0.8:
                    return True
        return False

    def _matches_product_table_filters(
        self,
        item: dict[str, Any],
        *,
        search_query: str,
        sync_status_filter: str,
        published_state_filter: str,
        visibility_filter: str,
        is_featured_filter: str,
        stock_status_filter: str,
    ) -> bool:
        if sync_status_filter:
            item_sync_status = str(item.get("sync_status", "")).strip().lower()
            if item_sync_status != sync_status_filter:
                return False
        if published_state_filter:
            item_published_state = str(item.get("status", "")).strip().lower()
            if item_published_state != published_state_filter:
                return False
        if visibility_filter:
            item_visibility = str(item.get("visibility", "")).strip().lower()
            if item_visibility != visibility_filter:
                return False
        if is_featured_filter:
            item_is_featured = "true" if bool(item.get("is_featured")) else "false"
            if item_is_featured != is_featured_filter:
                return False
        if stock_status_filter:
            item_stock_status = str(item.get("stock_status", "")).strip().lower()
            if item_stock_status != stock_status_filter:
                return False
        return self._matches_search(
            search_query,
            [
                str(item.get("name", "")),
                str(item.get("sku", "")),
                str(item.get("categories", "")),
            ],
        )

    def _compact_text(self, text: str) -> str:
        normalized = re.sub(r"[^0-9a-zа-я]+", " ", text.lower(), flags=re.IGNORECASE)
        return " ".join(normalized.split())

    def _get_active_product(self, session: Session, product_id: int) -> Product | None:
        return session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.is_archived.is_(False),
            )
        )

    def _get_active_products_by_ids(
        self,
        session: Session,
        product_ids: list[int],
    ) -> list[Product]:
        normalized_ids = sorted({int(product_id) for product_id in product_ids if product_id})
        if not normalized_ids:
            return []
        return list(
            session.scalars(
                select(Product)
                .where(
                    Product.id.in_(normalized_ids),
                    Product.is_archived.is_(False),
                )
                .order_by(Product.id.asc())
            ).all()
        )
