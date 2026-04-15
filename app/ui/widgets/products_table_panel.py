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
    product_selection_changed = Signal(object)
    product_double_clicked = Signal(int)
    select_filtered_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1
        self._checked_product_ids: set[int] = set()
        self._is_syncing_checks = False
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        group = QGroupBox("Товары")
        group_layout = QVBoxLayout(group)

        group_layout.addLayout(self._build_bulk_selection_bar())

        self.stack = QStackedWidget()
        self.empty_state = QLabel(
            "Нет товаров для отображения.\nИзмените фильтр или загрузите каталог."
        )
        self.empty_state.setStyleSheet("color: #5e6c83; font-size: 14px;")
        self.empty_state.setAlignment(Qt.AlignCenter)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setShowGrid(False)
        self.table_view.setStyleSheet(
            """
            QTableView {
                selection-background-color: #d8e7ff;
                selection-color: #1f2937;
            }
            QTableView::item:hover {
                background-color: #eaf4ff;
                color: #1f2937;
            }
            QTableView::item:selected {
                background-color: #d8e7ff;
                color: #1f2937;
            }
            QTableView::item:selected:hover {
                background-color: #cfe3ff;
                color: #1f2937;
            }
            """
        )
        self.table_view.doubleClicked.connect(self._emit_double_click)

        self.model = QStandardItemModel(0, 11)
        self.model.setHorizontalHeaderLabels(
            [
                "",
                "Название",
                "Цена",
                "Ед. изм.",
                "SKU",
                "Статус",
                "Видимость",
                "Рекомендуемый",
                "Наличие",
                "Категории",
                "Sync",
            ]
        )
        self.model.itemChanged.connect(self._on_item_changed)
        self.table_view.setModel(self.model)
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

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
        self._update_checked_count_label()

    def _build_bulk_selection_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.select_page_button = QPushButton("Выделить все")
        self.select_page_button.clicked.connect(self._select_current_page)
        self.select_page_button.setEnabled(False)
        layout.addWidget(self.select_page_button)

        self.select_filtered_button = QPushButton("Отметить по фильтру")
        self.select_filtered_button.clicked.connect(self.select_filtered_requested.emit)
        self.select_filtered_button.setEnabled(False)
        layout.addWidget(self.select_filtered_button)

        self.clear_checked_button = QPushButton("Снять выделение")
        self.clear_checked_button.clicked.connect(self.clear_checked_products)
        layout.addWidget(self.clear_checked_button)

        self.checked_count_label = QLabel("Выбрано для массовых действий: 0")
        self.checked_count_label.setStyleSheet("color: #5e6c83;")
        layout.addWidget(self.checked_count_label)
        layout.addStretch()
        return layout

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

    def selected_product_id(self) -> int | None:
        current_index = self.table_view.currentIndex()
        if not current_index.isValid():
            return None
        model_item = self.model.item(current_index.row(), 0)
        if model_item is None:
            return None
        product_id = model_item.data(Qt.ItemDataRole.UserRole)
        return int(product_id) if product_id is not None else None

    def checked_product_ids(self) -> list[int]:
        return sorted(self._checked_product_ids)

    def clear_checked_products(self) -> None:
        self._checked_product_ids.clear()
        self._sync_checks_from_state()
        self._update_checked_count_label()

    def add_checked_products(self, product_ids: list[int]) -> None:
        for product_id in product_ids:
            normalized_product_id = int(product_id)
            if normalized_product_id <= 0:
                continue
            self._checked_product_ids.add(normalized_product_id)
        self._sync_checks_from_state()
        self._update_checked_count_label()

    def populate_page(
        self,
        *,
        rows: list[dict],
        page: int,
        page_size: int,
        total_items: int,
        total_pages: int,
    ) -> None:
        self.table_view.setSortingEnabled(False)
        self._is_syncing_checks = True
        self.model.removeRows(0, self.model.rowCount())
        self._current_page = max(1, page)
        self._total_pages = max(1, total_pages)

        if not rows and total_items == 0:
            self.stack.setCurrentIndex(0)
            self.page_info_label.setText("Страница 1 из 1 · Всего: 0")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.select_page_button.setEnabled(False)
            self.select_filtered_button.setEnabled(False)
            self.product_selection_changed.emit(None)
            self.table_view.setSortingEnabled(True)
            self._is_syncing_checks = False
            self._update_checked_count_label()
            return

        for row in rows:
            product_id = int(row.get("id") or 0)
            items = [
                self._check_item(product_id),
                self._item(str(row.get("name", "")), user_data=product_id),
                self._item(self._price_label(row.get("price"))),
                self._item(str(row.get("price_unit", ""))),
                self._item(str(row.get("sku", ""))),
                self._item(self._status_label(str(row.get("status", "")))),
                self._item(self._visibility_label(str(row.get("visibility", "")))),
                self._item(self._featured_label(bool(row.get("is_featured")))),
                self._item(self._stock_status_label(str(row.get("stock_status", "")))),
                self._item(str(row.get("categories", ""))),
                self._item(self._sync_status_label(str(row.get("sync_status", "")))),
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
        self.select_page_button.setEnabled(True)
        self.select_filtered_button.setEnabled(total_items > 0)
        self.stack.setCurrentIndex(1)
        self.table_view.resizeColumnsToContents()
        self.table_view.setSortingEnabled(True)
        self.table_view.clearSelection()
        self.product_selection_changed.emit(None)
        self._is_syncing_checks = False
        self._update_checked_count_label()

    def _check_item(self, product_id: int) -> QStandardItem:
        item = QStandardItem("")
        item.setCheckable(True)
        item.setEditable(False)
        item.setData(product_id, Qt.ItemDataRole.UserRole)
        item.setCheckState(
            Qt.CheckState.Checked
            if product_id in self._checked_product_ids
            else Qt.CheckState.Unchecked
        )
        return item

    def _item(self, text: str, user_data: object | None = None) -> QStandardItem:
        item = QStandardItem(text)
        item.setEditable(False)
        if user_data is not None:
            item.setData(user_data, Qt.ItemDataRole.UserRole)
        return item

    def _sync_checks_from_state(self) -> None:
        self._is_syncing_checks = True
        for row_index in range(self.model.rowCount()):
            check_item = self.model.item(row_index, 0)
            if check_item is None:
                continue
            product_id = check_item.data(Qt.ItemDataRole.UserRole)
            if product_id is None:
                continue
            check_item.setCheckState(
                Qt.CheckState.Checked
                if int(product_id) in self._checked_product_ids
                else Qt.CheckState.Unchecked
            )
        self._is_syncing_checks = False

    def _current_page_product_ids(self) -> list[int]:
        product_ids: list[int] = []
        for row_index in range(self.model.rowCount()):
            check_item = self.model.item(row_index, 0)
            if check_item is None:
                continue
            product_id = check_item.data(Qt.ItemDataRole.UserRole)
            if product_id is not None:
                product_ids.append(int(product_id))
        return product_ids

    def _select_current_page(self) -> None:
        for product_id in self._current_page_product_ids():
            self._checked_product_ids.add(product_id)
        self._sync_checks_from_state()
        self._update_checked_count_label()

    def _update_checked_count_label(self) -> None:
        checked_total = len(self._checked_product_ids)
        self.checked_count_label.setText(
            f"Выбрано для массовых действий: {checked_total}"
        )
        self.clear_checked_button.setEnabled(checked_total > 0)

    def _on_page_size_changed(self, value: str) -> None:
        self.page_size_changed.emit(int(value))

    def _go_prev(self) -> None:
        if self._current_page > 1:
            self.page_changed.emit(self._current_page - 1)

    def _go_next(self) -> None:
        if self._current_page < self._total_pages:
            self.page_changed.emit(self._current_page + 1)

    def _on_selection_changed(self, *_args: object) -> None:
        self.product_selection_changed.emit(self.selected_product_id())

    def _on_item_changed(self, item: QStandardItem) -> None:
        if self._is_syncing_checks or item.column() != 0:
            return
        product_id = item.data(Qt.ItemDataRole.UserRole)
        if product_id is None:
            return
        normalized_product_id = int(product_id)
        if item.checkState() == Qt.CheckState.Checked:
            self._checked_product_ids.add(normalized_product_id)
        else:
            self._checked_product_ids.discard(normalized_product_id)
        self._update_checked_count_label()

    def _emit_double_click(self, _index: object) -> None:
        product_id = self.selected_product_id()
        if product_id is not None:
            self.product_double_clicked.emit(product_id)

    def _price_label(self, value: object) -> str:
        if value is None:
            return ""
        return str(value)

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

    def _status_label(self, status: str) -> str:
        labels = {
            "draft": "черновик",
            "published": "опубликован",
            "publish": "опубликован",
            "pending": "на проверке",
            "private": "приватный",
        }
        return labels.get(status, status)

    def _visibility_label(self, visibility: str) -> str:
        labels = {
            "visible": "везде",
            "catalog": "каталог",
            "search": "поиск",
            "hidden": "скрыт",
        }
        return labels.get(visibility, visibility)

    def _featured_label(self, is_featured: bool) -> str:
        return "да" if is_featured else "нет"

    def _stock_status_label(self, stock_status: str) -> str:
        labels = {
            "instock": "в наличии",
            "outofstock": "нет",
            "onbackorder": "под заказ",
        }
        return labels.get(stock_status, stock_status)
