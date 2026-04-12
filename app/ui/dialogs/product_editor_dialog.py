from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProductEditorDialog(QDialog):
    def __init__(
        self,
        *,
        category_options: list[dict],
        product_data: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._category_options = category_options
        self._product_data = product_data or {}
        self._result_data: dict | None = None

        self.setWindowTitle("Добавить товар" if product_data is None else "Изменить товар")
        self.setMinimumWidth(720)
        self.setMinimumHeight(620)
        self._build_ui()
        self._fill_data()

    @property
    def result_data(self) -> dict | None:
        return self._result_data

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Например: 850.00")
        self.price_unit_input = QLineEdit()
        self.price_unit_input.setPlaceholderText("кг / шт / упак")
        self.sku_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(120)

        self.categories_list = QListWidget()
        self.categories_list.setMinimumHeight(170)
        self.categories_list.itemChanged.connect(self._on_category_item_changed)
        for option in self._category_options:
            item = QListWidgetItem(str(option.get("name", "")))
            item.setData(Qt.ItemDataRole.UserRole, option.get("id"))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.categories_list.addItem(item)

        self.image_urls_input = QTextEdit()
        self.image_urls_input.setMinimumHeight(120)
        self.image_urls_input.setPlaceholderText(
            "По одному URL в строке.\nПервый URL будет основным изображением."
        )

        form.addRow("Название", self.name_input)
        form.addRow("Цена", self.price_input)
        form.addRow("Единица измерения", self.price_unit_input)
        form.addRow("SKU", self.sku_input)
        form.addRow("Описание", self.description_input)
        form.addRow(QLabel("Категории (чекбоксы)"), self.categories_list)
        form.addRow(QLabel("URL изображений"), self.image_urls_input)
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
        if not self._product_data:
            return
        self.name_input.setText(str(self._product_data.get("name", "")))
        self.description_input.setPlainText(str(self._product_data.get("description", "")))
        self.price_input.setText(str(self._product_data.get("price", "")))
        self.price_unit_input.setText(str(self._product_data.get("price_unit", "")))
        self.sku_input.setText(str(self._product_data.get("sku", "")))

        selected_category_ids = {
            int(value) for value in self._product_data.get("category_ids", [])
        }
        for row in range(self.categories_list.count()):
            item = self.categories_list.item(row)
            category_id = item.data(Qt.ItemDataRole.UserRole)
            checked = int(category_id) in selected_category_ids
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._set_item_bold(item, checked)

        image_urls = [
            str(url).strip()
            for url in self._product_data.get("image_urls", [])
            if str(url).strip()
        ]
        self.image_urls_input.setPlainText("\n".join(image_urls))

    def _on_category_item_changed(self, item: QListWidgetItem) -> None:
        self._set_item_bold(item, item.checkState() == Qt.CheckState.Checked)

    def _set_item_bold(self, item: QListWidgetItem, bold: bool) -> None:
        font = QFont(item.font())
        if font.pointSize() <= 0 and font.pixelSize() <= 0:
            font.setPointSize(9)
        font.setBold(bold)
        item.setFont(font)

    def _on_save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название товара не может быть пустым.")
            return

        price = self.price_input.text().strip()
        if price:
            try:
                Decimal(price)
            except (InvalidOperation, ValueError):
                QMessageBox.warning(self, "Ошибка", "Цена должна быть числом.")
                return

        category_ids: list[int] = []
        for index in range(self.categories_list.count()):
            item = self.categories_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                category_id = item.data(Qt.ItemDataRole.UserRole)
                if category_id is not None:
                    category_ids.append(int(category_id))

        image_urls = [
            row.strip()
            for row in self.image_urls_input.toPlainText().splitlines()
            if row.strip()
        ]

        self._result_data = {
            "name": name,
            "description": self.description_input.toPlainText().strip() or None,
            "price": price or None,
            "price_unit": self.price_unit_input.text().strip() or None,
            "sku": self.sku_input.text().strip() or None,
            "category_ids": category_ids,
            "image_urls": image_urls,
        }
        self.accept()
