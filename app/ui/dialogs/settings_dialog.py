from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import themed_icon


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки (заглушка Phase 1)")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Базовый модуль настроек создан в Phase 1.\n"
                "Параметры подключения и workflow будут добавлены позже."
            )
        )
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
