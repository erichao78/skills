#!/usr/bin/env python3
"""
根据门店编号和店铺名称获取店铺ID
"""

import os
from typing import Optional

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def get_shop_id(plaza_code: str, shop_name: str) -> Optional[int]:
    """
    根据门店编号和店铺名称获取店铺ID

    Args:
        plaza_code: 门店编号 (如 "0001")
        shop_name: 店铺名称 (如 "LE COQ SPORTIF(乐卡克公鸡)")

    Returns:
        店铺ID，若未找到返回None
    """
    url = f"{API_BASE}/admin/mdata/shop/shopList"
    params = {"plazaCode": plaza_code}

    headers = {}
    headers["Cookie"] = COOKIE

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    shop_list = data.get("data", {}).get("shop", [])

    # 精确匹配
    for shop in shop_list:
        if shop.get("name") == shop_name:
            return shop.get("id")

    # 模糊匹配（店铺名称包含搜索词）
    for shop in shop_list:
        if shop_name in shop.get("name", "") or shop.get("name", "") in shop_name:
            return shop.get("id")

    return None


def get_all_shops(plaza_code: str) -> list:
    """
    获取门店下所有店铺列表

    Args:
        plaza_code: 门店编号

    Returns:
        店铺列表
    """
    url = f"{API_BASE}/admin/mdata/shop/shopList"
    params = {"plazaCode": plaza_code}

    headers = {}
    headers["Cookie"] = COOKIE

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    return data.get("data", {}).get("shop", [])


if __name__ == "__main__":
    # 测试
    shops = get_all_shops("0001")
    for shop in shops[:3]:
        print(f"店铺ID: {shop.get('id')}, 名称: {shop.get('name')}")
