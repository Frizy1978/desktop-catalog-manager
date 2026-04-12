from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category


class CategoryRepository:
    def upsert_from_wc_payload(
        self,
        session: Session,
        payload: dict[str, Any],
    ) -> tuple[Category, bool]:
        wc_id = int(payload["id"])
        category = session.scalar(
            select(Category).where(Category.external_wc_id == wc_id)
        )
        created = category is None
        if category is None:
            category = Category(external_wc_id=wc_id)
            session.add(category)

        category.name = str(payload.get("name") or f"Категория {wc_id}")
        category.slug = str(payload.get("slug") or f"wc-category-{wc_id}")
        category.description = payload.get("description")
        category.image_path = (payload.get("image") or {}).get("src")
        category.sync_status = "imported"
        category.is_archived = False
        return category, created

    def bind_parent_links_from_wc(
        self,
        session: Session,
        category_payloads: list[dict[str, Any]],
    ) -> None:
        wc_to_category = {
            category.external_wc_id: category
            for category in session.scalars(select(Category)).all()
            if category.external_wc_id is not None
        }
        for payload in category_payloads:
            wc_id = int(payload["id"])
            category = wc_to_category.get(wc_id)
            if category is None:
                continue
            parent_external_id = int(payload.get("parent") or 0)
            if parent_external_id <= 0:
                category.parent_id = None
                continue
            parent = wc_to_category.get(parent_external_id)
            category.parent_id = parent.id if parent is not None else None

    def list_categories_for_sidebar(self, session: Session) -> list[dict]:
        rows = session.execute(
            select(Category.id, Category.name, Category.sync_status)
            .where(Category.is_archived.is_(False))
            .order_by(Category.name.asc())
        ).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "sync_status": row.sync_status,
            }
            for row in rows
        ]

    def external_to_local_id_map(self, session: Session) -> dict[int, int]:
        rows = session.execute(
            select(Category.external_wc_id, Category.id).where(
                Category.external_wc_id.is_not(None)
            )
        ).all()
        return {int(row.external_wc_id): int(row.id) for row in rows}
