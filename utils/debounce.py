from PySide6.QtCore import QTimer, QObject


class Debouncer(QObject):
    """防抖器：在指定延迟后执行回调，重复调用会重置计时器。"""

    def __init__(self, delay_ms: int = 300, parent=None):
        super().__init__(parent)
        self._delay_ms = delay_ms
        self._callback = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def set_callback(self, callback):
        self._callback = callback

    def trigger(self):
        """触发防抖，重置计时器。"""
        self._timer.start(self._delay_ms)

    def cancel(self):
        """取消当前等待中的触发。"""
        self._timer.stop()

    def _on_timeout(self):
        if self._callback:
            self._callback()