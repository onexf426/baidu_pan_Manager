from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

from ui.styles import SUCCESS_COLOR, DANGER_COLOR, WARNING_COLOR


class Toast(QLabel):
    """浮动提示组件，自动在指定时间后消失。"""

    def __init__(self, text: str, parent=None, duration: int = 3000, level: str = "success"):
        super().__init__(parent)
        self.setText(text)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(360)
        self.setMinimumHeight(44)
        self.setMaximumHeight(120)
        self.adjustSize()

        # 样式
        color_map = {
            "success": SUCCESS_COLOR,
            "error": DANGER_COLOR,
            "warning": WARNING_COLOR,
        }
        bg_color = color_map.get(level, SUCCESS_COLOR)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        # 窗口标志：置顶、无边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # 透明度动画
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        # 定时消失
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._duration = duration

    def show_toast(self):
        """显示 toast 并开始计时。"""
        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.width() - self.width() - 20
            y = 20
            self.move(self.parent().mapToGlobal(self.parent().rect().topLeft()) if hasattr(self.parent(), 'mapToGlobal') else self.parent().pos())
            # Use global coordinates
            global_pos = self.parent().mapToGlobal(parent_rect.topLeft())
            self.move(global_pos.x() + x, global_pos.y() + y)
        self.show()
        self.raise_()
        self._timer.start(self._duration)

    def _fade_out(self):
        """淡出动画。"""
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._anim.finished.connect(self.close)
        self._anim.start()


def show_toast(parent, text: str, level: str = "success", duration: int = 3000):
    """便捷函数：在 parent 窗口上显示 toast。"""
    toast = Toast(text, parent=parent, duration=duration, level=level)
    toast.show_toast()
    # 保持引用防止被 GC
    if not hasattr(parent, '_toasts'):
        parent._toasts = []
    parent._toasts.append(toast)
    # 清理已关闭的 toast
    parent._toasts = [t for t in parent._toasts if t.isVisible()]
    return toast