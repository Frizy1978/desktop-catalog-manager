from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
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

from app.services.product_image_service import ProductImageService
from app.ui.icons import themed_icon


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ProductEditorDialog(QDialog):
    def __init__(
        self,
        *,
        category_options: list[dict],
        product_data: dict | None = None,
        product_id: int | None = None,
        product_image_service: ProductImageService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._category_options = category_options
        self._product_data = product_data or {}
        self._product_id = product_id
        self._product_image_service = product_image_service
        self._result_data: dict[str, Any] | None = None

        self._pending_local_images: list[dict[str, Any]] = []
        self._image_rows: list[dict[str, Any]] = []

        self.setWindowTitle("Добавить товар" if product_id is None else "Изменить товар")
        self.setMinimumWidth(920)
        self.setMinimumHeight(740)
        self._build_ui()
        self._fill_data()
        self._reload_images()

    @property
    def result_data(self) -> dict[str, Any] | None:
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

        self.images_list = QListWidget()
        self.images_list.setMinimumHeight(230)
        self.images_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.images_list.setSpacing(4)
        self.images_list.itemDoubleClicked.connect(self._on_image_item_double_clicked)

        images_controls = QHBoxLayout()
        self.add_image_button = QPushButton("Добавить файл")
        self.add_image_button.setIcon(themed_icon("import_photos", color="#ffffff"))
        self.add_image_button.clicked.connect(self._on_add_local_images)
        images_controls.addWidget(self.add_image_button)

        self.remove_image_button = QPushButton("Удалить")
        self.remove_image_button.setIcon(themed_icon("delete_product", color="#ffffff"))
        self.remove_image_button.clicked.connect(self._on_remove_image)
        images_controls.addWidget(self.remove_image_button)
        images_controls.addStretch()

        image_panel = QVBoxLayout()
        image_panel.addWidget(self.images_list)
        image_panel.addLayout(images_controls)
        image_panel_widget = QWidget()
        image_panel_widget.setLayout(image_panel)

        form.addRow("Название", self.name_input)
        form.addRow("Цена", self.price_input)
        form.addRow("Единица измерения", self.price_unit_input)
        form.addRow("SKU", self.sku_input)
        form.addRow("Описание", self.description_input)
        form.addRow(QLabel("Категории (чекбоксы)"), self.categories_list)
        form.addRow(QLabel("Изображения товара"), image_panel_widget)
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
        if not self._product_data:
            return
        self.name_input.setText(str(self._product_data.get("name", "")))
        self.description_input.setPlainText(str(self._product_data.get("description", "")))
        self.price_input.setText(str(self._product_data.get("price", "")))
        self.price_unit_input.setText(str(self._product_data.get("price_unit", "")))
        self.sku_input.setText(str(self._product_data.get("sku", "")))

        selected_category_ids = {int(value) for value in self._product_data.get("category_ids", [])}
        for row in range(self.categories_list.count()):
            item = self.categories_list.item(row)
            category_id = item.data(Qt.ItemDataRole.UserRole)
            checked = int(category_id) in selected_category_ids
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._set_item_bold(item, checked)

    def _on_category_item_changed(self, item: QListWidgetItem) -> None:
        self._set_item_bold(item, item.checkState() == Qt.CheckState.Checked)

    def _set_item_bold(self, item: QListWidgetItem, bold: bool) -> None:
        font = QFont(item.font())
        if font.pointSize() <= 0 and font.pixelSize() <= 0:
            font.setPointSize(9)
        font.setBold(bold)
        item.setFont(font)

    def _reload_images(self) -> None:
        selected_key = None
        current = self.images_list.currentItem()
        if current is not None:
            selected_key = str(current.data(Qt.ItemDataRole.UserRole) or "")

        if self._product_id is not None and self._product_image_service is not None:
            self._image_rows = self._product_image_service.list_product_images(self._product_id)
        else:
            self._image_rows = [
                {
                    "id": None,
                    "source_type": "local_file",
                    "original_path": row["path"],
                    "local_path": row["path"],
                    "metadata": {"original_filename": Path(row["path"]).name},
                    "is_primary": bool(row.get("is_primary")),
                }
                for row in self._pending_local_images
            ]

        self.images_list.clear()
        for row in self._image_rows:
            row_key = self._row_key(row)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row_key)
            item.setSizeHint(QSize(0, 98))
            self.images_list.addItem(item)
            self.images_list.setItemWidget(item, self._build_image_item_widget(row))

        if selected_key:
            for index in range(self.images_list.count()):
                item = self.images_list.item(index)
                if str(item.data(Qt.ItemDataRole.UserRole) or "") == selected_key:
                    self.images_list.setCurrentItem(item)
                    break

    def _build_image_item_widget(self, row: dict[str, Any]) -> QWidget:
        row_key = self._row_key(row)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        thumb = ClickableImageLabel()
        thumb.setFixedSize(84, 84)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("border: 1px solid #d5dde8; border-radius: 6px; background: #f7f9fc;")
        pixmap = self._thumbnail_pixmap(row)
        if pixmap is None:
            thumb.setText("Нет\nпревью")
            thumb.setStyleSheet(
                "border: 1px solid #d5dde8; border-radius: 6px; background: #f7f9fc; color:#6b7280;"
            )
        else:
            thumb.setPixmap(pixmap)
        thumb.clicked.connect(lambda key=row_key: self._on_thumbnail_clicked(key))
        layout.addWidget(thumb)

        info_layout = QVBoxLayout()
        name_label = QLabel(self._display_name(row))
        name_font = QFont(name_label.font())
        if name_font.pointSize() <= 0 and name_font.pixelSize() <= 0:
            name_font.setPointSize(9)
        name_font.setBold(bool(row.get("is_primary")))
        name_label.setFont(name_font)
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        source_type = str(row.get("source_type") or "wc_url")
        source_label = QLabel("Локальный файл" if source_type == "local_file" else "Источник: URL")
        source_label.setStyleSheet("color:#5e6c83;")
        info_layout.addWidget(source_label)

        primary_checkbox = QCheckBox("Сделать основным")
        primary_checkbox.setChecked(bool(row.get("is_primary")))
        primary_checkbox.toggled.connect(lambda checked, key=row_key: self._on_primary_toggled(key, checked))
        info_layout.addWidget(primary_checkbox)
        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)
        return widget

    def _thumbnail_pixmap(self, row: dict[str, Any]) -> QPixmap | None:
        preview_path = self._preview_path(row)
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

    def _preview_path(self, row: dict[str, Any]) -> Path | None:
        if self._product_image_service is not None:
            return self._product_image_service.get_preview_path(row)

        raw_path = str(row.get("local_path") or row.get("original_path") or "").strip()
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def _display_name(self, row: dict[str, Any]) -> str:
        metadata = row.get("metadata")
        if isinstance(metadata, dict):
            original_filename = str(metadata.get("original_filename") or "").strip()
            if original_filename:
                return original_filename

        original_path = str(row.get("original_path") or "").strip()
        if original_path:
            original_name = Path(original_path).name
            if original_name:
                return original_name

        local_path = str(row.get("local_path") or "").strip()
        if local_path:
            local_name = Path(local_path).name
            if local_name:
                return local_name

        return "Без имени"

    def _row_key(self, row: dict[str, Any]) -> str:
        image_id = row.get("id")
        if image_id is not None:
            return f"id:{int(image_id)}"
        raw_path = str(row.get("original_path") or "").strip()
        return f"path:{raw_path}"

    def _find_row_by_key(self, row_key: str) -> dict[str, Any] | None:
        for row in self._image_rows:
            if self._row_key(row) == row_key:
                return row
        return None

    def _on_image_item_double_clicked(self, item: QListWidgetItem) -> None:
        row_key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        row = self._find_row_by_key(row_key)
        if row is not None:
            self._open_preview(row)

    def _on_thumbnail_clicked(self, row_key: str) -> None:
        for index in range(self.images_list.count()):
            item = self.images_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole) or "") == row_key:
                self.images_list.setCurrentItem(item)
                break
        row = self._find_row_by_key(row_key)
        if row is not None:
            self._open_preview(row)

    def _on_primary_toggled(self, row_key: str, checked: bool) -> None:
        if not checked:
            return
        row = self._find_row_by_key(row_key)
        if row is None:
            return

        if self._product_id is not None and self._product_image_service is not None:
            image_id = row.get("id")
            if image_id is None:
                return
            updated = self._product_image_service.set_primary_image(self._product_id, int(image_id))
            if not updated:
                QMessageBox.warning(self, "Ошибка", "Не удалось изменить основное изображение.")
            self._reload_images()
            return

        selected_path = str(row.get("original_path") or "").strip()
        for pending in self._pending_local_images:
            pending["is_primary"] = str(pending.get("path") or "").strip() == selected_path
        self._reload_images()

    def _on_add_local_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения товара",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;Все файлы (*.*)",
        )
        if not files:
            return

        if self._product_id is not None and self._product_image_service is not None:
            errors: list[str] = []
            for file_path in files:
                try:
                    self._product_image_service.add_local_image(self._product_id, file_path)
                except ValueError as exc:
                    errors.append(f"{Path(file_path).name}: {exc}")
            self._reload_images()
            if errors:
                QMessageBox.warning(self, "Часть файлов не добавлена", "\n".join(errors))
            return

        existing_paths = {str(row.get("path", "")).strip() for row in self._pending_local_images}
        for file_path in files:
            normalized = str(file_path).strip()
            if not normalized or normalized in existing_paths:
                continue
            self._pending_local_images.append({"path": normalized, "is_primary": False})
            existing_paths.add(normalized)

        if self._pending_local_images and not any(bool(row.get("is_primary")) for row in self._pending_local_images):
            self._pending_local_images[0]["is_primary"] = True
        self._reload_images()

    def _on_remove_image(self) -> None:
        current_item = self.images_list.currentItem()
        if current_item is None:
            QMessageBox.information(self, "Изображение не выбрано", "Выберите изображение в списке.")
            return
        row_key = str(current_item.data(Qt.ItemDataRole.UserRole) or "")
        row = self._find_row_by_key(row_key)
        if row is None:
            return

        if self._product_id is not None and self._product_image_service is not None:
            image_id = row.get("id")
            if image_id is None:
                return
            deleted = self._product_image_service.remove_image(self._product_id, int(image_id))
            if not deleted:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить изображение.")
            self._reload_images()
            return

        selected_path = str(row.get("original_path") or "").strip()
        self._pending_local_images = [
            pending
            for pending in self._pending_local_images
            if str(pending.get("path") or "").strip() != selected_path
        ]
        if self._pending_local_images and not any(bool(row.get("is_primary")) for row in self._pending_local_images):
            self._pending_local_images[0]["is_primary"] = True
        self._reload_images()

    def _open_preview(self, row: dict[str, Any]) -> None:
        preview_path = self._preview_path(row)
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
        preview_dialog.setWindowTitle(f"Предпросмотр: {preview_path.name}")
        preview_dialog.resize(960, 720)
        preview_layout = QVBoxLayout(preview_dialog)

        name_label = QLabel(self._display_name(row))
        name_font = QFont(name_label.font())
        if name_font.pointSize() <= 0 and name_font.pixelSize() <= 0:
            name_font.setPointSize(10)
        name_font.setBold(True)
        name_label.setFont(name_font)
        preview_layout.addWidget(name_label)

        preview_label = QLabel()
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setPixmap(
            pixmap.scaled(
                920,
                640,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        preview_layout.addWidget(preview_label)
        preview_dialog.exec()

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

        self._result_data = {
            "name": name,
            "description": self.description_input.toPlainText().strip() or None,
            "price": price or None,
            "price_unit": self.price_unit_input.text().strip() or None,
            "sku": self.sku_input.text().strip() or None,
            "category_ids": category_ids,
            "pending_local_images": deepcopy(self._pending_local_images),
        }
        self.accept()
