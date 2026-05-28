from PySide6.QtWidgets import QTreeView, QMenu, QInputDialog, QMessageBox
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush, QColor, QDrag
from PySide6.QtCore import Qt, Signal, QThread, QMimeData, QByteArray

from core.api import BaiduPanAPI
from utils.file_utils import get_filename


class _LoadDirsThread(QThread):
    finished = Signal(str, list)

    def __init__(self, api: BaiduPanAPI, dir_path: str):
        super().__init__()
        self._api = api
        self._dir_path = dir_path

    def run(self):
        try:
            data = self._api.list_files(self._dir_path, order="name", desc=0, limit=1000)
            children = []
            for item in data.get("list", []):
                if item.get("isdir"):
                    children.append({
                        "path": item["path"],
                        "filename": get_filename(item),
                    })
            self.finished.emit(self._dir_path, children)
        except Exception:
            self.finished.emit(self._dir_path, [])


class DirTree(QTreeView):
    """目录树组件，支持懒加载子目录与文件拖放。"""

    dir_selected = Signal(str)
    files_dropped_on_dir = Signal(str, list, int)  # (target_dir, source_paths, action: 0=move, 1=copy)

    def __init__(self, api: BaiduPanAPI, parent=None):
        super().__init__(parent)
        self._api = api
        self._loaded_paths: set = set()
        self._item_map: dict = {}
        self._load_threads: list = []

        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(True)
        self.setAnimated(True)
        self.setIndentation(20)

        # 启用拖放
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.DropOnly)
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)

        self.expanded.connect(self._on_expanded)
        self.clicked.connect(self._on_clicked)

        self._init_root()

    def _init_root(self):
        root = QStandardItem("📁 根目录")
        font = QFont(self.font())
        font.setBold(True)
        root.setFont(font)
        root.setData("/", Qt.ItemDataRole.UserRole)
        root.setEditable(False)
        root.setToolTip("/")
        root.setForeground(QBrush(QColor("#0066cc")))
        self._model.appendRow(root)
        self._item_map["/"] = root
        self.setCurrentIndex(root.index())
        self._load_children(root, "/")

    def _load_children(self, parent_item: QStandardItem, dir_path: str):
        if dir_path in self._loaded_paths:
            return

        thread = _LoadDirsThread(self._api, dir_path)
        thread.finished.connect(lambda path, children: self._on_children_loaded(parent_item, path, children))
        self._load_threads.append(thread)
        thread.start()

    def _on_children_loaded(self, parent_item: QStandardItem, dir_path: str, children: list):
        self._loaded_paths.add(dir_path)
        for child_data in children:
            child_path = child_data["path"]
            child_name = child_data["filename"]
            child = QStandardItem(f"📁 {child_name}")
            child.setData(child_path, Qt.ItemDataRole.UserRole)
            child.setEditable(False)
            child.setToolTip(child_path)
            child.setForeground(QBrush(QColor("#0066cc")))
            font = QFont(self.font())
            child.setFont(font)
            parent_item.appendRow(child)
            self._item_map[child_path] = child

        self.expand(parent_item.index())

    def _on_expanded(self, index):
        item = self._model.itemFromIndex(index)
        if item:
            dir_path = item.data(Qt.ItemDataRole.UserRole)
            if dir_path and dir_path not in self._loaded_paths:
                self._load_children(item, dir_path)

    def _on_clicked(self, index):
        item = self._model.itemFromIndex(index)
        if item:
            dir_path = item.data(Qt.ItemDataRole.UserRole)
            if dir_path:
                self.dir_selected.emit(dir_path)

    def get_selected_path(self) -> str:
        index = self.currentIndex()
        if index.isValid():
            item = self._model.itemFromIndex(index)
            if item:
                return item.data(Qt.ItemDataRole.UserRole) or "/"
        return "/"

    def refresh(self, dir_path: str = "/"):
        if dir_path in self._item_map:
            item = self._item_map[dir_path]
            item.removeRows(0, item.rowCount())
            self._loaded_paths.discard(dir_path)
            self._load_children(item, dir_path)

    # ── 拖放实现 ──

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-filelist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-filelist"):
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                self.setCurrentIndex(index)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-filelist"):
            event.ignore()
            return

        source_paths = str(event.mimeData().data("application/x-filelist"), "utf-8").strip().split("\n")
        source_paths = [p for p in source_paths if p]
        if not source_paths:
            event.ignore()
            return

        # 确定目标目录
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            item = self._model.itemFromIndex(index)
            target_dir = item.data(Qt.ItemDataRole.UserRole) if item else "/"
        else:
            target_dir = "/"

        menu = QMenu(self)
        move_action = menu.addAction("📁 移动到此处")
        copy_action = menu.addAction("📋 复制到此处")
        menu.addSeparator()
        cancel_action = menu.addAction("取消")

        action = menu.exec(self.viewport().mapToGlobal(event.position().toPoint()))
        if action == move_action:
            self.files_dropped_on_dir.emit(target_dir, source_paths, 0)
        elif action == copy_action:
            self.files_dropped_on_dir.emit(target_dir, source_paths, 1)

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return

        item = self._model.itemFromIndex(index)
        if not item:
            return

        dir_path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        refresh_action = menu.addAction("🔄 刷新")
        refresh_action.triggered.connect(lambda: self.refresh(dir_path))

        menu.exec(event.globalPos())

    def navigate_to(self, dir_path: str):
        parts = dir_path.strip("/").split("/")
        current_path = ""
        parent_item = self._item_map.get("/")
        if not parent_item:
            return

        for part in parts:
            if not part:
                continue
            current_path = current_path + "/" + part
            if current_path not in self._loaded_paths:
                parent_path = "/" if current_path.count("/") <= 1 else current_path.rsplit("/", 1)[0]
                self._load_children(parent_item, parent_path)

            child_item = self._item_map.get(current_path)
            if child_item:
                try:
                    index = child_item.index()
                    if index.isValid():
                        parent_item = child_item
                        self.expand(index)
                    else:
                        break
                except RuntimeError:
                    # 对象已被删除，重建 item_map
                    self._item_map = {"/": self._model.item(0)} if self._model.rowCount() > 0 else {}
                    break
            else:
                break

        if parent_item:
            try:
                idx = parent_item.index()
                if idx.isValid():
                    self.setCurrentIndex(idx)
            except RuntimeError:
                pass