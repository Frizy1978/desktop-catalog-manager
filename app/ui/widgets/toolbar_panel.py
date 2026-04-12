from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget

from app.ui.icons import themed_icon


class ToolbarPanel(QWidget):
    action_triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        self._add_primary_button(layout, "Импорт", "import_wc")
        self._add_primary_button(layout, "Выгрузка", "publish_wc")
        self._add_primary_button(layout, "Изменения", "show_changes")
        self._add_primary_button(layout, "Добавить", "add_product")
        self._add_primary_button(layout, "Изменить", "edit_product")

        self.more_button = QToolButton()
        self.more_button.setObjectName("toolbarMoreButton")
        self.more_button.setText("Ещё")
        self.more_button.setIcon(themed_icon("settings"))
        self.more_button.setIconSize(QSize(18, 18))
        self.more_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.more_button.setPopupMode(QToolButton.InstantPopup)
        self.more_button.setToolTip("Дополнительные действия")
        self.more_button.setMenu(self._build_overflow_menu(self.more_button))
        self.more_button.setMinimumHeight(36)
        self.more_button.setMinimumWidth(126)
        layout.addWidget(self.more_button)
        layout.addStretch()

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
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setToolTip(title)
        button.setMinimumHeight(36)
        button.setMinimumWidth(126)
        button.clicked.connect(
            lambda _checked=False, key=action_key: self.action_triggered.emit(key)
        )
        layout.addWidget(button)

    def _build_overflow_menu(self, parent: QWidget) -> QMenu:
        menu = QMenu(parent)
        self._add_menu_action(menu, "В архив", "archive_product")
        self._add_menu_action(menu, "Импорт фото", "import_photos")
        self._add_menu_action(menu, "Массовые действия", "bulk_actions")
        self._add_menu_action(menu, "Журнал операций", "logs")
        self._add_menu_action(menu, "Настройки", "settings")
        self._add_menu_action(
            menu,
            "Выгрузить в канал 2",
            "publish_channel2",
            enabled=False,
        )
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
