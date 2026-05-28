from PySide6.QtWidgets import (
    QTableView, QMenu, QLineEdit, QMessageBox, QAbstractItemView, QHeaderView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QColor, QBrush, QDrag
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QMimeData, QByteArray

from utils.file_utils import format_size, format_time, get_file_type, get_filename
from core.api import BaiduPanAPI


# 列索引
COL_NAME = 0
COL_SIZE = 1
COL_TIME = 2

COLUMN_HEADERS = ["名称", "大小", "修改时间"]

SORT_MAP = {
    COL_NAME: "name",
    COL_SIZE: "size",
    COL_TIME: "time",
}

# 文件类型 → 图标映射
FILE_ICONS = {
    "folder": "📁",
    "image": "🖼",
    "video": "🎬",
    "audio": "🎵",
    "archive": "📦",
    "document": "📄",
    "code": "💻",
    "pdf": "📕",
    "spreadsheet": "📊",
    "presentation": "📽",
    "text": "📝",
    "file": "📄",
}

_FOLDER_COLOR = QColor("#0066cc")
_FOLDER_BG = QColor("#F0F5FF")
_FILE_COLOR = QColor("#1D2129")


def _get_file_icon(filename: str, is_dir: bool, category: int = 0) -> str:
    """根据文件名和类型返回对应图标。"""
    if is_dir:
        return "📁"
    if category == 2:
        return "🖼"
    if category == 3:
        return "🎬"
    if category == 4:
        return "🎵"
    if category == 5:
        return "📦"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    icon_map = {
        "pdf": "📕",
        "doc": "📄", "docx": "📄",
        "xls": "📊", "xlsx": "📊",
        "ppt": "📽", "pptx": "📽",
        "txt": "📝", "md": "📝", "csv": "📝",
        "py": "💻", "js": "💻", "java": "💻", "cpp": "💻",
        "c": "💻", "go": "💻", "rs": "💻", "ts": "💻",
        "zip": "📦", "rar": "📦", "7z": "📦", "tar": "📦", "gz": "📦",
        "jpg": "🖼", "jpeg": "🖼", "png": "🖼", "gif": "🖼",
        "svg": "🖼", "webp": "🖼", "bmp": "🖼",
        "mp4": "🎬", "avi": "🎬", "mkv": "🎬", "mov": "🎬",
        "mp3": "🎵", "flac": "🎵", "wav": "🎵", "aac": "🎵",
    }
    return icon_map.get(ext, "📄")


class _LoadFilesThread(QThread):
    finished = Signal(str, dict)

    def __init__(self, api: BaiduPanAPI, dir_path: str, order: str, desc: int, start: int, limit: int):
        super().__init__()
        self._api = api
        self._dir_path = dir_path
        self._order = order
        self._desc = desc
        self._start = start
        self._limit = limit

    def run(self):
        try:
            data = self._api.list_files(
                self._dir_path, order=self._order, desc=self._desc,
                start=self._start, limit=self._limit
            )
            self.finished.emit(self._dir_path, data)
        except Exception:
            self.finished.emit(self._dir_path, {"list": []})


class _SearchThread(QThread):
    finished = Signal(dict)

    def __init__(self, api: BaiduPanAPI, keyword: str, dir_path: str, page: int, num: int):
        super().__init__()
        self._api = api
        self._keyword = keyword
        self._dir_path = dir_path
        self._page = page
        self._num = num

    def run(self):
        try:
            data = self._api.search(self._keyword, self._dir_path, page=self._page, num=self._num)
            self.finished.emit(data)
        except Exception:
            self.finished.emit({"list": []})


class FileTableView(QTableView):
    """文件列表表格组件，支持拖放和视觉区分。"""

    rename_requested = Signal(str, str)
    file_selected = Signal(dict)
    file_opened = Signal(dict)
    selection_changed = Signal(int)
    loading_started = Signal()
    loading_finished = Signal()
    total_info_changed = Signal(int, int, str)  # (total, selected, formatted_size)
    files_dropped = Signal(str, int)  # (target_dir, action: 0=move, 1=copy)
    move_requested = Signal(list)     # 右键菜单：移动选中文件
    copy_requested = Signal(list)     # 右键菜单：复制选中文件
    delete_requested = Signal(list)   # 右键菜单：删除选中文件

    def __init__(self, api: BaiduPanAPI, parent=None):
        super().__init__(parent)
        self._api = api
        self._current_dir = "/"
        self._files = []
        self._sort_column = COL_TIME
        self._sort_desc = True
        self._loading = False
        self._load_thread = None
        self._search_thread = None
        self._is_search_mode = False
        self._search_keyword = ""
        self._search_page = 1

        self._init_model()
        self._init_view()

    def _init_model(self):
        self._model = QStandardItemModel(self)
        self._model.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.setModel(self._model)

        header = self.horizontalHeader()
        header.sectionClicked.connect(self._on_header_clicked)
        header.setStretchLastSection(False)

        header.resizeSection(COL_NAME, 380)
        header.resizeSection(COL_SIZE, 100)
        header.resizeSection(COL_TIME, 160)

        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        for col in (COL_SIZE, COL_TIME):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)

    def _init_view(self):
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(False)
        self.setWordWrap(False)
        self.setMouseTracking(True)

        self.doubleClicked.connect(self._on_double_clicked)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # 拖放支持
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    # ── 拖放实现 ──

    def mouseMoveEvent(self, event):
        """开始拖拽。"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        selected = self.get_selected_files()
        if not selected:
            super().mouseMoveEvent(event)
            return

        drag = QDrag(self)
        mime = QMimeData()
        paths = [f["path"] for f in selected]
        names = [get_filename(f) for f in selected]
        mime.setText("\n".join(paths))
        mime.setData("application/x-filelist", QByteArray("\n".join(paths).encode()))
        mime.setData("application/x-filenames", QByteArray("\n".join(names).encode()))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("application/x-filelist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("application/x-filelist"):
            idx = self.indexAt(event.position().toPoint())
            if idx.isValid():
                row = idx.row()
                if 0 <= row < len(self._files) and self._files[row].get("isdir"):
                    self.setCurrentIndex(idx)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """接收拖放文件到当前目录或子目录。"""
        if not event.mimeData().hasFormat("application/x-filelist"):
            event.ignore()
            return

        source_paths = str(event.mimeData().data("application/x-filelist"), "utf-8").strip().split("\n")
        source_paths = [p for p in source_paths if p]
        if not source_paths:
            event.ignore()
            return

        # 确定目标目录
        target_dir = self._current_dir
        drop_row = self.indexAt(event.position().toPoint()).row()
        if 0 <= drop_row < len(self._files) and self._files[drop_row].get("isdir"):
            target_dir = self._files[drop_row]["path"]

        count = len(source_paths)
        self._show_drop_menu(source_paths, target_dir, event)

    def _show_drop_menu(self, source_paths: list, target_dir: str, event):
        menu = QMenu(self)
        move_action = menu.addAction("📁 移动到此处")
        copy_action = menu.addAction("📋 复制到此处")
        menu.addSeparator()
        cancel_action = menu.addAction("取消")

        action = menu.exec(self.viewport().mapToGlobal(event.position().toPoint()))
        if action == move_action:
            self._pending_drop = (source_paths, target_dir, 0)
            self.files_dropped.emit(target_dir, 0)
        elif action == copy_action:
            self._pending_drop = (source_paths, target_dir, 1)
            self.files_dropped.emit(target_dir, 1)

    @property
    def pending_drop(self):
        return getattr(self, '_pending_drop', None)

    def clear_pending_drop(self):
        self._pending_drop = None

    # ── 目录加载 ──

    def load_directory(self, dir_path: str, append: bool = False):
        if self._loading:
            return
        self._loading = True
        self._is_search_mode = False
        self._current_dir = dir_path
        self.loading_started.emit()

        if not append:
            self._files.clear()

        start = len(self._files) if append else 0
        order = SORT_MAP.get(self._sort_column, "time")
        desc = 1 if self._sort_desc else 0

        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.terminate()
            self._load_thread.wait()
        self._load_thread = _LoadFilesThread(self._api, dir_path, order, desc, start, 100)
        self._load_thread.finished.connect(lambda path, data: self._on_files_loaded(path, data, append))
        self._load_thread.start()

    def _on_files_loaded(self, dir_path: str, data: dict, append: bool):
        if dir_path != self._current_dir and not append:
            return
        self._loading = False
        new_files = data.get("list", [])
        if append:
            self._files.extend(new_files)
        else:
            self._files = new_files
        self._refresh_model()
        self.loading_finished.emit()
        self._update_total_info()

    def search_files(self, keyword: str, dir_path: str = "/", page: int = 1):
        if self._loading:
            return
        self._loading = True
        self._is_search_mode = True
        self._search_keyword = keyword
        self._search_page = page
        self.loading_started.emit()
        if page == 1:
            self._files.clear()

        self._search_thread = _SearchThread(self._api, keyword, dir_path, page, 100)
        self._search_thread.finished.connect(self._on_search_finished)
        self._search_thread.start()

    def _on_search_finished(self, data: dict):
        self._loading = False
        self._files.extend(data.get("list", []))
        self._refresh_model()
        self.loading_finished.emit()
        self._update_total_info()

    def _refresh_model(self):
        """用当前文件列表刷新表格，目录和文件视觉上清晰区分。"""
        self._model.removeRows(0, self._model.rowCount())

        for file_info in self._files:
            is_dir = file_info.get("isdir", 0)
            category = file_info.get("category", 0)
            name = get_filename(file_info)
            icon = _get_file_icon(name, is_dir, category)
            display_name = f"  {icon}  {name}"

            row_items = []

            # ── 名称（带图标） ──
            name_item = QStandardItem(display_name)
            name_item.setEditable(False)
            name_item.setToolTip(name)
            name_item.setData(file_info, Qt.ItemDataRole.UserRole)
            if is_dir:
                font = QFont(self.font())
                font.setBold(True)
                name_item.setFont(font)
                name_item.setForeground(QBrush(_FOLDER_COLOR))
                name_item.setBackground(QBrush(_FOLDER_BG))
            else:
                name_item.setForeground(QBrush(_FILE_COLOR))
            row_items.append(name_item)

            # ── 大小 ──
            size = file_info.get("size", 0)
            size_item = QStandardItem(format_size(size) if not is_dir else "")
            size_item.setEditable(False)
            size_item.setData(size, Qt.ItemDataRole.UserRole)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if is_dir:
                size_item.setForeground(QBrush(QColor("#C0C4CC")))
            row_items.append(size_item)

            # ── 修改时间 ──
            mtime = file_info.get("mtime", 0)
            if mtime == 0:
                mtime = file_info.get("server_mtime", 0)
            time_item = QStandardItem(format_time(mtime))
            time_item.setEditable(False)
            time_item.setData(mtime, Qt.ItemDataRole.UserRole)
            row_items.append(time_item)

            self._model.appendRow(row_items)

        self.viewport().update()

    def _on_header_clicked(self, logical_index: int):
        if self._sort_column == logical_index:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = logical_index
            self._sort_desc = True
        if self._is_search_mode:
            self._files.clear()
            self.search_files(self._search_keyword, self._current_dir)
        else:
            self.load_directory(self._current_dir)

    def _on_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self._files):
            file_info = self._files[row]
            if file_info.get("isdir"):
                self.file_opened.emit(file_info)

    def _on_selection_changed(self):
        self._update_total_info()

    def _update_total_info(self):
        total = len(self._files)
        selected = len(self.get_selected_files())
        total_size = sum(f.get("size", 0) for f in self._files)
        self.total_info_changed.emit(total, selected, format_size(total_size))

    def get_selected_files(self) -> list:
        selected = []
        for index in self.selectionModel().selectedRows():
            row = index.row()
            if 0 <= row < len(self._files):
                selected.append(self._files[row])
        return selected

    def get_all_files(self) -> list:
        return list(self._files)

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        menu = QMenu(self)

        row = index.row() if index.isValid() else -1
        selected = self.get_selected_files()
        clicked_file = self._files[row] if 0 <= row < len(self._files) else None

        # 右键点中的文件不在已选中范围内，则仅选中该文件
        if clicked_file and clicked_file not in selected:
            self.clearSelection()
            self.selectRow(row)
            selected = [clicked_file]
        else:
            selected = self.get_selected_files()

        if not selected:
            return

        file_count = len(selected)
        is_single = file_count == 1
        file_info = selected[0]
        is_dir = file_info.get("isdir", 0)

        # 标题
        if is_single:
            menu.addAction(f"📄 {get_filename(file_info)}").setEnabled(False)
        else:
            menu.addAction(f"已选中 {file_count} 个文件").setEnabled(False)
        menu.addSeparator()

        # 打开（仅目录）
        if is_single and is_dir:
            open_action = menu.addAction("📂 打开")
            open_action.triggered.connect(lambda: self.file_opened.emit(file_info))
            menu.addSeparator()

        # 移动
        move_action = menu.addAction("📁 移动到...")
        move_action.triggered.connect(lambda: self.move_requested.emit(selected))
        # 复制
        copy_action = menu.addAction("📋 复制到...")
        copy_action.triggered.connect(lambda: self.copy_requested.emit(selected))
        menu.addSeparator()
        # 重命名（仅单个）
        if is_single:
            rename_action = menu.addAction("✏ 重命名")
            rename_action.triggered.connect(lambda: self._start_rename(row))
        # 删除
        delete_action = menu.addAction("🗑 删除")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(selected))
        menu.addSeparator()
        # 详情
        if is_single:
            detail_action = menu.addAction("ℹ 查看详情")
            detail_action.triggered.connect(lambda: self.file_selected.emit(file_info))

        menu.exec(event.globalPos())

    def _start_rename(self, row: int):
        if row < 0 or row >= len(self._files):
            return
        self._renaming_row = row
        file_info = self._files[row]
        index = self._model.index(row, COL_NAME)

        # 确保行高足够容纳编辑器
        self.resizeRowToContents(row)
        row_h = self.rowHeight(row)
        if row_h < 30:
            self.setRowHeight(row, 30)

        editor = QLineEdit(self)
        editor.setText(get_filename(file_info))
        editor.setMinimumHeight(28)
        editor.setStyleSheet("""
            QLineEdit {
                border: 2px solid #0066cc;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 14px;
                font-weight: normal;
                background: #ffffff;
                color: #1d1d1f;
                selection-background-color: #d6e4fd;
            }
        """)
        self.setIndexWidget(index, editor)
        # 让编辑器填满单元格
        editor.setGeometry(self.visualRect(index))
        editor.setFocus()
        editor.selectAll()
        editor.returnPressed.connect(lambda: self._finish_rename(row, editor.text()))
        editor.destroyed.connect(lambda: setattr(self, '_renaming_row', -1))

    def _finish_rename(self, row: int, new_name: str):
        # 防止 editingFinished 和 returnPressed 重复触发
        if getattr(self, '_renaming_row', -1) != row:
            return
        self._renaming_row = -1

        if not new_name or row >= len(self._files):
            # 安全移除编辑器
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.setIndexWidget(self._model.index(row, COL_NAME), None))
            return

        file_info = self._files[row]
        old_name = get_filename(file_info)
        if new_name == old_name:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.setIndexWidget(self._model.index(row, COL_NAME), None))
            return

        self.rename_requested.emit(file_info["path"], new_name)
        # 延迟移除编辑器，避免在 editingFinished 事件处理中删除 widget
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.setIndexWidget(self._model.index(row, COL_NAME), None))

    def load_more(self):
        if not self._loading:
            if self._is_search_mode:
                self._search_page += 1
                self.search_files(self._search_keyword, self._current_dir, self._search_page)
            else:
                self.load_directory(self._current_dir, append=True)

    def refresh(self):
        if self._is_search_mode:
            self._files.clear()
            self.search_files(self._search_keyword, self._current_dir)
        else:
            self.load_directory(self._current_dir)

    @property
    def has_more(self) -> bool:
        return len(self._files) % 100 == 0 and len(self._files) > 0

    @property
    def current_dir(self) -> str:
        return self._current_dir