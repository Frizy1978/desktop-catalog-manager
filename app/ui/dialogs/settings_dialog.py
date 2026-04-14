from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import ensure_directory
from app.core.settings import AppSettings
from app.models.user import AuthenticatedUser
from app.services.auth_service import AuthService
from app.services.catalog_maintenance_service import CatalogMaintenanceService
from app.services.env_config_service import EnvConfigService
from app.ui.icons import themed_icon


class SettingsDialog(QDialog):
    def __init__(
        self,
        *,
        env_config_service: EnvConfigService,
        auth_service: AuthService,
        current_user: AuthenticatedUser,
        catalog_maintenance_service: CatalogMaintenanceService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._env_config_service = env_config_service
        self._auth_service = auth_service
        self._current_user = current_user
        self._catalog_maintenance_service = catalog_maintenance_service
        self._settings = AppSettings.load()

        self.wc_settings_changed = False
        self.catalog_cleared = False
        self.updated_admin_username: str | None = None

        self.setWindowTitle("Настройки")
        self.setMinimumWidth(760)
        self._build_ui()
        self._load_wc_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        root.addWidget(self._build_wc_group())
        root.addWidget(self._build_admin_group())
        root.addWidget(self._build_maintenance_group())
        root.addWidget(self._build_logging_group())

        controls = QHBoxLayout()
        controls.addStretch()
        close_button = QPushButton("Закрыть")
        close_button.setIcon(themed_icon("close", color="#ffffff"))
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        root.addLayout(controls)

    def _build_wc_group(self) -> QGroupBox:
        group = QGroupBox("WooCommerce и WordPress media")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.wc_base_url_input = QLineEdit()
        self.wc_base_url_input.setPlaceholderText("https://fisholha.ru/")
        self.wc_key_input = QLineEdit()
        self.wc_key_input.setPlaceholderText("ck_...")
        self.wc_secret_input = QLineEdit()
        self.wc_secret_input.setPlaceholderText("cs_...")

        self.wp_base_url_input = QLineEdit()
        self.wp_base_url_input.setPlaceholderText("https://fisholha.ru/")
        self.wp_username_input = QLineEdit()
        self.wp_username_input.setPlaceholderText("wp admin username")
        self.wp_application_password_input = QLineEdit()
        self.wp_application_password_input.setPlaceholderText(
            "xxxx xxxx xxxx xxxx xxxx xxxx"
        )
        self.wp_application_password_input.setEchoMode(QLineEdit.Password)

        layout.addWidget(QLabel("WooCommerce Base URL"), 0, 0)
        layout.addWidget(self.wc_base_url_input, 0, 1)
        layout.addWidget(QLabel("WooCommerce Consumer Key"), 1, 0)
        layout.addWidget(self.wc_key_input, 1, 1)
        layout.addWidget(QLabel("WooCommerce Consumer Secret"), 2, 0)
        layout.addWidget(self.wc_secret_input, 2, 1)

        layout.addWidget(QLabel("WP media base URL"), 3, 0)
        layout.addWidget(self.wp_base_url_input, 3, 1)
        layout.addWidget(QLabel("WP username"), 4, 0)
        layout.addWidget(self.wp_username_input, 4, 1)
        layout.addWidget(QLabel("WP application password"), 5, 0)
        layout.addWidget(self.wp_application_password_input, 5, 1)

        save_wc_button = QPushButton("Сохранить настройки подключения")
        save_wc_button.setIcon(themed_icon("settings", color="#ffffff"))
        save_wc_button.clicked.connect(self._save_wc_settings)
        layout.addWidget(save_wc_button, 6, 1)
        return group

    def _build_admin_group(self) -> QGroupBox:
        group = QGroupBox("Учетная запись администратора")
        layout = QFormLayout(group)

        self.admin_username_input = QLineEdit()
        self.admin_username_input.setText(self._current_user.username)
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setEchoMode(QLineEdit.Password)
        self.admin_password_confirm_input = QLineEdit()
        self.admin_password_confirm_input.setEchoMode(QLineEdit.Password)

        layout.addRow("Логин администратора", self.admin_username_input)
        layout.addRow("Новый пароль", self.admin_password_input)
        layout.addRow("Повтор пароля", self.admin_password_confirm_input)

        save_admin_button = QPushButton("Сохранить логин/пароль администратора")
        save_admin_button.setIcon(themed_icon("edit_product", color="#ffffff"))
        save_admin_button.clicked.connect(self._save_admin_credentials)
        layout.addRow("", save_admin_button)
        return group

    def _build_maintenance_group(self) -> QGroupBox:
        group = QGroupBox("Обслуживание каталога")
        layout = QVBoxLayout(group)

        warning = QLabel(
            "Очистка удалит локальные категории, товары, связи, URL изображений и журнал синхронизаций.\n"
            "Перед очисткой автоматически создается backup базы данных."
        )
        warning.setStyleSheet("color: #8a2f0a;")
        layout.addWidget(warning)

        clear_button = QPushButton("Очистить каталог")
        clear_button.setIcon(themed_icon("archive_product", color="#ffffff"))
        clear_button.clicked.connect(self._clear_catalog)
        layout.addWidget(clear_button)
        return group

    def _build_logging_group(self) -> QGroupBox:
        group = QGroupBox("Логи")
        layout = QFormLayout(group)

        max_bytes = int(self._settings.log_max_bytes)
        backup_count = int(self._settings.log_backup_count)
        logs_dir = str(self._settings.logs_dir)

        size_text = f"{max_bytes:,} байт ({self._format_megabytes(max_bytes):.2f} МБ)".replace(
            ",",
            " ",
        )
        self.log_rotation_size_label = QLabel(size_text)
        self.log_rotation_backups_label = QLabel(str(backup_count))
        self.logs_dir_label = QLabel(logs_dir)
        self.logs_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addRow("Макс. размер файла лога", self.log_rotation_size_label)
        layout.addRow("Количество архивов", self.log_rotation_backups_label)
        layout.addRow("Папка логов", self.logs_dir_label)

        open_logs_button = QPushButton("Открыть папку логов")
        open_logs_button.setIcon(themed_icon("logs", color="#ffffff"))
        open_logs_button.clicked.connect(self._open_logs_folder)
        layout.addRow("", open_logs_button)
        return group

    @staticmethod
    def _format_megabytes(bytes_count: int) -> float:
        return bytes_count / float(1024 * 1024)

    def _load_wc_settings(self) -> None:
        values = self._env_config_service.load_values(
            {
                "FISHOLHA_WC_BASE_URL": "https://fisholha.ru/",
                "FISHOLHA_WC_CONSUMER_KEY": "",
                "FISHOLHA_WC_CONSUMER_SECRET": "",
                "FISHOLHA_WP_BASE_URL": "https://fisholha.ru/",
                "FISHOLHA_WP_USERNAME": "",
                "FISHOLHA_WP_APPLICATION_PASSWORD": "",
            }
        )
        self.wc_base_url_input.setText(values["FISHOLHA_WC_BASE_URL"])
        self.wc_key_input.setText(values["FISHOLHA_WC_CONSUMER_KEY"])
        self.wc_secret_input.setText(values["FISHOLHA_WC_CONSUMER_SECRET"])
        self.wp_base_url_input.setText(values["FISHOLHA_WP_BASE_URL"])
        self.wp_username_input.setText(values["FISHOLHA_WP_USERNAME"])
        self.wp_application_password_input.setText(
            values["FISHOLHA_WP_APPLICATION_PASSWORD"]
        )

    def _save_wc_settings(self) -> None:
        wc_base_url = self.wc_base_url_input.text().strip() or "https://fisholha.ru/"
        consumer_key = self.wc_key_input.text().strip()
        consumer_secret = self.wc_secret_input.text().strip()
        wp_base_url = self.wp_base_url_input.text().strip() or "https://fisholha.ru/"
        wp_username = self.wp_username_input.text().strip()
        wp_application_password = self.wp_application_password_input.text().strip()

        self._env_config_service.save_values(
            {
                "FISHOLHA_WC_BASE_URL": wc_base_url,
                "FISHOLHA_WC_CONSUMER_KEY": consumer_key,
                "FISHOLHA_WC_CONSUMER_SECRET": consumer_secret,
                "FISHOLHA_WP_BASE_URL": wp_base_url,
                "FISHOLHA_WP_USERNAME": wp_username,
                "FISHOLHA_WP_APPLICATION_PASSWORD": wp_application_password,
            }
        )
        self.wc_settings_changed = True
        QMessageBox.information(
            self,
            "Настройки сохранены",
            "Параметры WooCommerce и WordPress media сохранены в .env.",
        )

    def _save_admin_credentials(self) -> None:
        username = self.admin_username_input.text().strip()
        password = self.admin_password_input.text()
        password_confirm = self.admin_password_confirm_input.text()

        if not username:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Логин администратора не может быть пустым.",
            )
            return
        if not password:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Введите новый пароль администратора.",
            )
            return
        if password != password_confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают.")
            return

        try:
            self._auth_service.update_user_credentials(
                user_id=self._current_user.id,
                username=username,
                password=password,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return

        self.updated_admin_username = username
        self.admin_password_input.clear()
        self.admin_password_confirm_input.clear()
        QMessageBox.information(
            self,
            "Успешно",
            "Логин и пароль администратора обновлены.",
        )

    def _clear_catalog(self) -> None:
        confirmation = QMessageBox.question(
            self,
            "Подтверждение очистки",
            "Очистить каталог?\n\nПеред очисткой будет создан backup базы данных.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmation != QMessageBox.Yes:
            return

        try:
            backup_path = self._catalog_maintenance_service.clear_catalog_with_backup()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Ошибка очистки",
                f"Не удалось очистить каталог: {exc}",
            )
            return

        self.catalog_cleared = True
        QMessageBox.information(
            self,
            "Каталог очищен",
            f"Очистка завершена.\nBackup создан:\n{backup_path}",
        )

    def _open_logs_folder(self) -> None:
        logs_dir = Path(self._settings.logs_dir)
        ensure_directory(logs_dir)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))
        if not opened:
            QMessageBox.warning(
                self,
                "Не удалось открыть папку",
                f"Не удалось открыть папку логов:\n{logs_dir}",
            )
