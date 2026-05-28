import time
from core.config import Config
from core.auth import refresh_access_token


class TokenManager:
    """Token 生命周期管理器。

    策略：预检查 + 失败重试。
    - 请求前检查 token 是否即将过期（提前 5 分钟），过期则先刷新。
    - 请求返回 -10/-11 错误时，尝试刷新并重试一次。
    """

    def __init__(self):
        self._config = Config()

    def get_valid_token(self) -> str:
        """返回有效的 access_token，必要时先刷新。"""
        if self._config.is_token_expired():
            self._do_refresh()
        return self._config.get("access_token")

    def refresh_and_retry(self, request_func, *args, **kwargs):
        """
        包装 API 请求：如果返回 token 无效错误，自动刷新并重试一次。

        request_func: 一个返回 requests.Response 的函数
        """
        resp = request_func(*args, **kwargs)
        data = resp.json() if resp.content else {}
        errno = data.get("errno", 0)

        if errno in (-10, -11):
            if self._do_refresh():
                resp = request_func(*args, **kwargs)
            else:
                raise TokenExpiredError("Token 已失效，请重新授权")

        return resp

    def _do_refresh(self) -> bool:
        """使用 refresh_token 刷新 access_token。成功返回 True。"""
        refresh_token = self._config.get("refresh_token")
        app_key = self._config.get("app_key")
        secret_key = self._config.get("secret_key")

        if not all([refresh_token, app_key, secret_key]):
            return False

        try:
            data = refresh_access_token(app_key, secret_key, refresh_token)
            self._config.set("access_token", data["access_token"])
            self._config.set("refresh_token", data["refresh_token"])
            self._config.set("token_expires_at", int(time.time()) + data.get("expires_in", 2592000))
            self._config.save()
            return True
        except Exception:
            return False


class TokenExpiredError(Exception):
    """Token 过期且刷新失败时抛出。"""
    pass