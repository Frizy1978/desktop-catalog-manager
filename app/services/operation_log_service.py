from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.repositories.sync_run_repository import SyncRunRepository


class OperationLogService:
    def __init__(self, repository: SyncRunRepository) -> None:
        self._repository = repository

    def list_recent_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._repository.list_recent_runs(limit=limit)
        return [self._normalize_row(row) for row in rows]

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        started_at = row.get("started_at")
        finished_at = row.get("finished_at")
        return {
            "id": row.get("id"),
            "sync_type": row.get("sync_type") or "",
            "status": row.get("status") or "",
            "status_label": self._status_label(str(row.get("status") or "")),
            "started_at": started_at,
            "finished_at": finished_at,
            "started_at_label": self._format_dt(started_at),
            "finished_at_label": self._format_dt(finished_at),
            "duration_label": self._format_duration(started_at, finished_at),
            "counters": self._safe_json_object(row.get("counters_json")),
            "errors": self._safe_json_array(row.get("errors_json")),
        }

    def _status_label(self, status: str) -> str:
        labels = {
            "pending": "ожидает",
            "running": "выполняется",
            "success": "успешно",
            "error": "ошибка",
        }
        return labels.get(status, status)

    def _format_dt(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    def _format_duration(self, started_at: Any, finished_at: Any) -> str:
        if not isinstance(started_at, datetime):
            return "-"
        if not isinstance(finished_at, datetime):
            return "выполняется"
        seconds = int(max(0.0, (finished_at - started_at).total_seconds()))
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}ч {minutes}м {sec}с"
        if minutes > 0:
            return f"{minutes}м {sec}с"
        return f"{sec}с"

    def _safe_json_object(self, raw: Any) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _safe_json_array(self, raw: Any) -> list[str]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]
