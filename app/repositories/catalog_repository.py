from __future__ import annotations

import math

from app.db.session import SqlAlchemyDatabase
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository


class CatalogRepository:
    """Phase 3 repository facade for catalog read/write operations."""

    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database
        self._category_repository = CategoryRepository()
        self._product_repository = ProductRepository()

    def list_categories_for_sidebar(self) -> list[dict]:
        with self._database.session_scope() as session:
            return self._category_repository.list_categories_for_sidebar(session)

    def list_category_options(self) -> list[dict]:
        with self._database.session_scope() as session:
            return self._category_repository.list_category_options(session)

    def get_category_details(self, category_id: int) -> dict | None:
        with self._database.session_scope() as session:
            return self._category_repository.get_category_details(session, category_id)

    def create_category(
        self,
        *,
        name: str,
        slug: str | None,
        description: str | None,
        parent_id: int | None,
        image_paths: list[str] | None = None,
    ) -> int:
        with self._database.session_scope() as session:
            return self._category_repository.create_category(
                session,
                name=name,
                slug=slug,
                description=description,
                parent_id=parent_id,
                image_paths=image_paths,
            )

    def update_category(
        self,
        *,
        category_id: int,
        name: str,
        slug: str | None,
        description: str | None,
        parent_id: int | None,
        image_paths: list[str] | None = None,
    ) -> None:
        with self._database.session_scope() as session:
            self._category_repository.update_category(
                session,
                category_id=category_id,
                name=name,
                slug=slug,
                description=description,
                parent_id=parent_id,
                image_paths=image_paths,
            )

    def list_products_for_table(
        self,
        *,
        page: int,
        page_size: int,
        category_id: int | None = None,
        search_query: str = "",
    ) -> dict:
        with self._database.session_scope() as session:
            items, total_items = self._product_repository.list_products_for_table(
                session,
                page=page,
                page_size=page_size,
                category_id=category_id,
                search_query=search_query,
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

    def get_product_details(self, product_id: int) -> dict | None:
        with self._database.session_scope() as session:
            return self._product_repository.get_product_details(session, product_id)

    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: str | None,
        price_unit: str | None,
        sku: str | None,
        category_ids: list[int],
        image_urls: list[str] | None = None,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.create_product(
                session,
                name=name,
                description=description,
                price=price,
                price_unit=price_unit,
                sku=sku,
                category_ids=category_ids,
                image_urls=image_urls,
            )

    def update_product(
        self,
        *,
        product_id: int,
        name: str,
        description: str | None,
        price: str | None,
        price_unit: str | None,
        sku: str | None,
        category_ids: list[int],
        image_urls: list[str] | None = None,
    ) -> None:
        with self._database.session_scope() as session:
            self._product_repository.update_product(
                session,
                product_id=product_id,
                name=name,
                description=description,
                price=price,
                price_unit=price_unit,
                sku=sku,
                category_ids=category_ids,
                image_urls=image_urls,
            )

    def archive_product(self, product_id: int) -> bool:
        with self._database.session_scope() as session:
            return self._product_repository.archive_product(session, product_id)
