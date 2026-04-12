from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import themed_icon


class OperationLogDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Журнал операций (заглушка Phase 1)")
        self.setMinimumWidth(640)
        self.setMinimumHeight(360)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Экран журнала операций подготовлен.\n"
                "Импорт/публикация и события будут отображаться в следующих фазах."
            )
        )
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
