from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import themed_icon

_RU_TO_LAT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CategoryEditorDialog(QDialog):
    def __init__(
        self,
        *,
        category_options: list[dict],
        category_data: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._category_data = category_data or {}
        self._category_options = category_options
        self._result_data: dict | None = None
        self._slug_touched = False
        self._image_entries: list[dict[str, Any]] = []

        self.setWindowTitle("Добавить категорию" if category_data is None else "Изменить категорию")
        self.setMinimumWidth(760)
        self.setMinimumHeight(640)
        self._build_ui()
        self._fill_data()
        self._reload_image_list()

    @property
    def result_data(self) -> dict | None:
        return self._result_data

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self._on_name_changed)

        self.slug_input = QLineEdit()
        self.slug_input.setPlaceholderText("Заполняется автоматически, можно изменить вручную")
        self.slug_input.textEdited.connect(self._on_slug_edited)

        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(110)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("Без родительской категории", None)
        current_id = self._category_data.get("id")
        for option in self._category_options:
            option_id = option.get("id")
            if current_id is not None and option_id == current_id:
                continue
            self.parent_combo.addItem(str(option.get("name", "")), option_id)

        self.image_list = QListWidget()
        self.image_list.setMinimumHeight(220)
        self.image_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.image_list.setSpacing(4)
        self.image_list.itemDoubleClicked.connect(self._on_image_item_double_clicked)

        image_buttons = QHBoxLayout()
        add_image_button = QPushButton("Добавить изображения")
        add_image_button.setIcon(themed_icon("import_photos", color="#ffffff"))
        add_image_button.clicked.connect(self._add_images)

        remove_image_button = QPushButton("Удалить выбранное")
        remove_image_button.setIcon(themed_icon("delete_product", color="#ffffff"))
        remove_image_button.clicked.connect(self._remove_selected_image)

        image_buttons.addWidget(add_image_button)
        image_buttons.addWidget(remove_image_button)
        image_buttons.addStretch()

        image_panel = QVBoxLayout()
        image_panel.addWidget(self.image_list)
        image_panel.addLayout(image_buttons)
        image_panel_widget = QWidget()
        image_panel_widget.setLayout(image_panel)

        form.addRow("Название", self.name_input)
        form.addRow("Slug", self.slug_input)
        form.addRow("Родительская категория", self.parent_combo)
        form.addRow("Описание", self.description_input)
        form.addRow("Изображения категории", image_panel_widget)
        root.addLayout(form)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText("Сохранить")
        if cancel_button is not None:
            cancel_button.setText("Отмена")

        self.button_box.accepted.connect(self._on_save)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

    def _fill_data(self) -> None:
        if not self._category_data:
            return
        self.name_input.setText(str(self._category_data.get("name", "")))
        self.slug_input.setText(str(self._category_data.get("slug", "")))
        self.description_input.setPlainText(str(self._category_data.get("description", "")))
        parent_id = self._category_data.get("parent_id")
        index = self.parent_combo.findData(parent_id)
        self.parent_combo.setCurrentIndex(index if index >= 0 else 0)

        image_paths = [str(value).strip() for value in self._category_data.get("image_paths", []) if str(value).strip()]
        source_url = str(self._category_data.get("image_source_url") or "").strip()
        local_path = str(self._category_data.get("image_local_path") or "").strip()
        if source_url and source_url not in image_paths:
            image_paths.insert(0, source_url)

        self._image_entries = []
        for idx, image_path in enumerate(image_paths):
            entry = {
                "path": image_path,
                "is_primary": idx == 0,
            }
            if local_path and source_url and image_path == source_url:
                entry["preview_local_path"] = local_path
            self._image_entries.append(entry)

        self._slug_touched = True

    def _on_slug_edited(self, _value: str) -> None:
        self._slug_touched = True

    def _on_name_changed(self, value: str) -> None:
        if self._slug_touched:
            return
        self.slug_input.setText(self._slugify(value))

    def _slugify(self, value: str) -> str:
        lowered = value.strip().lower()
        transliterated = "".join(_RU_TO_LAT.get(ch, ch) for ch in lowered)
        normalized = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
        return normalized

    def _reload_image_list(self) -> None:
        selected_key = None
        current_item = self.image_list.currentItem()
        if current_item is not None:
            selected_key = str(current_item.data(Qt.ItemDataRole.UserRole) or "")

        self.image_list.clear()
        for index, entry in enumerate(self._image_entries):
            key = self._entry_key(index, entry)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(0, 96))
            self.image_list.addItem(item)
            self.image_list.setItemWidget(item, self._build_image_item_widget(index, entry))

        if selected_key:
            for index in range(self.image_list.count()):
                item = self.image_list.item(index)
                if str(item.data(Qt.ItemDataRole.UserRole) or "") == selected_key:
                    self.image_list.setCurrentItem(item)
                    break

    def _build_image_item_widget(self, index: int, entry: dict[str, Any]) -> QWidget:
        key = self._entry_key(index, entry)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        thumb = ClickableImageLabel()
        thumb.setFixedSize(84, 84)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("border: 1px solid #d5dde8; border-radius: 6px; background: #f7f9fc;")
        pixmap = self._thumbnail_pixmap(entry)
        if pixmap is None:
            thumb.setText("Нет\nпревью")
            thumb.setStyleSheet(
                "border: 1px solid #d5dde8; border-radius: 6px; background: #f7f9fc; color:#6b7280;"
            )
        else:
            thumb.setPixmap(pixmap)
        thumb.clicked.connect(lambda row_key=key: self._on_thumbnail_clicked(row_key))
        layout.addWidget(thumb)

        info_layout = QVBoxLayout()
        name_label = QLabel(self._display_name(entry))
        name_font = QFont(name_label.font())
        if name_font.pointSize() <= 0 and name_font.pixelSize() <= 0:
            name_font.setPointSize(9)
        name_font.setBold(bool(entry.get("is_primary")))
        name_label.setFont(name_font)
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        source_label = QLabel("URL" if self._is_remote_url(str(entry.get("path") or "")) else "Локальный файл")
        source_label.setStyleSheet("color:#5e6c83;")
        info_layout.addWidget(source_label)

        primary_checkbox = QCheckBox("Сделать основным")
        primary_checkbox.setChecked(bool(entry.get("is_primary")))
        primary_checkbox.toggled.connect(lambda checked, row_key=key: self._on_primary_toggled(row_key, checked))
        info_layout.addWidget(primary_checkbox)
        info_layout.addStretch()

        layout.addLayout(info_layout, stretch=1)
        return widget

    def _entry_key(self, index: int, entry: dict[str, Any]) -> str:
        return f"{index}:{str(entry.get('path') or '').strip()}"

    def _find_entry_by_key(self, key: str) -> tuple[int, dict[str, Any]] | None:
        for index, entry in enumerate(self._image_entries):
            if self._entry_key(index, entry) == key:
                return index, entry
        return None

    def _add_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения категории",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp);;Все файлы (*.*)",
        )
        if not files:
            return
        existing_paths = {str(item.get("path") or "").strip() for item in self._image_entries}
        for file_path in files:
            normalized = str(file_path).strip()
            if not normalized or normalized in existing_paths:
                continue
            self._image_entries.append({"path": normalized, "is_primary": False})
            existing_paths.add(normalized)

        if self._image_entries and not any(bool(entry.get("is_primary")) for entry in self._image_entries):
            self._image_entries[0]["is_primary"] = True
        self._reload_image_list()

    def _remove_selected_image(self) -> None:
        current_item = self.image_list.currentItem()
        if current_item is None:
            QMessageBox.information(self, "Изображение не выбрано", "Выберите изображение в списке.")
            return
        key = str(current_item.data(Qt.ItemDataRole.UserRole) or "")
        found = self._find_entry_by_key(key)
        if found is None:
            return
        index, _entry = found
        del self._image_entries[index]
        if self._image_entries and not any(bool(entry.get("is_primary")) for entry in self._image_entries):
            self._image_entries[0]["is_primary"] = True
        self._reload_image_list()

    def _on_primary_toggled(self, key: str, checked: bool) -> None:
        if not checked:
            return
        found = self._find_entry_by_key(key)
        if found is None:
            return
        selected_index, _entry = found
        for index, entry in enumerate(self._image_entries):
            entry["is_primary"] = index == selected_index
        self._reload_image_list()

    def _resolve_preview_path(self, entry: dict[str, Any]) -> Path | None:
        preview_local = str(entry.get("preview_local_path") or "").strip()
        if preview_local:
            candidate = Path(preview_local)
            if candidate.exists() and candidate.is_file():
                return candidate

        path_value = str(entry.get("path") or "").strip()
        if not path_value:
            return None
        if self._is_remote_url(path_value):
            return None
        candidate = Path(path_value)
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def _thumbnail_pixmap(self, entry: dict[str, Any]) -> QPixmap | None:
        preview_path = self._resolve_preview_path(entry)
        if preview_path is None:
            return None
        pixmap = QPixmap(str(preview_path))
        if pixmap.isNull():
            return None
        return pixmap.scaled(
            80,
            80,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _display_name(self, entry: dict[str, Any]) -> str:
        value = str(entry.get("path") or "").strip()
        if not value:
            return "Без имени"
        if self._is_remote_url(value):
            parsed = urlparse(value)
            name = Path(parsed.path).name
            return name or value
        return Path(value).name or value

    def _on_thumbnail_clicked(self, key: str) -> None:
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole) or "") == key:
                self.image_list.setCurrentItem(item)
                break
        found = self._find_entry_by_key(key)
        if found is None:
            return
        _index, entry = found
        self._open_preview(entry)

    def _on_image_item_double_clicked(self, item: QListWidgetItem) -> None:
        key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        found = self._find_entry_by_key(key)
        if found is None:
            return
        _index, entry = found
        self._open_preview(entry)

    def _open_preview(self, entry: dict[str, Any]) -> None:
        preview_path = self._resolve_preview_path(entry)
        if preview_path is None:
            QMessageBox.information(
                self,
                "Предпросмотр недоступен",
                "Для этого изображения локальный предпросмотр недоступен.",
            )
            return

        pixmap = QPixmap(str(preview_path))
        if pixmap.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть изображение.")
            return

        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle(f"Предпросмотр: {self._display_name(entry)}")
        preview_dialog.resize(960, 720)
        layout = QVBoxLayout(preview_dialog)

        title = QLabel(self._display_name(entry))
        font = QFont(title.font())
        if font.pointSize() <= 0 and font.pixelSize() <= 0:
            font.setPointSize(10)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setPixmap(
            pixmap.scaled(
                920,
                640,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(image_label)
        preview_dialog.exec()

    def _collect_images(self) -> list[str]:
        if not self._image_entries:
            return []
        indexed_entries = list(enumerate(self._image_entries))
        indexed_entries.sort(key=lambda pair: (not bool(pair[1].get("is_primary")), pair[0]))
        result: list[str] = []
        seen: set[str] = set()
        for _idx, entry in indexed_entries:
            value = str(entry.get("path") or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _is_remote_url(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered.startswith("http://") or lowered.startswith("https://")

    def _on_save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название категории не может быть пустым.")
            return

        self._result_data = {
            "name": name,
            "slug": self.slug_input.text().strip() or self._slugify(name) or None,
            "description": self.description_input.toPlainText().strip() or None,
            "parent_id": self.parent_combo.currentData(),
            "image_paths": self._collect_images(),
        }
        self.accept()
