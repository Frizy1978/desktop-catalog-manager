from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.db.models import PublishJob
from app.db.session import SqlAlchemyDatabase


class PublishJobRepository:
    def __init__(self, database: SqlAlchemyDatabase) -> None:
        self._database = database

    def start_job(
        self,
        *,
        target: str,
        entities: dict[str, Any] | None = None,
    ) -> int:
        with self._database.session_scope() as session:
            job = PublishJob(
                target=target,
                status="running",
                created_at=datetime.now(),
                entities_json=json.dumps(entities or {}, ensure_ascii=False),
            )
            session.add(job)
            session.flush()
            return int(job.id)

    def finish_job(
        self,
        job_id: int,
        *,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        with self._database.session_scope() as session:
            job = session.scalar(select(PublishJob).where(PublishJob.id == job_id))
            if job is None:
                return
            job.status = status
            job.result_json = json.dumps(result or {}, ensure_ascii=False)
