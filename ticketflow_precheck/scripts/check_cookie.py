#!/usr/bin/env python3
"""
Cookie 管理器：负责 Cookie 的读取、写入、校验和统一获取。
Cookie 持久化存储在技能目录下的 .cookie 文件中，跨 Session 可复用。
"""

import os
from typing import Optional

import requests

API_BASE = "http://124.70.133.190:18080"

COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cookie")

ENV_KEY = "TICKETFLOW_COOKIE"


def _read_cookie_from_file() -> Optional[str]:
    """从 .cookie 文件读取 Cookie 值。"""
    if not os.path.exists(COOKIE_FILE):
        return None
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            cookie = f.read().strip()
        return cookie if cookie else None
    except OSError:
        return None


def _write_cookie_to_file(cookie: str) -> None:
    """将 Cookie 值写入 .cookie 文件。"""
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie.strip())


def clear_cookie_file() -> None:
    """清除 .cookie 文件中的无效 Cookie（删除文件）。"""
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)


def validate_cookie(cookie: str) -> bool:
    """
    通过轻量级 API 调用校验 Cookie 是否仍然有效。
    使用工单列表接口发送一次最小请求，根据返回的 errcode 判断认证状态。
    """
    url = f"{API_BASE}/admin/ticketflow/list"
    headers = {
        "Content-Type": "application/json",
        "Cookie": cookie,
    }
    payload = {
        "page": 1,
        "limit": 1,
        "type": "2",
        "plazaCode": "9999",
        "timeType": "1",
        "operatorType": "1",
        "sort": "add_time",
        "order": "desc",
        "priority": "0",
        "status": "INIT",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 401:
            return False
        data = resp.json()
        return data.get("errcode") == 0
    except Exception:
        return False


def get_cookie() -> str:
    """
    统一获取 Cookie 的入口。按以下优先级查找：
      1. .cookie 文件
      2. 环境变量 TICKETFLOW_COOKIE（兼容旧用法，找到后自动写入文件）

    找到 Cookie 后会校验有效性，无效则清除文件并抛出异常提示用户提供新值。
    如果两处都没有 Cookie，同样抛出异常。
    """
    cookie = _read_cookie_from_file()

    if not cookie:
        cookie = os.getenv(ENV_KEY)
        if cookie:
            _write_cookie_to_file(cookie)

    if not cookie:
        raise RuntimeError(
            "Cookie 不存在。请提供有效的 Cookie 值，"
            "然后调用 set_cookie(cookie_value) 进行设置。"
        )

    if not validate_cookie(cookie):
        clear_cookie_file()
        raise RuntimeError(
            "当前 Cookie 已失效。请提供最新的 Cookie 值，"
            "然后调用 set_cookie(cookie_value) 进行更新。"
        )

    return cookie


def set_cookie(cookie_value: str) -> str:
    """
    设置新的 Cookie：校验有效性后写入 .cookie 文件。

    Args:
        cookie_value: 用户提供的新 Cookie 值

    Returns:
        写入成功的 Cookie 值

    Raises:
        ValueError: Cookie 值为空
        RuntimeError: Cookie 校验失败
    """
    if not cookie_value or not cookie_value.strip():
        raise ValueError("Cookie 值不能为空")

    cookie_value = cookie_value.strip()

    if not validate_cookie(cookie_value):
        raise RuntimeError("提供的 Cookie 无效，请确认后重新提供。")

    _write_cookie_to_file(cookie_value)
    os.environ[ENV_KEY] = cookie_value
    print("Cookie 已验证并保存。")
    return cookie_value


if __name__ == "__main__":
    try:
        cookie = get_cookie()
        display = f"{cookie[:20]}..." if len(cookie) > 20 else cookie
        print(f"当前 Cookie 有效: {display}")
    except RuntimeError as e:
        print(f"错误: {e}")
