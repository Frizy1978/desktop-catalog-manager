from __future__ import annotations

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
        session.execute(delete(ProductImage).where(ProductImage.product_id == product_id))
        prepared: list[tuple[str, int, bool]] = []
        for image in images:
            src = str(image.get("src") or "").strip()
            if not src:
                continue
            position = int(image.get("position") or 0)
            preferred_primary = position == 0
            prepared.append((src, position, preferred_primary))

        if not prepared:
            return 0

        prepared.sort(key=lambda item: item[1])

        primary_index = 0
        for index, item in enumerate(prepared):
            if item[2]:
                primary_index = index
                break

        inserted = 0
        for index, (src, position, _preferred_primary) in enumerate(prepared):
            session.add(
                ProductImage(
                    product_id=product_id,
                    original_path=src,
                    local_path=None,
                    is_primary=(index == primary_index),
                    sort_order=position,
                )
            )
            inserted += 1
        return inserted

    def list_products_for_table(
        self,
        session: Session,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)

        total_items = int(
            session.execute(
                select(func.count(Product.id)).where(Product.is_archived.is_(False))
            ).scalar_one()
        )

        offset = (safe_page - 1) * safe_page_size
        rows = session.execute(
            select(
                Product.id,
                Product.name,
                Product.sku,
                Product.price,
                Product.price_unit,
                Product.sync_status,
                Product.updated_at,
                Product.published_state,
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
            .group_by(Product.id)
            .order_by(Product.updated_at.desc())
            .offset(offset)
            .limit(safe_page_size)
        ).all()
        items = [
            {
                "id": row.id,
                "name": row.name,
                "sku": row.sku,
                "price": row.price,
                "price_unit": row.price_unit,
                "sync_status": row.sync_status,
                "updated_at": row.updated_at,
                "published_state": row.published_state,
                "category_name": row.categories or "",
            }
            for row in rows
        ]
        return items, total_items

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
