from __future__ import annotations

from app.core.database import Database


class CatalogRepository:
    """Phase 1 placeholder repository for category/product read models."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_categories_for_sidebar(self) -> list[dict]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, sync_status
                FROM categories
                WHERE is_archived = 0
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def list_products_for_table(self) -> list[dict]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    products.id,
                    products.name,
                    products.sku,
                    products.price,
                    products.price_unit,
                    products.sync_status,
                    products.updated_at,
                    products.published_state
                FROM products
                WHERE products.is_archived = 0
                ORDER BY products.updated_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
