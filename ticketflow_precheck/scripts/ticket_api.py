#!/usr/bin/env python3
"""
工单相关 API：查询工单列表、获取工单详情、提交工单更新
"""

from typing import Optional

import requests
from scripts.check_cookie import get_cookie

API_BASE = "http://124.70.133.190:18080"


def _headers(content_type: str = "application/json") -> dict:
    return {
        "Content-Type": content_type,
        "Cookie": get_cookie(),
    }


def get_ticket_by_code(ticket_code: str) -> Optional[dict]:
    """
    根据工单编号查询工单信息。

    Args:
        ticket_code: 工单编号，如 T000117738002663038508819

    Returns:
        工单信息 dict，未找到返回 None
    """
    url = f"{API_BASE}/admin/ticketflow/list"
    payload = {
        "page": 1,
        "limit": 999,
        "code": ticket_code,
        "type": "2",
        "plazaCode": "9999",
        "timeType": "1",
        "operatorType": "1",
        "sort": "add_time",
        "order": "desc",
        "priority": "0",
        "status": "INIT",
    }

    response = requests.post(url, json=payload, headers=_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"查询工单列表失败: {data.get('errmsg')}")

    items = data.get("data", {}).get("items", [])
    if not items:
        return None

    for item in items:
        if item.get("code") == ticket_code:
            return item

    return items[0]


def get_ticket_detail(ticket_id: int) -> dict:
    """
    获取工单详细信息。

    Args:
        ticket_id: 工单 ID

    Returns:
        工单详情 dict
    """
    url = f"{API_BASE}/admin/ticketflow/read"
    params = {"id": ticket_id}

    response = requests.get(url, params=params, headers=_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取工单详情失败: {data.get('errmsg')}")

    return data.get("data", {})


def submit_ticket_update(
    ticket_detail: dict,
    huodan_file_url: str,
    huodan_file_name: str,
    unique_spus: list,
    goods_count: int,
    column_mapping: dict,
) -> dict:
    """
    提交工单更新，将活动货单信息写入工单。

    Args:
        ticket_detail: 完整的工单详情（从 get_ticket_detail 获取）
        huodan_file_url: 活动货单文件 URL
        huodan_file_name: 活动货单文件名
        unique_spus: 唯一 SPU 编码列表
        goods_count: 货品总数
        column_mapping: 列名映射 dict，包含 spuColumn, skuColumn 等

    Returns:
        API 响应 dict
    """
    url = f"{API_BASE}/admin/ticketflow/update"

    detail = dict(ticket_detail.get("detail", {}))
    detail.update(
        {
            "spuColumn": column_mapping.get("spuColumn", "商品SPU"),
            "skuColumn": column_mapping.get("skuColumn", "商品SKU"),
            "oriPriceColumn": column_mapping.get("oriPriceColumn", "吊牌价"),
            "aolaiColumn": column_mapping.get("aolaiColumn", "奥莱价"),
            "stockColumn": column_mapping.get("stockColumn", "库存"),
            "colorColumn": column_mapping.get("colorColumn", "颜色"),
            "sizeColumn": column_mapping.get("sizeColumn", "尺码"),
            "goodsSns": unique_spus,
            "unCompletedTotal": goods_count,
            "unMatchedTotal": goods_count,
        }
    )

    huodan_file_size = 0
    try:
        resp = requests.head(huodan_file_url, timeout=10)
        huodan_file_size = int(resp.headers.get("Content-Length", 0))
    except Exception:
        pass

    payload = {
        "id": ticket_detail["id"],
        "code": ticket_detail["code"],
        "type": ticket_detail.get("type", 2),
        "typeL2": ticket_detail.get("typeL2", 1),
        "typeL2Font": ticket_detail.get("typeL2Font", [1]),
        "plazaCode": ticket_detail.get("plazaCode"),
        "origin": ticket_detail.get("origin"),
        "shopId": ticket_detail.get("shopId"),
        "status": ticket_detail.get("status"),
        "title": ticket_detail.get("title"),
        "level": ticket_detail.get("level", "normal"),
        "content": ticket_detail.get("content", ""),
        "remark": ticket_detail.get("remark", ""),
        "reporter": ticket_detail.get("reporter"),
        "assignee": ticket_detail.get("assignee"),
        "addBy": ticket_detail.get("addBy"),
        "addTime": ticket_detail.get("addTime"),
        "updateBy": ticket_detail.get("updateBy"),
        "currentUser": ticket_detail.get("currentUser"),
        "startTime": ticket_detail.get("startTime"),
        "endTime": ticket_detail.get("endTime"),
        "kickoffTime": ticket_detail.get("kickoffTime"),
        "finishTime": ticket_detail.get("finishTime"),
        "activityType": ticket_detail.get("activityType"),
        "activityLevel": ticket_detail.get("activityLevel"),
        "categoryName": ticket_detail.get("categoryName"),
        "isGroupFlag": ticket_detail.get("isGroupFlag", True),
        "createMode": ticket_detail.get("createMode", 2),
        "deleted": ticket_detail.get("deleted", False),
        "autoCreate": ticket_detail.get("autoCreate", 0),
        "dialogueId": ticket_detail.get("dialogueId", ""),
        "biActivityId": ticket_detail.get("biActivityId"),
        "relateTicketId": ticket_detail.get("relateTicketId"),
        "chatIds": ticket_detail.get("chatIds", []),
        "columns": ticket_detail.get("columns", []),
        "images": ticket_detail.get("images", []),
        "thirdFile": ticket_detail.get("thirdFile", []),
        "brdFile": ticket_detail.get("brdFile", []),
        "secondFile": [
            {
                "fileName": huodan_file_name,
                "fileSize": huodan_file_size,
                "fileUrl": huodan_file_url,
            }
        ],
        "detail": detail,
        "goodsSns": unique_spus,
        "goodsCount": goods_count,
        "needAddedNum": goods_count,
        "enabledNum": ticket_detail.get("enabledNum", 0),
        "realAddedNum": ticket_detail.get("realAddedNum", 0),
        "enabledTotal": ticket_detail.get("enabledTotal", 0),
        "unEnabledTotal": ticket_detail.get("unEnabledTotal", 0),
        "unCompletedTotal": goods_count,
    }

    response = requests.post(url, json=payload, headers=_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"提交工单更新失败: {data.get('errmsg')}")

    return data


if __name__ == "__main__":
    ticket = get_ticket_by_code("T000117738002663038508819")
    if ticket:
        print(
            f"工单ID: {ticket['id']}, 编号: {ticket['code']}, 状态: {ticket['status']}"
        )
        detail = get_ticket_detail(ticket["id"])
        print(f"店铺ID: {detail.get('shopId')}, 标题: {detail.get('title')}")
    else:
        print("未找到工单")
