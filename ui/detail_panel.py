from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal

from utils.file_utils import format_size, format_time, get_filename


class DetailPanel(QWidget):
    """文件详情面板，显示在右侧或底部。"""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.setVisible(False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("文件详情")
        title.setObjectName("subtitleLabel")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setObjectName("secondaryBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self._on_close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #E0E4E8;")
        layout.addWidget(line)

        # 详情字段
        self._fields = {}
        field_labels = [
            ("filename", "文件名"),
            ("path", "完整路径"),
            ("size", "文件大小"),
            ("type", "文件类型"),
            ("mtime", "修改时间"),
            ("md5", "MD5"),
        ]

        for key, label_text in field_labels:
            row = QHBoxLayout()
            row.setSpacing(8)

            label = QLabel(f"{label_text}：")
            label.setFixedWidth(70)
            label.setStyleSheet("color: #666666; font-size: 12px;")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

            value = QLabel("")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setStyleSheet("color: #333333; font-size: 13px;")

            row.addWidget(label)
            row.addWidget(value, 1)
            layout.addLayout(row)

            self._fields[key] = value

        layout.addStretch()

    def show_file(self, file_info: dict):
        """显示文件详情。file_info 包含 filename, path, size, isdir, mtime, md5 等字段。"""
        self._fields["filename"].setText(get_filename(file_info))
        self._fields["path"].setText(file_info.get("path", ""))

        size = file_info.get("size", 0)
        self._fields["size"].setText(format_size(size) if size else "—")

        is_dir = file_info.get("isdir", 0)
        file_type = "文件夹" if is_dir else file_info.get("type", "文件")
        self._fields["type"].setText(file_type)

        mtime = file_info.get("mtime", 0)
        self._fields["mtime"].setText(format_time(mtime) if mtime else "—")

        md5 = file_info.get("md5", "")
        self._fields["md5"].setText(md5 if md5 else "—")

        self.setVisible(True)

    def _on_close(self):
        self.setVisible(False)
        self.closed.emit()