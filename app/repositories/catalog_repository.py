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
        sync_status_filter: str = "",
        published_state_filter: str = "",
        visibility_filter: str = "",
        is_featured_filter: str = "",
        stock_status_filter: str = "",
    ) -> dict:
        with self._database.session_scope() as session:
            items, total_items = self._product_repository.list_products_for_table(
                session,
                page=page,
                page_size=page_size,
                category_id=category_id,
                search_query=search_query,
                sync_status_filter=sync_status_filter,
                published_state_filter=published_state_filter,
                visibility_filter=visibility_filter,
                is_featured_filter=is_featured_filter,
                stock_status_filter=stock_status_filter,
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

    def list_product_ids_for_table_selection(
        self,
        *,
        category_id: int | None = None,
        search_query: str = "",
        sync_status_filter: str = "",
        published_state_filter: str = "",
        visibility_filter: str = "",
        is_featured_filter: str = "",
        stock_status_filter: str = "",
    ) -> list[int]:
        with self._database.session_scope() as session:
            return self._product_repository.list_product_ids_for_table_selection(
                session,
                category_id=category_id,
                search_query=search_query,
                sync_status_filter=sync_status_filter,
                published_state_filter=published_state_filter,
                visibility_filter=visibility_filter,
                is_featured_filter=is_featured_filter,
                stock_status_filter=stock_status_filter,
            )

    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: str | None,
        price_unit: str | None,
        sku: str | None,
        published_state: str | None,
        visibility: str | None,
        is_featured: bool,
        stock_status: str | None,
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
                published_state=published_state,
                visibility=visibility,
                is_featured=is_featured,
                stock_status=stock_status,
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
        published_state: str | None,
        visibility: str | None,
        is_featured: bool,
        stock_status: str | None,
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
                published_state=published_state,
                visibility=visibility,
                is_featured=is_featured,
                stock_status=stock_status,
                category_ids=category_ids,
                image_urls=image_urls,
            )

    def archive_product(self, product_id: int) -> bool:
        with self._database.session_scope() as session:
            return self._product_repository.archive_product(session, product_id)

    def bulk_update_product_price_unit(
        self,
        *,
        product_ids: list[int],
        price_unit: str | None,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_price_unit(
                session,
                product_ids=product_ids,
                price_unit=price_unit,
            )

    def bulk_update_product_price(
        self,
        *,
        product_ids: list[int],
        price: str,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_price(
                session,
                product_ids=product_ids,
                price=price,
            )

    def bulk_replace_product_category(
        self,
        *,
        product_ids: list[int],
        category_id: int,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_replace_category(
                session,
                product_ids=product_ids,
                category_id=category_id,
            )

    def bulk_update_product_published_state(
        self,
        *,
        product_ids: list[int],
        published_state: str,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_published_state(
                session,
                product_ids=product_ids,
                published_state=published_state,
            )

    def bulk_update_product_visibility(
        self,
        *,
        product_ids: list[int],
        visibility: str,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_visibility(
                session,
                product_ids=product_ids,
                visibility=visibility,
            )

    def bulk_update_product_featured(
        self,
        *,
        product_ids: list[int],
        is_featured: bool,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_featured(
                session,
                product_ids=product_ids,
                is_featured=is_featured,
            )

    def bulk_update_product_stock_status(
        self,
        *,
        product_ids: list[int],
        stock_status: str,
    ) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_update_stock_status(
                session,
                product_ids=product_ids,
                stock_status=stock_status,
            )

    def bulk_archive_products(self, *, product_ids: list[int]) -> int:
        with self._database.session_scope() as session:
            return self._product_repository.bulk_archive_products(
                session,
                product_ids=product_ids,
            )

    def get_publish_preview(self) -> dict:
        with self._database.session_scope() as session:
            categories = self._category_repository.list_categories_for_publish(session)
            products = self._product_repository.list_products_publish_preview(session)
            return {
                "categories": categories,
                "products": products,
                "categories_total": len(categories),
                "products_total": len(products),
                "total_items": len(categories) + len(products),
            }
