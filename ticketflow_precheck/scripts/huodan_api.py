#!/usr/bin/env python3
"""
活动货单自动生成 API
"""

from typing import Optional

import requests
from scripts.check_cookie import get_cookie

API_BASE = "http://124.70.133.190:18080"


def auto_generate_huodan(shop_id: int, file_url: str) -> Optional[dict]:
    """
    调用 AI 接口自动分析原始货单并生成标准活动货单。

    Args:
        shop_id: 店铺 ID
        file_url: 原始货单文件 URL

    Returns:
        成功时返回 dict，包含:
            - sheets: 原始文件 sheet 信息列表
            - columnContent: 列内容
            - standardFileUrl: 生成的标准活动货单文件 URL（为空则表示生成失败）
        失败时返回 None
    """
    url = f"{API_BASE}/admin/ai_huodan/excel/analyze_and_generated"
    headers = {
        "Content-Type": "application/json",
        "Cookie": get_cookie(),
    }
    payload = {
        "shopId": shop_id,
        "fileUrl": file_url,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        print(f"自动生成活动货单失败: {data.get('errmsg')}")
        return None

    result = data.get("data", {})
    standard_url = result.get("standardFileUrl", "")

    if standard_url:
        print(f"活动货单自动生成成功: {standard_url}")
    else:
        print("系统无法自动识别原始货单列结构，需要手动映射")

    return result


if __name__ == "__main__":
    result = auto_generate_huodan(
        shop_id=1000745,
        file_url="https://ossmp.shanshan-business.com/15f875e79e7af69053b5fe5ff925c2c0@0x0.xlsx",
    )
    if result:
        print(f"Sheets: {len(result.get('sheets', []))}")
        print(f"Standard URL: {result.get('standardFileUrl', 'N/A')}")
