#!/usr/bin/env python3
"""
商品审核批准
"""

import os
from typing import List, Tuple

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def approve_goods(
    goods_ids: List[int], approve_status: str = "Y"
) -> Tuple[int, List[str]]:
    """
    审核批准商品

    Args:
        goods_ids: 商品ID列表
        approve_status: 审核状态 ("Y"=通过, "N"=不通过)

    Returns:
        (成功数量, 失败原因列表)
    """
    url = f"{API_BASE}/admin/goods/admin/goods/approve"

    payload = {
        "items": [{"id": gid} for gid in goods_ids],
        "approveStatus": approve_status,
    }

    headers = {"Content-Type": "application/json"}
    headers["Cookie"] = COOKIE

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    result_data = data.get("data", {})
    approve_count = result_data.get("approveCount", 0)
    fail_reason = result_data.get("failReason", [])

    return approve_count, fail_reason


def approve_single_goods(goods_id: int) -> bool:
    """
    审核单个商品

    Args:
        goods_id: 商品ID

    Returns:
        是否成功
    """
    count, _ = approve_goods([goods_id])
    return count > 0


if __name__ == "__main__":
    # 测试
    count, reasons = approve_goods([2132336])
    print(f"审核结果: 成功 {count} 个")
    if reasons:
        print(f"失败原因: {reasons}")
