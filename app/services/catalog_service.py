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
    ) -> dict:
        return self._repository.list_products_for_table(
            page=page,
            page_size=page_size,
            category_id=category_id,
            search_query=search_query,
        )

    def get_product_details(self, product_id: int) -> dict | None:
        return self._repository.get_product_details(product_id)

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
        return self._repository.create_product(
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
        self._repository.update_product(
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
        return self._repository.archive_product(product_id)
