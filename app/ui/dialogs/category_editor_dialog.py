from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
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

        self.setWindowTitle(
            "Добавить категорию" if category_data is None else "Изменить категорию"
        )
        self.setMinimumWidth(620)
        self.setMinimumHeight(560)
        self._build_ui()
        self._fill_data()

    @property
    def result_data(self) -> dict | None:
        return self._result_data

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self._on_name_changed)

        self.slug_input = QLineEdit()
        self.slug_input.setPlaceholderText(
            "Заполняется автоматически, можно поправить вручную"
        )
        self.slug_input.textEdited.connect(self._on_slug_edited)

        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(120)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("Без родительской категории", None)
        current_id = self._category_data.get("id")
        for option in self._category_options:
            option_id = option.get("id")
            if current_id is not None and option_id == current_id:
                continue
            self.parent_combo.addItem(str(option.get("name", "")), option_id)

        self.image_list = QListWidget()
        self.image_list.setMinimumHeight(120)

        image_buttons = QHBoxLayout()
        add_image_button = QPushButton("Добавить изображения")
        add_image_button.setIcon(themed_icon("import_photos", color="#ffffff"))
        add_image_button.clicked.connect(self._add_images)

        remove_image_button = QPushButton("Удалить выбранные")
        remove_image_button.setIcon(themed_icon("delete_product", color="#ffffff"))
        remove_image_button.clicked.connect(self._remove_selected_images)

        image_buttons.addWidget(add_image_button)
        image_buttons.addWidget(remove_image_button)

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
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
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

        for image_path in self._category_data.get("image_paths", []):
            self.image_list.addItem(str(image_path))
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

    def _add_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения категории",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp);;Все файлы (*.*)",
        )
        if not files:
            return
        existing = {self.image_list.item(i).text() for i in range(self.image_list.count())}
        for file_path in files:
            if file_path not in existing:
                self.image_list.addItem(file_path)

    def _remove_selected_images(self) -> None:
        for item in self.image_list.selectedItems():
            row = self.image_list.row(item)
            self.image_list.takeItem(row)

    def _collect_images(self) -> list[str]:
        return [
            self.image_list.item(i).text().strip()
            for i in range(self.image_list.count())
            if self.image_list.item(i).text().strip()
        ]

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
