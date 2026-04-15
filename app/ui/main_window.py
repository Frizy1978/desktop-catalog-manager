from __future__ import annotations

import logging
from typing import Callable, cast

from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QSplitterHandle,
    QVBoxLayout,
    QWidget,
)

from app.models.user import AuthenticatedUser
from app.services.auth_service import AuthService
from app.services.catalog_maintenance_service import CatalogMaintenanceService
from app.services.catalog_service import CatalogService
from app.services.env_config_service import EnvConfigService
from app.services.operation_log_service import OperationLogService
from app.services.publish_service import (
    PublishRunResult,
    PublishSelection,
    WooCommercePublishService,
)
from app.services.product_image_service import ProductImageService
from app.services.sync_import_service import ImportRunResult, WooCommerceImportService
from app.ui.dialogs.bulk_product_edit_dialog import BulkProductEditDialog
from app.ui.dialogs.category_editor_dialog import CategoryEditorDialog
from app.ui.dialogs.operation_log_dialog import OperationLogDialog
from app.ui.dialogs.publish_changes_dialog import PublishChangesDialog
from app.ui.dialogs.product_editor_dialog import ProductEditorDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.widgets.categories_panel import CategoriesPanel
from app.ui.widgets.products_table_panel import ProductsTablePanel
from app.ui.widgets.toolbar_panel import ToolbarPanel
from app.ui.workers.import_worker import ImportWorker
from app.ui.workers.publish_worker import PublishWorker

logger = logging.getLogger(__name__)


class CatalogSplitterHandle(QSplitterHandle):
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#d7deea"))

        border_pen = QPen(QColor("#b8c4d6"))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawLine(0, 0, 0, self.height())
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

        grip_pen = QPen(QColor("#7c8ea8"))
        grip_pen.setWidth(2)
        painter.setPen(grip_pen)
        center_x = self.rect().center().x()
        center_y = self.rect().center().y()
        for offset in (-10, 0, 10):
            painter.drawLine(center_x, center_y + offset - 4, center_x, center_y + offset + 4)


class CatalogSplitter(QSplitter):
    def createHandle(self) -> QSplitterHandle:
        return CatalogSplitterHandle(self.orientation(), self)


class MainWindow(QMainWindow):
    def __init__(
        self,
        current_user: AuthenticatedUser,
        catalog_service: CatalogService,
        auth_service: AuthService,
        env_config_service: EnvConfigService,
        catalog_maintenance_service: CatalogMaintenanceService,
        operation_log_service: OperationLogService,
        product_image_service: ProductImageService,
        import_service_factory: Callable[[], WooCommerceImportService | None],
        import_service: WooCommerceImportService | None = None,
        publish_service_factory: Callable[[], WooCommercePublishService | None] | None = None,
        publish_service: WooCommercePublishService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._catalog_service = catalog_service
        self._auth_service = auth_service
        self._env_config_service = env_config_service
        self._catalog_maintenance_service = catalog_maintenance_service
        self._operation_log_service = operation_log_service
        self._product_image_service = product_image_service
        self._import_service_factory = import_service_factory
        self._import_service = import_service
        self._publish_service_factory = publish_service_factory
        self._publish_service = publish_service

        self._products_page = 1
        self._products_page_size = 50
        self._selected_category_id: int | None = None
        self._selected_product_id: int | None = None
        self._search_query = ""
        self._sync_status_filter = ""
        self._published_state_filter = ""
        self._visibility_filter = ""
        self._is_featured_filter = ""
        self._stock_status_filter = ""

        self._import_thread: QThread | None = None
        self._import_worker: ImportWorker | None = None
        self._import_progress_dialog: QProgressDialog | None = None
        self._publish_thread: QThread | None = None
        self._publish_worker: PublishWorker | None = None
        self._publish_progress_dialog: QProgressDialog | None = None

        self.setWindowTitle("Fish Olha — Менеджер каталога")
        self.resize(1440, 880)
        self._build_ui()
        self._update_status_bar()
        self._reload_catalog_view()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = CatalogSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)
        self.categories_panel = CategoriesPanel()

        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.toolbar_panel = ToolbarPanel()
        self.products_table_panel = ProductsTablePanel()
        self.products_table_panel.page_changed.connect(self._on_products_page_changed)
        self.products_table_panel.page_size_changed.connect(
            self._on_products_page_size_changed
        )
        self.products_table_panel.product_selection_changed.connect(
            self._on_product_selection_changed
        )
        self.products_table_panel.product_double_clicked.connect(
            self._on_product_double_clicked
        )
        self.products_table_panel.select_filtered_requested.connect(
            self._on_select_filtered_products_requested
        )

        right_layout.addWidget(self.toolbar_panel)
        right_layout.addWidget(self.products_table_panel, stretch=1)

        splitter.addWidget(self.categories_panel)
        splitter.addWidget(right_side)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 1100])

        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self.toolbar_panel.action_triggered.connect(self._handle_toolbar_action)
        self.toolbar_panel.search_changed.connect(self._on_search_changed)
        self.toolbar_panel.filters_changed.connect(self._on_products_filters_changed)
        self.categories_panel.action_triggered.connect(self._handle_category_action)
        self.categories_panel.category_selected.connect(self._on_category_selected)

    def _update_status_bar(self) -> None:
        role_labels = {
            "admin": "администратор",
            "editor": "редактор",
            "viewer": "наблюдатель",
        }
        role_name = role_labels.get(self._current_user.role, self._current_user.role)
        self.statusBar().showMessage(
            f"Выполнен вход: {self._current_user.username} ({role_name})"
        )

    def _reload_catalog_view(self) -> None:
        category_rows = self._catalog_service.get_category_sidebar_items()
        valid_category_ids = {
            int(row["id"]) for row in category_rows if row.get("id") is not None
        }
        if self._selected_category_id not in valid_category_ids:
            self._selected_category_id = None
        self.categories_panel.populate(
            category_rows,
            selected_category_id=self._selected_category_id,
        )
        self._load_products_page()

    def _load_products_page(self) -> None:
        effective_category_id = self._effective_products_category_id()
        page_data = self._catalog_service.get_products_table_page(
            page=self._products_page,
            page_size=self._products_page_size,
            category_id=effective_category_id,
            search_query=self._search_query,
            sync_status_filter=self._sync_status_filter,
            published_state_filter=self._published_state_filter,
            visibility_filter=self._visibility_filter,
            is_featured_filter=self._is_featured_filter,
            stock_status_filter=self._stock_status_filter,
        )
        total_pages = int(page_data["total_pages"])
        if self._products_page > total_pages:
            self._products_page = total_pages
            page_data = self._catalog_service.get_products_table_page(
                page=self._products_page,
                page_size=self._products_page_size,
                category_id=effective_category_id,
                search_query=self._search_query,
                sync_status_filter=self._sync_status_filter,
                published_state_filter=self._published_state_filter,
                visibility_filter=self._visibility_filter,
                is_featured_filter=self._is_featured_filter,
                stock_status_filter=self._stock_status_filter,
            )

        self.products_table_panel.populate_page(
            rows=page_data["items"],
            page=int(page_data["page"]),
            page_size=int(page_data["page_size"]),
            total_items=int(page_data["total_items"]),
            total_pages=int(page_data["total_pages"]),
        )

    def _effective_products_category_id(self) -> int | None:
        return None if self._search_query else self._selected_category_id

    @Slot(int)
    def _on_products_page_changed(self, page: int) -> None:
        self._products_page = max(1, page)
        self._load_products_page()

    @Slot(int)
    def _on_products_page_size_changed(self, page_size: int) -> None:
        self._products_page_size = max(1, page_size)
        self._products_page = 1
        self._load_products_page()

    @Slot(object)
    def _on_category_selected(self, category_id: object) -> None:
        self._selected_category_id = int(category_id) if category_id is not None else None
        self._products_page = 1
        self._load_products_page()

    @Slot(str)
    def _on_search_changed(self, search_query: str) -> None:
        self._search_query = search_query.strip()
        self._products_page = 1
        self._load_products_page()

    @Slot(object)
    def _on_products_filters_changed(self, filters: object) -> None:
        payload = filters if isinstance(filters, dict) else {}
        self._sync_status_filter = str(payload.get("sync_status") or "").strip()
        self._published_state_filter = str(payload.get("published_state") or "").strip()
        self._visibility_filter = str(payload.get("visibility") or "").strip()
        self._is_featured_filter = str(payload.get("is_featured") or "").strip()
        self._stock_status_filter = str(payload.get("stock_status") or "").strip()
        self._products_page = 1
        self._load_products_page()

    @Slot(object)
    def _on_product_selection_changed(self, product_id: object) -> None:
        self._selected_product_id = int(product_id) if product_id is not None else None
        if self._selected_product_id is None:
            return

        product_details = self._catalog_service.get_product_details(self._selected_product_id)
        if not product_details:
            return

        category_ids = product_details.get("category_ids") or []
        if not category_ids:
            return

        first_category_id = int(category_ids[0])
        self.categories_panel.select_category(first_category_id, emit_signal=False)

    @Slot(int)
    def _on_product_double_clicked(self, product_id: int) -> None:
        self._selected_product_id = product_id
        self._open_edit_product_dialog()

    @Slot()
    def _on_select_filtered_products_requested(self) -> None:
        product_ids = self._catalog_service.get_products_table_selection_ids(
            category_id=self._effective_products_category_id(),
            search_query=self._search_query,
            sync_status_filter=self._sync_status_filter,
            published_state_filter=self._published_state_filter,
            visibility_filter=self._visibility_filter,
            is_featured_filter=self._is_featured_filter,
            stock_status_filter=self._stock_status_filter,
        )
        self.products_table_panel.add_checked_products(product_ids)

    def _handle_toolbar_action(self, action_key: str) -> None:
        if action_key == "import_wc":
            self._handle_import_from_wc()
            return
        if action_key == "publish_wc":
            self._handle_publish_to_wc()
            return
        if action_key == "show_changes":
            self._open_publish_changes_dialog()
            return
        if action_key == "add_product":
            self._open_add_product_dialog()
            return
        if action_key == "edit_product":
            self._open_edit_product_dialog()
            return
        if action_key == "delete_product":
            self._delete_selected_product()
            return
        if action_key == "bulk_actions":
            self._open_bulk_actions_dialog()
            return
        if action_key == "settings":
            self._open_settings()
            return
        if action_key == "logs":
            OperationLogDialog(
                operation_log_service=self._operation_log_service,
                parent=self,
            ).exec()
            return

    def _open_add_product_dialog(self) -> None:
        category_options = self._catalog_service.get_category_options()
        dialog = ProductEditorDialog(
            category_options=category_options,
            product_data=None,
            product_id=None,
            product_image_service=self._product_image_service,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_data:
            return

        payload = self._extract_product_payload(dialog.result_data)
        try:
            created_product_id = self._catalog_service.create_product(**payload)
            self._attach_pending_images(
                created_product_id,
                dialog.result_data.get("pending_local_images", []),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        self._products_page = 1
        self._reload_catalog_view()

    def _open_edit_product_dialog(self) -> None:
        product_id = self._selected_product_id or self.products_table_panel.selected_product_id()
        if product_id is None:
            QMessageBox.information(self, "Товар не выбран", "Выберите товар в таблице.")
            return

        product_data = self._catalog_service.get_product_details(product_id)
        if product_data is None:
            QMessageBox.warning(self, "Ошибка", "Товар не найден.")
            self._reload_catalog_view()
            return

        category_options = self._catalog_service.get_category_options()
        dialog = ProductEditorDialog(
            category_options=category_options,
            product_data=product_data,
            product_id=product_id,
            product_image_service=self._product_image_service,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_data:
            return

        payload = self._extract_product_payload(dialog.result_data)
        try:
            self._catalog_service.update_product(
                product_id=product_id,
                **payload,
            )
            self._attach_pending_images(
                product_id,
                dialog.result_data.get("pending_local_images", []),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        self._reload_catalog_view()

    def _extract_product_payload(self, result_data: dict) -> dict:
        return {
            "name": result_data.get("name"),
            "description": result_data.get("description"),
            "price": result_data.get("price"),
            "price_unit": result_data.get("price_unit"),
            "sku": result_data.get("sku"),
            "published_state": result_data.get("published_state"),
            "visibility": result_data.get("visibility"),
            "is_featured": bool(result_data.get("is_featured")),
            "stock_status": result_data.get("stock_status"),
            "category_ids": result_data.get("category_ids", []),
            "image_urls": None,
        }

    def _attach_pending_images(
        self,
        product_id: int,
        pending_local_images: list[dict],
    ) -> None:
        if not pending_local_images:
            return

        primary_image_id: int | None = None
        for image_row in pending_local_images:
            source_path = str(image_row.get("path") or "").strip()
            if not source_path:
                continue
            added_row = self._product_image_service.add_local_image(product_id, source_path)
            if bool(image_row.get("is_primary")):
                primary_image_id = int(added_row["id"])

        if primary_image_id is not None:
            self._product_image_service.set_primary_image(product_id, primary_image_id)

    def _delete_selected_product(self) -> None:
        product_id = self._selected_product_id or self.products_table_panel.selected_product_id()
        if product_id is None:
            QMessageBox.information(self, "Товар не выбран", "Выберите товар в таблице.")
            return

        confirmation = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Удалить выбранный товар из локального каталога (в архив)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        deleted = self._catalog_service.archive_product(product_id)
        if not deleted:
            QMessageBox.warning(self, "Ошибка", "Товар не найден.")
            return
        self._reload_catalog_view()

    def _open_bulk_actions_dialog(self) -> None:
        product_ids = self.products_table_panel.checked_product_ids()
        if not product_ids:
            QMessageBox.information(
                self,
                "Нет выбранных товаров",
                "Отметьте хотя бы один товар в таблице для массового действия.",
            )
            return

        dialog = BulkProductEditDialog(
            selected_count=len(product_ids),
            category_options=self._catalog_service.get_category_options(),
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_data:
            return

        action = str(dialog.result_data.get("action") or "")
        try:
            if action == "set_price_unit":
                changed_count = self._catalog_service.bulk_update_product_price_unit(
                    product_ids=product_ids,
                    price_unit=dialog.result_data.get("price_unit"),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Единица измерения цены обновлена у товаров: {changed_count}.",
                )
            elif action == "set_price":
                changed_count = self._catalog_service.bulk_update_product_price(
                    product_ids=product_ids,
                    price=str(dialog.result_data.get("price") or ""),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Цена обновлена у товаров: {changed_count}.",
                )
            elif action == "replace_category":
                changed_count = self._catalog_service.bulk_replace_product_category(
                    product_ids=product_ids,
                    category_id=int(dialog.result_data.get("category_id") or 0),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Категория заменена у товаров: {changed_count}.",
                )
            elif action == "set_published_state":
                changed_count = self._catalog_service.bulk_update_product_published_state(
                    product_ids=product_ids,
                    published_state=str(dialog.result_data.get("published_state") or ""),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Статус публикации обновлён у товаров: {changed_count}.",
                )
            elif action == "set_visibility":
                changed_count = self._catalog_service.bulk_update_product_visibility(
                    product_ids=product_ids,
                    visibility=str(dialog.result_data.get("visibility") or ""),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Видимость обновлена у товаров: {changed_count}.",
                )
            elif action == "set_featured":
                changed_count = self._catalog_service.bulk_update_product_featured(
                    product_ids=product_ids,
                    is_featured=bool(dialog.result_data.get("is_featured")),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Признак рекомендуемого обновлён у товаров: {changed_count}.",
                )
            elif action == "set_stock_status":
                changed_count = self._catalog_service.bulk_update_product_stock_status(
                    product_ids=product_ids,
                    stock_status=str(dialog.result_data.get("stock_status") or ""),
                )
                QMessageBox.information(
                    self,
                    "Массовое изменение выполнено",
                    f"Наличие обновлено у товаров: {changed_count}.",
                )
            elif action == "archive_products":
                archived_count = self._catalog_service.bulk_archive_products(
                    product_ids=product_ids
                )
                QMessageBox.information(
                    self,
                    "Массовая архивация выполнена",
                    f"В архив перемещено товаров: {archived_count}.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Выбрано неподдерживаемое массовое действие.",
                )
                return
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        self.products_table_panel.clear_checked_products()
        self._reload_catalog_view()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(
            env_config_service=self._env_config_service,
            auth_service=self._auth_service,
            current_user=self._current_user,
            catalog_maintenance_service=self._catalog_maintenance_service,
            parent=self,
        )
        dialog.exec()

        if dialog.wc_settings_changed:
            self._import_service = self._import_service_factory()
            if self._publish_service_factory is not None:
                self._publish_service = self._publish_service_factory()

        if dialog.updated_admin_username:
            self._current_user.username = dialog.updated_admin_username
            self._update_status_bar()

        if dialog.catalog_cleared:
            self._selected_category_id = None
            self._selected_product_id = None
            self._search_query = ""
            self._products_page = 1
            self._reload_catalog_view()

    def _handle_import_from_wc(self) -> None:
        if self._import_service is None:
            QMessageBox.warning(
                self,
                "Импорт недоступен",
                "Заполните параметры WooCommerce в .env: "
                "FISHOLHA_WC_BASE_URL, FISHOLHA_WC_CONSUMER_KEY, FISHOLHA_WC_CONSUMER_SECRET.",
            )
            return

        if self._import_thread is not None and self._import_thread.isRunning():
            QMessageBox.information(
                self,
                "Импорт уже выполняется",
                "Подождите завершения текущего импорта.",
            )
            return

        if self._publish_thread is not None and self._publish_thread.isRunning():
            QMessageBox.information(
                self,
                "Операция недоступна",
                "Дождитесь завершения текущей публикации.",
            )
            return

        self.toolbar_panel.setEnabled(False)
        self._import_progress_dialog = QProgressDialog(
            "Подготовка импорта...",
            "",
            0,
            100,
            self,
        )
        self._import_progress_dialog.setWindowTitle("Импорт WooCommerce")
        self._import_progress_dialog.setWindowModality(Qt.ApplicationModal)
        self._import_progress_dialog.setCancelButton(None)
        self._import_progress_dialog.setAutoClose(False)
        self._import_progress_dialog.setAutoReset(False)
        self._import_progress_dialog.setMinimumDuration(0)
        self._import_progress_dialog.setValue(0)
        self._import_progress_dialog.show()

        self._import_thread = QThread(self)
        self._import_worker = ImportWorker(self._import_service)
        self._import_worker.moveToThread(self._import_thread)

        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.progress_changed.connect(self._on_import_progress)
        self._import_worker.import_finished.connect(self._on_import_finished)
        self._import_worker.import_finished.connect(self._import_thread.quit)
        self._import_worker.import_finished.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._on_import_thread_finished)
        self._import_thread.finished.connect(self._import_thread.deleteLater)
        self._import_thread.start()

    def _handle_publish_to_wc(self) -> None:
        self._open_publish_changes_dialog()

    def _open_publish_changes_dialog(self) -> None:
        if self._publish_service is None:
            QMessageBox.warning(
                self,
                "Публикация недоступна",
                "Заполните параметры WooCommerce в .env: "
                "FISHOLHA_WC_BASE_URL, FISHOLHA_WC_CONSUMER_KEY, FISHOLHA_WC_CONSUMER_SECRET.",
            )
            return

        if self._import_thread is not None and self._import_thread.isRunning():
            QMessageBox.information(
                self,
                "Операция недоступна",
                "Дождитесь завершения текущего импорта.",
            )
            return
        if self._publish_thread is not None and self._publish_thread.isRunning():
            QMessageBox.information(
                self,
                "Публикация уже выполняется",
                "Дождитесь завершения текущей публикации.",
            )
            return

        dialog = PublishChangesDialog(
            catalog_service=self._catalog_service,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self._start_publish_to_wc(dialog.publish_selection)

    def _start_publish_to_wc(
        self,
        selection: PublishSelection | None = None,
    ) -> None:
        self.toolbar_panel.setEnabled(False)
        self._publish_progress_dialog = QProgressDialog(
            "Подготовка публикации...",
            "",
            0,
            100,
            self,
        )
        self._publish_progress_dialog.setWindowTitle("Публикация в WooCommerce")
        self._publish_progress_dialog.setWindowModality(Qt.ApplicationModal)
        self._publish_progress_dialog.setCancelButton(None)
        self._publish_progress_dialog.setAutoClose(False)
        self._publish_progress_dialog.setAutoReset(False)
        self._publish_progress_dialog.setMinimumDuration(0)
        self._publish_progress_dialog.setValue(0)
        self._publish_progress_dialog.show()

        self._publish_thread = QThread(self)
        self._publish_worker = PublishWorker(self._publish_service, selection=selection)
        self._publish_worker.moveToThread(self._publish_thread)

        self._publish_thread.started.connect(self._publish_worker.run)
        self._publish_worker.progress_changed.connect(self._on_publish_progress)
        self._publish_worker.publish_finished.connect(self._on_publish_finished)
        self._publish_worker.publish_finished.connect(self._publish_thread.quit)
        self._publish_worker.publish_finished.connect(self._publish_worker.deleteLater)
        self._publish_thread.finished.connect(self._on_publish_thread_finished)
        self._publish_thread.finished.connect(self._publish_thread.deleteLater)
        self._publish_thread.start()

    @Slot(int, str)
    def _on_import_progress(self, percent: int, message: str) -> None:
        if self._import_progress_dialog is None:
            return
        self._import_progress_dialog.setLabelText(message)
        self._import_progress_dialog.setValue(percent)

    @Slot(object)
    def _on_import_finished(self, result_object: object) -> None:
        result = cast(ImportRunResult, result_object)
        if self._import_progress_dialog is not None:
            self._import_progress_dialog.setValue(100)
            self._import_progress_dialog.close()
            self._import_progress_dialog = None

        self.toolbar_panel.setEnabled(True)
        self._products_page = 1
        self._reload_catalog_view()

        if result.success:
            counters = result.counters
            QMessageBox.information(
                self,
                "Импорт завершён",
                (
                    "Импорт из WooCommerce выполнен успешно.\n\n"
                    f"Категории: {counters.get('categories_total', 0)} "
                    f"(новые: {counters.get('categories_created', 0)}, обновлены: {counters.get('categories_updated', 0)})\n"
                    f"Товары: {counters.get('products_total', 0)} "
                    f"(новые: {counters.get('products_created', 0)}, обновлены: {counters.get('products_updated', 0)})\n"
                    f"Связи товар-категория: {counters.get('product_category_links', 0)}\n"
                    f"Изображения (URL): {counters.get('product_images', 0)}"
                ),
            )
            return

        logger.error("Импорт WooCommerce завершился ошибкой: %s", "; ".join(result.errors))
        QMessageBox.critical(
            self,
            "Ошибка импорта",
            "Импорт завершился с ошибкой:\n" + "\n".join(result.errors),
        )

    @Slot()
    def _on_import_thread_finished(self) -> None:
        self._import_thread = None
        self._import_worker = None

    @Slot(int, str)
    def _on_publish_progress(self, percent: int, message: str) -> None:
        if self._publish_progress_dialog is None:
            return
        self._publish_progress_dialog.setLabelText(message)
        self._publish_progress_dialog.setValue(percent)

    @Slot(object)
    def _on_publish_finished(self, result_object: object) -> None:
        result = cast(PublishRunResult, result_object)
        if self._publish_progress_dialog is not None:
            self._publish_progress_dialog.setValue(100)
            self._publish_progress_dialog.close()
            self._publish_progress_dialog = None

        self.toolbar_panel.setEnabled(True)
        self._products_page = 1
        self._reload_catalog_view()

        if result.success:
            counters = result.counters
            QMessageBox.information(
                self,
                "Публикация завершена",
                (
                    "Публикация в WooCommerce выполнена успешно.\n\n"
                    f"Категории: {counters.get('categories_total', 0)} "
                    f"(создано: {counters.get('categories_created', 0)}, "
                    f"обновлено: {counters.get('categories_updated', 0)}, "
                    f"ошибок: {counters.get('categories_failed', 0)})\n"
                    f"Товары: {counters.get('products_total', 0)} "
                    f"(создано: {counters.get('products_created', 0)}, "
                    f"обновлено: {counters.get('products_updated', 0)}, "
                    f"ошибок: {counters.get('products_failed', 0)})\n"
                    f"Изображения категорий: загружено {counters.get('category_images_uploaded', 0)}, "
                    f"переиспользовано {counters.get('category_images_reused', 0)}, "
                    f"ошибок {counters.get('category_images_failed', 0)}\n"
                    f"Изображения товаров: загружено {counters.get('product_images_uploaded', 0)}, "
                    f"переиспользовано {counters.get('product_images_reused', 0)}, "
                    f"ошибок {counters.get('product_images_failed', 0)}"
                ),
            )
            return

        logger.error(
            "Publish to WooCommerce finished with errors: %s",
            "; ".join(result.errors),
        )
        shown_errors = result.errors[:20]
        hidden_count = max(0, len(result.errors) - len(shown_errors))
        details_text = "\n".join(shown_errors)
        if hidden_count > 0:
            details_text += f"\n... и ещё {hidden_count} ошибок"
        QMessageBox.critical(
            self,
            "Ошибка публикации",
            "Публикация завершилась с ошибками:\n" + details_text,
        )

    @Slot()
    def _on_publish_thread_finished(self) -> None:
        self._publish_thread = None
        self._publish_worker = None

    def _handle_category_action(self, action_key: str) -> None:
        if action_key == "add_category":
            self._open_add_category_dialog()
            return
        if action_key == "edit_category":
            self._open_edit_category_dialog()
            return

    def _open_add_category_dialog(self) -> None:
        category_options = self._catalog_service.get_category_options()
        dialog = CategoryEditorDialog(
            category_options=category_options,
            category_data=None,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_data:
            return
        try:
            new_category_id = self._catalog_service.create_category(**dialog.result_data)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self._selected_category_id = new_category_id
        self._products_page = 1
        self._reload_catalog_view()

    def _open_edit_category_dialog(self) -> None:
        category_id = self._selected_category_id
        if category_id is None:
            QMessageBox.information(
                self,
                "Категория не выбрана",
                "Выберите категорию в левом дереве.",
            )
            return

        category_data = self._catalog_service.get_category_details(category_id)
        if category_data is None:
            QMessageBox.warning(self, "Ошибка", "Категория не найдена.")
            self._reload_catalog_view()
            return

        category_options = self._catalog_service.get_category_options()
        dialog = CategoryEditorDialog(
            category_options=category_options,
            category_data=category_data,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_data:
            return

        try:
            self._catalog_service.update_category(
                category_id=category_id,
                **dialog.result_data,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        self._reload_catalog_view()
