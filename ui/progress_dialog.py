from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QThread

from core.api import BaiduPanAPI, errmsg as api_errmsg

# 批量操作每组大小
BATCH_SIZE = 200
BATCH_INTERVAL = 1.0  # 秒
RATE_LIMIT_RETRY = 3
RATE_LIMIT_WAIT = 2.0  # 秒


class _BatchWorker(QThread):
    """后台执行批量操作。"""

    progress = Signal(int, int, str)   # (completed, total, message)
    finished = Signal(int, int, list)  # (success_count, fail_count, failures)
    cancelled = Signal()

    def __init__(self, api: BaiduPanAPI, opera: str, filelist: list, dest: str = ""):
        super().__init__()
        self._api = api
        self._opera = opera
        self._filelist = filelist
        self._dest = dest
        self._cancelled = False

    def run(self):
        import time

        total = len(self._filelist)
        success_count = 0
        fail_count = 0
        failures = []  # [(path, error_msg)]

        # 分批处理
        batches = [self._filelist[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

        for batch_idx, batch in enumerate(batches):
            if self._cancelled:
                self.cancelled.emit()
                return

            completed = batch_idx * BATCH_SIZE
            self.progress.emit(completed, total, f"正在处理 {completed}/{total}...")

            # 构造请求体
            if self._opera == "delete":
                req_list = batch  # ["/path/file", ...]
            elif self._opera in ("move", "copy"):
                # 不传空的 newname，否则百度 API 返回 errno=12
                req_list = [{"path": p, "dest": self._dest} for p in batch]
            else:
                req_list = batch

            # 带重试的请求
            for attempt in range(RATE_LIMIT_RETRY):
                try:
                    if self._opera == "move":
                        data = self._api.move_files(req_list)
                    elif self._opera == "copy":
                        data = self._api.copy_files(req_list)
                    elif self._opera == "delete":
                        data = self._api.delete_files(req_list)
                    else:
                        break

                    errno = data.get("errno", 0)
                    if errno == 31034:  # 频率限制
                        time.sleep(RATE_LIMIT_WAIT)
                        continue

                    if errno != 0:
                        # 顶层错误：整个批次失败
                        errmsg = data.get("errmsg") or api_errmsg(errno)
                        fail_count += len(batch)
                        for p in batch:
                            path = p if isinstance(p, str) else p.get("path", "?")
                            failures.append((path, errmsg))
                        break

                    # 统计每个文件的成功/失败
                    info_list = data.get("info", [])
                    if isinstance(info_list, list) and len(info_list) > 0:
                        for item in info_list:
                            item_errno = item.get("errno", 0)
                            if item_errno == 0:
                                success_count += 1
                            else:
                                fail_count += 1
                                msg = item.get("errmsg") or api_errmsg(item_errno)
                                failures.append((item.get("path", "?"), msg))
                    else:
                        success_count += len(batch)
                    break

                except Exception as e:
                    fail_count += len(batch)
                    failures.append(("", str(e)))
                    break

            # 批次间隔
            if batch_idx < len(batches) - 1:
                time.sleep(BATCH_INTERVAL)

        self.progress.emit(total, total, "操作完成")
        self.finished.emit(success_count, fail_count, failures)

    def cancel(self):
        self._cancelled = True


class ProgressDialog(QDialog):
    """批量操作进度对话框。"""

    operation_complete = Signal(int, int, list)  # (success, fail, failures)

    def __init__(self, api: BaiduPanAPI, opera: str, filelist: list,
                 dest: str = "", parent=None):
        super().__init__(parent)
        self._api = api
        self._opera = opera
        self._filelist = filelist
        self._dest = dest
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        opera_names = {
            "move": "移动",
            "copy": "复制",
            "delete": "删除",
        }
        op_name = opera_names.get(self._opera, self._opera)
        total = len(self._filelist)

        self.setWindowTitle(f"{op_name}文件")
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel(f"正在{op_name} {total} 个文件...")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # 状态文字
        self._status_label = QLabel("准备中...")
        self._status_label.setObjectName("hintLabel")
        layout.addWidget(self._status_label)

        # 结果区域（初始隐藏）
        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setMaximumHeight(120)
        self._result_text.setVisible(False)
        layout.addWidget(self._result_text)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("secondaryBtn")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        self._close_btn.setVisible(False)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

    def start(self):
        """启动批量操作。"""
        self._worker = _BatchWorker(self._api, self._opera, self._filelist, self._dest)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_progress(self, completed: int, total: int, message: str):
        self._progress_bar.setValue(completed)
        self._status_label.setText(message)

    def _on_finished(self, success: int, fail: int, failures: list):
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._cancel_btn.setVisible(False)
        self._close_btn.setVisible(True)

        op_name = {"move": "移动", "copy": "复制", "delete": "删除"}.get(self._opera, self._opera)

        if fail == 0:
            self._status_label.setText(f"✅ 全部 {success} 个文件{op_name}成功")
        else:
            self._status_label.setText(f"成功 {success} 个，失败 {fail} 个")
            if failures:
                self._result_text.setVisible(True)
                lines = [f"• {path or '?'}：{msg}" for path, msg in failures[:20]]
                if len(failures) > 20:
                    lines.append(f"... 还有 {len(failures) - 20} 个失败")
                self._result_text.setPlainText("\n".join(lines))

        self.operation_complete.emit(success, fail, failures)

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
        self._status_label.setText("正在取消...")

    def _on_cancelled(self):
        self._progress_bar.setValue(0)
        self._status_label.setText("操作已取消")
        self._cancel_btn.setVisible(False)
        self._close_btn.setVisible(True)