from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import ensure_directory


@dataclass(slots=True)
class RememberedLogin:
    username: str
    password: str
    remember_password: bool


class LoginMemoryService:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        ensure_directory(storage_path.parent)

    def load(self) -> RememberedLogin:
        if not self._storage_path.exists():
            return RememberedLogin(username="", password="", remember_password=False)

        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return RememberedLogin(username="", password="", remember_password=False)

        return RememberedLogin(
            username=str(data.get("username") or ""),
            password=str(data.get("password") or ""),
            remember_password=bool(data.get("remember_password", False)),
        )

    def save(self, username: str, password: str) -> None:
        payload = {
            "username": username,
            "password": password,
            "remember_password": True,
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        if self._storage_path.exists():
            self._storage_path.unlink()
