from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.services.publish_service import PublishRunResult, WooCommercePublishService

logger = logging.getLogger(__name__)


class PublishWorker(QObject):
    progress_changed = Signal(int, str)
    publish_finished = Signal(object)

    def __init__(self, publish_service: WooCommercePublishService) -> None:
        super().__init__()
        self._publish_service = publish_service

    @Slot()
    def run(self) -> None:
        try:
            result = self._publish_service.run_publish(progress_callback=self._on_progress)
        except Exception:  # noqa: BLE001
            logger.exception("Publish worker crashed unexpectedly")
            result = PublishRunResult(
                success=False,
                counters={},
                errors=[
                    "Внутренняя ошибка публикации. Подробности записаны в журнал логов.",
                ],
            )
        self.publish_finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress_changed.emit(percent, message)
