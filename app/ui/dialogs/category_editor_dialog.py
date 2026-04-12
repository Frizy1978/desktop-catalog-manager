from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import themed_icon


class CategoryEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактор категории (заглушка Phase 1)")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Редактор категории подготовлен в Phase 1.\n"
                "Полный CRUD будет реализован в следующих фазах."
            )
        )
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
