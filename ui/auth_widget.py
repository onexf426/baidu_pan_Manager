import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QApplication, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer

from core.config import Config
from core.auth import get_auth_url, exchange_code_for_token, save_auth_result
from ui.toast import show_toast


class _ExchangeThread(QThread):
    """后台线程：用授权码换取 token。"""
    success = Signal(dict)
    error = Signal(str)

    def __init__(self, app_key: str, secret_key: str, code: str):
        super().__init__()
        self._app_key = app_key
        self._secret_key = secret_key
        self._code = code

    def run(self):
        try:
            result = exchange_code_for_token(self._app_key, self._secret_key, self._code)
            save_auth_result(result)
            self.success.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AuthWidget(QWidget):
    """API Key 配置 + 手动授权页面。"""

    auth_success = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config()
        self._exchange_thread = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(80, 30, 80, 30)

        # ── 标题 ──
        title = QLabel("百度网盘 API 配置")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── 步骤说明 ──
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setPlainText(
            "获取 API Key 步骤：\n"
            "1. 打开 https://pan.baidu.com/union/home\n"
            "2. 用百度账号登录，点击「申请接入」→ 创建应用\n"
            "3. 应用名随便填，类型选「软件」\n"
            "4. 在「应用详情」获取 AppKey 和 SecretKey"
        )
        instructions.setFixedHeight(110)
        layout.addWidget(instructions)

        # ── Key 输入框 ──
        key_frame = QFrame()
        key_frame.setStyleSheet("QFrame { background: white; border-radius: 8px; padding: 12px; }")
        key_layout = QVBoxLayout(key_frame)
        key_layout.setSpacing(8)

        # AppKey
        row1 = QHBoxLayout()
        lbl1 = QLabel("AppKey：")
        lbl1.setFixedWidth(80)
        self._app_key_input = QLineEdit()
        self._app_key_input.setPlaceholderText("请输入 AppKey")
        self._app_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._app_key_toggle = QPushButton("显示")
        self._app_key_toggle.setObjectName("eyeBtn")
        self._app_key_toggle.setFixedWidth(40)
        self._app_key_toggle.clicked.connect(
            lambda: self._toggle_echo(self._app_key_input, self._app_key_toggle)
        )
        row1.addWidget(lbl1)
        row1.addWidget(self._app_key_input, 1)
        row1.addWidget(self._app_key_toggle)
        key_layout.addLayout(row1)

        # SecretKey
        row2 = QHBoxLayout()
        lbl2 = QLabel("SecretKey：")
        lbl2.setFixedWidth(80)
        self._secret_key_input = QLineEdit()
        self._secret_key_input.setPlaceholderText("请输入 SecretKey")
        self._secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret_key_toggle = QPushButton("显示")
        self._secret_key_toggle.setObjectName("eyeBtn")
        self._secret_key_toggle.setFixedWidth(36)
        self._secret_key_toggle.clicked.connect(
            lambda: self._toggle_echo(self._secret_key_input, self._secret_key_toggle)
        )
        row2.addWidget(lbl2)
        row2.addWidget(self._secret_key_input, 1)
        row2.addWidget(self._secret_key_toggle)
        key_layout.addLayout(row2)

        layout.addWidget(key_frame)

        # ── 授权操作区域 ──
        self._auth_frame = QFrame()
        self._auth_frame.setStyleSheet(
            "QFrame { background: #F0F5FF; border: 1px solid #D6E4FD; border-radius: 10px; padding: 16px; }"
        )
        auth_layout = QVBoxLayout(self._auth_frame)
        auth_layout.setSpacing(12)

        # 步骤 1：打开授权页面
        step1_label = QLabel("① 点击下方按钮，在浏览器中完成百度授权")
        step1_label.setStyleSheet("font-size: 13px; color: #333; background: transparent; font-weight: 600;")
        auth_layout.addWidget(step1_label)

        self._open_btn = QPushButton("打开授权页面")
        self._open_btn.setFixedWidth(180)
        self._open_btn.clicked.connect(self._on_open_auth_page)
        open_row = QHBoxLayout()
        open_row.addWidget(self._open_btn)
        open_row.addStretch()
        auth_layout.addLayout(open_row)

        # 步骤 2：粘贴授权码
        step2_label = QLabel("② 授权完成后，浏览器会显示授权码，将其粘贴到下方：")
        step2_label.setStyleSheet("font-size: 13px; color: #333; background: transparent; font-weight: 600; padding-top: 6px;")
        auth_layout.addWidget(step2_label)

        code_row = QHBoxLayout()
        code_row.setSpacing(8)
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("粘贴授权码（Authorization Code）")
        self._code_input.setMinimumWidth(200)
        code_row.addWidget(self._code_input, 1)

        self._submit_btn = QPushButton("完成授权")
        self._submit_btn.setFixedWidth(100)
        self._submit_btn.clicked.connect(self._on_submit_code)
        code_row.addWidget(self._submit_btn)
        auth_layout.addLayout(code_row)

        # 提示
        hint = QLabel("提示：授权后浏览器会跳转到一个新页面，页面上会直接显示授权码。")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        auth_layout.addWidget(hint)

        layout.addWidget(self._auth_frame)

        # ── 状态提示 ──
        self._status_label = QLabel("")
        self._status_label.setObjectName("hintLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        layout.addStretch()

        # 加载已保存的 Key
        self._load_saved_config()

    def _load_saved_config(self):
        app_key = self._config.get("app_key", "")
        secret_key = self._config.get("secret_key", "")
        if app_key:
            self._app_key_input.setText(app_key)
        if secret_key:
            self._secret_key_input.setText(secret_key)

    def _toggle_echo(self, line_edit: QLineEdit, btn: QPushButton):
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("隐藏")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("显示")

    def _on_open_auth_page(self):
        app_key = self._app_key_input.text().strip()
        if not app_key:
            show_toast(self, "请先填写 AppKey", level="warning")
            return
        # 保存 key
        self._config.set("app_key", app_key)
        self._config.set("secret_key", self._secret_key_input.text().strip())
        self._config.save()
        # 打开浏览器
        url = get_auth_url(app_key)
        webbrowser.open(url)
        self._status_label.setText("已在浏览器中打开授权页面，请完成授权后将授权码粘贴到下方。")
        self._code_input.setFocus()

    def _on_submit_code(self):
        app_key = self._app_key_input.text().strip()
        secret_key = self._secret_key_input.text().strip()
        code = self._code_input.text().strip()

        if not app_key or not secret_key:
            show_toast(self, "请填写 AppKey 和 SecretKey", level="warning")
            return
        if not code:
            show_toast(self, "请输入授权码", level="warning")
            return

        # 保存 key
        self._config.set("app_key", app_key)
        self._config.set("secret_key", secret_key)
        self._config.save()

        # 禁用按钮
        self._submit_btn.setEnabled(False)
        self._submit_btn.setText("授权中...")
        self._status_label.setText("正在验证授权码...")

        # 后台换取 token
        self._exchange_thread = _ExchangeThread(app_key, secret_key, code)
        self._exchange_thread.success.connect(self._on_success)
        self._exchange_thread.error.connect(self._on_error)
        self._exchange_thread.start()

    def _on_success(self, result: dict):
        self._submit_btn.setEnabled(True)
        self._submit_btn.setText("完成授权")
        self._status_label.setText("")
        show_toast(self, "授权成功！", level="success")
        self._config.set("last_dir", "/")
        self._config.save()
        QTimer.singleShot(800, self.auth_success.emit)

    def _on_error(self, error_msg: str):
        self._submit_btn.setEnabled(True)
        self._submit_btn.setText("完成授权")
        self._status_label.setText(f"❌ {error_msg}")
        show_toast(self, error_msg, level="error", duration=5000)