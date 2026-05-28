"""自包含的文件浏览面板，可复用于标签页和分屏视图中。"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread

from core.api import BaiduPanAPI
from ui.dir_tree import DirTree
from ui.file_table import FileTableView


class FilePane(QWidget):
    """一个完整的文件浏览面板：导航栏 + 目录树 + 文件表格。"""

    dir_changed = Signal(str)                    # 导航到新目录
    file_selected = Signal(dict)                 # 文件被选中（用于详情面板）
    file_opened = Signal(dict)                   # 文件被打开（目录进入）
    status_message = Signal(str)                 # 状态栏消息
    files_dropped_on_tree = Signal(str, list, int)  # 拖放到目录树
    files_dropped_on_table = Signal(str, int)      # 拖放到文件表格区域
    rename_requested = Signal(str, str)           # 重命名请求
    move_requested = Signal(list)                 # 右键/工具栏：移动
    copy_requested = Signal(list)                 # 右键/工具栏：复制
    delete_requested = Signal(list)               # 右键/工具栏：删除
    loading_started = Signal()
    loading_finished = Signal()
    total_info_changed = Signal(int, int, str)

    def __init__(self, api: BaiduPanAPI, parent=None):
        super().__init__(parent)
        self._api = api
        self._current_dir = "/"
        self._nav_history = []
        self._nav_index = -1
        self._nav_updating = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 导航栏 ──
        self._nav_bar = self._create_nav_bar()
        layout.addWidget(self._nav_bar)

        # ── 主分割器：目录树 + 文件表格 ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)

        # 左侧目录树
        self._dir_tree = DirTree(self._api)
        self._dir_tree.setMinimumWidth(140)
        self._dir_tree.setMaximumWidth(350)
        self._splitter.addWidget(self._dir_tree)

        # 右侧文件表格
        self._file_table = FileTableView(self._api)
        self._splitter.addWidget(self._file_table)

        self._splitter.setSizes([200, 600])
        layout.addWidget(self._splitter, 1)

    def _create_nav_bar(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("navBar")
        nav.setFixedHeight(36)
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(6, 4, 6, 4)
        nav_layout.setSpacing(4)

        self._btn_back = QPushButton("◀")
        self._btn_back.setObjectName("smallBtn")
        self._btn_back.setFixedSize(28, 28)
        self._btn_back.setToolTip("后退")
        self._btn_back.clicked.connect(self._on_nav_back)
        self._btn_back.setEnabled(False)
        nav_layout.addWidget(self._btn_back)

        self._btn_forward = QPushButton("▶")
        self._btn_forward.setObjectName("smallBtn")
        self._btn_forward.setFixedSize(28, 28)
        self._btn_forward.setToolTip("前进")
        self._btn_forward.clicked.connect(self._on_nav_forward)
        self._btn_forward.setEnabled(False)
        nav_layout.addWidget(self._btn_forward)

        self._btn_up = QPushButton("⬆")
        self._btn_up.setObjectName("smallBtn")
        self._btn_up.setFixedSize(28, 28)
        self._btn_up.setToolTip("上一级")
        self._btn_up.clicked.connect(self._on_nav_up)
        self._btn_up.setEnabled(False)
        nav_layout.addWidget(self._btn_up)

        # 路径标签
        self._path_label = QLabel("/")
        self._path_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 13px;
                padding: 0 8px;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }
        """)
        self._path_label.setCursor(Qt.CursorShape.IBeamCursor)
        self._path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        nav_layout.addWidget(self._path_label, 1)

        self._btn_refresh = QPushButton("🔄")
        self._btn_refresh.setObjectName("smallBtn")
        self._btn_refresh.setFixedSize(28, 28)
        self._btn_refresh.setToolTip("刷新")
        self._btn_refresh.clicked.connect(self.refresh)
        nav_layout.addWidget(self._btn_refresh)

        return nav

    def _connect_signals(self):
        self._dir_tree.dir_selected.connect(self._on_dir_tree_selected)
        self._dir_tree.files_dropped_on_dir.connect(self._on_dir_tree_drop)
        self._file_table.file_selected.connect(self.file_selected)
        self._file_table.file_opened.connect(self._on_file_table_opened)
        self._file_table.files_dropped.connect(self._on_file_table_drop)
        self._file_table.rename_requested.connect(self.rename_requested)
        self._file_table.move_requested.connect(self.move_requested)
        self._file_table.copy_requested.connect(self.copy_requested)
        self._file_table.delete_requested.connect(self.delete_requested)
        self._file_table.loading_started.connect(self.loading_started)
        self._file_table.loading_finished.connect(self.loading_finished)
        self._file_table.total_info_changed.connect(self.total_info_changed)

        # 滚动加载
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._check_scroll_load)
        self._file_table.verticalScrollBar().valueChanged.connect(
            lambda: self._scroll_timer.start(200)
        )

    # ── 导航 ──

    def load_directory(self, dir_path: str):
        self._current_dir = dir_path
        self._file_table.load_directory(dir_path)
        self._record_navigation(dir_path)
        self._update_nav_state(dir_path)
        self.dir_changed.emit(dir_path)

    def _on_dir_tree_selected(self, dir_path: str):
        self.load_directory(dir_path)

    def _on_file_table_opened(self, file_info: dict):
        if file_info.get("isdir"):
            dir_path = file_info["path"]
            self.load_directory(dir_path)
            self._dir_tree.navigate_to(dir_path)

    def _record_navigation(self, dir_path: str):
        if self._nav_updating:
            return
        if self._nav_index < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[:self._nav_index + 1]
        if not self._nav_history or self._nav_history[-1] != dir_path:
            self._nav_history.append(dir_path)
            self._nav_index = len(self._nav_history) - 1

    def _update_nav_state(self, dir_path: str):
        self._path_label.setText(dir_path)
        self._btn_back.setEnabled(self._nav_index > 0)
        self._btn_forward.setEnabled(self._nav_index < len(self._nav_history) - 1)
        parent = self._get_parent_path(dir_path)
        self._btn_up.setEnabled(parent is not None)

    def _get_parent_path(self, dir_path: str):
        if not dir_path or dir_path == "/":
            return None
        parts = dir_path.rstrip("/").split("/")
        if len(parts) <= 1:
            return "/"
        return "/".join(parts[:-1]) or "/"

    def _on_nav_back(self):
        if self._nav_index <= 0:
            return
        self._nav_index -= 1
        prev = self._nav_history[self._nav_index]
        self._nav_updating = True
        self.load_directory(prev)
        self._nav_updating = False
        try:
            self._dir_tree.navigate_to(prev)
        except RuntimeError:
            pass

    def _on_nav_forward(self):
        if self._nav_index >= len(self._nav_history) - 1:
            return
        self._nav_index += 1
        nxt = self._nav_history[self._nav_index]
        self._nav_updating = True
        self.load_directory(nxt)
        self._nav_updating = False
        try:
            self._dir_tree.navigate_to(nxt)
        except RuntimeError:
            pass

    def _on_nav_up(self):
        parent = self._get_parent_path(self._current_dir)
        if parent is None:
            return
        self.load_directory(parent)
        try:
            self._dir_tree.navigate_to(parent)
        except RuntimeError:
            pass

    # ── 拖放处理 ──

    def _on_dir_tree_drop(self, target_dir: str, source_paths: list, action: int):
        self.files_dropped_on_tree.emit(target_dir, source_paths, action)

    def _on_file_table_drop(self, target_dir: str, action: int):
        self.files_dropped_on_table.emit(target_dir, action)

    @property
    def pending_drop(self):
        return self._file_table.pending_drop

    def clear_pending_drop(self):
        self._file_table.clear_pending_drop()

    # ── 滚动加载 ──

    def _check_scroll_load(self):
        vbar = self._file_table.verticalScrollBar()
        if vbar.value() >= vbar.maximum() - 50 and self._file_table.has_more:
            self._file_table.load_more()

    # ── 公开接口 ──

    def refresh(self):
        self._file_table.refresh()
        self._dir_tree.refresh("/")

    def set_tree_visible(self, visible: bool):
        """显示/隐藏目录树 — 分屏时自动隐藏以节省空间。"""
        self._tree_visible = visible
        self._dir_tree.setVisible(visible)

    def is_tree_visible(self) -> bool:
        return getattr(self, '_tree_visible', True)

    def get_selected_files(self) -> list:
        return self._file_table.get_selected_files()

    def search_files(self, keyword: str):
        self._file_table.search_files(keyword)

    def clear_search(self):
        self._file_table.load_directory(self._current_dir)

    def filter_by_category(self, category_id: int):
        class _FilterThread(QThread):
            finished = Signal(dict)
            def __init__(self, api, cat_id):
                super().__init__()
                self._api = api
                self._cat_id = cat_id
            def run(self):
                try:
                    self.finished.emit(self._api.list_by_category(self._cat_id))
                except Exception:
                    self.finished.emit({"list": []})

        self._filter_thread = _FilterThread(self._api, category_id)
        self._filter_thread.finished.connect(self._on_filter_finished)
        self._filter_thread.start()

    def _on_filter_finished(self, data: dict):
        self._file_table._files = data.get("list", [])
        self._file_table._is_search_mode = True
        self._file_table._refresh_model()

    @property
    def file_table(self) -> FileTableView:
        return self._file_table

    @property
    def dir_tree(self) -> DirTree:
        return self._dir_tree

    @property
    def current_dir(self) -> str:
        return self._current_dir

    @property
    def splitter(self) -> QSplitter:
        return self._splitter