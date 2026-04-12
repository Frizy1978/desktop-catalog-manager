from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class ProductsTablePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        group = QGroupBox("Товары")
        group_layout = QVBoxLayout(group)

        self.stack = QStackedWidget()

        self.empty_state = QLabel(
            "Товары не загружены.\nИспользуйте «Загрузить из WooCommerce» для импорта каталога."
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

        self.stack.addWidget(empty_page)
        self.stack.addWidget(table_page)
        self.stack.setCurrentIndex(0)

        group_layout.addWidget(self.stack)
        root_layout.addWidget(group)

    def populate(self, rows: list[dict]) -> None:
        self.model.removeRows(0, self.model.rowCount())
        if not rows:
            self.stack.setCurrentIndex(0)
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
        self.stack.setCurrentIndex(1)

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
