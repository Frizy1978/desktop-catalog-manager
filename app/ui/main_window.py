from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.models.user import AuthenticatedUser
from app.services.catalog_service import CatalogService
from app.ui.dialogs.category_editor_dialog import CategoryEditorDialog
from app.ui.dialogs.operation_log_dialog import OperationLogDialog
from app.ui.dialogs.product_editor_dialog import ProductEditorDialog
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.widgets.categories_panel import CategoriesPanel
from app.ui.widgets.products_table_panel import ProductsTablePanel
from app.ui.widgets.toolbar_panel import ToolbarPanel


class MainWindow(QMainWindow):
    def __init__(
        self,
        current_user: AuthenticatedUser,
        catalog_service: CatalogService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._catalog_service = catalog_service

        self.setWindowTitle("Fish Olha — Менеджер каталога")
        self.resize(1440, 880)
        self._build_ui()
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

        right_layout.addWidget(self.toolbar_panel)
        right_layout.addWidget(self.products_table_panel, stretch=1)

        splitter.addWidget(self.categories_panel)
        splitter.addWidget(right_side)
        splitter.setSizes([320, 1120])

        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        role_labels = {
            "admin": "администратор",
            "editor": "редактор",
            "viewer": "наблюдатель",
        }
        role_name = role_labels.get(self._current_user.role, self._current_user.role)
        self.statusBar().showMessage(
            f"Выполнен вход: {self._current_user.username} ({role_name})"
        )

        self.toolbar_panel.action_triggered.connect(self._handle_toolbar_action)
        self.categories_panel.action_triggered.connect(self._handle_category_action)

    def _load_initial_data(self) -> None:
        category_rows = self._catalog_service.get_category_sidebar_items()
        product_rows = self._catalog_service.get_products_table_rows()
        self.categories_panel.populate(category_rows)
        self.products_table_panel.populate(product_rows)

    def _handle_toolbar_action(self, action_key: str) -> None:
        if action_key in {"add_product", "edit_product"}:
            ProductEditorDialog(self).exec()
            return

        if action_key == "settings":
            SettingsDialog(self).exec()
            return

        if action_key == "logs":
            OperationLogDialog(self).exec()
            return

        if action_key == "show_changes":
            QMessageBox.information(
                self,
                "Заглушка Phase 1",
                "Просмотр изменений будет реализован в одной из следующих фаз.",
            )
            return

        if action_key in {
            "import_wc",
            "publish_wc",
            "archive_product",
            "bulk_actions",
            "import_photos",
            "publish_channel2",
        }:
            action_titles = {
                "import_wc": "Загрузить из WooCommerce",
                "publish_wc": "Выгрузить в WooCommerce",
                "archive_product": "Архивировать товар",
                "bulk_actions": "Массовые действия",
                "import_photos": "Импорт фото",
                "publish_channel2": "Выгрузить в канал 2",
            }
            QMessageBox.information(
                self,
                "Заглушка Phase 1",
                f"Действие «{action_titles.get(action_key, action_key)}» подготовлено и будет реализовано позже.",
            )
            return

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
            "Заглушка Phase 1",
            f"Действие категории «{action_titles.get(action_key, action_key)}» пока не реализовано.",
        )
