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

            connection.exec_driver_sql(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_product_primary_image
                ON product_images(product_id)
                WHERE is_primary = 1
                """
            )
