from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFrame, QMessageBox, QInputDialog,
    QTabWidget, QTabBar, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QEvent

from core.config import Config
from core.api import BaiduPanAPI
from ui.auth_widget import AuthWidget
from ui.file_pane import FilePane
from ui.search_bar import SearchBar
from ui.detail_panel import DetailPanel
from ui.progress_dialog import ProgressDialog
from ui.toast import show_toast
from utils.file_utils import format_size, get_filename


class _CreateFolderThread(QThread):
    finished = Signal(object)

    def __init__(self, api: BaiduPanAPI, path: str):
        super().__init__()
        self._api = api
        self._path = path

    def run(self):
        try:
            data = self._api.create_folder(self._path)
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit({"errno": -1, "errmsg": str(e)})


class _RenameThread(QThread):
    finished = Signal(dict)

    def __init__(self, api: BaiduPanAPI, path: str, newname: str):
        super().__init__()
        self._api = api
        self._path = path
        self._newname = newname

    def run(self):
        try:
            data = self._api.rename_file(self._path, self._newname)
            self.finished.emit(data)
        except Exception as e:
            self.finished.emit({"errno": -1, "errmsg": str(e)})


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._config = Config()
        self._api = BaiduPanAPI()
        self._toasts = []
        self._panes = []  # 所有 FilePane 实例
        self._split_mode = False  # 是否分屏模式
        self._init_window()
        self._check_auth()

    # ══════════════════════════════════════
    #  初始化
    # ══════════════════════════════════════

    def _init_window(self):
        self.setWindowTitle("百度网盘文件管理器")
        self.setMinimumSize(960, 600)
        w, h = self._config.get("window_size", [1400, 850])
        self.resize(w, h)

        self._central = QWidget()
        self.setCentralWidget(self._central)
        self._main_layout = QVBoxLayout(self._central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

    def _check_auth(self):
        if self._config.has_keys() and self._config.is_authorized():
            self._show_main_ui()
        else:
            self._show_auth_ui()

    def _show_auth_ui(self):
        self._clear_central()
        self._auth_widget = AuthWidget()
        self._auth_widget.auth_success.connect(self._on_auth_success)
        self._main_layout.addWidget(self._auth_widget)

    def _on_auth_success(self):
        self._show_main_ui()

    def _show_main_ui(self):
        self._clear_central()
        self._api = BaiduPanAPI()
        self._panes.clear()

        # ── 搜索栏 ──
        self._search_bar = SearchBar()
        self._search_bar.search_requested.connect(self._on_search)
        self._search_bar.filter_changed.connect(self._on_filter)
        self._search_bar.search_cleared.connect(self._on_search_cleared)
        self._main_layout.addWidget(self._search_bar)

        # ── 状态栏（必须在标签系统之前创建，因为 tab 变化信号会触发状态更新） ──
        self._status_label = QLabel("就绪")
        self.statusBar().addWidget(self._status_label, 1)

        # ── 标签栏 + 主内容区域 ──
        self._init_tab_system()

        # ── 详情面板 ──
        self._detail_panel = DetailPanel()
        self._detail_panel.setMinimumHeight(100)
        self._detail_panel.setMaximumHeight(220)
        self._detail_panel.setVisible(False)
        self._main_layout.addWidget(self._detail_panel)

        # ── 底部工具栏 ──
        self._init_toolbar()

        # ── 加载初始目录 ──
        last_dir = self._config.get("last_dir", "/")
        if self._panes:
            self._panes[0].load_directory(last_dir)
            self._update_tab_label(0, last_dir)

    # ══════════════════════════════════════
    #  标签系统
    # ══════════════════════════════════════

    def _init_tab_system(self):
        """初始化标签页系统。"""
        # 标签页容器
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.setDocumentMode(True)
        self._tab_widget.tabBar().setExpanding(False)
        self._tab_widget.tabBar().setElideMode(Qt.TextElideMode.ElideRight)

        # 自定义标签栏样式 — Apple 风格
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f5f5f7; }
            QTabBar::tab {
                background: transparent;
                color: #7a7a7a;
                border: none;
                border-radius: 6px 6px 0 0;
                padding: 6px 14px 6px 14px;
                margin-right: 2px;
                margin-top: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 80px;
                max-width: 180px;
                letter-spacing: -0.1px;
            }
            QTabBar::tab:hover { background: #f0f0f0; color: #1d1d1f; }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0066cc;
                font-weight: 600;
            }
            QTabBar::close-button {
                subcontrol-position: right;
                margin-left: 8px;
                margin-right: 2px;
            }
        """)

        # 添加 "+" 按钮到标签栏右侧
        self._btn_add_tab = QPushButton("+")
        self._btn_add_tab.setObjectName("tabBtn")
        self._btn_add_tab.setFixedSize(28, 28)
        self._btn_add_tab.setToolTip("新建标签页")
        self._btn_add_tab.clicked.connect(self._on_add_tab)
        self._tab_widget.setCornerWidget(self._btn_add_tab, Qt.Corner.TopRightCorner)

        # 分屏按钮
        self._btn_split = QPushButton("◫")
        self._btn_split.setObjectName("tabBtn")
        self._btn_split.setFixedSize(28, 28)
        self._btn_split.setToolTip("分屏浏览")
        self._btn_split.clicked.connect(self._on_toggle_split)

        # 把分屏按钮放到标签栏左侧
        self._tab_widget.setCornerWidget(self._btn_split, Qt.Corner.TopLeftCorner)

        # 主分屏器（支持左右双栏）
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setChildrenCollapsible(False)

        # 左侧：主标签页
        self._left_tab_widget = self._tab_widget

        # 右侧：分屏标签页（初始隐藏）
        self._right_tab_widget = QTabWidget()
        self._right_tab_widget.setTabsClosable(True)
        self._right_tab_widget.setMovable(True)
        self._right_tab_widget.tabCloseRequested.connect(self._on_right_tab_close)
        self._right_tab_widget.currentChanged.connect(self._on_right_tab_changed)
        self._right_tab_widget.setDocumentMode(True)
        self._right_tab_widget.tabBar().setExpanding(False)
        self._right_tab_widget.setVisible(False)
        self._right_tab_widget.setStyleSheet(self._tab_widget.styleSheet())

        self._right_panes = []

        self._main_splitter.addWidget(self._left_tab_widget)
        self._main_splitter.addWidget(self._right_tab_widget)

        self._main_layout.addWidget(self._main_splitter, 1)

        # 创建第一个标签页
        self._add_new_tab()

    def _add_new_tab(self, to_right: bool = False) -> FilePane:
        """创建新的 FilePane 标签页。"""
        pane = FilePane(self._api)
        pane.dir_changed.connect(lambda path, p=pane: self._on_pane_dir_changed(p, path))
        pane.file_selected.connect(self._on_file_selected)
        pane.file_opened.connect(self._on_file_opened)
        pane.rename_requested.connect(self._on_rename)
        pane.files_dropped_on_tree.connect(self._on_pane_drop_on_tree)
        pane.files_dropped_on_table.connect(self._on_pane_drop_on_table)
        pane.loading_started.connect(self._on_loading_started)
        pane.loading_finished.connect(self._on_loading_finished)
        pane.total_info_changed.connect(self._on_total_info_changed)
        pane.move_requested.connect(lambda files, p=pane: self._on_context_move(files))
        pane.copy_requested.connect(lambda files, p=pane: self._on_context_copy(files))
        pane.delete_requested.connect(lambda files, p=pane: self._on_context_delete(files))
        # 用事件过滤器可靠跟踪用户最后操作的 pane（checkbox 点击不会触发 clicked 信号）
        pane.file_table.installEventFilter(self)
        pane.dir_tree.installEventFilter(self)

        if to_right:
            self._right_panes.append(pane)
            pane.set_tree_visible(False)  # 分屏模式不显示目录树
            idx = self._right_tab_widget.addTab(pane, "新标签页")
            self._right_tab_widget.setCurrentIndex(idx)
            self._right_tab_widget.setVisible(True)
        else:
            self._panes.append(pane)
            idx = self._tab_widget.addTab(pane, "新标签页")
            self._tab_widget.setCurrentIndex(idx)

        return pane

    def _on_add_tab(self):
        self._add_new_tab()
        if self._panes:
            last_dir = self._config.get("last_dir", "/")
            self._panes[-1].load_directory(last_dir)

    def _on_tab_close(self, index: int):
        """关闭主标签页。"""
        if self._tab_widget.count() <= 1 and not self._right_tab_widget.isVisible():
            return  # 至少保留一个标签页
        pane = self._tab_widget.widget(index)
        if pane in self._panes:
            self._panes.remove(pane)
        self._tab_widget.removeTab(index)
        pane.deleteLater()

    def _on_right_tab_close(self, index: int):
        """关闭右侧分屏标签页。"""
        pane = self._right_tab_widget.widget(index)
        if pane in self._right_panes:
            self._right_panes.remove(pane)
        self._right_tab_widget.removeTab(index)
        pane.deleteLater()
        if self._right_tab_widget.count() == 0:
            self._right_tab_widget.setVisible(False)
            self._split_mode = False
            # 恢复所有左侧目录树
            for p in self._panes:
                p.set_tree_visible(True)

    def _on_tab_changed(self, index: int):
        if 0 <= index < len(self._panes):
            pane = self._panes[index]
            self._update_status_for_pane(pane)

    def _on_right_tab_changed(self, index: int):
        if 0 <= index < len(self._right_panes):
            pane = self._right_panes[index]
            self._update_status_for_pane(pane)

    def _on_toggle_split(self):
        """切换分屏模式 — 分屏时自动隐藏目录树以节省屏幕空间。"""
        if not self._split_mode:
            # 进入分屏：在右侧创建一个新标签页
            self._split_mode = True
            new_pane = self._add_new_tab(to_right=True)
            active = self._active_pane()
            if active:
                new_pane.load_directory(active.current_dir)
            # 自动隐藏所有目录树（左右分屏各半，宽度不够放树）
            total_width = self.width()
            self._main_splitter.setSizes([total_width // 2, total_width // 2])
            for pane in self._panes + self._right_panes:
                pane.set_tree_visible(False)
        else:
            # 退出分屏：恢复目录树
            self._split_mode = False
            while self._right_tab_widget.count() > 0:
                self._on_right_tab_close(0)
            self._right_tab_widget.setVisible(False)
            for pane in self._panes:
                pane.set_tree_visible(True)

    def _update_tab_label(self, index: int, dir_path: str, is_right: bool = False):
        """更新标签页标题为当前目录名。"""
        name = dir_path.rstrip("/").split("/")[-1] if dir_path != "/" else "根目录"
        if not name:
            name = "根目录"
        tab_widget = self._right_tab_widget if is_right else self._tab_widget
        if 0 <= index < tab_widget.count():
            tab_widget.setTabText(index, name)
            tab_widget.setTabToolTip(index, dir_path)

    def _on_pane_dir_changed(self, pane: FilePane, dir_path: str):
        """标签页目录变化时更新标签。"""
        # 更新对应标签标题
        if pane in self._panes:
            idx = self._panes.index(pane)
            self._update_tab_label(idx, dir_path, is_right=False)
        elif pane in self._right_panes:
            idx = self._right_panes.index(pane)
            self._update_tab_label(idx, dir_path, is_right=True)
        # 更新搜索栏状态
        if pane == self._active_pane():
            self._config.set("last_dir", dir_path)
            self._config.save()

    def _active_pane(self) -> FilePane | None:
        """获取用户最后操作的面板（优先检查焦点，回退到当前标签页）。"""
        # 优先：用户最后点击的文件表格或目录树所在的面板
        lp = getattr(self, '_last_focused_pane', None)
        if lp is not None and (lp in self._panes or lp in self._right_panes):
            return lp
        # 回退到右侧分屏
        if self._right_tab_widget.isVisible():
            idx = self._right_tab_widget.currentIndex()
            if 0 <= idx < len(self._right_panes):
                return self._right_panes[idx]
        # 回退到左侧标签页
        idx = self._tab_widget.currentIndex()
        if 0 <= idx < len(self._panes):
            return self._panes[idx]
        return None

    def eventFilter(self, obj, event):
        """事件过滤器：跟踪用户最后交互的面板（checkbox 点击等也能捕获）。"""
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn, QEvent.Type.KeyPress):
            for p in self._panes + self._right_panes:
                if obj is p.file_table or obj is p.dir_tree or obj is p.file_table.viewport() or obj is p.dir_tree.viewport():
                    self._last_focused_pane = p
                    break
        return super().eventFilter(obj, event)

    def _update_status_for_pane(self, pane: FilePane):
        """根据面板状态更新状态栏。"""
        total = len(pane.file_table.get_all_files())
        selected = len(pane.file_table.get_selected_files())
        total_size = sum(f.get("size", 0) for f in pane.file_table.get_all_files())
        self._status_label.setText(
            f"共 {total} 个文件 | 已选 {selected} 个 | 总大小 {format_size(total_size)}"
        )

    # ══════════════════════════════════════
    #  工具栏
    # ══════════════════════════════════════

    def _init_toolbar(self):
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(56)
        btn_layout = QHBoxLayout(toolbar)
        btn_layout.setContentsMargins(16, 12, 16, 12)
        btn_layout.setSpacing(8)

        new_btn = QPushButton("📁 新建文件夹")
        new_btn.setObjectName("secondaryBtn")
        new_btn.clicked.connect(self._on_new_folder)
        btn_layout.addWidget(new_btn)

        btn_layout.addStretch()

        move_btn = QPushButton("移动到...")
        move_btn.setObjectName("secondaryBtn")
        move_btn.clicked.connect(self._on_move)
        btn_layout.addWidget(move_btn)

        copy_btn = QPushButton("复制到...")
        copy_btn.setObjectName("secondaryBtn")
        copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(copy_btn)

        rename_btn = QPushButton("重命名")
        rename_btn.setObjectName("secondaryBtn")
        rename_btn.clicked.connect(self._on_rename_selected)
        btn_layout.addWidget(rename_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(delete_btn)

        self._main_layout.addWidget(toolbar)

    # ══════════════════════════════════════
    #  搜索 / 筛选
    # ══════════════════════════════════════

    def _on_search(self, keyword: str):
        pane = self._active_pane()
        if pane:
            pane.search_files(keyword)
        history = self._config.get("search_history", [])
        if keyword in history:
            history.remove(keyword)
        history.insert(0, keyword)
        self._config.set("search_history", history[:20])
        self._config.save()

    def _on_filter(self, category_id: int):
        pane = self._active_pane()
        if not pane:
            return
        if category_id == 0:
            pane.clear_search()
        else:
            pane.filter_by_category(category_id)

    def _on_search_cleared(self):
        pane = self._active_pane()
        if pane:
            pane.clear_search()

    # ══════════════════════════════════════
    #  选中 / 详情
    # ══════════════════════════════════════

    def _on_file_selected(self, file_info: dict):
        self._detail_panel.show_file(file_info)

    def _on_file_opened(self, file_info: dict):
        """文件被双击打开（通常是目录进入）。"""
        if file_info.get("isdir"):
            dir_path = file_info["path"]
            pane = self._active_pane()
            if pane:
                pane._dir_tree.navigate_to(dir_path)

    def _on_total_info_changed(self, total: int, selected: int, total_size_str: str):
        self._status_label.setText(
            f"共 {total} 个文件 | 已选 {selected} 个 | 总大小 {total_size_str}"
        )

    def _on_loading_started(self):
        self._status_label.setText("加载中...")

    def _on_loading_finished(self):
        pass

    # ══════════════════════════════════════
    #  拖放处理
    # ══════════════════════════════════════

    def _on_pane_drop_on_tree(self, target_dir: str, source_paths: list, action: int):
        """文件拖放到目录树节点。"""
        self._execute_drop_operation(source_paths, target_dir, action)

    def _on_pane_drop_on_table(self, target_dir: str, action: int):
        """文件拖放到表格区域。"""
        # 从最近产生 pending_drop 的面板获取源路径
        for pane in self._panes + self._right_panes:
            pd_info = pane.pending_drop
            if pd_info:
                source_paths, _, act = pd_info
                self._execute_drop_operation(source_paths, target_dir, act)
                pane.clear_pending_drop()
                break

    def _execute_drop_operation(self, source_paths: list, target_dir: str, action: int):
        """执行移动/复制操作。"""
        if not source_paths:
            return
        op_name = "移动" if action == 0 else "复制"
        op_type = "move" if action == 0 else "copy"
        dlg = ProgressDialog(self._api, op_type, source_paths, dest=target_dir, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete(op_name, s, f))
        dlg.start()
        dlg.exec()

    # ══════════════════════════════════════
    #  文件操作
    # ══════════════════════════════════════

    def _get_operation_files(self) -> list:
        """获取要操作的文件列表（选中行）。"""
        pane = self._active_pane()
        if not pane:
            return []
        return pane.get_selected_files()

    def _on_move(self):
        files = self._get_operation_files()
        if not files:
            show_toast(self, "请先选择要移动的文件", level="warning")
            return
        dest = self._show_dir_picker("选择移动目标目录")
        if not dest:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "move", file_paths, dest=dest, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("移动", s, f))
        dlg.start()
        dlg.exec()

    def _on_copy(self):
        files = self._get_operation_files()
        if not files:
            show_toast(self, "请先选择要复制的文件", level="warning")
            return
        dest = self._show_dir_picker("选择复制目标目录")
        if not dest:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "copy", file_paths, dest=dest, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("复制", s, f))
        dlg.start()
        dlg.exec()

    def _on_delete(self):
        files = self._get_operation_files()
        if not files:
            show_toast(self, "请先选择要删除的文件", level="warning")
            return
        names = "\n".join(f"  • {get_filename(f)}" for f in files[:10])
        if len(files) > 10:
            names += f"\n  ... 还有 {len(files) - 10} 个"
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除以下 {len(files)} 个文件？此操作不可撤销！\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "delete", file_paths, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("删除", s, f))
        dlg.start()
        dlg.exec()

    def _on_rename_selected(self):
        files = self._get_operation_files()
        if not files:
            show_toast(self, "请先选择要重命名的文件", level="warning")
            return
        if len(files) > 1:
            show_toast(self, "重命名一次只能操作一个文件", level="warning")
            return
        pane = self._active_pane()
        if not pane:
            return
        file_info = files[0]
        for i, f in enumerate(pane.file_table.get_all_files()):
            if f["path"] == file_info["path"]:
                pane.file_table._start_rename(i)
                break

    def _on_rename(self, path: str, newname: str):
        self._rename_thread = _RenameThread(self._api, path, newname)
        self._rename_thread.finished.connect(self._on_rename_finished)
        self._rename_thread.start()

    def _on_rename_finished(self, data: dict):
        errno = data.get("errno", -1)
        if errno == 0:
            show_toast(self, "重命名成功")
            pane = self._active_pane()
            if pane:
                pane.refresh()
        else:
            show_toast(self, f"重命名失败：{data.get('errmsg', '未知错误')}", level="error")

    def _on_new_folder(self):
        pane = self._active_pane()
        if not pane:
            return
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称：")
        if not ok or not name.strip():
            return
        current_dir = pane.current_dir
        folder_path = current_dir.rstrip("/") + "/" + name.strip()
        self._create_folder_thread = _CreateFolderThread(self._api, folder_path)
        self._create_folder_thread.finished.connect(self._on_create_folder_finished)
        self._create_folder_thread.start()

    def _on_create_folder_finished(self, data: dict):
        errno = data.get("errno", -1)
        if errno == 0:
            show_toast(self, "文件夹创建成功")
            pane = self._active_pane()
            if pane:
                pane.refresh()
        else:
            show_toast(self, f"创建失败：{data.get('errmsg', '未知错误')}", level="error")

    def _on_op_complete(self, op_name: str, success: int, fail: int):
        show_toast(self, f"{op_name}完成：成功 {success} 个，失败 {fail} 个")
        # 刷新所有面板
        for pane in self._panes + self._right_panes:
            try:
                pane.refresh()
            except Exception:
                pass

    # ══════════════════════════════════════
    #  右键菜单操作（接收文件列表直接操作）
    # ══════════════════════════════════════

    def _on_context_move(self, files: list):
        dest = self._show_dir_picker("选择移动目标目录")
        if not dest:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "move", file_paths, dest=dest, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("移动", s, f))
        dlg.start()
        dlg.exec()

    def _on_context_copy(self, files: list):
        dest = self._show_dir_picker("选择复制目标目录")
        if not dest:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "copy", file_paths, dest=dest, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("复制", s, f))
        dlg.start()
        dlg.exec()

    def _on_context_delete(self, files: list):
        names = "\n".join(f"  • {get_filename(f)}" for f in files[:10])
        if len(files) > 10:
            names += f"\n  ... 还有 {len(files) - 10} 个"
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除以下 {len(files)} 个文件？此操作不可撤销！\n\n{names}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        file_paths = [f["path"] for f in files]
        dlg = ProgressDialog(self._api, "delete", file_paths, parent=self)
        dlg.operation_complete.connect(lambda s, f, _: self._on_op_complete("删除", s, f))
        dlg.start()
        dlg.exec()

    # ══════════════════════════════════════
    #  目录选择器
    # ══════════════════════════════════════

    def _show_dir_picker(self, title: str) -> str:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTreeWidget
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setMinimumSize(420, 520)
        layout = QVBoxLayout(dlg)

        tree = QTreeWidget(dlg)
        tree.setHeaderLabel("选择目录")
        # 用字典跟踪已加载的目录路径，避免重复加载
        picker_loaded = set()
        tree.itemExpanded.connect(lambda item: self._load_picker_children(item, picker_loaded))
        layout.addWidget(tree, 1)

        root = QTreeWidgetItem(tree, ["📁 / 根目录"])
        root.setData(0, Qt.ItemDataRole.UserRole, "/")
        self._load_picker_children(root, picker_loaded)
        tree.expandItem(root)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            item = tree.currentItem()
            if item:
                return item.data(0, Qt.ItemDataRole.UserRole) or ""
        return ""

    def _load_picker_children(self, parent_item, loaded_set: set):
        """懒加载目录选择器的子目录。"""
        dir_path = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not dir_path or dir_path in loaded_set:
            return
        loaded_set.add(dir_path)

        parent_item.takeChildren()
        data = self._api.list_files(dir_path, order="name", desc=0, limit=500)
        if data.get("errno", 0) != 0:
            return
        for item in data.get("list", []):
            if item.get("isdir"):
                name = get_filename(item)
                child_path = item["path"]
                child = QTreeWidgetItem(parent_item, [f"📁 {name}"])
                child.setData(0, Qt.ItemDataRole.UserRole, child_path)
                QTreeWidgetItem(child, ["..."])

    # ══════════════════════════════════════
    #  杂项
    # ══════════════════════════════════════

    def _clear_central(self):
        while self._main_layout.count():
            item = self._main_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def closeEvent(self, event):
        size = self.size()
        self._config.set("window_size", [size.width(), size.height()])
        self._config.save()
        super().closeEvent(event)