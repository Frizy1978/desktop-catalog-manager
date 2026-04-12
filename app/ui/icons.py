from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

try:
    import qtawesome as qta
except Exception:
    qta = None

ACCENT_COLOR = "#2f6feb"
MUTED_COLOR = "#8b9bb3"

ICON_NAME_BY_KEY = {
    "import_wc": "mdi6.download-outline",
    "publish_wc": "mdi6.upload-outline",
    "publish_channel2": "mdi6.cloud-upload-outline",
    "show_changes": "mdi6.history",
    "add_product": "mdi6.plus-box-outline",
    "edit_product": "mdi6.pencil-outline",
    "delete_product": "mdi6.delete-outline",
    "archive_product": "mdi6.archive-outline",
    "import_photos": "mdi6.image-plus-outline",
    "bulk_actions": "mdi6.select-multiple",
    "settings": "mdi6.cog-outline",
    "logs": "mdi6.text-box-search-outline",
    "refresh": "mdi6.refresh",
    "search": "mdi6.magnify",
    "add_category": "mdi6.plus",
    "edit_category": "mdi6.pencil-outline",
    "archive_category": "mdi6.archive-outline",
    "login": "mdi6.login",
    "close": "mdi6.close",
}


def app_logo_icon() -> QIcon:
    logo_path = Path("Icons") / "logo_mn.png"
    if logo_path.exists():
        source = QPixmap(str(logo_path.resolve()))
        if source.isNull():
            return QIcon()

        base_side = max(source.width(), source.height())
        base = QPixmap(base_side, base_side)
        base.fill(Qt.GlobalColor.transparent)

        painter = QPainter(base)
        x_offset = (base_side - source.width()) // 2
        y_offset = (base_side - source.height()) // 2
        painter.drawPixmap(x_offset, y_offset, source)
        painter.end()

        icon = QIcon()
        for side in (16, 20, 24, 32, 40, 48, 64, 128, 256):
            variant = base.scaled(
                side,
                side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon.addPixmap(variant)
        return icon
    return QIcon()


def app_logo_pixmap(max_width: int = 240, max_height: int = 120) -> QPixmap:
    logo_path = Path("Icons") / "logo_mn.png"
    if not logo_path.exists():
        return QPixmap()

    source = QPixmap(str(logo_path.resolve()))
    if source.isNull():
        return QPixmap()

    return source.scaled(
        max_width,
        max_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def themed_icon(
    icon_key: str,
    enabled: bool = True,
    color: str | None = None,
) -> QIcon:
    if qta is None:
        return QIcon()
    qtawesome_name = ICON_NAME_BY_KEY.get(icon_key, "mdi6.circle-outline")
    icon_color = color if color is not None else (ACCENT_COLOR if enabled else MUTED_COLOR)
    try:
        return qta.icon(qtawesome_name, color=icon_color)
    except Exception:
        return QIcon()
