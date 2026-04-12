from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class ProductsTablePanel(QWidget):
    page_changed = Signal(int)
    page_size_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        group = QGroupBox("Товары")
        group_layout = QVBoxLayout(group)

        self.stack = QStackedWidget()

        self.empty_state = QLabel(
            "Товары не загружены.\nИспользуйте «Импорт» для загрузки каталога."
        )
        self.empty_state.setStyleSheet("color: #5e6c83; font-size: 14px;")
        self.empty_state.setAlignment(Qt.AlignCenter)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.model = QStandardItemModel(0, 10)
        self.model.setHorizontalHeaderLabels(
            [
                "Выбор",
                "Фото",
                "Название",
                "Категория",
                "SKU",
                "Цена",
                "Ед. изм.",
                "Статус синхронизации",
                "Обновлено",
                "Видимость",
            ]
        )
        self.table_view.setModel(self.model)

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addWidget(self.empty_state)

        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.addWidget(self.table_view)
        table_layout.addLayout(self._build_pagination_bar())

        self.stack.addWidget(empty_page)
        self.stack.addWidget(table_page)
        self.stack.setCurrentIndex(0)

        group_layout.addWidget(self.stack)
        root_layout.addWidget(group)

    def _build_pagination_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 6, 0, 0)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["25", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)

        self.prev_button = QPushButton("←")
        self.prev_button.setToolTip("Предыдущая страница")
        self.prev_button.clicked.connect(self._go_prev)

        self.next_button = QPushButton("→")
        self.next_button.setToolTip("Следующая страница")
        self.next_button.clicked.connect(self._go_next)

        self.page_info_label = QLabel("Страница 1 из 1 · Всего: 0")
        self.page_info_label.setStyleSheet("color: #5e6c83;")

        layout.addWidget(QLabel("На странице:"))
        layout.addWidget(self.page_size_combo)
        layout.addSpacing(10)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        layout.addSpacing(10)
        layout.addWidget(self.page_info_label)
        layout.addStretch()
        return layout

    def current_page_size(self) -> int:
        return int(self.page_size_combo.currentText())

    def populate_page(
        self,
        *,
        rows: list[dict],
        page: int,
        page_size: int,
        total_items: int,
        total_pages: int,
    ) -> None:
        self.model.removeRows(0, self.model.rowCount())
        self._current_page = max(1, page)
        self._total_pages = max(1, total_pages)

        if not rows and total_items == 0:
            self.stack.setCurrentIndex(0)
            self.page_info_label.setText("Страница 1 из 1 · Всего: 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return

        for row in rows:
            sync_status = self._sync_status_label(str(row.get("sync_status", "")))
            visibility = self._visibility_label(str(row.get("published_state", "")))
            items = [
                QStandardItem(""),
                QStandardItem(""),
                QStandardItem(str(row.get("name", ""))),
                QStandardItem(str(row.get("category_name", ""))),
                QStandardItem(str(row.get("sku", ""))),
                QStandardItem(str(row.get("price", ""))),
                QStandardItem(str(row.get("price_unit", ""))),
                QStandardItem(sync_status),
                QStandardItem(str(row.get("updated_at", ""))),
                QStandardItem(visibility),
            ]
            self.model.appendRow(items)

        combo_value = str(page_size)
        if self.page_size_combo.currentText() != combo_value:
            self.page_size_combo.blockSignals(True)
            if self.page_size_combo.findText(combo_value) < 0:
                self.page_size_combo.addItem(combo_value)
            self.page_size_combo.setCurrentText(combo_value)
            self.page_size_combo.blockSignals(False)

        self.page_info_label.setText(
            f"Страница {self._current_page} из {self._total_pages} · Всего: {total_items}"
        )
        self.prev_button.setEnabled(self._current_page > 1)
        self.next_button.setEnabled(self._current_page < self._total_pages)
        self.stack.setCurrentIndex(1)

    def _on_page_size_changed(self, value: str) -> None:
        self.page_size_changed.emit(int(value))

    def _go_prev(self) -> None:
        if self._current_page > 1:
            self.page_changed.emit(self._current_page - 1)

    def _go_next(self) -> None:
        if self._current_page < self._total_pages:
            self.page_changed.emit(self._current_page + 1)

    def _sync_status_label(self, status: str) -> str:
        labels = {
            "synced": "синхронизировано",
            "modified_local": "изменено локально",
            "new_local": "новое локально",
            "publish_pending": "ожидает публикации",
            "publish_error": "ошибка публикации",
            "imported": "импортировано",
            "archived": "в архиве",
        }
        return labels.get(status, status)

    def _visibility_label(self, state: str) -> str:
        labels = {
            "draft": "черновик",
            "visible": "видимый",
            "hidden": "скрытый",
            "published": "опубликован",
        }
        return labels.get(state, state)
