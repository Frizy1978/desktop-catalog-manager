from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMenu, QToolButton, QWidget

from app.ui.icons import themed_icon


class ToolbarPanel(QWidget):
    action_triggered = Signal(str)
    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        self._add_primary_button(layout, "Загрузить", "import_wc")
        self._add_primary_button(layout, "Выгрузить", "publish_wc")
        self._add_primary_button(layout, "Изменения", "show_changes")
        self._add_primary_button(layout, "Добавить", "add_product")
        self._add_primary_button(layout, "Изменить", "edit_product")
        self._add_primary_button(layout, "Удалить", "delete_product")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию и SKU...")
        self.search_input.textChanged.connect(
            lambda text: self.search_changed.emit(text.strip())
        )
        self.search_input.setMinimumWidth(280)
        self.search_input.textChanged.connect(self._sync_clear_button_state)
        layout.addWidget(self.search_input, stretch=1)

        self.clear_search_button = QToolButton()
        self.clear_search_button.setObjectName("toolbarActionButton")
        self.clear_search_button.setIcon(themed_icon("close"))
        self.clear_search_button.setIconSize(QSize(16, 16))
        self.clear_search_button.setToolTip("Очистить поиск")
        self.clear_search_button.setMinimumHeight(36)
        self.clear_search_button.setMinimumWidth(40)
        self.clear_search_button.clicked.connect(self._clear_search)
        self.clear_search_button.setEnabled(False)
        layout.addWidget(self.clear_search_button)

        self.more_button = QToolButton()
        self.more_button.setObjectName("toolbarMoreButton")
        self.more_button.setText("Ещё")
        self.more_button.setIcon(themed_icon("settings"))
        self.more_button.setIconSize(QSize(18, 18))
        self.more_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more_button.setToolTip("Дополнительные действия")
        self.more_button.setMenu(self._build_overflow_menu(self.more_button))
        self.more_button.setMinimumHeight(36)
        self.more_button.setMinimumWidth(120)
        layout.addWidget(self.more_button)

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
        self._add_menu_action(menu, "Журнал операций", "logs")
        self._add_menu_action(menu, "Настройки", "settings")
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
