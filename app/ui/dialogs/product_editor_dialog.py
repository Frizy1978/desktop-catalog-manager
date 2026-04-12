from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.icons import themed_icon


class ProductEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактор товара (заглушка Phase 1)")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Диалог редактирования товара подготовлен.\n"
                "Детальные поля и поведение будут добавлены позже."
            )
        )
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
