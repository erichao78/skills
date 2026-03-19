#!/usr/bin/env python3
"""
更新商品主图
"""

import os

import requests

API_BASE = "http://124.70.133.190:18080"
COOKIE = os.getenv("GOODS_AUDIT_COOKIE")


def update_gallery(
    goods_id: int, processed_pic_url: str, template_category: str
) -> bool:
    """
    更新商品主图（第一张图为抠图后的白底图）

    Args:
        goods_id: 商品ID
        processed_pic_url: 抠图后的图片URL
        template_category: 模板分类名称

    Returns:
        是否成功
    """
    url = f"{API_BASE}/admin/goods/admin/pic-package/batch-update-gallery"

    payload = {
        "goodsList": [
            {
                "id": goods_id,
                "picUrl": processed_pic_url,
                "templateCategory": template_category,
            }
        ],
        "galleryFlag": True,
        "whiteBackgroundPicFlag": True,
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
    result = update_gallery(
        2132336,
        "https://psmp-test.shanshan-business.com:28081/app/mdata/oss/storage/fetch/eff73b574f99ae0ec308a49df01463e0@854x854.jpg",
        "其他",
    )
    print(f"更新结果: {result}")
