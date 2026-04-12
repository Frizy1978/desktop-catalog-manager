from __future__ import annotations

import difflib
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Category, Product, ProductCategoryLink, ProductImage


class ProductRepository:
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
        product.published_state = str(payload.get("status") or "draft")
        product.sync_status = "imported"
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

        existing_wc_images = session.scalars(
            select(ProductImage).where(
                ProductImage.product_id == product_id,
                ProductImage.source_type == "wc_url",
            )
        ).all()
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

            target_row.is_primary = index == primary_index
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
    ) -> tuple[list[dict], int]:
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        normalized_search = search_query.strip()

        stmt = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                Product.price,
                Product.price_unit,
                Product.published_state,
                Product.sync_status,
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
                "categories": row.categories or "",
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

        filtered_items = [
            item
            for item in all_items
            if self._matches_search(
                normalized_search,
                [
                    str(item.get("name", "")),
                    str(item.get("sku", "")),
                    str(item.get("categories", "")),
                ],
            )
        ]
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
                "sync_status": item["sync_status"],
                "categories": item["categories"],
            }
            for item in paged_items
        ]
        return items, total_items

    def get_product_details(self, session: Session, product_id: int) -> dict | None:
        product = session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.is_archived.is_(False),
            )
        )
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
            "sync_status": product.sync_status,
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
            is_featured=False,
            visibility="visible",
            published_state="draft",
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
        category_ids: list[int],
        image_urls: list[str] | None = None,
    ) -> None:
        product = session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.is_archived.is_(False),
            )
        )
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
        product.is_archived = False
        product.published_state = product.published_state or "draft"
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
        product = session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.is_archived.is_(False),
            )
        )
        if product is None:
            return False
        product.is_archived = True
        if product.external_wc_id is not None:
            product.sync_status = "archived"
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

    def _compact_text(self, text: str) -> str:
        normalized = re.sub(r"[^a-zа-я0-9]+", " ", text.lower(), flags=re.IGNORECASE)
        return " ".join(normalized.split())
