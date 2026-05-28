import os
from datetime import datetime


def format_size(size_bytes: int) -> str:
    """将字节大小格式化为可读字符串。"""
    if size_bytes < 0:
        return "未知"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024**2:.1f} MB"
    return f"{size_bytes / 1024**3:.2f} GB"


def format_time(timestamp: int) -> str:
    """将 Unix 时间戳格式化为可读字符串。"""
    if not timestamp:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return ""


def get_filename(file_info: dict) -> str:
    """从文件信息字典中安全获取文件名，兼容新旧版 API。"""
    return file_info.get("filename") or file_info.get("server_filename", "")


# 文件扩展名到类型的映射
_CATEGORY_MAP = {
    1: "文档",
    2: "图片",
    3: "视频",
    4: "音乐",
    5: "压缩包",
    6: "其他",
}

_EXT_TYPE_MAP = {
    # 文档
    ".doc": "文档", ".docx": "文档", ".xls": "文档", ".xlsx": "文档",
    ".ppt": "文档", ".pptx": "文档", ".pdf": "文档", ".txt": "文档",
    ".csv": "文档", ".md": "文档", ".rtf": "文档",
    # 图片
    ".jpg": "图片", ".jpeg": "图片", ".png": "图片", ".gif": "图片",
    ".bmp": "图片", ".svg": "图片", ".webp": "图片", ".ico": "图片",
    ".tiff": "图片", ".psd": "图片",
    # 视频
    ".mp4": "视频", ".avi": "视频", ".mkv": "视频", ".mov": "视频",
    ".wmv": "视频", ".flv": "视频", ".rmvb": "视频", ".rm": "视频",
    ".ts": "视频", ".m4v": "视频",
    # 音乐
    ".mp3": "音乐", ".flac": "音乐", ".wav": "音乐", ".aac": "音乐",
    ".ogg": "音乐", ".wma": "音乐", ".m4a": "音乐", ".ape": "音乐",
    # 压缩包
    ".zip": "压缩包", ".rar": "压缩包", ".7z": "压缩包", ".tar": "压缩包",
    ".gz": "压缩包", ".bz2": "压缩包", ".xz": "压缩包",
}


def get_file_type(filename: str, category_id: int = 0) -> str:
    """根据文件名扩展名和百度分类 ID 返回类型名称。"""
    if category_id and category_id in _CATEGORY_MAP:
        return _CATEGORY_MAP[category_id]
    ext = os.path.splitext(filename)[1].lower()
    return _EXT_TYPE_MAP.get(ext, "其他")


def get_file_icon_name(filename: str, is_dir: bool) -> str:
    """返回文件图标标识（供 UI 层使用）。"""
    if is_dir:
        return "folder"
    ext = os.path.splitext(filename)[1].lower()
    icon_map = {
        ".doc": "word", ".docx": "word",
        ".xls": "excel", ".xlsx": "excel",
        ".ppt": "powerpoint", ".pptx": "powerpoint",
        ".pdf": "pdf", ".txt": "text", ".md": "text",
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image",
        ".bmp": "image", ".svg": "image", ".webp": "image",
        ".mp4": "video", ".avi": "video", ".mkv": "video", ".mov": "video",
        ".mp3": "audio", ".flac": "audio", ".wav": "audio",
        ".zip": "archive", ".rar": "archive", ".7z": "archive",
    }
    return icon_map.get(ext, "file")