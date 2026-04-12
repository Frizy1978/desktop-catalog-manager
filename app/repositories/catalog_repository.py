from __future__ import annotations

import math

from app.db.session import SqlAlchemyDatabase
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository


class CatalogRepository:
    """Phase 2 repository facade for catalog read models."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database
        self._category_repository = CategoryRepository()
        self._product_repository = ProductRepository()

    def list_categories_for_sidebar(self) -> list[dict]:
        with self._database.session_scope() as session:
            return self._category_repository.list_categories_for_sidebar(session)

    def list_products_for_table(
        self,
        *,
        page: int,
        page_size: int,
    ) -> dict:
        with self._database.session_scope() as session:
            items, total_items = self._product_repository.list_products_for_table(
                session,
                page=page,
                page_size=page_size,
            )
            safe_page_size = max(1, page_size)
            total_pages = max(1, math.ceil(total_items / safe_page_size))
            safe_page = min(max(1, page), total_pages)
            return {
                "items": items,
                "page": safe_page,
                "page_size": safe_page_size,
                "total_items": total_items,
                "total_pages": total_pages,
            }
