import json
import time
import requests
from core.config import Config
from core.token_manager import TokenManager, TokenExpiredError


# 错误码常量
ERR_PARAM = -6
ERR_TOKEN_INVALID = -10
ERR_UNAUTHORIZED = -11
ERR_RATE_LIMIT = 31034
ERR_FILE_EXISTS = 31061
ERR_MOVE_LIMIT = 31062
ERR_FILE_NOT_FOUND = 31066

# 错误码 → 人类可读消息
ERR_MESSAGES = {
    -6: "参数错误",
    -8: "文件路径无效或文件不存在",
    -10: "Token 已失效，请重新授权",
    -11: "未授权，请检查 AppKey/SecretKey",
    12: "操作失败：目标位置可能已有同名文件",
    31034: "请求频率过高，请稍后重试",
    31061: "文件已存在",
    31062: "移动次数超限（普通用户每日限制）",
    31066: "文件不存在",
    31175: "文件名包含非法字符",
    31200: "文件大小超限",
    42211: "文件已被锁定或正在使用",
}

def errmsg(code) -> str:
    """将错误码转为人类可读消息。"""
    if code in ERR_MESSAGES:
        return ERR_MESSAGES[code]
    return f"未知错误 (errno={code})"


class BaiduPanAPI:
    """百度网盘 API 封装。"""

    BASE_URL = "https://pan.baidu.com/rest/2.0/xpan/file"
    NAS_URL = "https://pan.baidu.com/rest/2.0/xpan/nas"
    QUOTA_URL = "https://pan.baidu.com/api/quota"

    def __init__(self):
        self._config = Config()
        self._token_mgr = TokenManager()

    def _headers(self) -> dict:
        return {}

    def _inject_token(self, params: dict) -> dict:
        """将 access_token 注入请求参数。"""
        token = self._token_mgr.get_valid_token()
        params = dict(params) if params else {}
        params["access_token"] = token
        return params

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """发起请求，自动处理 token 注入和刷新重试。"""
        kwargs.setdefault("timeout", 15)
        kwargs.setdefault("headers", {})

        # 将 access_token 注入到 params 中
        if "params" in kwargs:
            kwargs["params"] = self._inject_token(kwargs["params"])
        else:
            kwargs["params"] = self._inject_token({})

        def do_request():
            return requests.request(method, url, **kwargs)

        resp = self._token_mgr.refresh_and_retry(do_request)
        return resp.json() if resp.content else {}

    def _request_with_retry(self, method: str, url: str, max_retries: int = 3, **kwargs) -> dict:
        """发起请求，自动处理频率限制重试。"""
        for attempt in range(max_retries):
            data = self._request(method, url, **kwargs)
            errno = data.get("errno", 0)
            if errno == ERR_RATE_LIMIT:
                time.sleep(2)
                continue
            return data
        return data  # 最后一次的结果

    # ── 文件列表 ──

    def list_files(self, dir_path: str = "/", order: str = "time", desc: int = 1,
                   start: int = 0, limit: int = 100) -> dict:
        """获取目录下的文件列表。"""
        resp = self._request("GET", self.BASE_URL, params={
            "method": "list",
            "dir": dir_path,
            "order": order,
            "desc": desc,
            "start": start,
            "limit": limit,
            "web": 1,
        })
        return resp

    def list_by_category(self, category: int, start: int = 0, limit: int = 100) -> dict:
        """按分类获取文件列表。"""
        resp = self._request("GET", self.BASE_URL, params={
            "method": "list",
            "category": category,
            "start": start,
            "limit": limit,
            "web": 1,
        })
        return resp

    # ── 搜索 ──

    def search(self, keyword: str, dir_path: str = "/", recursion: int = 1,
               page: int = 1, num: int = 100) -> dict:
        """搜索文件。"""
        resp = self._request("GET", self.BASE_URL, params={
            "method": "search",
            "key": keyword,
            "dir": dir_path,
            "recursion": recursion,
            "page": page,
            "num": num,
            "web": 1,
        })
        return resp

    # ── 文件操作 ──

    def move_files(self, filelist: list) -> dict:
        """批量移动文件。filelist: [{"path": "/src", "dest": "/dest"}]"""
        # 去掉空的 newname 字段，否则 API 返回 errno=12
        clean = []
        for item in filelist:
            entry = {"path": item["path"], "dest": item["dest"]}
            if item.get("newname"):
                entry["newname"] = item["newname"]
            clean.append(entry)
        return self._filemanager("move", clean)

    def copy_files(self, filelist: list) -> dict:
        """批量复制文件。"""
        clean = []
        for item in filelist:
            entry = {"path": item["path"], "dest": item["dest"]}
            if item.get("newname"):
                entry["newname"] = item["newname"]
            clean.append(entry)
        return self._filemanager("copy", clean)

    def delete_files(self, filelist: list) -> dict:
        """批量删除文件。filelist: ["/path/file1", "/path/file2"]"""
        return self._filemanager("delete", filelist)

    def rename_file(self, path: str, newname: str) -> dict:
        """重命名文件。"""
        return self._filemanager("rename", [{"path": path, "newname": newname}])

    def _filemanager(self, opera: str, filelist: list) -> dict:
        """通用文件管理操作。"""
        url = f"{self.BASE_URL}?method=filemanager&opera={opera}"
        return self._request_with_retry("POST", url, data={
            "async": 0,
            "filelist": json.dumps(filelist, ensure_ascii=False),
        })

    # ── 创建文件夹 ──

    def create_folder(self, path: str) -> dict:
        """创建文件夹。"""
        resp = self._request("POST", self.BASE_URL, params={
            "method": "create",
        }, data={
            "path": path,
            "isdir": 1,
        })
        return resp

    # ── 用户信息 ──

    def get_user_info(self) -> dict:
        """获取用户信息。"""
        return self._request("GET", self.NAS_URL, params={"method": "uinfo"})

    # ── 容量信息 ──

    def get_quota(self) -> dict:
        """获取网盘容量信息。"""
        return self._request("GET", self.QUOTA_URL, params={
            "checkfree": 1,
            "checkexpire": 1,
        })