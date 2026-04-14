from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import themed_icon


class CategoriesPanel(QWidget):
    action_triggered = Signal(str)
    category_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._categories: list[dict] = []
        self._selected_category_id: int | None = None
        self._thumb_icon_cache: dict[str, QIcon | None] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        group = QGroupBox("Категории")
        layout = QVBoxLayout(group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск категорий...")
        self.search_input.textChanged.connect(self._rebuild_tree)
        layout.addWidget(self.search_input)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIconSize(QSize(20, 20))
        self.tree_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree_widget.setMinimumWidth(260)
        self.tree_widget.setStyleSheet(
            """
            QTreeWidget::item:selected {
                color: #6f42c1;
                font-weight: 700;
                background: #efe8ff;
                border-radius: 4px;
            }
            """
        )
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree_widget, stretch=1)

        controls = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.edit_button = QPushButton("Изменить")
        self.add_button.setIcon(themed_icon("add_category", color="#ffffff"))
        self.edit_button.setIcon(themed_icon("edit_category", color="#ffffff"))

        self.add_button.clicked.connect(lambda: self.action_triggered.emit("add_category"))
        self.edit_button.clicked.connect(lambda: self.action_triggered.emit("edit_category"))

        controls.addWidget(self.add_button)
        controls.addWidget(self.edit_button)
        layout.addLayout(controls)
        root_layout.addWidget(group)

    def populate(
        self,
        categories: list[dict],
        *,
        selected_category_id: int | None = None,
    ) -> None:
        self._categories = list(categories)
        self._selected_category_id = selected_category_id
        self._thumb_icon_cache.clear()
        self._rebuild_tree()

    def selected_category_id(self) -> int | None:
        return self._selected_category_id

    def select_category(self, category_id: int | None, *, emit_signal: bool) -> None:
        self._selected_category_id = category_id
        item = self._find_item_by_category_id(category_id)
        if item is None:
            return
        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(item)
        self.tree_widget.blockSignals(False)
        if emit_signal:
            self.category_selected.emit(self._selected_category_id)

    def _rebuild_tree(self) -> None:
        query = self.search_input.text().strip().lower()
        filtered_categories = self._filter_categories(query)
        category_by_id = {
            int(item["id"]): item
            for item in filtered_categories
            if item.get("id") is not None
        }
        children_by_parent: dict[int | None, list[dict]] = defaultdict(list)
        for category in filtered_categories:
            parent_id = category.get("parent_id")
            if parent_id not in category_by_id:
                parent_id = None
            children_by_parent[parent_id].append(category)

        self.tree_widget.blockSignals(True)
        self.tree_widget.clear()
        all_item = QTreeWidgetItem(["Все категории"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, None)
        self.tree_widget.addTopLevelItem(all_item)
        self._add_children(all_item, children_by_parent, None)
        all_item.setExpanded(True)
        self.tree_widget.expandAll()

        selected_item = self._find_item_by_category_id(self._selected_category_id)
        if selected_item is None:
            selected_item = all_item
            self._selected_category_id = None
        self.tree_widget.setCurrentItem(selected_item)
        self.tree_widget.blockSignals(False)

    def _filter_categories(self, query: str) -> list[dict]:
        if not query:
            return list(self._categories)

        by_id = {
            int(item["id"]): item
            for item in self._categories
            if item.get("id") is not None
        }
        matched_ids: set[int] = set()
        for category in self._categories:
            category_id = category.get("id")
            if category_id is None:
                continue
            name = str(category.get("name", "")).lower()
            if query in name:
                matched_ids.add(int(category_id))

        include_ids = set(matched_ids)
        for category_id in list(matched_ids):
            cursor = by_id.get(category_id)
            while cursor is not None:
                parent_id = cursor.get("parent_id")
                if parent_id is None or parent_id in include_ids:
                    break
                include_ids.add(int(parent_id))
                cursor = by_id.get(int(parent_id))

        return [item for item in self._categories if int(item.get("id") or 0) in include_ids]

    def _add_children(
        self,
        parent_item: QTreeWidgetItem,
        children_by_parent: dict[int | None, list[dict]],
        parent_id: int | None,
    ) -> None:
        for category in sorted(
            children_by_parent.get(parent_id, []),
            key=lambda c: str(c.get("name", "")).lower(),
        ):
            item = QTreeWidgetItem([str(category.get("name", "Без названия"))])
            category_id = int(category["id"])
            item.setData(0, Qt.ItemDataRole.UserRole, category_id)
            self._apply_category_thumbnail(item, category)
            self._apply_unsynced_style(item, str(category.get("sync_status", "")))
            parent_item.addChild(item)
            self._add_children(item, children_by_parent, category_id)

    def _apply_unsynced_style(self, item: QTreeWidgetItem, sync_status: str) -> None:
        if sync_status not in {"new_local", "modified_local", "publish_pending", "publish_error"}:
            return
        item.setForeground(0, QColor("#c26a00"))
        font = QFont(item.font(0))
        if font.pointSize() <= 0 and font.pixelSize() <= 0:
            font.setPointSize(9)
        font.setBold(True)
        item.setFont(0, font)

    def _apply_category_thumbnail(self, item: QTreeWidgetItem, category: dict) -> None:
        preview_path = str(category.get("image_preview_path") or "").strip()
        if not preview_path:
            return
        icon = self._resolve_thumbnail_icon(preview_path)
        if icon is not None:
            item.setIcon(0, icon)

    def _resolve_thumbnail_icon(self, preview_path: str) -> QIcon | None:
        cached = self._thumb_icon_cache.get(preview_path)
        if preview_path in self._thumb_icon_cache:
            return cached

        candidate = Path(preview_path)
        if not candidate.exists() or not candidate.is_file():
            self._thumb_icon_cache[preview_path] = None
            return None

        pixmap = QPixmap(str(candidate))
        if pixmap.isNull():
            self._thumb_icon_cache[preview_path] = None
            return None

        thumb = pixmap.scaled(
            20,
            20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        icon = QIcon(thumb)
        self._thumb_icon_cache[preview_path] = icon
        return icon

    def _find_item_by_category_id(self, category_id: int | None) -> QTreeWidgetItem | None:
        if category_id is None:
            return self.tree_widget.topLevelItem(0)
        root = self.tree_widget.invisibleRootItem()
        stack: list[QTreeWidgetItem] = [root.child(i) for i in range(root.childCount())]
        while stack:
            item = stack.pop()
            if item.data(0, Qt.ItemDataRole.UserRole) == category_id:
                return item
            stack.extend(item.child(i) for i in range(item.childCount()))
        return None

    def _on_selection_changed(self) -> None:
        item = self.tree_widget.currentItem()
        if item is None:
            return
        value = item.data(0, Qt.ItemDataRole.UserRole)
        self._selected_category_id = int(value) if value is not None else None
        self.category_selected.emit(self._selected_category_id)
