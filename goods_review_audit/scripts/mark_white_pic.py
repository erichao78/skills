#!/usr/bin/env python3
"""
标记商品白底图
"""

import os

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def mark_white_pic(goods_id: int, force_override: bool = False) -> bool:
    """
    标记商品白底图

    Args:
        goods_id: 商品ID
        force_override: 是否强制覆盖已有白底图标记

    Returns:
        是否成功
    """
    url = f"{API_BASE}/admin/goods/admin/pic-package/batch-update-pic-flag"

    payload = {
        "goodsList": [{"id": goods_id}],
        "picQualityFlag": 1,
        "forceOverrideWhitePic": force_override,
    }

    headers = {"Content-Type": "application/json"}
    headers["Cookie"] = COOKIE

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    return True


if __name__ == "__main__":
    # 测试
    result = mark_white_pic(2132336)
    print(f"标记结果: {result}")
