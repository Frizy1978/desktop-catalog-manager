from __future__ import annotations

import logging
from typing import Callable, cast

from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.models.user import AuthenticatedUser
from app.services.auth_service import AuthService
from app.services.catalog_maintenance_service import CatalogMaintenanceService
from app.services.catalog_service import CatalogService
from app.services.env_config_service import EnvConfigService
from app.services.operation_log_service import OperationLogService
from app.services.sync_import_service import ImportRunResult, WooCommerceImportService
from app.ui.dialogs.category_editor_dialog import CategoryEditorDialog
from app.ui.dialogs.operation_log_dialog import OperationLogDialog
from app.ui.dialogs.product_editor_dialog import ProductEditorDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.widgets.categories_panel import CategoriesPanel
from app.ui.widgets.products_table_panel import ProductsTablePanel
from app.ui.widgets.toolbar_panel import ToolbarPanel
from app.ui.workers.import_worker import ImportWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        current_user: AuthenticatedUser,
        catalog_service: CatalogService,
        auth_service: AuthService,
        env_config_service: EnvConfigService,
        catalog_maintenance_service: CatalogMaintenanceService,
        operation_log_service: OperationLogService,
        import_service_factory: Callable[[], WooCommerceImportService | None],
        import_service: WooCommerceImportService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._catalog_service = catalog_service
        self._auth_service = auth_service
        self._env_config_service = env_config_service
        self._catalog_maintenance_service = catalog_maintenance_service
        self._operation_log_service = operation_log_service
        self._import_service_factory = import_service_factory
        self._import_service = import_service

        self._products_page = 1
        self._products_page_size = 50

        self._import_thread: QThread | None = None
        self._import_worker: ImportWorker | None = None
        self._import_progress_dialog: QProgressDialog | None = None

        self.setWindowTitle("Fish Olha — Менеджер каталога")
        self.resize(1440, 880)
        self._build_ui()
        self._update_status_bar()
        self._load_initial_data()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)

        splitter = QSplitter()
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

        right_layout.addWidget(self.toolbar_panel)
        right_layout.addWidget(self.products_table_panel, stretch=1)

        splitter.addWidget(self.categories_panel)
        splitter.addWidget(right_side)
        splitter.setSizes([320, 1120])

        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        self.toolbar_panel.action_triggered.connect(self._handle_toolbar_action)
        self.categories_panel.action_triggered.connect(self._handle_category_action)

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

    def _load_initial_data(self) -> None:
        category_rows = self._catalog_service.get_category_sidebar_items()
        self.categories_panel.populate(category_rows)
        self._load_products_page()

    def _load_products_page(self) -> None:
        page_data = self._catalog_service.get_products_table_page(
            page=self._products_page,
            page_size=self._products_page_size,
        )
        total_pages = int(page_data["total_pages"])
        if self._products_page > total_pages:
            self._products_page = total_pages
            page_data = self._catalog_service.get_products_table_page(
                page=self._products_page,
                page_size=self._products_page_size,
            )

        self.products_table_panel.populate_page(
            rows=page_data["items"],
            page=int(page_data["page"]),
            page_size=int(page_data["page_size"]),
            total_items=int(page_data["total_items"]),
            total_pages=int(page_data["total_pages"]),
        )

    @Slot(int)
    def _on_products_page_changed(self, page: int) -> None:
        self._products_page = max(1, page)
        self._load_products_page()

    @Slot(int)
    def _on_products_page_size_changed(self, page_size: int) -> None:
        self._products_page_size = max(1, page_size)
        self._products_page = 1
        self._load_products_page()

    def _handle_toolbar_action(self, action_key: str) -> None:
        if action_key == "import_wc":
            self._handle_import_from_wc()
            return

        if action_key in {"add_product", "edit_product"}:
            ProductEditorDialog(self).exec()
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

        if action_key == "show_changes":
            QMessageBox.information(
                self,
                "Заглушка Phase 2",
                "Просмотр изменений будет реализован в одной из следующих фаз.",
            )
            return

        if action_key in {
            "publish_wc",
            "archive_product",
            "bulk_actions",
            "import_photos",
            "publish_channel2",
        }:
            action_titles = {
                "publish_wc": "Выгрузить в WooCommerce",
                "archive_product": "Архивировать товар",
                "bulk_actions": "Массовые действия",
                "import_photos": "Импорт фото",
                "publish_channel2": "Выгрузить в канал 2",
            }
            QMessageBox.information(
                self,
                "Заглушка Phase 2",
                f"Действие «{action_titles.get(action_key, action_key)}» подготовлено и будет реализовано позже.",
            )
            return

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

        if dialog.updated_admin_username:
            self._current_user.username = dialog.updated_admin_username
            self._update_status_bar()

        if dialog.catalog_cleared:
            self._products_page = 1
            self._load_initial_data()

    def _handle_import_from_wc(self) -> None:
        if self._import_service is None:
            QMessageBox.warning(
                self,
                "Импорт недоступен",
                "Заполните WooCommerce параметры в .env: "
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
        self._load_initial_data()

        if result.success:
            counters = result.counters
            QMessageBox.information(
                self,
                "Импорт завершен",
                (
                    "Импорт из WooCommerce выполнен успешно.\n\n"
                    f"Категории: {counters['categories_total']} "
                    f"(новые: {counters['categories_created']}, обновлены: {counters['categories_updated']})\n"
                    f"Товары: {counters['products_total']} "
                    f"(новые: {counters['products_created']}, обновлены: {counters['products_updated']})\n"
                    f"Связи товар-категория: {counters['product_category_links']}\n"
                    f"Изображения (URL): {counters['product_images']}"
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

    def _handle_category_action(self, action_key: str) -> None:
        if action_key in {"add_category", "edit_category", "archive_category"}:
            CategoryEditorDialog(self).exec()
            return

        action_titles = {
            "add_category": "Добавить категорию",
            "edit_category": "Изменить категорию",
            "archive_category": "Архивировать категорию",
        }
        QMessageBox.information(
            self,
            "Заглушка Phase 2",
            f"Действие категории «{action_titles.get(action_key, action_key)}» пока не реализовано.",
        )
