from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.catalog_service import CatalogService
from app.services.publish_service import PublishSelection
from app.ui.icons import themed_icon


class PublishChangesDialog(QDialog):
    def __init__(
        self,
        *,
        catalog_service: CatalogService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog_service = catalog_service
        self.publish_selection: PublishSelection | None = None
        self._categories: list[dict[str, Any]] = []
        self._products: list[dict[str, Any]] = []

        self.setWindowTitle("Изменения перед публикацией")
        self.resize(1180, 720)
        self._build_ui()
        self._reload_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        header_layout = QHBoxLayout()
        self.summary_label = QLabel("Загрузка изменений...")
        header_layout.addWidget(self.summary_label)
        header_layout.addStretch()

        self.selection_summary_label = QLabel("")
        self.selection_summary_label.setStyleSheet("color: #5e6c83;")
        header_layout.addWidget(self.selection_summary_label)

        refresh_button = QPushButton("Обновить")
        refresh_button.setIcon(themed_icon("refresh", color="#ffffff"))
        refresh_button.clicked.connect(self._reload_preview)
        header_layout.addWidget(refresh_button)
        root.addLayout(header_layout)

        root.addWidget(self._build_target_panel())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(
            self._build_table_panel(
                title="Категории к публикации",
                table_attr_name="categories_table",
                select_all_attr_name="select_all_categories_checkbox",
                select_all_text="Выбрать все категории",
                headers=["Публикация", "ID", "Название", "Slug", "Статус", "WC ID"],
            )
        )
        splitter.addWidget(
            self._build_table_panel(
                title="Товары к публикации",
                table_attr_name="products_table",
                select_all_attr_name="select_all_products_checkbox",
                select_all_text="Выбрать все товары",
                headers=[
                    "Публикация",
                    "ID",
                    "Название",
                    "SKU",
                    "Категории",
                    "Статус",
                    "WC ID",
                ],
            )
        )
        splitter.setSizes([270, 360])
        root.addWidget(splitter, stretch=1)

        controls = QHBoxLayout()
        controls.addStretch()

        self.publish_selected_button = QPushButton("Опубликовать отмеченное")
        self.publish_selected_button.setIcon(themed_icon("publish_wc", color="#ffffff"))
        self.publish_selected_button.clicked.connect(self._publish_selected)
        controls.addWidget(self.publish_selected_button)

        self.publish_all_button = QPushButton("Опубликовать всё")
        self.publish_all_button.setIcon(themed_icon("publish_wc", color="#ffffff"))
        self.publish_all_button.clicked.connect(self._publish_all)
        controls.addWidget(self.publish_all_button)

        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.reject)
        controls.addWidget(close_button)
        root.addLayout(controls)

    def _build_target_panel(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        title_label = QLabel("Канал публикации")
        title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(title_label, 0, 0)

        radios_layout = QHBoxLayout()
        self.publish_target_group = QButtonGroup(self)

        self.target_wc_radio = QRadioButton("WooCommerce")
        self.target_wc_radio.setChecked(True)
        self.publish_target_group.addButton(self.target_wc_radio)
        radios_layout.addWidget(self.target_wc_radio)

        self.target_yandex_radio = QRadioButton("Яндекс (позже)")
        self.target_yandex_radio.setEnabled(False)
        self.target_yandex_radio.setToolTip(
            "Канал будет добавлен в будущей фазе. Сейчас активна публикация только в WooCommerce."
        )
        self.publish_target_group.addButton(self.target_yandex_radio)
        radios_layout.addWidget(self.target_yandex_radio)
        radios_layout.addStretch()

        layout.addLayout(radios_layout, 0, 1)

        note_label = QLabel(
            "Экран подготовлен под будущие каналы публикации, "
            "но в текущей фазе доступен только WooCommerce."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #5e6c83;")
        layout.addWidget(note_label, 1, 0, 1, 2)
        return panel

    def _build_table_panel(
        self,
        *,
        title: str,
        table_attr_name: str,
        select_all_attr_name: str,
        select_all_text: str,
        headers: list[str],
    ) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600;")
        toolbar.addWidget(title_label)
        toolbar.addStretch()

        select_all_checkbox = QCheckBox(select_all_text)
        toolbar.addWidget(select_all_checkbox)
        setattr(self, select_all_attr_name, select_all_checkbox)
        layout.addLayout(toolbar)

        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        select_all_checkbox.toggled.connect(
            lambda checked, current_table=table: self._set_all_checked(current_table, checked)
        )
        setattr(self, table_attr_name, table)
        layout.addWidget(table)
        return panel

    def _reload_preview(self) -> None:
        preview = self._catalog_service.get_publish_preview()
        self._categories = list(preview.get("categories") or [])
        self._products = list(preview.get("products") or [])

        self._populate_categories()
        self._populate_products()

        categories_total = int(preview.get("categories_total") or 0)
        products_total = int(preview.get("products_total") or 0)
        total_items = int(preview.get("total_items") or 0)
        if total_items == 0:
            self.summary_label.setText("Нет локальных изменений, ожидающих публикации.")
        else:
            self.summary_label.setText(
                f"К публикации: {total_items} объектов "
                f"(категории: {categories_total}, товары: {products_total})"
            )

        has_items = total_items > 0
        self.publish_all_button.setEnabled(has_items)
        self.publish_selected_button.setEnabled(has_items)
        self._update_selection_summary()

    def _populate_categories(self) -> None:
        self.categories_table.blockSignals(True)
        self.categories_table.setRowCount(0)
        for row in self._categories:
            row_index = self.categories_table.rowCount()
            self.categories_table.insertRow(row_index)
            self._set_checkbox_widget(self.categories_table, row_index, 0, row["id"])
            self._set_text_cell(self.categories_table, row_index, 1, str(row["id"]), row["id"])
            self._set_text_cell(self.categories_table, row_index, 2, str(row.get("name") or ""))
            self._set_text_cell(self.categories_table, row_index, 3, str(row.get("slug") or ""))
            self._set_text_cell(
                self.categories_table,
                row_index,
                4,
                self._sync_status_label(str(row.get("sync_status") or "")),
            )
            self._set_text_cell(
                self.categories_table,
                row_index,
                5,
                str(row.get("external_wc_id") or ""),
            )
        self.categories_table.blockSignals(False)
        self.categories_table.resizeColumnsToContents()
        self._sync_select_all_checkbox(
            self.categories_table,
            self.select_all_categories_checkbox,
        )

    def _populate_products(self) -> None:
        self.products_table.blockSignals(True)
        self.products_table.setRowCount(0)
        for row in self._products:
            row_index = self.products_table.rowCount()
            self.products_table.insertRow(row_index)
            self._set_checkbox_widget(self.products_table, row_index, 0, row["id"])
            self._set_text_cell(self.products_table, row_index, 1, str(row["id"]), row["id"])
            self._set_text_cell(self.products_table, row_index, 2, str(row.get("name") or ""))
            self._set_text_cell(self.products_table, row_index, 3, str(row.get("sku") or ""))
            self._set_text_cell(
                self.products_table,
                row_index,
                4,
                str(row.get("categories") or ""),
            )
            self._set_text_cell(
                self.products_table,
                row_index,
                5,
                self._sync_status_label(str(row.get("sync_status") or "")),
            )
            self._set_text_cell(
                self.products_table,
                row_index,
                6,
                str(row.get("external_wc_id") or ""),
            )
        self.products_table.blockSignals(False)
        self.products_table.resizeColumnsToContents()
        self._sync_select_all_checkbox(
            self.products_table,
            self.select_all_products_checkbox,
        )

    def _set_checkbox_widget(
        self,
        table: QTableWidget,
        row: int,
        column: int,
        row_id: int,
    ) -> None:
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.setProperty("row_id", int(row_id))
        checkbox.toggled.connect(
            lambda _checked, current_table=table: self._on_row_checkbox_toggled(current_table)
        )

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        table.setCellWidget(row, column, container)

    def _set_text_cell(
        self,
        table: QTableWidget,
        row: int,
        column: int,
        text: str,
        user_data: object | None = None,
    ) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        )
        if user_data is not None:
            item.setData(Qt.ItemDataRole.UserRole, user_data)
        table.setItem(row, column, item)

    def _set_all_checked(self, table: QTableWidget, checked: bool) -> None:
        for row_index in range(table.rowCount()):
            checkbox = self._row_checkbox(table, row_index)
            if checkbox is None:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        self._sync_select_all_for_table(table)
        self._update_selection_summary()

    def _publish_all(self) -> None:
        self.publish_selection = PublishSelection(target=self._selected_target())
        self.accept()

    def _publish_selected(self) -> None:
        category_ids = self._checked_ids(self.categories_table)
        product_ids = self._checked_ids(self.products_table)
        if not category_ids and not product_ids:
            QMessageBox.information(
                self,
                "Ничего не отмечено",
                "Отметьте хотя бы одну категорию или один товар для публикации.",
            )
            return
        self.publish_selection = PublishSelection(
            target=self._selected_target(),
            category_ids=category_ids,
            product_ids=product_ids,
        )
        self.accept()

    def _checked_ids(self, table: QTableWidget) -> list[int]:
        ids: list[int] = []
        for row_index in range(table.rowCount()):
            checkbox = self._row_checkbox(table, row_index)
            if checkbox is None or not checkbox.isChecked():
                continue
            row_id = checkbox.property("row_id")
            if row_id is not None:
                ids.append(int(row_id))
        return sorted(set(ids))

    def _selected_target(self) -> str:
        if self.target_wc_radio.isChecked():
            return "wc"
        return "wc"

    def _on_row_checkbox_toggled(self, table: QTableWidget) -> None:
        self._sync_select_all_for_table(table)
        self._update_selection_summary()

    def _sync_select_all_for_table(self, table: QTableWidget) -> None:
        if table is self.categories_table:
            self._sync_select_all_checkbox(
                self.categories_table,
                self.select_all_categories_checkbox,
            )
            return
        if table is self.products_table:
            self._sync_select_all_checkbox(
                self.products_table,
                self.select_all_products_checkbox,
            )

    def _sync_select_all_checkbox(
        self,
        table: QTableWidget,
        checkbox: QCheckBox,
    ) -> None:
        if table.rowCount() == 0:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
            return

        checked_count = len(self._checked_ids(table))
        checkbox.blockSignals(True)
        checkbox.setChecked(checked_count == table.rowCount())
        checkbox.blockSignals(False)

    def _row_checkbox(self, table: QTableWidget, row_index: int) -> QCheckBox | None:
        container = table.cellWidget(row_index, 0)
        if container is None:
            return None
        checkbox = container.findChild(QCheckBox)
        return checkbox

    def _update_selection_summary_legacy(self) -> None:
        checked_categories = len(self._checked_ids(self.categories_table))
        checked_products = len(self._checked_ids(self.products_table))
        self.selection_summary_label.setText(
            f"Отмечено: категории {checked_categories}, товары {checked_products}"
        )

    def _update_selection_summary(self) -> None:
        checked_categories = len(self._checked_ids(self.categories_table))
        checked_products = len(self._checked_ids(self.products_table))
        checked_total = checked_categories + checked_products
        self.selection_summary_label.setText(
            f"Отмечено: {checked_total} "
            f"(категории {checked_categories}, товары {checked_products})"
        )
        self.publish_selected_button.setEnabled(checked_total > 0)

    def _sync_status_label(self, status: str) -> str:
        labels = {
            "synced": "синхронизировано",
            "modified_local": "изменено локально",
            "new_local": "новое локально",
            "publish_pending": "ожидает публикации",
            "publish_error": "ошибка публикации",
            "archived": "в архиве",
        }
        return labels.get(status, status)
