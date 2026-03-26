---
name: ticketflow_precheck
description: 工单预检处理技能。当运营人员需要处理数字化工单、进行货单预检、生成活动货单、提交货单时使用此技能。支持自动化工单信息获取、活动货单自动/手动生成、货单数据完整性和合规性校验、异常数据反馈、货单文件上传与提交等完整流程。典型触发场景："预处理工单T000117738002663038508819"、"预检工单XXX"、"工单XXX货单预处理"、"提交工单XXX的货单"。即使用户只是提到"货单预检"、"预处理工单"、"工单预检"，也应使用此技能。
compatibility: 需要 Python 3.9+、requests 库、openpyxl 库（用于 Excel 文件处理）
---

# 工单预检处理技能

本技能用于自动化处理杉杉奥莱数字化工单的货单预检流程。接收运营人员提供的工单编号后，自动获取工单信息、生成活动货单、进行数据预检校验，最终完成货单提交。

## 脚本执行方式

`scripts/` 目录中的脚本都是独立的 Python 文件，每个文件内包含可调用的函数。所有 API 调用的身份认证 Cookie 统一由 `scripts/check_cookie.py` 管理，Cookie 持久化存储在技能目录下的 `.cookie` 文件中，跨 Session 自动复用。**在执行过程中决不允许自己新创建脚本，只能使用 `scripts/` 目录中的脚本**

**执行脚本有两种方式**：

1. **Shell 直接运行**（适合快速测试）：`python scripts/xxx.py`
2. **在 Python 代码中导入**（推荐用于流程编排）：需要先确保导入路径正确，例如：

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from scripts.check_cookie import get_cookie, set_cookie, validate_cookie
from scripts.ticket_api import get_ticket_by_code, get_ticket_detail, submit_ticket_update
from scripts.huodan_api import auto_generate_huodan
from scripts.excel_utils import download_excel, get_sheet_columns, read_excel_data, create_standard_huodan
from scripts.precheck import precheck_huodan
from scripts.file_upload import upload_file
from scripts.export_report import export_exception_report
```

## 工作流程

### 第〇步：确认 Cookie 有效

所有 API 调用都需要有效的 Cookie。Cookie 持久化存储在技能目录下的 `.cookie` 文件中，跨 Session 自动复用。在开始任何操作之前，调用 `get_cookie()` 检查 Cookie 状态：

```python
from scripts.check_cookie import get_cookie, set_cookie

try:
    cookie = get_cookie()
    # Cookie 存在且有效，直接进入下一步
except RuntimeError as e:
    # Cookie 不存在或已失效，提示用户提供新的 Cookie
    print(e)
```

`get_cookie()` 内部会自动完成以下流程：

1. 从 `.cookie` 文件读取 Cookie（如果文件不存在，会兼容读取环境变量 `TICKETFLOW_COOKIE` 并自动写入文件）
2. 通过轻量级 API 调用校验 Cookie 是否仍然有效
3. 如果有效，直接返回 Cookie 值
4. 如果无效或不存在，抛出 `RuntimeError` 异常

当 `get_cookie()` 抛出异常时，提示用户提供最新的 Cookie 值，然后调用 `set_cookie()` 保存：

```python
from scripts.check_cookie import set_cookie

# 用户提供新的 Cookie 后
set_cookie("用户提供的cookie值")
# set_cookie 会校验有效性，通过后自动写入 .cookie 文件
```

### 第一步：获取工单信息

从用户指令中提取工单编号（如 `T000117738002663038508819`），工单编号通常以 `T` 开头。

#### 1.1 查询工单列表

使用 `scripts/ticket_api.py` 中的 `get_ticket_by_code()` 函数获取工单基本信息：

```python
from scripts.ticket_api import get_ticket_by_code

ticket_info = get_ticket_by_code("T000117738002663038508819")
# 返回 dict: 工单信息，包含 id, shopId, code, brdFile 等
# 未找到则返回 None
```

关键字段说明：

- `id`: 工单 ID，后续查详情和提交更新时使用
- `shopId`: 店铺 ID，生成活动货单时使用
- `code`: 工单编号
- `brdFile`: 原始货单文件列表，每项含 `fileName`, `fileUrl`, `fileSize`
- `status`: 工单状态，应为 `"INIT"`（待处理）

如果未找到工单，提示用户确认工单编号是否正确，或工单状态是否为待处理（INIT）。

#### 1.2 获取工单详情

拿到工单 ID 后，使用 `get_ticket_detail()` 获取完整工单详情：

```python
from scripts.ticket_api import get_ticket_detail

ticket_detail = get_ticket_detail(ticket_info["id"])
# 返回 dict: 工单详细信息
```

详情中需要关注的字段：

- `brdFile`: 原始货单文件信息（后续 Step 2 使用）
- `detail`: 工单明细信息
- `shopId`: 店铺 ID
- 其他字段在 Step 6 构建更新请求时需要完整保留

### 第二步：生成活动货单

#### 2.1 尝试自动生成活动货单

从上一步的 `brdFile` 中提取原始货单文件 URL，调用自动生成接口：

```python
from scripts.huodan_api import auto_generate_huodan

result = auto_generate_huodan(
    shop_id=ticket_detail["shopId"],
    file_url=ticket_detail["brdFile"][0]["fileUrl"]
)
# 返回 dict: {"sheets": [...], "standardFileUrl": "...", "columnContent": {...}}
# 如果 standardFileUrl 非空，说明自动生成成功
```

**判断结果**：

- `result["standardFileUrl"]` 非空 → 自动生成成功，记录生成方式为 `"auto"`，进入 Step 3
- `result["standardFileUrl"]` 为空或 `result` 为 `None` → 自动生成失败，进入 Step 2.2

#### 2.2 手动生成活动货单（需要用户交互）

当自动生成失败时，需要引导用户完成原始货单列与活动货单标准列的对应关系。

**步骤一：下载并解析原始货单**

```python
from scripts.excel_utils import download_excel, get_sheet_columns

local_path = download_excel(ticket_detail["brdFile"][0]["fileUrl"])
columns_info = get_sheet_columns(local_path)
# 返回 dict: {sheet_name: [column_names]}
```

**步骤二：展示列名并请求用户确认对应关系**

活动货单标准列名称为：
| 标准列名 | 说明 |
|---------|------|
| 商品名称 | 商品名称 |
| 商品SPU | 商品款号 |
| 商品SKU | 商品条码 |
| 吊牌价 | 原始吊牌价 |
| 奥莱价 | 奥莱售价 |
| 库存 | 库存数量 |
| 品类 | 商品品类 |
| 颜色 | 颜色 |
| 尺码 | 尺码 |
| 季节 | 季节 |
| 性别 | 性别 |

将原始货单的列名称展示给用户，让用户指定每个标准列对应原始文件中的哪一列。如果原始文件中没有某个标准列的对应列，用户可以标记为"无"。

**务必等用户确认对应关系正确后再继续生成活动货单文件。**

**步骤三：根据映射关系生成标准活动货单**

```python
from scripts.excel_utils import read_excel_data, create_standard_huodan

original_data = read_excel_data(local_path, sheet_name="Sheet1")

column_mapping = {
    "商品名称": "用户指定的原始列名",
    "商品SPU": "款号",
    "商品SKU": "条码",
    "吊牌价": "吊牌价",
    "奥莱价": "奥莱价",
    "库存": "库存数",
    "品类": None,
    "颜色": "颜色",
    "尺码": "尺码名称",
    "季节": "季节名称",
    "性别": "性别名称"
}

output_path = create_standard_huodan(original_data, column_mapping, output_dir="/tmp")
# 返回 str: 生成的标准活动货单文件路径
```

记录生成方式为 `"local"`。

### 第三步：活动货单预检

对活动货单进行数据完整性和合规性校验。

**如果是自动生成的活动货单**，先下载文件：

```python
from scripts.excel_utils import download_excel, read_excel_data

huodan_path = download_excel(result["standardFileUrl"])
huodan_data = read_excel_data(huodan_path)
```

**如果是本地生成的活动货单**，直接读取：

```python
from scripts.excel_utils import read_excel_data

huodan_data = read_excel_data(output_path)
```

**执行预检**：

```python
from scripts.precheck import precheck_huodan

check_result = precheck_huodan(huodan_data)
# 返回 dict:
# {
#     "passed": bool,
#     "total_rows": int,
#     "valid_rows": int,
#     "deduped_count": int,       # 完全重复被去重的行数
#     "exceptions": [             # 异常列表
#         {
#             "type": "missing_data|duplicate_conflict|invalid_price|negative_stock",
#             "rows": [行号列表],
#             "field": "字段名",
#             "detail": "异常描述",
#             "samples": [示例数据]
#         }
#     ],
#     "clean_data": [dict]        # 去重且通过校验的数据
# }
```

#### 检验规则

1. **数据完整性**：SPU、SKU、吊牌价、奥莱价、库存、品类、季节、性别、颜色、尺码 — 任何字段存在缺失则标记异常
2. **重复检查**：
   - 完全重复的行 → 自动去重（记录去重数量）
   - 同 SPU/SKU 但部分字段不同 → 标记异常
3. **价格检查**：吊牌价或奥莱价 ≤ 0 → 标记异常
4. **库存检查**：库存 < 0 → 标记异常

### 第四步：检验反馈

根据预检结果决定后续操作：

#### 存在异常 → 终止任务

```python
from scripts.export_report import export_exception_report

if not check_result["passed"]:
    report_path = export_exception_report(
        ticket_code=ticket_detail["code"],
        exceptions=check_result["exceptions"],
        output_dir="/tmp"
    )
```

向用户反馈异常信息，提示格式如：

> 工单编号 T000117738002663038508819，原始货单文件缺少品类信息/货单SKU异常/货单价格异常/货单库存异常...，请修正后重新上传。

同时附上异常数据的 Excel 报告文件，并**终止任务**。

#### 预检通过 → 继续提交

如果 `check_result["passed"]` 为 `True`，进入下一步。

### 第五步：货单文件上传

**如果活动货单是自动生成的（`"auto"`），跳过此步骤**，直接使用 `standardFileUrl` 作为活动货单文件 URL。

如果是本地生成的活动货单（`"local"`），需要上传文件：

```python
from scripts.file_upload import upload_file

upload_result = upload_file(output_path)
# 返回 dict:
# {
#     "url": "https://ossmp.shanshan-business.com/xxx.xlsx",
#     "name": "活动货单文件名.xlsx",
#     "size": 12345
# }
```

上传成功后，`upload_result["url"]` 即为活动货单文件 URL，`upload_result["name"]` 为文件名。

### 第六步：货单提交

汇总前面步骤的数据，构建并提交工单更新请求：

```python
from scripts.ticket_api import submit_ticket_update

# 确定活动货单文件信息
if generate_mode == "auto":
    huodan_file_url = result["standardFileUrl"]
    huodan_file_name = huodan_file_url.split("/")[-1]
else:
    huodan_file_url = upload_result["url"]
    huodan_file_name = upload_result["name"]

# 从预检通过的数据中提取唯一 SPU 列表
spu_column = "商品SPU"
unique_spus = list(set(
    row[spu_column] for row in check_result["clean_data"]
    if row.get(spu_column)
))

# 标准列名映射
standard_columns = {
    "spuColumn": "商品SPU",
    "skuColumn": "商品SKU",
    "oriPriceColumn": "吊牌价",
    "aolaiColumn": "奥莱价",
    "stockColumn": "库存",
    "colorColumn": "颜色",
    "sizeColumn": "尺码"
}

update_result = submit_ticket_update(
    ticket_detail=ticket_detail,
    huodan_file_url=huodan_file_url,
    huodan_file_name=huodan_file_name,
    unique_spus=unique_spus,
    goods_count=len(check_result["clean_data"]),
    column_mapping=standard_columns
)
# 返回 dict: API 响应
```

提交成功后反馈用户：

> 工单 T000117738002663038508819，货单预处理成功，活动货单已更新，请尽快提交并提醒门店进行确认。

同时附上活动货单 Excel 文件。

## 错误处理

### Cookie 过期或无效

API 返回认证失败（HTTP 401 或 errcode 非 0 且提示权限相关）时：

1. 调用 `clear_cookie_file()` 清除 `.cookie` 文件中的无效值
2. 提示用户提供最新的 Cookie 值
3. 调用 `set_cookie(new_cookie_value)` 校验并保存新 Cookie
4. 重试失败的操作

```python
from scripts.check_cookie import clear_cookie_file, set_cookie

clear_cookie_file()
# 提示用户提供新 Cookie 后
set_cookie("用户提供的新cookie值")
```

### 工单未找到

`get_ticket_by_code()` 返回 `None` 时，可能原因：

1. 工单编号输入错误
2. 工单状态不是 `INIT`（已被处理）
3. 当前用户无权查看该工单

提示用户确认工单编号并核实工单状态。

### 原始货单文件无法下载

`download_excel()` 抛出异常时：

1. 检查文件 URL 是否有效
2. 检查网络连接
3. 确认文件是否已过期被删除

### 自动生成失败

`auto_generate_huodan()` 返回空 `standardFileUrl`：这是正常情况，系统无法自动识别原始货单的列结构，进入手动映射流程即可。

### API 调用失败

所有脚本在 API 返回 `errcode != 0` 时会抛出 `Exception`。捕获异常后：

1. 记录具体的错误信息（`errmsg`）
2. 判断是网络问题、权限问题还是数据问题
3. 如果是 Cookie 过期，提示用户重新提供

## 脚本函数速查

| 脚本文件           | 函数                                                                                                               | 参数                              | 返回值                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------- | ---------------------------- |
| `check_cookie.py`  | `get_cookie()`                                                                                                     | 无                                | `str`（有效 Cookie 值）      |
| `check_cookie.py`  | `set_cookie(cookie_value)`                                                                                         | `str`                             | `str`（写入成功的 Cookie）   |
| `check_cookie.py`  | `validate_cookie(cookie)`                                                                                          | `str`                             | `bool`                       |
| `check_cookie.py`  | `clear_cookie_file()`                                                                                              | 无                                | `None`                       |
| `ticket_api.py`    | `get_ticket_by_code(ticket_code)`                                                                                  | `str`                             | `dict \| None`               |
| `ticket_api.py`    | `get_ticket_detail(ticket_id)`                                                                                     | `int`                             | `dict`                       |
| `ticket_api.py`    | `submit_ticket_update(ticket_detail, huodan_file_url, huodan_file_name, unique_spus, goods_count, column_mapping)` | `dict, str, str, list, int, dict` | `dict`                       |
| `huodan_api.py`    | `auto_generate_huodan(shop_id, file_url)`                                                                          | `int, str`                        | `dict \| None`               |
| `excel_utils.py`   | `download_excel(url, save_dir="/tmp")`                                                                             | `str, str`                        | `str`（本地文件路径）        |
| `excel_utils.py`   | `get_sheet_columns(file_path)`                                                                                     | `str`                             | `dict`（{sheet: [columns]}） |
| `excel_utils.py`   | `read_excel_data(file_path, sheet_name=None)`                                                                      | `str, str?`                       | `list[dict]`                 |
| `excel_utils.py`   | `create_standard_huodan(data, column_mapping, output_dir="/tmp")`                                                  | `list, dict, str`                 | `str`（输出文件路径）        |
| `precheck.py`      | `precheck_huodan(data)`                                                                                            | `list[dict]`                      | `dict`（预检结果）           |
| `file_upload.py`   | `upload_file(file_path)`                                                                                           | `str`                             | `dict`（含 url, name, size） |
| `export_report.py` | `export_exception_report(ticket_code, exceptions, output_dir="/tmp")`                                              | `str, list, str`                  | `str`（报告文件路径）        |
