from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.services.sync_import_service import ImportRunResult, WooCommerceImportService

logger = logging.getLogger(__name__)


class ImportWorker(QObject):
    progress_changed = Signal(int, str)
    import_finished = Signal(object)

    def __init__(self, import_service: WooCommerceImportService) -> None:
        super().__init__()
        self._import_service = import_service

    @Slot()
    def run(self) -> None:
        try:
            result = self._import_service.run_initial_import(
                progress_callback=self._on_progress
            )
        except Exception:  # noqa: BLE001
            logger.exception("Import worker crashed unexpectedly")
            result = ImportRunResult(
                success=False,
                counters={},
                errors=[
                    "Внутренняя ошибка импорта. Подробности записаны в журнал логов.",
                ],
            )
        self.import_finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress_changed.emit(percent, message)
