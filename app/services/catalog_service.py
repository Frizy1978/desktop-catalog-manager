from __future__ import annotations

from app.repositories.catalog_repository import CatalogRepository


class CatalogService:
    """Phase 1 read-only service for sidebar/table scaffolds."""

    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    def get_category_sidebar_items(self) -> list[dict]:
        return self._repository.list_categories_for_sidebar()

    def get_products_table_page(self, page: int, page_size: int) -> dict:
        return self._repository.list_products_for_table(page=page, page_size=page_size)
