import json
import os
import sys
import time
from pathlib import Path


def _get_config_dir() -> Path:
    """获取配置目录，优先用 APPDATA，回退到 exe 同目录。"""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "baidu-pan-manager"
    # 回退：exe 同目录下的 config 文件夹
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable)) / "config"
    return Path(os.path.expanduser("~")) / "baidu-pan-manager"


CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT_CONFIG = {
    "app_key": "",
    "secret_key": "",
    "access_token": "",
    "refresh_token": "",
    "token_expires_at": 0,
    "theme": "light",
    "last_dir": "/",
    "search_history": [],
    "window_size": [1200, 800],
    "column_widths": [300, 100, 80, 150, 100],
    "sort_column": "time",
    "sort_order": "desc",
    "callback_port": 8080,
}


class Config:
    """应用配置管理器，单例模式。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._loaded = False
        return cls._instance

    def load(self) -> dict:
        """加载配置文件，不存在则创建默认配置。"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = dict(_DEFAULT_CONFIG)
        else:
            self._data = dict(_DEFAULT_CONFIG)
        # 补充缺失的默认字段
        for key, val in _DEFAULT_CONFIG.items():
            if key not in self._data:
                self._data[key] = val
        self._loaded = True
        return self._data

    def save(self):
        """将当前配置写入文件。"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        if not self._loaded:
            self.load()
        return self._data.get(key, default)

    def set(self, key: str, value):
        if not self._loaded:
            self.load()
        self._data[key] = value

    def is_authorized(self) -> bool:
        """检查是否已完成授权（有有效的 token）。"""
        return bool(self.get("access_token")) and bool(self.get("refresh_token"))

    def is_token_expired(self) -> bool:
        """检查 token 是否即将过期（提前 5 分钟）。"""
        expires_at = self.get("token_expires_at", 0)
        return time.time() >= expires_at - 300

    def has_keys(self) -> bool:
        """检查是否已配置 AppKey 和 SecretKey。"""
        return bool(self.get("app_key")) and bool(self.get("secret_key"))

    @property
    def data(self) -> dict:
        if not self._loaded:
            self.load()
        return self._data