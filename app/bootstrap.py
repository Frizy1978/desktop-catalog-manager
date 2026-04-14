from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog

from app.core.database import Database
from app.core.logging_config import configure_logging
from app.core.settings import AppSettings
from app.db.session import SqlAlchemyDatabase
from app.integrations.wp_media_client import (
    WordPressMediaClient,
    WordPressMediaClientConfig,
    WordPressMediaClientError,
)
from app.integrations.woocommerce_client import WooCommerceClient, WooCommerceClientConfig
from app.repositories.auth_repository import AuthRepository
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.publish_job_repository import PublishJobRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_image_repository import ProductImageRepository
from app.repositories.sync_run_repository import SyncRunRepository
from app.services.auth_service import AuthService
from app.services.catalog_maintenance_service import CatalogMaintenanceService
from app.services.catalog_service import CatalogService
from app.services.env_config_service import EnvConfigService
from app.services.login_memory_service import LoginMemoryService
from app.services.operation_log_service import OperationLogService
from app.services.publish_service import WooCommercePublishService
from app.services.product_image_service import ProductImageService
from app.services.sync_import_service import WooCommerceImportService
from app.services.wc_image_download_service import WooImageDownloadService
from app.services.wc_media_publish_service import WooMediaPublishService
from app.ui.icons import app_logo_icon
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.styles import apply_styles

logger = logging.getLogger(__name__)


def run() -> int:
    settings = AppSettings.load()
    configure_logging(
        settings.logs_dir,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    database = Database(db_path=settings.db_path)
    database.initialize()
    orm_database = SqlAlchemyDatabase(db_path=settings.db_path)
    orm_database.initialize()

    auth_repository = AuthRepository(database=database)
    auth_service = AuthService(
        auth_repository=auth_repository,
        default_admin_username=settings.default_admin_username,
        default_admin_password=settings.default_admin_password,
    )
    auth_service.ensure_bootstrap_user()

    catalog_repository = CatalogRepository(database=orm_database)
    catalog_service = CatalogService(repository=catalog_repository)

    env_config_service = EnvConfigService(Path(".env"))
    catalog_maintenance_service = CatalogMaintenanceService(
        db_path=settings.db_path,
        backups_dir=settings.app_data_dir / "backups",
    )
    login_memory_service = LoginMemoryService(
        storage_path=settings.app_data_dir / "login_memory.json"
    )
    product_image_service = ProductImageService(
        database=orm_database,
        repository=ProductImageRepository(),
        media_root=settings.media_dir,
    )
    sync_run_repository = SyncRunRepository(database=orm_database)
    publish_job_repository = PublishJobRepository(database=orm_database)
    operation_log_service = OperationLogService(repository=sync_run_repository)

    import_service_factory = lambda: _build_import_service(
        orm_database=orm_database,
        sync_run_repository=sync_run_repository,
    )
    import_service = import_service_factory()
    publish_service_factory = lambda: _build_publish_service(
        orm_database=orm_database,
        sync_run_repository=sync_run_repository,
        publish_job_repository=publish_job_repository,
    )
    publish_service = publish_service_factory()

    application = QApplication(sys.argv)
    apply_styles(application)
    logo_icon = app_logo_icon()
    if not logo_icon.isNull():
        application.setWindowIcon(logo_icon)

    login_dialog = LoginDialog(
        auth_service=auth_service,
        login_memory_service=login_memory_service,
    )
    if not logo_icon.isNull():
        login_dialog.setWindowIcon(logo_icon)
    if login_dialog.exec() != QDialog.Accepted or not login_dialog.authenticated_user:
        return 0

    window = MainWindow(
        current_user=login_dialog.authenticated_user,
        catalog_service=catalog_service,
        auth_service=auth_service,
        env_config_service=env_config_service,
        catalog_maintenance_service=catalog_maintenance_service,
        operation_log_service=operation_log_service,
        product_image_service=product_image_service,
        import_service_factory=import_service_factory,
        import_service=import_service,
        publish_service_factory=publish_service_factory,
        publish_service=publish_service,
    )
    if not logo_icon.isNull():
        window.setWindowIcon(logo_icon)
    window.show()
    return application.exec()


def _build_import_service(
    *,
    orm_database: SqlAlchemyDatabase,
    sync_run_repository: SyncRunRepository,
) -> WooCommerceImportService | None:
    settings = AppSettings.load()
    if not (
        settings.wc_base_url
        and settings.wc_consumer_key
        and settings.wc_consumer_secret
    ):
        return None

    wc_client = WooCommerceClient(
        WooCommerceClientConfig(
            base_url=settings.wc_base_url,
            consumer_key=settings.wc_consumer_key,
            consumer_secret=settings.wc_consumer_secret,
            timeout_seconds=settings.wc_timeout_seconds,
            verify_ssl=settings.wc_verify_ssl,
        )
    )
    image_download_service = WooImageDownloadService(
        database=orm_database,
        product_repository=ProductImageRepository(),
        category_repository=CategoryRepository(),
        media_root=settings.media_dir,
        timeout_seconds=settings.wc_timeout_seconds,
        verify_ssl=settings.wc_verify_ssl,
    )
    return WooCommerceImportService(
        database=orm_database,
        category_repository=CategoryRepository(),
        product_repository=ProductRepository(),
        sync_run_repository=sync_run_repository,
        wc_client=wc_client,
        image_download_service=image_download_service,
    )


def _build_publish_service(
    *,
    orm_database: SqlAlchemyDatabase,
    sync_run_repository: SyncRunRepository,
    publish_job_repository: PublishJobRepository,
) -> WooCommercePublishService | None:
    settings = AppSettings.load()
    if not (
        settings.wc_base_url
        and settings.wc_consumer_key
        and settings.wc_consumer_secret
    ):
        return None

    wc_client = WooCommerceClient(
        WooCommerceClientConfig(
            base_url=settings.wc_base_url,
            consumer_key=settings.wc_consumer_key,
            consumer_secret=settings.wc_consumer_secret,
            timeout_seconds=settings.wc_timeout_seconds,
            verify_ssl=settings.wc_verify_ssl,
        )
    )
    wp_media_client: WordPressMediaClient | None = None
    if (
        settings.wp_base_url
        and settings.wp_username
        and settings.wp_application_password
    ):
        try:
            wp_media_client = WordPressMediaClient(
                WordPressMediaClientConfig(
                    base_url=settings.wp_base_url,
                    username=settings.wp_username,
                    application_password=settings.wp_application_password,
                    timeout_seconds=settings.wc_timeout_seconds,
                    verify_ssl=settings.wc_verify_ssl,
                )
            )
        except WordPressMediaClientError:
            logger.warning(
                "WordPress media client disabled due to invalid configuration."
            )
            wp_media_client = None

    product_image_repository = ProductImageRepository()
    media_publish_service = WooMediaPublishService(
        database=orm_database,
        category_repository=CategoryRepository(),
        product_image_repository=product_image_repository,
        wp_media_client=wp_media_client,
    )
    return WooCommercePublishService(
        database=orm_database,
        category_repository=CategoryRepository(),
        product_repository=ProductRepository(),
        sync_run_repository=sync_run_repository,
        publish_job_repository=publish_job_repository,
        wc_client=wc_client,
        media_publish_service=media_publish_service,
    )
