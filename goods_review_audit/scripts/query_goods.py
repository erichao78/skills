#!/usr/bin/env python3
"""
查询商品详细信息
"""

import os
from typing import Optional

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def query_goods_list(
    plaza_code: str,
    shop_id: int,
    goods_sn: Optional[str] = None,
    goods_name: Optional[str] = None,
) -> list:
    """
    查询商品列表

    Args:
        plaza_code: 门店编号
        shop_id: 店铺ID
        goods_sn: 商品编码（可选）
        goods_name: 商品名称（可选）

    Returns:
        商品列表
    """
    url = f"{API_BASE}/admin/goods/admin/goods/list"

    payload = {
        "page": 1,
        "limit": 999,
        "plazaCode": plaza_code,
        "shopId": shop_id,
        "categoryId": None,
        "goodsSn": goods_sn,
        "goodsSnIncludeFlag": "include",
        "skuCode": None,
        "goodsName": goods_name,
        "subGoodsName": None,
        "minPrice": None,
        "maxPrice": None,
        "publishFlag": 0,
        "picFlag": 1,
        "unCompletedFlag": False,
        "unCompletedStatus": 0,
        "approveStatus": "A",
        "stockFlag": 0,
        "afterSaleFlag": 0,
        "sepicalFlag": 0,
        "enabledFlag": 1,
        "couponFlag": 0,
        "goodsSource": 0,
        "picSource": 0,
        "picQualityFlag": 0,
        "sort": "add_time",
        "order": "desc",
    }

    headers = {"Content-Type": "application/json"}
    headers["Cookie"] = COOKIE

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"API调用失败: {data.get('errmsg')}")

    return data.get("data", {}).get("items", [])


def find_goods_by_sn(plaza_code: str, shop_id: int, goods_sn: str) -> Optional[dict]:
    """根据商品编码查找商品"""
    goods_list = query_goods_list(plaza_code, shop_id, goods_sn=goods_sn)
    for goods in goods_list:
        if goods.get("goodsSn") == goods_sn:
            return goods
    return None


def find_goods_by_name(
    plaza_code: str, shop_id: int, goods_name: str
) -> Optional[dict]:
    """根据商品名称查找商品"""
    goods_list = query_goods_list(plaza_code, shop_id, goods_name=goods_name)
    if goods_list:
        return goods_list[0]
    return None


def extract_goods_info(goods: dict) -> dict:
    """
    提取商品关键信息

    Args:
        goods: 商品完整数据

    Returns:
        商品关键信息
    """
    import re

    gallery = goods.get("gallery", [])
    detail_html = goods.get("detail", "")
    detail_img_count = len(re.findall(r"<img\s", detail_html)) if detail_html else 0

    return {
        "id": goods.get("id"),
        "goodsSn": goods.get("goodsSn"),
        "name": goods.get("name"),
        "goodsTitle": goods.get("goodsTitle"),
        "shopId": goods.get("shopId"),
        "shopName": goods.get("shop", {}).get("name"),
        "brandId": goods.get("brandCategoryId"),
        "categoryNames": goods.get("categoryNames"),
        "parentCategoryName": goods.get("parentCategoryName"),
        "categoryGender": goods.get("categoryGender"),
        "categorySeason": goods.get("categorySeason"),
        "minOriPrice": goods.get("minOriPrice"),
        "maxOriPrice": goods.get("maxOriPrice"),
        "minCurPrice": goods.get("minCurPrice"),
        "maxCurPrice": goods.get("maxCurPrice"),
        "discountRate": goods.get("discountRate"),
        "galleryCount": len(gallery),
        "detailImgCount": detail_img_count,
        "gallery": gallery,
        "detail": detail_html,
        "picUrl": goods.get("picUrl"),
        "skuPicUrls": goods.get("skuPicUrls", []),
        "productList": goods.get("productList", []),
        "approveStatus": goods.get("approveStatus"),
        "enabled": goods.get("enabled"),
    }


if __name__ == "__main__":
    # 测试
    goods = query_goods_list("0001", 1000043)
    if goods:
        info = extract_goods_info(goods[0])
        print(f"商品ID: {info['id']}")
        print(f"商品名称: {info['name']}")
        print(f"主图数量: {info['picCount']}")
        print(f"详情图数量: {info['detailCount']}")
