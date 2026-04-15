from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class BulkProductEditDialog(QDialog):
    def __init__(
        self,
        *,
        selected_count: int,
        category_options: list[dict] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected_count = selected_count
        self._category_options = category_options or []
        self.result_data: dict[str, str | int | bool | None] | None = None
        self.setWindowTitle("Массовые действия")
        self.resize(560, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        summary_label = QLabel(
            f"Выбрано товаров: {self._selected_count}. Выберите одно массовое действие."
        )
        summary_label.setWordWrap(True)
        root.addWidget(summary_label)

        mode_group_box = QGroupBox("Действие")
        mode_layout = QVBoxLayout(mode_group_box)

        self.mode_group = QButtonGroup(self)

        self.price_unit_radio = QRadioButton("Изменить единицу измерения цены")
        self.price_unit_radio.setChecked(True)
        self.mode_group.addButton(self.price_unit_radio)
        mode_layout.addWidget(self.price_unit_radio)

        self.price_radio = QRadioButton("Изменить цену")
        self.mode_group.addButton(self.price_radio)
        mode_layout.addWidget(self.price_radio)

        self.category_radio = QRadioButton("Заменить категорию")
        self.mode_group.addButton(self.category_radio)
        mode_layout.addWidget(self.category_radio)

        self.published_state_radio = QRadioButton("Изменить статус публикации")
        self.mode_group.addButton(self.published_state_radio)
        mode_layout.addWidget(self.published_state_radio)

        self.visibility_radio = QRadioButton("Изменить видимость в каталоге")
        self.mode_group.addButton(self.visibility_radio)
        mode_layout.addWidget(self.visibility_radio)

        self.featured_radio = QRadioButton("Изменить признак рекомендуемого товара")
        self.mode_group.addButton(self.featured_radio)
        mode_layout.addWidget(self.featured_radio)

        self.stock_status_radio = QRadioButton("Изменить наличие")
        self.mode_group.addButton(self.stock_status_radio)
        mode_layout.addWidget(self.stock_status_radio)

        self.archive_radio = QRadioButton("Архивировать выбранные товары")
        self.mode_group.addButton(self.archive_radio)
        mode_layout.addWidget(self.archive_radio)
        root.addWidget(mode_group_box)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._build_price_unit_page())
        self.mode_stack.addWidget(self._build_price_page())
        self.mode_stack.addWidget(self._build_category_page())
        self.mode_stack.addWidget(self._build_published_state_page())
        self.mode_stack.addWidget(self._build_visibility_page())
        self.mode_stack.addWidget(self._build_featured_page())
        self.mode_stack.addWidget(self._build_stock_status_page())
        self.mode_stack.addWidget(self._build_archive_page())
        root.addWidget(self.mode_stack)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_dialog)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.price_unit_radio.toggled.connect(self._sync_mode_state)
        self.price_radio.toggled.connect(self._sync_mode_state)
        self.category_radio.toggled.connect(self._sync_mode_state)
        self.published_state_radio.toggled.connect(self._sync_mode_state)
        self.visibility_radio.toggled.connect(self._sync_mode_state)
        self.featured_radio.toggled.connect(self._sync_mode_state)
        self.stock_status_radio.toggled.connect(self._sync_mode_state)
        self.archive_radio.toggled.connect(self._sync_mode_state)
        self._sync_mode_state()

    def _build_price_unit_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        field_row = QHBoxLayout()
        field_row.addWidget(QLabel("Новая ед. изм.:"))
        self.price_unit_input = QLineEdit()
        self.price_unit_input.setPlaceholderText("Например: кг, шт, уп.")
        field_row.addWidget(self.price_unit_input, stretch=1)
        layout.addLayout(field_row)

        hint_label = QLabel(
            "Оставьте поле пустым, если нужно очистить значение у выбранных товаров."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addWidget(hint_label)
        return page

    def _build_price_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Например: 1290 или 1290.50")
        layout.addRow("Новая цена:", self.price_input)

        hint_label = QLabel(
            "Значение будет записано как обычная цена товара и заменит текущую sale price."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_category_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.category_combo = QComboBox()
        for option in self._category_options:
            category_id = option.get("id")
            category_name = str(option.get("name") or "").strip()
            if category_id is None or not category_name:
                continue
            self.category_combo.addItem(category_name, int(category_id))
        layout.addRow("Новая категория:", self.category_combo)

        hint_label = QLabel(
            "Категории у выбранных товаров будут заменены на одну выбранную категорию."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_published_state_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.published_state_combo = QComboBox()
        self.published_state_combo.addItem("Черновик", "draft")
        self.published_state_combo.addItem("Опубликован", "publish")
        self.published_state_combo.addItem("На проверке", "pending")
        self.published_state_combo.addItem("Приватный", "private")
        layout.addRow("Новый статус:", self.published_state_combo)

        hint_label = QLabel(
            "Статус сохранится локально и будет использован при следующей публикации в WooCommerce."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_visibility_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.visibility_combo = QComboBox()
        self.visibility_combo.addItem("Виден везде", "visible")
        self.visibility_combo.addItem("Только каталог", "catalog")
        self.visibility_combo.addItem("Только поиск", "search")
        self.visibility_combo.addItem("Скрыт", "hidden")
        layout.addRow("Новая видимость:", self.visibility_combo)

        hint_label = QLabel(
            "Это поле управляет будущей видимостью товара в каталоге WooCommerce."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_featured_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.featured_combo = QComboBox()
        self.featured_combo.addItem("Сделать рекомендуемыми", True)
        self.featured_combo.addItem("Снять признак рекомендуемого", False)
        layout.addRow("Новое состояние:", self.featured_combo)

        hint_label = QLabel(
            "Признак рекомендуемого товара будет применён ко всем выбранным позициям."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_stock_status_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stock_status_combo = QComboBox()
        self.stock_status_combo.addItem("В наличии", "instock")
        self.stock_status_combo.addItem("Нет в наличии", "outofstock")
        self.stock_status_combo.addItem("Под заказ", "onbackorder")
        layout.addRow("Новое наличие:", self.stock_status_combo)

        hint_label = QLabel(
            "Значение сохранится локально и будет использовано при следующей публикации товара в WooCommerce."
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #5e6c83;")
        layout.addRow("", hint_label)
        return page

    def _build_archive_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        archive_note_label = QLabel(
            "Товары будут переведены в локальный архив и исчезнут из активной таблицы."
        )
        archive_note_label.setWordWrap(True)
        archive_note_label.setStyleSheet("color: #5e6c83;")
        layout.addWidget(archive_note_label)
        return page

    def _sync_mode_state(self) -> None:
        if self.price_unit_radio.isChecked():
            self.mode_stack.setCurrentIndex(0)
            return
        if self.price_radio.isChecked():
            self.mode_stack.setCurrentIndex(1)
            return
        if self.category_radio.isChecked():
            self.mode_stack.setCurrentIndex(2)
            return
        if self.published_state_radio.isChecked():
            self.mode_stack.setCurrentIndex(3)
            return
        if self.visibility_radio.isChecked():
            self.mode_stack.setCurrentIndex(4)
            return
        if self.featured_radio.isChecked():
            self.mode_stack.setCurrentIndex(5)
            return
        if self.stock_status_radio.isChecked():
            self.mode_stack.setCurrentIndex(6)
            return
        self.mode_stack.setCurrentIndex(7)

    def _accept_dialog(self) -> None:
        if self.price_unit_radio.isChecked():
            self.result_data = {
                "action": "set_price_unit",
                "price_unit": self.price_unit_input.text().strip() or None,
            }
            self.accept()
            return

        if self.price_radio.isChecked():
            price_value = self.price_input.text().strip()
            if not price_value:
                QMessageBox.warning(
                    self,
                    "Некорректная цена",
                    "Укажите цену для массового изменения.",
                )
                return
            self.result_data = {
                "action": "set_price",
                "price": price_value,
            }
            self.accept()
            return

        if self.category_radio.isChecked():
            category_id = self.category_combo.currentData()
            if category_id is None:
                QMessageBox.warning(
                    self,
                    "Нет категории",
                    "Нет доступной категории для массового изменения.",
                )
                return
            self.result_data = {
                "action": "replace_category",
                "category_id": int(category_id),
            }
            self.accept()
            return

        if self.published_state_radio.isChecked():
            published_state = self.published_state_combo.currentData()
            if published_state is None:
                QMessageBox.warning(
                    self,
                    "Нет статуса",
                    "Нет доступного статуса публикации для массового изменения.",
                )
                return
            self.result_data = {
                "action": "set_published_state",
                "published_state": str(published_state),
            }
            self.accept()
            return

        if self.visibility_radio.isChecked():
            visibility = self.visibility_combo.currentData()
            if visibility is None:
                QMessageBox.warning(
                    self,
                    "Нет видимости",
                    "Нет доступного значения видимости для массового изменения.",
                )
                return
            self.result_data = {
                "action": "set_visibility",
                "visibility": str(visibility),
            }
            self.accept()
            return

        if self.featured_radio.isChecked():
            featured_value = self.featured_combo.currentData()
            if featured_value is None:
                QMessageBox.warning(
                    self,
                    "Нет значения",
                    "Нет доступного значения признака рекомендуемого товара.",
                )
                return
            self.result_data = {
                "action": "set_featured",
                "is_featured": bool(featured_value),
            }
            self.accept()
            return

        if self.stock_status_radio.isChecked():
            stock_status = self.stock_status_combo.currentData()
            if stock_status is None:
                QMessageBox.warning(
                    self,
                    "Нет наличия",
                    "Нет доступного значения наличия для массового изменения.",
                )
                return
            self.result_data = {
                "action": "set_stock_status",
                "stock_status": str(stock_status),
            }
            self.accept()
            return

        if self.archive_radio.isChecked():
            confirmation = QMessageBox.question(
                self,
                "Подтверждение архивации",
                f"Архивировать выбранные товары ({self._selected_count})?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self.result_data = {
                "action": "archive_products",
            }
            self.accept()
