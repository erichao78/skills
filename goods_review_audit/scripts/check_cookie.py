#!/usr/bin/env python3
"""
检查并设置 GOODS_AUDIT_COOKIE 环境变量
"""

import os

ENV_KEY = "GOODS_AUDIT_COOKIE"


def check_and_set_cookie(cookie_value: str = None) -> str:
    """
    检查 GOODS_AUDIT_COOKIE 是否存在，不存在则进行赋值。

    Args:
        cookie_value: 要设置的Cookie值，为None时会提示用户输入

    Returns:
        当前的Cookie值
    """
    existing = os.getenv(ENV_KEY)
    if existing:
        print(f"{ENV_KEY} 已存在")
        return existing

    if cookie_value is None:
        cookie_value = input(f"{ENV_KEY} 未设置，请输入Cookie值: ").strip()

    if not cookie_value:
        raise ValueError("Cookie值不能为空")

    os.environ[ENV_KEY] = cookie_value
    print(f"{ENV_KEY} 已设置")
    return cookie_value


if __name__ == "__main__":
    cookie = check_and_set_cookie()
    print(
        f"当前Cookie: {cookie[:20]}..." if len(cookie) > 20 else f"当前Cookie: {cookie}"
    )
