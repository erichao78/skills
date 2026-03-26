#!/usr/bin/env python3
"""
查询商品模板分类
"""

import os

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


# 所有模板分类名称
ALL_TEMPLATE_CATEGORIES = [
    "鞋",
    "上装",
    "下装-成人",
    "下装-儿童",
    "包-默认",
    "包-大",
    "包-小",
    "内衣",
    "美妆",
    "内衣-模特",
    "上装-模特",
    "下装-模特",
    "套装-模特",
    "其他",
]


def query_template_category(goods_id: int) -> str:
    """
    查询商品模板分类名称

    Args:
        goods_id: 商品ID

    Returns:
        模板分类名称
    """
    url = f"{API_BASE}/admin/goods/admin/pic-package/query-template-category"

    payload = {"goodsList": [{"id": goods_id}]}

    headers = {"Content-Type": "application/json"}
    headers["Cookie"] = COOKIE

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    goods_list = data.get("data", {}).get("goodsList", [])
    if goods_list:
        return goods_list[0].get("templateCategory", "其他")

    return "其他"


if __name__ == "__main__":
    # 测试
    template = query_template_category(2132336)
    print(f"模板分类: {template}")
