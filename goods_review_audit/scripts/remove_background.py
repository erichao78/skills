#!/usr/bin/env python3
"""
图片背景抠图
"""

import os

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def remove_background(goods_id: int, pic_url: str, template_name: str) -> str:
    """
    执行图片背景抠图

    Args:
        goods_id: 商品ID
        pic_url: 待抠图的图片URL
        template_name: 模板分类名称

    Returns:
        抠图后的图片URL
    """
    url = f"{API_BASE}/admin/ai-photo/admin/photo/batch-remove-background"

    payload = {
        "goodsList": [
            {"goodsId": goods_id, "picUrl": pic_url, "templateName": template_name}
        ],
        "batchFlag": True,
        "removeType": "RMBG",
    }

    headers = {"Content-Type": "application/json"}
    headers["Cookie"] = COOKIE

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    goods_list = data.get("data", {}).get("goodsList", [])
    if goods_list:
        return goods_list[0].get("processedPicUrl", "")

    return ""


if __name__ == "__main__":
    # 测试
    result = remove_background(
        2132336,
        "https://psmp-test.shanshan-business.com:28081/app/mdata/oss/storage/fetch/f365ab10ba12cc4f661a41143fa618d6@855x855.jpg",
        "其他",
    )
    print(f"抠图结果: {result}")
