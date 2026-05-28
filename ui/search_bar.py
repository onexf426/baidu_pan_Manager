from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel
)
from PySide6.QtCore import Signal, Qt

from utils.debounce import Debouncer


class SearchBar(QWidget):
    """搜索栏组件：搜索框 + 筛选下拉框。"""

    search_requested = Signal(str)          # 搜索关键词
    filter_changed = Signal(int)            # 分类 ID（0=全部）
    search_cleared = Signal()               # 清空搜索

    # 筛选选项：(显示文字, category_id)
    FILTER_OPTIONS = [
        ("全部", 0),
        ("文档", 1),
        ("图片", 2),
        ("视频", 3),
        ("音乐", 4),
        ("压缩包", 5),
        ("其他", 6),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._debouncer = Debouncer(delay_ms=300, parent=self)
        self._debouncer.set_callback(self._do_search)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 搜索标签
        search_icon = QLabel("搜索:")
        search_icon.setStyleSheet("background: transparent; font-size: 13px; color: #666;")
        layout.addWidget(search_icon)

        # 搜索输入框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索网盘文件...")
        self._search_input.setMinimumWidth(200)
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._on_enter_pressed)
        layout.addWidget(self._search_input, 1)

        # 清除按钮
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("secondaryBtn")
        self._clear_btn.setFixedSize(32, 32)
        self._clear_btn.setToolTip("清除搜索")
        self._clear_btn.clicked.connect(self._on_clear)
        self._clear_btn.setVisible(False)
        layout.addWidget(self._clear_btn)

        # 搜索按钮
        self._search_btn = QPushButton("搜索")
        self._search_btn.setFixedSize(64, 36)
        self._search_btn.clicked.connect(self._do_search)
        layout.addWidget(self._search_btn)

        # 筛选下拉框
        self._filter_combo = QComboBox()
        self._filter_combo.setFixedWidth(100)
        for label, _ in self.FILTER_OPTIONS:
            self._filter_combo.addItem(label)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_combo)

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        if text:
            self._debouncer.trigger()
        else:
            self._debouncer.cancel()
            self.search_cleared.emit()

    def _on_enter_pressed(self):
        self._debouncer.cancel()
        self._do_search()

    def _on_clear(self):
        self._search_input.clear()
        self._clear_btn.setVisible(False)
        self.search_cleared.emit()

    def _do_search(self):
        keyword = self._search_input.text().strip()
        if keyword:
            self.search_requested.emit(keyword)

    def _on_filter_changed(self, index: int):
        _, category_id = self.FILTER_OPTIONS[index]
        self.filter_changed.emit(category_id)

    def get_keyword(self) -> str:
        return self._search_input.text().strip()

    def get_filter_category(self) -> int:
        return self.FILTER_OPTIONS[self._filter_combo.currentIndex()][1]

    def set_keyword(self, keyword: str):
        self._search_input.setText(keyword)