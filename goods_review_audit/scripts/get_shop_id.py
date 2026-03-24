#!/usr/bin/env python3
"""
根据门店编号和店铺名称获取店铺ID
"""

import os
from typing import Optional

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def find_matching_shops(plaza_code: str, shop_name: str) -> list[dict]:
    """
    根据门店编号和店铺名称查找所有匹配的店铺。

    匹配逻辑：先收集精确匹配结果，若无精确匹配再收集模糊匹配结果（互相包含关系）。

    Args:
        plaza_code: 门店编号 (如 "0001")
        shop_name: 店铺名称 (如 "LE COQ SPORTIF(乐卡克公鸡)")

    Returns:
        匹配的店铺列表，每项为 {"id": int, "name": str}；无匹配返回空列表
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

    exact_matches = [
        {"id": shop.get("id"), "name": shop.get("name")}
        for shop in shop_list
        if shop.get("name") == shop_name
    ]
    if exact_matches:
        return exact_matches

    fuzzy_matches = [
        {"id": shop.get("id"), "name": shop.get("name")}
        for shop in shop_list
        if shop_name in shop.get("name", "") or shop.get("name", "") in shop_name
    ]
    return fuzzy_matches


def get_shop_id(plaza_code: str, shop_name: str) -> Optional[int]:
    """
    根据门店编号和店铺名称获取店铺ID（向后兼容，返回首个匹配）

    Args:
        plaza_code: 门店编号 (如 "0001")
        shop_name: 店铺名称 (如 "LE COQ SPORTIF(乐卡克公鸡)")

    Returns:
        店铺ID，若未找到返回None
    """
    matches = find_matching_shops(plaza_code, shop_name)
    return matches[0]["id"] if matches else None


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
