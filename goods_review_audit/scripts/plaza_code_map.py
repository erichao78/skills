#!/usr/bin/env python3
"""
门店编号(PlazaCode)映射表
"""

PLAZA_CODE_MAP = {
    "宁波店": "0001",
    "哈尔滨店": "0002",
    "郑州中牟店": "0003",
    "晋中店": "0004",
    "南昌店": "0005",
    "赣州店": "0006",
    "兰州店": "0007",
    "乌鲁木齐店": "0008",
    "衡阳店": "0009",
    "沈阳店": "0010",
    "贵阳店": "0011",
    "深圳店": "0012",
    "南宁店": "0013",
    "徐州店": "0014",
    "太原店": "0016",
    "天津店": "0017",
    "郑州二七店": "0018",
    "成都店": "0019",
    "大连店": "0020",
    "合肥店": "0021",
    "武汉店": "0022",
    "长沙店": "0023",
    "无锡店": "0024",
}

def get_plaza_code(store_name: str) -> str | None:
    """根据店铺名称获取plazaCode"""
    return PLAZA_CODE_MAP.get(store_name)

def get_all_plaza_codes() -> dict:
    """获取所有plazaCode映射"""
    return PLAZA_CODE_MAP.copy()


if __name__ == "__main__":
    # 测试
    print("晋中店:", get_plaza_code("晋中店"))
    print("宁波店:", get_plaza_code("宁波店"))
    print("所有映射:", get_all_plaza_codes())
