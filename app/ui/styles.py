from PySide6.QtWidgets import QApplication


BASE_STYLESHEET = """
QWidget {
    background: #f6f8fb;
    color: #1f2937;
    font-family: "Segoe UI";
    font-size: 13px;
}

QMainWindow, QDialog {
    background: #f6f8fb;
}

QLineEdit, QListWidget, QTableView, QTextEdit {
    background: #ffffff;
    border: 1px solid #d5dde8;
    border-radius: 8px;
    padding: 6px;
}

QPushButton {
    background: #2f6feb;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-weight: 600;
    padding: 7px 12px;
}

QPushButton:hover {
    background: #255fcd;
}

QPushButton:disabled {
    background: #b4c3dc;
    color: #eef2f8;
}

QToolButton#toolbarActionButton, QToolButton#toolbarMoreButton {
    background: #ffffff;
    border: 1px solid #d5dde8;
    border-radius: 8px;
    color: #1f2937;
    font-weight: 600;
    padding: 6px 12px;
}

QToolButton#toolbarActionButton:hover, QToolButton#toolbarMoreButton:hover {
    background: #eef4ff;
    border: 1px solid #9bb8f1;
}

QToolButton#toolbarActionButton:pressed, QToolButton#toolbarMoreButton:pressed {
    background: #e2ecff;
}

QToolButton#toolbarActionButton:disabled, QToolButton#toolbarMoreButton:disabled {
    color: #8b9bb3;
    background: #f3f6fb;
}

QToolButton#toolbarMoreButton::menu-indicator {
    image: none;
    width: 0px;
}

QGroupBox {
    border: 1px solid #dce3ee;
    border-radius: 10px;
    margin-top: 10px;
    background: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #46556a;
}

QHeaderView::section {
    background-color: #eef2f8;
    border: none;
    border-right: 1px solid #d5dde8;
    border-bottom: 1px solid #d5dde8;
    padding: 8px 6px;
    font-weight: 600;
}
"""


def apply_styles(application: QApplication) -> None:
    application.setStyleSheet(BASE_STYLESHEET)
