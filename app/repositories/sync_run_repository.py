from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.db.models import SyncRun
from app.db.session import SqlAlchemyDatabase


class SyncRunRepository:
    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    def start_run(self, sync_type: str) -> int:
        with self._database.session_scope() as session:
            run = SyncRun(
                sync_type=sync_type,
                status="running",
                started_at=datetime.now(),
            )
            session.add(run)
            session.flush()
            return int(run.id)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        counters: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        with self._database.session_scope() as session:
            run = session.scalar(select(SyncRun).where(SyncRun.id == run_id))
            if run is None:
                return
            run.status = status
            run.finished_at = datetime.now()
            run.counters_json = json.dumps(counters or {}, ensure_ascii=False)
            run.errors_json = json.dumps(errors or [], ensure_ascii=False)

    def list_recent_runs(self, limit: int = 20) -> list[dict]:
        with self._database.session_scope() as session:
            rows = session.execute(
                select(
                    SyncRun.id,
                    SyncRun.sync_type,
                    SyncRun.status,
                    SyncRun.started_at,
                    SyncRun.finished_at,
                    SyncRun.counters_json,
                    SyncRun.errors_json,
                )
                .order_by(SyncRun.started_at.desc())
                .limit(limit)
            ).all()
            return [
                {
                    "id": row.id,
                    "sync_type": row.sync_type,
                    "status": row.status,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "counters_json": row.counters_json,
                    "errors_json": row.errors_json,
                }
                for row in rows
            ]
