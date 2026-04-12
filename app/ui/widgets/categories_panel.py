from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import themed_icon


class CategoriesPanel(QWidget):
    action_triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)

        group = QGroupBox("Категории")
        layout = QVBoxLayout(group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск категорий...")
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.addItem("Все категории")
        layout.addWidget(self.list_widget, stretch=1)

        controls = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.edit_button = QPushButton("Изменить")
        self.archive_button = QPushButton("В архив")
        self.add_button.setIcon(themed_icon("add_category", color="#ffffff"))
        self.edit_button.setIcon(themed_icon("edit_category", color="#ffffff"))
        self.archive_button.setIcon(themed_icon("archive_category", color="#ffffff"))

        self.add_button.clicked.connect(lambda: self.action_triggered.emit("add_category"))
        self.edit_button.clicked.connect(lambda: self.action_triggered.emit("edit_category"))
        self.archive_button.clicked.connect(
            lambda: self.action_triggered.emit("archive_category")
        )

        controls.addWidget(self.add_button)
        controls.addWidget(self.edit_button)
        controls.addWidget(self.archive_button)
        layout.addLayout(controls)

        root_layout.addWidget(group)

    def populate(self, categories: list[dict]) -> None:
        self.list_widget.clear()
        if not categories:
            self.list_widget.addItem("Категории пока отсутствуют")
            return

        for category in categories:
            name = category.get("name", "Без названия")
            sync_status = self._sync_status_label(str(category.get("sync_status", "unknown")))
            self.list_widget.addItem(f"{name} [{sync_status}]")

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
