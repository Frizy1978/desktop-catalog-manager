from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.core.database import Database
from app.core.settings import AppSettings
from app.repositories.auth_repository import AuthRepository
from app.repositories.catalog_repository import CatalogRepository
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService
from app.ui.icons import app_logo_icon
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.styles import apply_styles


def run() -> int:
    settings = AppSettings.load()

    database = Database(db_path=settings.db_path)
    database.initialize()

    auth_repository = AuthRepository(database=database)
    auth_service = AuthService(
        auth_repository=auth_repository,
        default_admin_username=settings.default_admin_username,
        default_admin_password=settings.default_admin_password,
    )
    auth_service.ensure_bootstrap_user()

    catalog_repository = CatalogRepository(database=database)
    catalog_service = CatalogService(repository=catalog_repository)

    application = QApplication(sys.argv)
    apply_styles(application)
    logo_icon = app_logo_icon()
    if not logo_icon.isNull():
        application.setWindowIcon(logo_icon)

    login_dialog = LoginDialog(auth_service=auth_service)
    if not logo_icon.isNull():
        login_dialog.setWindowIcon(logo_icon)
    if login_dialog.exec() != QDialog.Accepted or not login_dialog.authenticated_user:
        return 0

    window = MainWindow(
        current_user=login_dialog.authenticated_user,
        catalog_service=catalog_service,
    )
    if not logo_icon.isNull():
        window.setWindowIcon(logo_icon)
    window.show()
    return application.exec()
