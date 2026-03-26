#!/usr/bin/env python3
"""
文件上传 API：将本地文件上传到服务器
"""

import os

import requests
from scripts.check_cookie import get_cookie

API_BASE = "http://124.70.133.190:18080"


def upload_file(file_path: str) -> dict:
    """
    上传文件到服务器。

    Args:
        file_path: 本地文件路径

    Returns:
        dict: 包含 url, name, size 等字段
    """
    url = f"{API_BASE}/admin/mdata/storage/create"

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    filename = os.path.basename(file_path)
    headers = {"Cookie": get_cookie()}

    with open(file_path, "rb") as f:
        files = {
            "file": (
                filename,
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        response = requests.post(url, files=files, headers=headers, timeout=60)

    response.raise_for_status()

    data = response.json()
    if data.get("errcode") != 0:
        raise Exception(f"文件上传失败: {data.get('errmsg')}")

    result = data.get("data", {})
    print(f"文件上传成功: {result.get('url')}")

    return {
        "url": result.get("url", ""),
        "name": result.get("uploadFileName", filename),
        "size": result.get("size", os.path.getsize(file_path)),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = upload_file(sys.argv[1])
        print(f"URL: {result['url']}")
        print(f"Name: {result['name']}")
        print(f"Size: {result['size']}")
    else:
        print("用法: python file_upload.py <file_path>")
