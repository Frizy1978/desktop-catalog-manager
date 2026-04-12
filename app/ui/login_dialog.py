from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.user import AuthenticatedUser
from app.services.auth_service import AuthService
from app.services.login_memory_service import LoginMemoryService
from app.ui.icons import app_logo_pixmap, themed_icon


class LoginDialog(QDialog):
    def __init__(
        self,
        auth_service: AuthService,
        login_memory_service: LoginMemoryService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._login_memory_service = login_memory_service
        self.authenticated_user: AuthenticatedUser | None = None

        self.setWindowTitle("Вход в систему")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._build_ui()
        self._load_remembered_credentials()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        logo_pixmap = app_logo_pixmap(max_width=220, max_height=110)
        if not logo_pixmap.isNull():
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            root_layout.addWidget(logo_label)

        title = QLabel("Fish Olha Catalog Manager")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Локальный доступ к управлению каталогом")
        subtitle.setStyleSheet("color: #5e6c83;")
        subtitle.setAlignment(Qt.AlignCenter)

        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логин")
        self.username_input.setText("admin")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин", self.username_input)
        form_layout.addRow("Пароль", self.password_input)

        self.show_password_checkbox = QCheckBox("Показать пароль")
        self.show_password_checkbox.toggled.connect(self._toggle_password_visibility)
        form_layout.addRow("", self.show_password_checkbox)

        self.remember_password_checkbox = QCheckBox("Сохранить пароль")
        form_layout.addRow("", self.remember_password_checkbox)

        root_layout.addLayout(form_layout)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b42318; font-weight: 600;")
        self.error_label.setVisible(False)
        root_layout.addWidget(self.error_label)

        controls = QHBoxLayout()
        controls.addStretch()
        self.login_button = QPushButton("Войти")
        self.login_button.setIcon(themed_icon("login", color="#ffffff"))
        self.login_button.clicked.connect(self._attempt_login)
        controls.addWidget(self.login_button)
        root_layout.addLayout(controls)

        self.username_input.returnPressed.connect(self._attempt_login)
        self.password_input.returnPressed.connect(self._attempt_login)

    def _load_remembered_credentials(self) -> None:
        if self._login_memory_service is None:
            return
        remembered = self._login_memory_service.load()
        if remembered.username:
            self.username_input.setText(remembered.username)
        if remembered.remember_password:
            self.password_input.setText(remembered.password)
            self.remember_password_checkbox.setChecked(True)

    def _attempt_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error("Введите логин и пароль.")
            return

        user = self._auth_service.authenticate(username=username, password=password)
        if user is None:
            self._show_error("Неверные учетные данные.")
            return

        if self._login_memory_service is not None:
            if self.remember_password_checkbox.isChecked():
                self._login_memory_service.save(username=username, password=password)
            else:
                self._login_memory_service.clear()

        self.authenticated_user = user
        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _toggle_password_visibility(self, checked: bool) -> None:
        self.password_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
