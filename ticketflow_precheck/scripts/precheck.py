#!/usr/bin/env python3
"""
活动货单预检校验：数据完整性、重复检查、价格合规、库存校验
"""

from typing import Any

REQUIRED_FIELDS = [
    "商品SPU",
    "商品SKU",
    "吊牌价",
    "奥莱价",
    "库存",
    "品类",
    "季节",
    "性别",
    "颜色",
    "尺码",
]
PRICE_FIELDS = ["吊牌价", "奥莱价"]
STOCK_FIELD = "库存"
SPU_FIELD = "商品SPU"
SKU_FIELD = "商品SKU"


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _row_signature(row: dict) -> tuple:
    """生成行的完整签名，用于判断完全重复"""
    return tuple(sorted((k, str(v)) for k, v in row.items()))


def _check_completeness(data: list) -> list:
    """检查数据完整性：必填字段是否缺失"""
    exceptions = {}

    for row_idx, row in enumerate(data, start=2):
        for field in REQUIRED_FIELDS:
            if _is_empty(row.get(field)):
                key = ("missing_data", field)
                if key not in exceptions:
                    exceptions[key] = {
                        "type": "missing_data",
                        "field": field,
                        "rows": [],
                        "detail": f"{field} 字段存在缺失",
                        "samples": [],
                    }
                exceptions[key]["rows"].append(row_idx)
                if len(exceptions[key]["samples"]) < 3:
                    exceptions[key]["samples"].append(
                        {
                            "row": row_idx,
                            SPU_FIELD: row.get(SPU_FIELD, ""),
                            SKU_FIELD: row.get(SKU_FIELD, ""),
                            field: row.get(field),
                        }
                    )

    return list(exceptions.values())


def _check_duplicates(data: list) -> tuple:
    """
    检查重复数据。

    Returns:
        (deduped_data, deduped_count, exceptions)
        - deduped_data: 去除完全重复后的数据
        - deduped_count: 被去重的行数
        - exceptions: 同 SPU/SKU 但字段不同的异常
    """
    seen_signatures = {}
    deduped_data = []
    deduped_count = 0

    for row_idx, row in enumerate(data, start=2):
        sig = _row_signature(row)
        if sig in seen_signatures:
            deduped_count += 1
            continue
        seen_signatures[sig] = row_idx
        deduped_data.append(row)

    sku_groups = {}
    for row_idx, row in enumerate(deduped_data, start=2):
        spu = str(row.get(SPU_FIELD, "")).strip()
        sku = str(row.get(SKU_FIELD, "")).strip()
        key = (spu, sku)
        if key == ("", ""):
            continue
        if key not in sku_groups:
            sku_groups[key] = []
        sku_groups[key].append({"row": row_idx, "data": row})

    exceptions = []
    for (spu, sku), group in sku_groups.items():
        if len(group) <= 1:
            continue

        first = group[0]["data"]
        has_conflict = False
        for item in group[1:]:
            for field in REQUIRED_FIELDS:
                if str(first.get(field, "")) != str(item["data"].get(field, "")):
                    has_conflict = True
                    break
            if has_conflict:
                break

        if has_conflict:
            exceptions.append(
                {
                    "type": "duplicate_conflict",
                    "field": f"{SPU_FIELD}/{SKU_FIELD}",
                    "rows": [item["row"] for item in group],
                    "detail": f"SPU={spu}, SKU={sku} 存在多条记录但部分字段不一致",
                    "samples": [
                        {
                            "row": item["row"],
                            SPU_FIELD: spu,
                            SKU_FIELD: sku,
                            **{f: item["data"].get(f) for f in REQUIRED_FIELDS},
                        }
                        for item in group[:3]
                    ],
                }
            )

    return deduped_data, deduped_count, exceptions


def _check_prices(data: list) -> list:
    """检查价格合规性：吊牌价、奥莱价必须大于 0"""
    exceptions = {}

    for row_idx, row in enumerate(data, start=2):
        for field in PRICE_FIELDS:
            val = _to_number(row.get(field))
            if val <= 0 and not _is_empty(row.get(field)):
                key = ("invalid_price", field)
                if key not in exceptions:
                    exceptions[key] = {
                        "type": "invalid_price",
                        "field": field,
                        "rows": [],
                        "detail": f"{field} 存在小于等于 0 的数据",
                        "samples": [],
                    }
                exceptions[key]["rows"].append(row_idx)
                if len(exceptions[key]["samples"]) < 3:
                    exceptions[key]["samples"].append(
                        {
                            "row": row_idx,
                            SPU_FIELD: row.get(SPU_FIELD, ""),
                            SKU_FIELD: row.get(SKU_FIELD, ""),
                            field: row.get(field),
                        }
                    )

    return list(exceptions.values())


def _check_stock(data: list) -> list:
    """检查库存：库存不能小于 0"""
    exception_rows = []
    samples = []

    for row_idx, row in enumerate(data, start=2):
        val = _to_number(row.get(STOCK_FIELD))
        if val < 0 and not _is_empty(row.get(STOCK_FIELD)):
            exception_rows.append(row_idx)
            if len(samples) < 3:
                samples.append(
                    {
                        "row": row_idx,
                        SPU_FIELD: row.get(SPU_FIELD, ""),
                        SKU_FIELD: row.get(SKU_FIELD, ""),
                        STOCK_FIELD: row.get(STOCK_FIELD),
                    }
                )

    if exception_rows:
        return [
            {
                "type": "negative_stock",
                "field": STOCK_FIELD,
                "rows": exception_rows,
                "detail": "库存存在小于 0 的数据",
                "samples": samples,
            }
        ]

    return []


def precheck_huodan(data: list) -> dict:
    """
    对活动货单数据执行全面预检。

    Args:
        data: 活动货单数据 list[dict]

    Returns:
        dict:
            passed: 是否全部通过
            total_rows: 原始总行数
            valid_rows: 有效行数（去重后）
            deduped_count: 完全重复被去重的行数
            exceptions: 异常列表
            clean_data: 去重后的干净数据
    """
    total_rows = len(data)

    deduped_data, deduped_count, dup_exceptions = _check_duplicates(data)

    all_exceptions = []
    all_exceptions.extend(_check_completeness(deduped_data))
    all_exceptions.extend(dup_exceptions)
    all_exceptions.extend(_check_prices(deduped_data))
    all_exceptions.extend(_check_stock(deduped_data))

    passed = len(all_exceptions) == 0

    return {
        "passed": passed,
        "total_rows": total_rows,
        "valid_rows": len(deduped_data),
        "deduped_count": deduped_count,
        "exceptions": all_exceptions,
        "clean_data": deduped_data,
    }


if __name__ == "__main__":
    test_data = [
        {
            "商品名称": "测试商品A",
            "商品SPU": "SPU001",
            "商品SKU": "SKU001",
            "吊牌价": 100,
            "奥莱价": 80,
            "库存": 10,
            "品类": "运动",
            "颜色": "黑色",
            "尺码": "L",
            "季节": "秋季",
            "性别": "男",
        },
        {
            "商品名称": "测试商品B",
            "商品SPU": "SPU002",
            "商品SKU": "SKU002",
            "吊牌价": 200,
            "奥莱价": 0,
            "库存": -5,
            "品类": "运动",
            "颜色": "白色",
            "尺码": "M",
            "季节": "春季",
            "性别": "女",
        },
        {
            "商品名称": "测试商品C",
            "商品SPU": "SPU003",
            "商品SKU": "",
            "吊牌价": 150,
            "奥莱价": 120,
            "库存": 20,
            "品类": "",
            "颜色": "红色",
            "尺码": "S",
            "季节": "夏季",
            "性别": "男",
        },
    ]

    result = precheck_huodan(test_data)
    print(f"预检通过: {result['passed']}")
    print(f"总行数: {result['total_rows']}, 有效行数: {result['valid_rows']}")
    print(f"去重数: {result['deduped_count']}")
    for exc in result["exceptions"]:
        print(f"  异常: [{exc['type']}] {exc['detail']} (影响行: {exc['rows']})")
