from __future__ import annotations

import sqlite3
from typing import Any

from app.core.database import Database


class AuthRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def count_users(self) -> int:
        with self._database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            return int(row["count"])

    def ensure_role(self, name: str, description: str | None = None) -> int:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO roles(name, description)
                VALUES(?, ?)
                """,
                (name, description),
            )
            row = connection.execute(
                "SELECT id FROM roles WHERE name = ?",
                (name,),
            ).fetchone()
            return int(row["id"])

    def create_user(
        self,
        username: str,
        password_hash: str,
        password_salt: str,
        role_id: int,
    ) -> int:
        with self._database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users(username, password_hash, password_salt, role_id)
                VALUES(?, ?, ?, ?)
                """,
                (username, password_hash, password_salt, role_id),
            )
            return int(cursor.lastrowid)

    def get_user_credentials(self, username: str) -> dict[str, Any] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    users.id,
                    users.username,
                    users.password_hash,
                    users.password_salt,
                    roles.name AS role_name
                FROM users
                INNER JOIN roles ON users.role_id = roles.id
                WHERE users.username = ? AND users.is_active = 1
                """,
                (username,),
            ).fetchone()
            return dict(row) if row is not None else None

    def update_last_login(self, user_id: int) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (user_id,),
            )

    def update_user_credentials(
        self,
        *,
        user_id: int,
        username: str,
        password_hash: str,
        password_salt: str,
    ) -> None:
        with self._database.connect() as connection:
            try:
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?,
                        password_hash = ?,
                        password_salt = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (username, password_hash, password_salt, user_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Логин уже используется другим пользователем.") from exc
