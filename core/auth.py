import time
import requests
from core.config import Config

TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
AUTHORIZE_URL = "https://openapi.baidu.com/oauth/2.0/authorize"


def get_auth_url(app_key: str) -> str:
    """
    生成 OAuth2 授权页面 URL。

    用户在浏览器中打开此 URL，完成授权后，
    浏览器会跳转到 redirect_uri 并附带 code 参数。
    """
    return (
        f"{AUTHORIZE_URL}"
        f"?response_type=code"
        f"&client_id={app_key}"
        f"&redirect_uri=oob"
        f"&scope=basic,netdisk"
    )


def exchange_code_for_token(app_key: str, secret_key: str, code: str) -> dict:
    """
    用授权码换取 access_token。

    返回:
        {
            "access_token": "...",
            "refresh_token": "...",
            "expires_in": 2592000,
        }

    失败抛出 RuntimeError。
    """
    resp = requests.post(TOKEN_URL, params={
        "grant_type": "authorization_code",
        "code": code.strip(),
        "client_id": app_key,
        "client_secret": secret_key,
        "redirect_uri": "oob",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "access_token" not in data:
        error_msg = data.get("error_description", data.get("error", "未知错误"))
        raise RuntimeError(f"获取 token 失败：{error_msg}")

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 2592000),
    }


def refresh_access_token(app_key: str, secret_key: str, refresh_token: str) -> dict:
    """
    用 refresh_token 刷新 access_token。

    返回: 同 exchange_code_for_token。
    """
    resp = requests.post(TOKEN_URL, params={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": app_key,
        "client_secret": secret_key,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "access_token" not in data:
        raise RuntimeError("刷新 token 失败")

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_in": data.get("expires_in", 2592000),
    }


def save_auth_result(token_data: dict):
    """将授权结果保存到配置文件。"""
    config = Config()
    config.set("access_token", token_data["access_token"])
    config.set("refresh_token", token_data["refresh_token"])
    config.set("token_expires_at", int(time.time()) + token_data.get("expires_in", 2592000))
    config.save()