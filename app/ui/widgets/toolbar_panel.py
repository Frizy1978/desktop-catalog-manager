from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from app.ui.icons import themed_icon


class ToolbarPanel(QWidget):
    action_triggered = Signal(str)
    search_changed = Signal(str)
    filters_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(8)

        commands_row = QHBoxLayout()
        commands_row.setContentsMargins(0, 0, 0, 0)
        commands_row.setSpacing(8)

        self._add_primary_button(commands_row, "Загрузить", "import_wc")
        self._add_primary_button(commands_row, "Выгрузить", "publish_wc")
        self._add_primary_button(commands_row, "Изменения", "show_changes")
        self._add_primary_button(commands_row, "Добавить", "add_product")
        self._add_primary_button(commands_row, "Массово", "bulk_actions")
        commands_row.addStretch()

        self.more_button = QToolButton()
        self.more_button.setObjectName("toolbarMoreButton")
        self.more_button.setText("Ещё")
        self.more_button.setIcon(themed_icon("settings"))
        self.more_button.setIconSize(QSize(18, 18))
        self.more_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_button.setToolTip("Дополнительные действия")
        self.more_button.setMenu(self._build_overflow_menu(self.more_button))
        self.more_button.setMinimumHeight(36)
        self.more_button.setMinimumWidth(120)
        commands_row.addWidget(self.more_button)

        root_layout.addLayout(commands_row)

        filters_row = QHBoxLayout()
        filters_row.setContentsMargins(0, 0, 0, 0)
        filters_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию и SKU...")
        self.search_input.textChanged.connect(
            lambda text: self.search_changed.emit(text.strip())
        )
        self.search_input.textChanged.connect(self._sync_clear_button_state)
        self.search_input.setMinimumWidth(320)
        filters_row.addWidget(self.search_input, stretch=1)

        self.clear_search_button = QToolButton()
        self.clear_search_button.setObjectName("toolbarActionButton")
        self.clear_search_button.setIcon(themed_icon("close"))
        self.clear_search_button.setIconSize(QSize(16, 16))
        self.clear_search_button.setToolTip("Очистить поиск")
        self.clear_search_button.setMinimumHeight(36)
        self.clear_search_button.setMinimumWidth(40)
        self.clear_search_button.clicked.connect(self._clear_search)
        self.clear_search_button.setEnabled(False)
        filters_row.addWidget(self.clear_search_button)

        self.filters_button = QToolButton()
        self.filters_button.setObjectName("toolbarActionButton")
        self.filters_button.setText("Фильтры")
        self.filters_button.setIcon(themed_icon("search"))
        self.filters_button.setIconSize(QSize(18, 18))
        self.filters_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.filters_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.filters_button.setToolTip("Фильтры таблицы товаров")
        self.filters_button.setMinimumHeight(36)
        self.filters_button.setMinimumWidth(130)
        self.filters_button.setMenu(self._build_filters_menu(self.filters_button))
        filters_row.addWidget(self.filters_button)

        root_layout.addLayout(filters_row)
        self._sync_filters_button_state()

    def _add_primary_button(
        self,
        layout: QHBoxLayout,
        title: str,
        action_key: str,
    ) -> None:
        button = QToolButton()
        button.setObjectName("toolbarActionButton")
        button.setText(title)
        button.setIcon(themed_icon(action_key))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setToolTip(title)
        button.setMinimumHeight(36)
        button.clicked.connect(
            lambda _checked=False, key=action_key: self.action_triggered.emit(key)
        )
        layout.addWidget(button)

    def _build_overflow_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(parent)
        self._add_menu_action(menu, "Изменить товар", "edit_product")
        self._add_menu_action(menu, "Удалить товар", "delete_product")
        menu.addSeparator()
        self._add_menu_action(menu, "Журнал операций", "logs")
        self._add_menu_action(menu, "Настройки", "settings")
        return menu

    def _build_filters_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(parent)

        container = QWidget(menu)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        sync_status_label = QLabel("Статус синхронизации", container)
        sync_status_label.setToolTip(
            "Состояние локальных изменений\nи синхронизации товара."
        )
        layout.addWidget(sync_status_label)

        self.sync_status_filter = QComboBox(container)
        self.sync_status_filter.addItem("Все товары", "")
        self.sync_status_filter.addItem("Изменённые", "modified_local")
        self.sync_status_filter.addItem("Новые/созданные", "new_local")
        self.sync_status_filter.addItem("Ожидают публикации", "publish_pending")
        self.sync_status_filter.addItem("Ошибка публикации", "publish_error")
        self.sync_status_filter.addItem("Синхронизированы", "synced")
        self.sync_status_filter.currentIndexChanged.connect(self._emit_filters_changed)
        self.sync_status_filter.setMinimumWidth(220)
        self.sync_status_filter.setToolTip(
            "Фильтр по локальному состоянию:\nизменён, новый, ожидает публикации, синхронизирован."
        )
        layout.addWidget(self.sync_status_filter)

        published_state_label = QLabel("Статус публикации", container)
        published_state_label.setToolTip(
            "Статус публикации товара\nв WooCommerce."
        )
        layout.addWidget(published_state_label)

        self.published_state_filter = QComboBox(container)
        self.published_state_filter.addItem("Все", "")
        self.published_state_filter.addItem("Черновик", "draft")
        self.published_state_filter.addItem("Опубликован", "publish")
        self.published_state_filter.addItem("На проверке", "pending")
        self.published_state_filter.addItem("Приватный", "private")
        self.published_state_filter.currentIndexChanged.connect(self._emit_filters_changed)
        self.published_state_filter.setMinimumWidth(220)
        self.published_state_filter.setToolTip(
            "Фильтр по статусу публикации:\nчерновик, опубликован, на проверке, приватный."
        )
        layout.addWidget(self.published_state_filter)

        visibility_label = QLabel("Видимость в каталоге", container)
        visibility_label.setToolTip(
            "Как товар должен отображаться\nна витрине WooCommerce."
        )
        layout.addWidget(visibility_label)

        self.visibility_filter = QComboBox(container)
        self.visibility_filter.addItem("Вся видимость", "")
        self.visibility_filter.addItem("Видим везде", "visible")
        self.visibility_filter.addItem("Только в каталоге", "catalog")
        self.visibility_filter.addItem("Только в поиске", "search")
        self.visibility_filter.addItem("Скрыт", "hidden")
        self.visibility_filter.currentIndexChanged.connect(self._emit_filters_changed)
        self.visibility_filter.setMinimumWidth(220)
        self.visibility_filter.setToolTip(
            "Фильтр по видимости:\nвезде, только в каталоге, только в поиске, скрыт."
        )
        layout.addWidget(self.visibility_filter)

        featured_label = QLabel("Рекомендуемый товар", container)
        featured_label.setToolTip(
            "Показывает, отмечен ли товар\nкак рекомендуемый."
        )
        layout.addWidget(featured_label)

        self.is_featured_filter = QComboBox(container)
        self.is_featured_filter.addItem("Все", "")
        self.is_featured_filter.addItem("Да", "true")
        self.is_featured_filter.addItem("Нет", "false")
        self.is_featured_filter.currentIndexChanged.connect(self._emit_filters_changed)
        self.is_featured_filter.setMinimumWidth(220)
        self.is_featured_filter.setToolTip(
            "Фильтр по признаку\nрекомендуемого товара."
        )
        layout.addWidget(self.is_featured_filter)

        stock_status_label = QLabel("Наличие", container)
        stock_status_label.setToolTip(
            "Показывает, доступен ли товар\nдля покупки."
        )
        layout.addWidget(stock_status_label)

        self.stock_status_filter = QComboBox(container)
        self.stock_status_filter.addItem("Все", "")
        self.stock_status_filter.addItem("В наличии", "instock")
        self.stock_status_filter.addItem("Нет в наличии", "outofstock")
        self.stock_status_filter.addItem("Под заказ", "onbackorder")
        self.stock_status_filter.currentIndexChanged.connect(self._emit_filters_changed)
        self.stock_status_filter.setMinimumWidth(220)
        self.stock_status_filter.setToolTip(
            "Фильтр по наличию:\nв наличии, нет в наличии, под заказ."
        )
        layout.addWidget(self.stock_status_filter)

        self.clear_filters_button = QToolButton(container)
        self.clear_filters_button.setObjectName("toolbarActionButton")
        self.clear_filters_button.setText("Сбросить фильтры")
        self.clear_filters_button.setIcon(themed_icon("close"))
        self.clear_filters_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.clear_filters_button.setMinimumHeight(34)
        self.clear_filters_button.clicked.connect(self._clear_filters)
        layout.addWidget(self.clear_filters_button)

        action = QWidgetAction(menu)
        action.setDefaultWidget(container)
        menu.addAction(action)
        return menu

    def _add_menu_action(
        self,
        menu: QMenu,
        title: str,
        action_key: str,
        enabled: bool = True,
    ) -> None:
        action = menu.addAction(themed_icon(action_key, enabled=enabled), title)
        action.setEnabled(enabled)
        action.triggered.connect(
            lambda _checked=False, key=action_key: self.action_triggered.emit(key)
        )

    def _clear_search(self) -> None:
        self.search_input.clear()
        self.search_input.setFocus()

    def _sync_clear_button_state(self, text: str) -> None:
        self.clear_search_button.setEnabled(bool(text.strip()))

    def _clear_filters(self) -> None:
        self.sync_status_filter.blockSignals(True)
        self.published_state_filter.blockSignals(True)
        self.visibility_filter.blockSignals(True)
        self.is_featured_filter.blockSignals(True)
        self.stock_status_filter.blockSignals(True)
        self.sync_status_filter.setCurrentIndex(0)
        self.published_state_filter.setCurrentIndex(0)
        self.visibility_filter.setCurrentIndex(0)
        self.is_featured_filter.setCurrentIndex(0)
        self.stock_status_filter.setCurrentIndex(0)
        self.sync_status_filter.blockSignals(False)
        self.published_state_filter.blockSignals(False)
        self.visibility_filter.blockSignals(False)
        self.is_featured_filter.blockSignals(False)
        self.stock_status_filter.blockSignals(False)
        self._emit_filters_changed()

    def _emit_filters_changed(self) -> None:
        self._sync_filters_button_state()
        self.filters_changed.emit(
            {
                "sync_status": str(self.sync_status_filter.currentData() or ""),
                "published_state": str(self.published_state_filter.currentData() or ""),
                "visibility": str(self.visibility_filter.currentData() or ""),
                "is_featured": str(self.is_featured_filter.currentData() or ""),
                "stock_status": str(self.stock_status_filter.currentData() or ""),
            }
        )

    def _sync_filters_button_state(self) -> None:
        active_filters = (
            int(bool(self.sync_status_filter.currentData()))
            + int(bool(self.published_state_filter.currentData()))
            + int(bool(self.visibility_filter.currentData()))
            + int(bool(self.is_featured_filter.currentData()))
            + int(bool(self.stock_status_filter.currentData()))
        )
        self.clear_filters_button.setEnabled(active_filters > 0)
        if active_filters > 0:
            self.filters_button.setText(f"Фильтры ({active_filters})")
        else:
            self.filters_button.setText("Фильтры")
