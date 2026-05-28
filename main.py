import sys
import os
import ctypes


def is_frozen():
    """判断是否在 PyInstaller 打包后的 exe 中运行。"""
    return getattr(sys, 'frozen', False)


def get_app_dir():
    """获取应用根目录（打包后为 exe 所在目录，开发时为脚本所在目录）。"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """获取资源目录（打包后为 _MEIPASS 临时目录）。"""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# 确保项目根目录在 sys.path 中
APP_DIR = get_app_dir()
RESOURCE_DIR = get_resource_dir()
sys.path.insert(0, RESOURCE_DIR)


def main():
    # 设置 Windows 任务栏图标（让任务栏显示正确图标而非 Python 默认图标）
    if sys.platform == 'win32':
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BaiduPanManager.1.0")
        except Exception:
            pass

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt

    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("百度网盘文件管理器")
    app.setOrganizationName("BaiduPanManager")

    # 设置全局样式
    from ui.styles import get_stylesheet
    app.setStyleSheet(get_stylesheet())

    # 设置应用图标
    icon_path = os.path.join(RESOURCE_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 加载配置
    from core.config import Config
    config = Config()
    config.load()

    # 创建主窗口
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()