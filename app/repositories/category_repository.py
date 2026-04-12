from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, select
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
            select(
                Category.id,
                Category.name,
                Category.parent_id,
                Category.sync_status,
            )
            .where(Category.is_archived.is_(False))
            .order_by(Category.name.asc())
        ).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "parent_id": row.parent_id,
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

    def list_category_options(self, session: Session) -> list[dict]:
        rows = session.execute(
            select(Category.id, Category.name)
            .where(Category.is_archived.is_(False))
            .order_by(Category.name.asc())
        ).all()
        return [{"id": int(row.id), "name": str(row.name)} for row in rows]

    def get_by_id(self, session: Session, category_id: int) -> Category | None:
        return session.scalar(
            select(Category).where(
                Category.id == category_id,
                Category.is_archived.is_(False),
            )
        )

    def get_category_details(self, session: Session, category_id: int) -> dict | None:
        category = self.get_by_id(session, category_id)
        if category is None:
            return None
        return {
            "id": int(category.id),
            "name": category.name,
            "slug": category.slug,
            "description": category.description or "",
            "parent_id": category.parent_id,
            "image_paths": self._split_image_paths(category.image_path),
            "sync_status": category.sync_status,
        }

    def create_category(
        self,
        session: Session,
        *,
        name: str,
        slug: str | None,
        description: str | None,
        parent_id: int | None,
        image_paths: list[str] | None = None,
    ) -> int:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название категории не может быть пустым.")

        base_slug = self._normalize_slug(slug or normalized_name, fallback="category")
        final_slug = self._ensure_unique_slug(session, base_slug, exclude_id=None)
        validated_parent_id = self._validate_parent(session, parent_id, current_id=None)

        category = Category(
            name=normalized_name,
            slug=final_slug,
            description=(description or "").strip() or None,
            parent_id=validated_parent_id,
            image_path=self._join_image_paths(image_paths),
            external_wc_id=None,
            sync_status="new_local",
            is_archived=False,
        )
        session.add(category)
        session.flush()
        return int(category.id)

    def update_category(
        self,
        session: Session,
        *,
        category_id: int,
        name: str,
        slug: str | None,
        description: str | None,
        parent_id: int | None,
        image_paths: list[str] | None = None,
    ) -> None:
        category = self.get_by_id(session, category_id)
        if category is None:
            raise ValueError("Категория не найдена.")

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название категории не может быть пустым.")

        source_slug = (slug or "").strip() or category.slug or normalized_name
        base_slug = self._normalize_slug(source_slug, fallback="category")
        final_slug = self._ensure_unique_slug(session, base_slug, exclude_id=category.id)
        validated_parent_id = self._validate_parent(
            session,
            parent_id,
            current_id=category.id,
        )

        category.name = normalized_name
        category.slug = final_slug
        category.description = (description or "").strip() or None
        category.parent_id = validated_parent_id
        category.image_path = self._join_image_paths(image_paths)
        category.is_archived = False

        if category.external_wc_id is not None and category.sync_status in {
            "imported",
            "synced",
        }:
            category.sync_status = "modified_local"

    def _validate_parent(
        self,
        session: Session,
        parent_id: int | None,
        *,
        current_id: int | None,
    ) -> int | None:
        if parent_id is None:
            return None
        if parent_id <= 0:
            return None
        if current_id is not None and parent_id == current_id:
            raise ValueError("Категория не может быть родительской самой себе.")

        parent = self.get_by_id(session, parent_id)
        if parent is None:
            raise ValueError("Родительская категория не найдена.")
        return int(parent.id)

    def _normalize_slug(self, value: str, *, fallback: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return normalized or fallback

    def _ensure_unique_slug(
        self,
        session: Session,
        base_slug: str,
        *,
        exclude_id: int | None,
    ) -> str:
        candidate = base_slug
        suffix = 2
        while self._slug_exists(session, candidate, exclude_id=exclude_id):
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate

    def _slug_exists(
        self,
        session: Session,
        slug: str,
        *,
        exclude_id: int | None,
    ) -> bool:
        stmt = select(func.count(Category.id)).where(
            Category.slug == slug,
        )
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        count = session.execute(stmt).scalar_one()
        return int(count) > 0

    def _split_image_paths(self, raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def _join_image_paths(self, values: list[str] | None) -> str | None:
        if not values:
            return None
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            return None
        return "\n".join(cleaned)
