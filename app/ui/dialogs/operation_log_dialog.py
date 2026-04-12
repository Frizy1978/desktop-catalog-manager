from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.operation_log_service import OperationLogService
from app.ui.icons import themed_icon


class OperationLogDialog(QDialog):
    def __init__(
        self,
        *,
        operation_log_service: OperationLogService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._operation_log_service = operation_log_service
        self._runs: list[dict[str, Any]] = []

        self.setWindowTitle("Журнал операций")
        self.resize(980, 560)
        self._build_ui()
        self._reload_runs()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.summary_label = QLabel("Загрузка журнала...")
        toolbar.addWidget(self.summary_label)
        toolbar.addStretch()

        refresh_button = QPushButton("Обновить")
        refresh_button.setIcon(themed_icon("refresh", color="#ffffff"))
        refresh_button.clicked.connect(self._reload_runs)
        toolbar.addWidget(refresh_button)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_runs_table())
        splitter.addWidget(self._build_details_panel())
        splitter.setSizes([330, 200])
        root.addWidget(splitter)

        controls = QHBoxLayout()
        controls.addStretch()
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        root.addLayout(controls)

    def _build_runs_table(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Тип", "Статус", "Начало", "Окончание", "Длительность"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.table)
        return panel

    def _build_details_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        counters_label = QLabel("Счётчики")
        self.counters_text = QTextEdit()
        self.counters_text.setReadOnly(True)
        self.counters_text.setPlaceholderText("Нет данных")

        errors_label = QLabel("Ошибки")
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setPlaceholderText("Нет ошибок")

        layout.addWidget(counters_label)
        layout.addWidget(self.counters_text, stretch=1)
        layout.addWidget(errors_label)
        layout.addWidget(self.errors_text, stretch=1)
        return panel

    def _reload_runs(self) -> None:
        self._runs = self._operation_log_service.list_recent_runs(limit=200)
        self.table.setRowCount(0)

        if not self._runs:
            self.summary_label.setText("Запусков синхронизации пока нет.")
            self.counters_text.clear()
            self.errors_text.clear()
            return

        self.summary_label.setText(f"Показано запусков: {len(self._runs)}")
        for run in self._runs:
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)
            self._set_cell(row_index, 0, str(run["id"]))
            self._set_cell(row_index, 1, str(run["sync_type"]))
            self._set_cell(row_index, 2, str(run["status_label"]))
            self._set_cell(row_index, 3, str(run["started_at_label"]))
            self._set_cell(row_index, 4, str(run["finished_at_label"]))
            self._set_cell(row_index, 5, str(run["duration_label"]))

        self.table.selectRow(0)

    def _set_cell(self, row: int, column: int, value: str) -> None:
        item = QTableWidgetItem(value)
        item.setTextAlignment(
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        )
        self.table.setItem(row, column, item)

    def _on_selection_changed(self) -> None:
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            self.counters_text.clear()
            self.errors_text.clear()
            return

        index = selected_indexes[0].row()
        if index < 0 or index >= len(self._runs):
            self.counters_text.clear()
            self.errors_text.clear()
            return

        run = self._runs[index]
        counters = run.get("counters") or {}
        errors = run.get("errors") or []

        self.counters_text.setPlainText(
            json.dumps(counters, ensure_ascii=False, indent=2) if counters else "Нет данных"
        )
        self.errors_text.setPlainText("\n".join(errors) if errors else "Нет ошибок")
