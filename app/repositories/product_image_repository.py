from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Product, ProductImage


class ProductImageRepository:
    def ensure_product_exists(self, session: Session, product_id: int) -> bool:
        product = session.scalar(
            select(Product.id).where(
                Product.id == product_id,
                Product.is_archived.is_(False),
            )
        )
        return product is not None

    def list_by_product(self, session: Session, product_id: int) -> list[dict[str, Any]]:
        rows = session.execute(
            select(
                ProductImage.id,
                ProductImage.product_id,
                ProductImage.original_path,
                ProductImage.local_path,
                ProductImage.source_type,
                ProductImage.metadata_json,
                ProductImage.is_primary,
                ProductImage.sort_order,
                ProductImage.created_at,
            )
            .where(ProductImage.product_id == product_id)
            .order_by(
                ProductImage.is_primary.desc(),
                ProductImage.sort_order.asc(),
                ProductImage.id.asc(),
            )
        ).all()
        return [
            {
                "id": int(row.id),
                "product_id": int(row.product_id),
                "original_path": row.original_path,
                "local_path": row.local_path,
                "source_type": row.source_type or "wc_url",
                "metadata_json": row.metadata_json,
                "metadata": self._safe_metadata(row.metadata_json),
                "is_primary": bool(row.is_primary),
                "sort_order": int(row.sort_order),
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def list_for_publish(
        self,
        session: Session,
        product_id: int,
    ) -> list[dict[str, Any]]:
        return self.list_by_product(session, product_id)

    def set_wc_media_mapping(
        self,
        session: Session,
        *,
        image_id: int,
        wc_media_id: int,
        wc_source_url: str,
    ) -> bool:
        image = session.scalar(select(ProductImage).where(ProductImage.id == image_id))
        if image is None:
            return False

        metadata = self._safe_metadata(image.metadata_json)
        metadata["wc_media_id"] = int(wc_media_id)
        metadata["wc_source_url"] = str(wc_source_url).strip()
        image.metadata_json = json.dumps(metadata, ensure_ascii=False)
        return True

    def add_local_image(
        self,
        session: Session,
        *,
        product_id: int,
        original_path: str,
        local_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        next_sort_order = int(
            session.execute(
                select(func.coalesce(func.max(ProductImage.sort_order), -1) + 1).where(
                    ProductImage.product_id == product_id
                )
            ).scalar_one()
        )
        has_primary = bool(
            session.execute(
                select(func.count(ProductImage.id)).where(
                    ProductImage.product_id == product_id,
                    ProductImage.is_primary.is_(True),
                )
            ).scalar_one()
        )

        image = ProductImage(
            product_id=product_id,
            original_path=original_path,
            local_path=local_path,
            source_type="local_file",
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False)
            if metadata is not None
            else None,
            is_primary=not has_primary,
            sort_order=next_sort_order,
        )
        session.add(image)
        session.flush()
        return {
            "id": int(image.id),
            "product_id": int(image.product_id),
            "original_path": image.original_path,
            "local_path": image.local_path,
            "source_type": image.source_type,
            "metadata_json": image.metadata_json,
            "metadata": metadata or {},
            "is_primary": bool(image.is_primary),
            "sort_order": int(image.sort_order),
        }

    def set_primary(self, session: Session, *, product_id: int, image_id: int) -> bool:
        image = session.scalar(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
            )
        )
        if image is None:
            return False

        session.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )
        image.is_primary = True
        return True

    def remove_image(
        self,
        session: Session,
        *,
        product_id: int,
        image_id: int,
    ) -> dict[str, Any] | None:
        image = session.scalar(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
            )
        )
        if image is None:
            return None

        was_primary = bool(image.is_primary)
        removed = {
            "id": int(image.id),
            "product_id": int(image.product_id),
            "local_path": image.local_path,
            "source_type": image.source_type or "wc_url",
        }
        session.delete(image)
        session.flush()

        if was_primary:
            next_image = session.scalar(
                select(ProductImage)
                .where(ProductImage.product_id == product_id)
                .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            )
            if next_image is not None:
                next_image.is_primary = True
        return removed

    def _safe_metadata(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def list_wc_images_without_local_path(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(
                ProductImage.id,
                ProductImage.product_id,
                ProductImage.original_path,
            )
            .join(Product, Product.id == ProductImage.product_id)
            .where(
                Product.is_archived.is_(False),
                ProductImage.source_type == "wc_url",
                (ProductImage.local_path.is_(None)) | (ProductImage.local_path == ""),
            )
            .order_by(ProductImage.product_id.asc(), ProductImage.sort_order.asc(), ProductImage.id.asc())
        ).all()
        return [
            {
                "id": int(row.id),
                "product_id": int(row.product_id),
                "source_url": str(row.original_path or "").strip(),
            }
            for row in rows
            if str(row.original_path or "").strip()
        ]

    def set_local_path(
        self,
        session: Session,
        *,
        image_id: int,
        local_path: str,
    ) -> bool:
        image = session.scalar(select(ProductImage).where(ProductImage.id == image_id))
        if image is None:
            return False
        image.local_path = local_path.strip()
        return True

    def list_wc_images(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(
                ProductImage.id,
                ProductImage.product_id,
                ProductImage.original_path,
                ProductImage.local_path,
            )
            .join(Product, Product.id == ProductImage.product_id)
            .where(
                Product.is_archived.is_(False),
                ProductImage.source_type == "wc_url",
            )
            .order_by(ProductImage.product_id.asc(), ProductImage.id.asc())
        ).all()
        return [
            {
                "id": int(row.id),
                "product_id": int(row.product_id),
                "source_url": str(row.original_path or "").strip(),
                "local_path": str(row.local_path or "").strip() or None,
            }
            for row in rows
            if str(row.original_path or "").strip()
        ]

    def list_existing_product_ids(self, session: Session) -> set[int]:
        rows = session.execute(select(Product.id)).all()
        return {int(row.id) for row in rows}
