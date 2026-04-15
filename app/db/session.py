from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


class SqlAlchemyDatabase:
    def __init__(self, db_path: Path) -> None:
        self._engine = create_engine(
            f"sqlite+pysqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            future=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
        self._configure_sqlite()

    def _configure_sqlite(self) -> None:
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

    def initialize(self) -> None:
        # Ensure model metadata is registered before table creation.
        from app.db import models as _models  # noqa: F401

        Base.metadata.create_all(self._engine)
        self._apply_runtime_migrations()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _apply_runtime_migrations(self) -> None:
        with self._engine.begin() as connection:
            table_info = connection.exec_driver_sql("PRAGMA table_info(product_images)")
            columns = {row[1] for row in table_info.fetchall()}
            if "local_path" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE product_images ADD COLUMN local_path TEXT"
                )
            if "source_type" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE product_images ADD COLUMN source_type TEXT NOT NULL DEFAULT 'wc_url'"
                )
            if "metadata_json" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE product_images ADD COLUMN metadata_json TEXT"
                )

            category_table_info = connection.exec_driver_sql("PRAGMA table_info(categories)")
            category_columns = {row[1] for row in category_table_info.fetchall()}
            if "image_source_url" not in category_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE categories ADD COLUMN image_source_url TEXT"
                )
            if "image_local_path" not in category_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE categories ADD COLUMN image_local_path TEXT"
                )
            connection.exec_driver_sql(
                """
                UPDATE categories
                SET image_source_url = image_path
                WHERE (image_source_url IS NULL OR image_source_url = '')
                  AND image_path IS NOT NULL
                  AND image_path != ''
                """
            )

            connection.exec_driver_sql(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_product_primary_image
                ON product_images(product_id)
                WHERE is_primary = 1
                """
            )

            product_table_info = connection.exec_driver_sql("PRAGMA table_info(products)")
            product_columns = {row[1] for row in product_table_info.fetchall()}
            if "stock_status" not in product_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE products ADD COLUMN stock_status TEXT NOT NULL DEFAULT 'instock'"
                )
            connection.exec_driver_sql(
                """
                UPDATE products
                SET stock_status = 'instock'
                WHERE stock_status IS NULL OR stock_status = ''
                """
            )
