---
name: goods_review_audit
description: 商品检查审核技能。当用户要求审核商品、检查商品合规性、进行商品数字化处理时使用此技能。支持多门店多品牌的商品自动审核流程，包括商品信息校验、图片质量检测、智能抠图处理等。典型触发场景："审核宁波店LE COQ SPORTIF商品"、"检查某门店某品牌商品"、"批量审核店铺商品"。即使用户只是提到"商品审核"、"审核一下"、"过一下商品"，也应使用此技能。
compatibility: 需要 Python 3.9+、requests 库、图像查看能力（用于主图质量判断）
---

# 商品检查审核技能

本技能用于自动化审核杉杉奥莱各门店的商品信息，确保商品数字化质量符合平台标准。

## 脚本执行方式

`scripts/` 目录中的脚本都是独立的 Python 文件，每个文件内包含可调用的函数。所有 API 调用都依赖环境变量 `GOODS_AUDIT_COOKIE` 进行身份认证。

**执行脚本有两种方式**：

1. **Shell 直接运行**（适合快速测试）：`python scripts/xxx.py`
2. **在 Python 代码中导入**（推荐用于流程编排）：需要先确保导入路径正确，例如：

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from scripts.plaza_code_map import get_plaza_code
from scripts.get_shop_id import get_shop_id
from scripts.query_goods import query_goods_list, extract_goods_info
from scripts.query_template import query_template_category
from scripts.remove_background import remove_background
from scripts.update_gallery import update_gallery
from scripts.mark_white_pic import mark_white_pic
from scripts.approve_goods import approve_goods
```

## 工作流程

### 第〇步：确认 Cookie 有效

所有 API 调用都需要有效的 Cookie。在开始任何操作之前，先检查环境变量 `GOODS_AUDIT_COOKIE` 是否已设置：

```python
import os
cookie = os.getenv("GOODS_AUDIT_COOKIE")
```

- 如果 `cookie` 为空或 `None`，提示用户提供 Cookie 值，然后设置环境变量：
  ```bash
  export GOODS_AUDIT_COOKIE="用户提供的cookie值"
  ```
- 如果已存在，可直接进入下一步。

也可以运行 `scripts/check_cookie.py` 中的 `check_and_set_cookie()` 来完成检查，但注意该函数在无交互环境下会调用 `input()` 导致阻塞，建议直接通过 Shell 设置环境变量。

### 第一步：解析用户指令

从用户指令中提取**门店名称**和**店铺（品牌）名称**：

```
用户指令：审核宁波店LE COQ SPORTIF(乐卡克公鸡)商品
门店名称：宁波店
店铺名称：LE COQ SPORTIF(乐卡克公鸡)
```

如果用户指令中的信息不完整，需要询问用户提供：

- 具体的门店名称
- 具体的店铺/品牌名称

### 第二步：获取门店编号

`scripts/plaza_code_map.py` 中定义了门店名称到 plazaCode 的映射。调用 `get_plaza_code()` 函数：

```python
from scripts.plaza_code_map import get_plaza_code

plaza_code = get_plaza_code("宁波店")  # 返回 "0001"，找不到则返回 None
```

如果返回 `None`，说明门店不在支持列表中，告知用户。支持的门店：宁波店、哈尔滨店、郑州中牟店、晋中店、南昌店、赣州店、兰州店、乌鲁木齐店、衡阳店、沈阳店、贵阳店、深圳店、南宁店、徐州店、太原店、天津店、郑州二七店、成都店、大连店、合肥店、武汉店、长沙店、无锡店。

### 第三步：获取店铺 ID

使用 `scripts/get_shop_id.py` 中的 `get_shop_id()` 函数：

```python
from scripts.get_shop_id import get_shop_id

shop_id = get_shop_id(plaza_code, "LE COQ SPORTIF(乐卡克公鸡)")
# 返回 int 类型的店铺ID，未找到返回 None
```

匹配逻辑：先精确匹配 `name` 字段，若未命中再做模糊匹配（互相包含关系）。

如果返回 `None`，说明在该门店下找不到此店铺/品牌，提示用户确认名称是否正确。

### 第四步：查询商品信息

使用 `scripts/query_goods.py` 中的 `query_goods_list()` 获取待审核商品列表：

```python
from scripts.query_goods import query_goods_list, extract_goods_info

goods_list = query_goods_list(plaza_code, shop_id)
# 返回 list[dict]，每个 dict 是一个商品的完整数据
```

该函数默认查询 `approveStatus="A"`（待审核）的商品。返回结果包含商品的基本信息、价格、库存、图片等全部字段。

对每个商品，使用 `extract_goods_info()` 提取关键信息：

```python
goods_info = extract_goods_info(goods_list[0])
# 返回包含以下字段的 dict:
# id, goodsSn, name, goodsTitle, shopId, shopName,
# brandId, categoryNames, parentCategoryName,
# categoryGender, categorySeason,
# minOriPrice, maxOriPrice, minCurPrice, maxCurPrice, discountRate,
# galleryCount (主图数量，由 len(gallery) 计算),
# detailImgCount (详情图数量，由正则匹配 detail HTML 中 <img> 标签计算),
# gallery (主图URL列表), detail (详情HTML原始内容),
# picUrl, skuPicUrls, productList, approveStatus, enabled
```

**注意**：API 返回的 `picCount` 和 `detailCount` 字段不可靠（常为0），`extract_goods_info` 已改为通过实际数据计算 `galleryCount` 和 `detailImgCount`。

### 第五步：商品信息合规性检测

对每个商品进行以下检查：

#### 5.1 基本信息完整性

- **SPU编码** (`goodsSn`): 必须存在且非空
- **商品名称** (`name`): 不得为空
- **商品标题** (`goodsTitle`): 不得少于5个中文字符
- **品牌信息** (`brandId`): 必须存在
- **分类信息** (`categoryNames`): 必须存在
- **性别/季节** (`categoryGender`, `categorySeason`): 必须填写

#### 5.2 价格合规性

- **奥莱价** (`minCurPrice`, `maxCurPrice`): 必须大于零
- **吊牌价** (`minOriPrice`, `maxOriPrice`): 必须大于等于奥莱价

#### 5.3 标题敏感词检测

参考 `references/sensitive_words.md` 中定义的敏感词库，对商品标题进行检测。该文件中包含了敏感词列表和一个示例检测函数 `check_sensitive_words`，可以直接复制该逻辑在内存中执行：

```python
SENSITIVE_WORDS = {
    "毒品", "赌博", "色情", "暴力", "诈骗", "传销", "枪支", "假货", "水货",
    "最", "第一", "顶级", "独一无二", "史无前例", "全网", "国家级", "世界级",
    "假一赔十", "绝对", "肯定", "100%", "保证", "无效退款",
    "盗版", "山寨", "仿版", "A货", "超A",
}

def check_sensitive_words(text: str) -> tuple[bool, list[str]]:
    found = [w for w in SENSITIVE_WORDS if w in text]
    return len(found) == 0, found
```

**检查范围**：商品标题 (`goodsTitle`)、商品名称 (`name`)

**检查项**：

- 标题长度不少于5个中文字符
- 违禁词：毒品、赌博、色情、暴力等
- 极限词：最、第一、顶级、全网等
- 虚假宣传：假一赔十、绝对、100%等

#### 5.4 属性一致性

检查以下字段之间的一致性：

- 品牌标题与品牌 ID
- 颜色与 SKU 规格
- 分类与分类名称
- 季节与性别标签

### 第六步：商品图片质量检测

#### 6.1 手拍图检测

使用图像查看能力（如 MCP browser 工具或其他图像工具）打开商品主图 URL，逐张判断是否为手拍图。判断标准：

- 拍摄角度是否随意（非专业产品摄影）
- 背景是否杂乱或不统一
- 是否有明显的生活场景痕迹
- 光影是否不均匀

如果发现手拍图，标记为不通过。

#### 6.2 图片数量检测

```python
gallery_count = goods_info.get('galleryCount', 0)      # 主图数量
detail_img_count = goods_info.get('detailImgCount', 0)  # 详情图数量
```

- 商品主图：至少3张
- 商品详情图：至少5张
- 额外检查：主图 URL 是否有重复（`gallery` 列表中相同 URL 出现多次视为问题）

不满足时记录具体的缺少数量。

#### 6.3 图片质量检测

使用图像查看工具检查每张主图：

1. **清晰度**：图片清晰，无模糊
2. **违规信息**：无违规文字、图案
3. **平台信息**：无淘宝、京东、抖音、唯品会等平台标识或水印
4. **完整性**：商品完整展示，无遮挡

#### 6.4 图片完整性检测

查看 `gallery` 字段中的图片 URL，检查是否包含以下类型：

- 正面图：展示商品正面
- 背面图：展示商品背面
- 细节图：展示商品细节特征
- 吊牌图：展示品牌吊牌和标签
- 尺码表图：展示尺码信息
- 颜色图：不同颜色的商品展示

### 第七步：智能抠图处理

对于通过图片检测的商品，进行白底图抠图处理。

#### 7.1 查询模板分类

使用 `scripts/query_template.py` 中的 `query_template_category()` 函数：

```python
from scripts.query_template import query_template_category

template_category = query_template_category(goods_id)
# 返回 str 类型的模板分类名称，默认 "其他"
```

#### 7.2 选择抠图源图片

按以下优先级选择：

1. 商品主图第一张 (`gallery[0]`)
2. 纯色背景模特图
3. 非纯色背景模特图

```python
source_pic_url = goods_info.get('gallery', [])[0]
```

#### 7.3 执行抠图

使用 `scripts/remove_background.py` 中的 `remove_background()` 函数：

```python
from scripts.remove_background import remove_background

processed_pic_url = remove_background(
    goods_id=goods_id,
    pic_url=source_pic_url,
    template_name=template_category,
)
# 返回 str: 抠图后的图片 URL；失败返回空字符串 ""
```

如果返回空字符串，说明抠图失败，标记为不通过。

#### 7.4 抠图质量校验

使用图像查看工具打开 `processed_pic_url`，检查：

- 背景是否为纯白色
- 商品是否完整（无缺失部分）
- 边缘是否自然（无明显锯齿或残留）

#### 7.5 更新主图

使用 `scripts/update_gallery.py` 中的 `update_gallery()` 函数，将白底图设为主图第一张：

```python
from scripts.update_gallery import update_gallery

success = update_gallery(
    goods_id=goods_id,
    processed_pic_url=processed_pic_url,
    template_category=template_category,
)
# 返回 bool: 成功返回 True，失败抛出异常
```

#### 7.6 标记白底图

使用 `scripts/mark_white_pic.py` 中的 `mark_white_pic()` 函数：

```python
from scripts.mark_white_pic import mark_white_pic

success = mark_white_pic(goods_id)
# 返回 bool: 成功返回 True，失败抛出异常
# 可选参数 force_override=True 强制覆盖已有标记
```

### 第八步：商品审核决策

#### 8.1 审核通过条件

只有同时满足以下所有条件的商品才能自动审核通过：

1. 商品信息完整且合规
2. 价格数据有效且合理
3. 标题无敏感词且长度符合要求
4. 属性字段一致
5. 非手拍图
6. 主图数量 >= 3张
7. 详情图数量 >= 5张
8. 图片质量合格（清晰、无违规、无平台信息）
9. 必要图片类型齐全
10. 抠图成功且白底图达标

#### 8.2 审核通过

使用 `scripts/approve_goods.py` 中的 `approve_goods()` 函数：

```python
from scripts.approve_goods import approve_goods

approve_count, fail_reasons = approve_goods([goods_id])
# 返回 tuple[int, list[str]]:
#   approve_count: 成功审核的数量
#   fail_reasons: 失败原因列表（为空表示全部成功）
```

支持批量审核多个商品：`approve_goods([id1, id2, id3])`。

**注意**：即使本地检测全部通过，API 端仍可能因业务规则拒绝审核，常见原因：

- "无共享库商品，无法审核"：商品尚未关联共享库，需运营人员先完成关联
- 其他后端校验失败

当 `approve_count == 0` 且 `fail_reasons` 非空时，将 API 返回的失败原因一并汇报给用户。

#### 8.3 审核不通过

对于不符合条件的商品，记录不通过原因，**不调用 `approve_goods`**。将原因汇总到最终报告中。

### 第九步：输出审核结果

按照以下格式向用户汇报审核结果：

```
【审核完成】

当前店铺 LE COQ SPORTIF(乐卡克公鸡) 共有 15 款商品

✅ 审核通过：10 款
❌ 不符合要求：5 款

【不通过详情】
1. R-SPEED MESH - 主图数量不足（当前2张，要求至少3张）
2. AIR MAX 2024 - 标题包含敏感词：最
3. ULTRA BOOST - 详情图数量不足（当前4张，要求至少5张）
4. STAN SMITH - 检测到手拍图，需要重新拍摄
5. SUPERSTAR - 抠图失败，背景不够纯净

如需修改后重新审核，请通知运营人员调整商品信息。
```

- 不通过商品 <= 10款时，逐条列出详情
- 不通过商品 > 10款时，按原因类型汇总统计
- 如有 API 端审核失败的商品（本地检测通过但后端拒绝），单独列出并展示 API 返回的失败原因

## 错误处理

### 门店名称不匹配

`get_plaza_code()` 返回 `None` 时，列出所有支持的门店名称让用户选择。

### 店铺不存在

`get_shop_id()` 返回 `None` 时，提示用户确认：

1. 店铺/品牌名称是否正确
2. 该店铺是否已在该门店开业
3. 是否有该店铺的查看权限

可调用 `get_all_shops(plaza_code)` 获取该门店下全部店铺列表供用户参考。

### API 调用失败

所有脚本在 API 返回 `errcode != 0` 时会抛出 `Exception`。捕获异常后：

1. 记录具体的错误信息
2. 判断是否为网络问题、权限问题（Cookie 过期）或数据问题
3. 如果是 Cookie 过期，提示用户重新提供 Cookie

## 脚本函数速查

| 脚本文件               | 函数                                                             | 参数             | 返回值                                   |
| ---------------------- | ---------------------------------------------------------------- | ---------------- | ---------------------------------------- |
| `plaza_code_map.py`    | `get_plaza_code(store_name)`                                     | `str`            | `str \| None`                            |
| `plaza_code_map.py`    | `get_all_plaza_codes()`                                          | 无               | `dict`                                   |
| `get_shop_id.py`       | `get_shop_id(plaza_code, shop_name)`                             | `str, str`       | `int \| None`                            |
| `get_shop_id.py`       | `get_all_shops(plaza_code)`                                      | `str`            | `list`                                   |
| `query_goods.py`       | `query_goods_list(plaza_code, shop_id)`                          | `str, int`       | `list[dict]`                             |
| `query_goods.py`       | `extract_goods_info(goods)`                                      | `dict`           | `dict` (含 galleryCount, detailImgCount) |
| `query_template.py`    | `query_template_category(goods_id)`                              | `int`            | `str`                                    |
| `remove_background.py` | `remove_background(goods_id, pic_url, template_name)`            | `int, str, str`  | `str`                                    |
| `update_gallery.py`    | `update_gallery(goods_id, processed_pic_url, template_category)` | `int, str, str`  | `bool`                                   |
| `mark_white_pic.py`    | `mark_white_pic(goods_id, force_override=False)`                 | `int, bool`      | `bool`                                   |
| `approve_goods.py`     | `approve_goods(goods_ids, approve_status="Y")`                   | `list[int], str` | `tuple[int, list[str]]`                  |
| `check_cookie.py`      | `check_and_set_cookie(cookie_value=None)`                        | `str \| None`    | `str`                                    |

## 参考文档

- `references/sensitive_words.md`: 敏感词词典、检测规则和示例检测函数
