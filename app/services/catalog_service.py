from __future__ import annotations

from app.repositories.catalog_repository import CatalogRepository


class CatalogService:
    """Phase 3 service for catalog UI read/write use-cases."""

    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    def get_category_sidebar_items(self) -> list[dict]:
        return self._repository.list_categories_for_sidebar()

    def get_category_options(self) -> list[dict]:
        return self._repository.list_category_options()

    def get_category_details(self, category_id: int) -> dict | None:
        return self._repository.get_category_details(category_id)

    def create_category(
        self,
        *,
        name: str,
        slug: str | None,
        description: str | None,
        parent_id: int | None,
        image_paths: list[str] | None = None,
    ) -> int:
        return self._repository.create_category(
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
        self._repository.update_category(
            category_id=category_id,
            name=name,
            slug=slug,
            description=description,
            parent_id=parent_id,
            image_paths=image_paths,
        )

    def get_products_table_page(
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
        return self._repository.list_products_for_table(
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

    def get_product_details(self, product_id: int) -> dict | None:
        return self._repository.get_product_details(product_id)

    def get_products_table_selection_ids(
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
        return self._repository.list_product_ids_for_table_selection(
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
        return self._repository.create_product(
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
        self._repository.update_product(
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
        return self._repository.archive_product(product_id)

    def bulk_update_product_price_unit(
        self,
        *,
        product_ids: list[int],
        price_unit: str | None,
    ) -> int:
        return self._repository.bulk_update_product_price_unit(
            product_ids=product_ids,
            price_unit=price_unit,
        )

    def bulk_update_product_price(
        self,
        *,
        product_ids: list[int],
        price: str,
    ) -> int:
        return self._repository.bulk_update_product_price(
            product_ids=product_ids,
            price=price,
        )

    def bulk_replace_product_category(
        self,
        *,
        product_ids: list[int],
        category_id: int,
    ) -> int:
        return self._repository.bulk_replace_product_category(
            product_ids=product_ids,
            category_id=category_id,
        )

    def bulk_update_product_published_state(
        self,
        *,
        product_ids: list[int],
        published_state: str,
    ) -> int:
        return self._repository.bulk_update_product_published_state(
            product_ids=product_ids,
            published_state=published_state,
        )

    def bulk_update_product_visibility(
        self,
        *,
        product_ids: list[int],
        visibility: str,
    ) -> int:
        return self._repository.bulk_update_product_visibility(
            product_ids=product_ids,
            visibility=visibility,
        )

    def bulk_update_product_featured(
        self,
        *,
        product_ids: list[int],
        is_featured: bool,
    ) -> int:
        return self._repository.bulk_update_product_featured(
            product_ids=product_ids,
            is_featured=is_featured,
        )

    def bulk_update_product_stock_status(
        self,
        *,
        product_ids: list[int],
        stock_status: str,
    ) -> int:
        return self._repository.bulk_update_product_stock_status(
            product_ids=product_ids,
            stock_status=stock_status,
        )

    def bulk_archive_products(self, *, product_ids: list[int]) -> int:
        return self._repository.bulk_archive_products(product_ids=product_ids)

    def get_publish_preview(self) -> dict:
        return self._repository.get_publish_preview()
