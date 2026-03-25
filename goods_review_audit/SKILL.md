---
name: goods_review_audit
description: 商品检查审核技能。当用户要求审核商品、检查商品合规性、进行商品数字化处理时使用此技能。支持多门店多品牌的商品自动审核流程，包括商品信息校验、图片质量检测、智能抠图处理等。典型触发场景："审核宁波店LE COQ SPORTIF商品"、"检查某门店某品牌商品"、"批量审核店铺商品"。即使用户只是提到"商品审核"、"审核一下"、"过一下商品"，也应使用此技能。
compatibility: 需要 Python 3.9+、requests 库、openpyxl 库（用于生成 Excel 审核报告）、图像查看能力（使用如 MCP browser 工具或其他图像工具，用于图片质量判断）
---

# 商品检查审核技能

本技能用于自动化审核杉杉奥莱各门店的商品信息，确保商品数字化质量符合平台标准。

## 脚本执行方式

`scripts/` 目录中的脚本都是独立的 Python 文件，每个文件内包含可调用的函数。所有 API 调用都依赖环境变量 `GOODS_AUDIT_COOKIE` 进行身份认证。**在执行过程中决不允许自己新创建脚本，只能使用 `scripts/` 目录中的脚本**

**执行脚本有两种方式**：

1. **Shell 直接运行**（适合快速测试）：`python scripts/xxx.py`
2. **在 Python 代码中导入**（推荐用于流程编排）：需要先确保导入路径正确，例如：

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from scripts.plaza_code_map import get_plaza_code
from scripts.get_shop_id import find_matching_shops, get_shop_id
from scripts.query_goods import query_goods_list, extract_goods_info
from scripts.query_template import query_template_category
from scripts.remove_background import remove_background
from scripts.update_gallery import update_gallery
from scripts.mark_white_pic import mark_white_pic
from scripts.approve_goods import approve_goods
from scripts.export_audit_result import export_audit_result, generate_summary_text
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

从用户指令中提取**门店名称**、**店铺（品牌）名称**和/或**商品 SPU 编码**：

```
示例1 — 审核店铺全部待审核商品：
用户指令：审核宁波店LE COQ SPORTIF(乐卡克公鸡)商品
→ 门店：宁波店，店铺：LE COQ SPORTIF(乐卡克公鸡)，SPU：无

示例2 — 审核指定 SPU 商品：
用户指令：审核宁波店LE COQ SPORTIF的R2401001和R2401002
→ 门店：宁波店，店铺：LE COQ SPORTIF，SPU：R2401001, R2401002
```

SPU 编码通常是字母+数字的组合（如 `R2401001`、`LCS-2024-001`），用户可能以逗号、空格或换行分隔多个编码。

如果用户指令信息不完整，至少需要**门店名称**和**店铺名称**才能查询，请询问用户补充。

### 第二步：获取门店编号

`scripts/plaza_code_map.py` 中定义了门店名称到 plazaCode 的映射。调用 `get_plaza_code()` 函数：

```python
from scripts.plaza_code_map import get_plaza_code

plaza_code = get_plaza_code("宁波店")  # 返回 "0001"，找不到则返回 None
```

如果返回 `None`，说明门店不在支持列表中，告知用户。支持的门店：宁波店、哈尔滨店、郑州中牟店、晋中店、南昌店、赣州店、兰州店、乌鲁木齐店、衡阳店、沈阳店、贵阳店、深圳店、南宁店、徐州店、太原店、天津店、郑州二七店、成都店、大连店、合肥店、武汉店、长沙店、无锡店。

### 第三步：获取店铺 ID

使用 `scripts/get_shop_id.py` 中的 `find_matching_shops()` 函数，返回所有匹配的店铺列表。同一门店下同品牌可能存在多个店铺（如不同楼层或区域），需要根据返回结果数量决定是否让用户确认：

```python
from scripts.get_shop_id import find_matching_shops

matches = find_matching_shops(plaza_code, "LE COQ SPORTIF")
# 返回 list[dict]，每项含 {"id": int, "name": str}

if len(matches) == 1:
    # 唯一匹配，直接使用，无需用户确认
    shop_id = matches[0]["id"]
elif len(matches) > 1:
    # 同一门店存在多个匹配店铺，列出供用户选择
    # 示例输出：
    #   1. 店铺ID: 123, 名称: LE COQ SPORTIF 1店
    #   2. 店铺ID: 456, 名称: LE COQ SPORTIF 2店
    # 等待用户指定后，使用对应的 shop_id
    pass
else:
    # 未找到匹配，提示用户确认名称或调用 get_all_shops() 列出该门店全部店铺
    pass
```

匹配逻辑：先收集精确匹配结果，若无精确匹配再收集模糊匹配结果（互相包含关系）。

### 第四步：查询商品信息

使用 `scripts/query_goods.py` 获取商品信息。根据第一步的解析结果选择查询方式：

#### 场景A：查询店铺全部待审核商品

当用户未指定 SPU 编码，需审核某店铺全部待审核商品时：

```python
from scripts.query_goods import query_goods_list, extract_goods_info

goods_list = query_goods_list(plaza_code, shop_id)
# 返回 list[dict]，每个 dict 是一个商品的完整数据
```

#### 场景B：按 SPU 编码查询指定商品

当用户指令中包含 SPU 编码时，使用 `find_goods_by_sn()` 精确查询指定商品：

```python
from scripts.query_goods import find_goods_by_sn, extract_goods_info

# 单个 SPU
goods = find_goods_by_sn(plaza_code, shop_id, "R2401001")
if goods:
    goods_list = [goods]

# 多个 SPU
spu_codes = ["R2401001", "R2401002", "R2401003"]
goods_list = []
not_found = []
for spu in spu_codes:
    result = find_goods_by_sn(plaza_code, shop_id, spu)
    if result:
        goods_list.append(result)
    else:
        not_found.append(spu)
# 如有未找到的 SPU，告知用户（可能编码有误、不属于该店铺或非待审核状态）
```

两种场景都默认只查询 `approveStatus="A"`（待审核）的商品。如果按 SPU 查询未找到结果，提示用户该商品可能编码有误、不属于该店铺，或已不在待审核状态。

#### 提取关键信息

无论使用哪种查询方式，对每个商品都使用 `extract_goods_info()` 提取关键信息：

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
- **SKU编码** (`productList`): 遍历列表检查`skuCode`必须存在且非空
- **商品名称** (`name`): 不得为空，不得少于5个中文字符
- **品牌信息** (`brandId`): 必须存在
- **分类信息** (`categoryNames`): 必须存在
- **性别/季节** (`categoryGender`, `categorySeason`): 必须填写

#### 5.2 价格合规性

- **奥莱价** (`minCurPrice`, `maxCurPrice`): 必须大于零
- **吊牌价** (`minOriPrice`, `maxOriPrice`): 必须大于等于奥莱价

#### 5.3 标题敏感词检测

参考 `references/sensitive_words.md` 中定义的敏感词库，对商品名称进行检测。该文件中包含了敏感词列表和一个示例检测函数 `check_sensitive_words`，可以直接复制该逻辑在内存中执行：

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

**检查范围**：商品名称 (`name`)

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
sku_pic_urls = goods_info.get('skuPicUrls', [])         # 颜色图列表
```

- 商品主图：至少3张
- 商品详情图：至少5张
- 额外检查：主图 URL 是否有重复（`gallery` 列表中相同 URL 出现多次视为问题）
- 颜色图检测：先检查 `skuPicUrls` 是否为空列表。如果 `skuPicUrls` 非空，再逐项检查列表中每个元素的 `picUrl` 字段是否为空——`picUrl` 为空说明该颜色缺少对应的展示图片，需要记录具体是哪个颜色缺图

```python
if sku_pic_urls:
    missing_pic_skus = [
        sku for sku in sku_pic_urls
        if not sku.get('picUrl')
    ]
    if missing_pic_skus:
        # 记录缺少颜色图的 SKU 信息，汇报给用户
        pass
```

不满足时记录具体的缺少数量。

#### 6.3 图片质量检测

使用图像查看能力（如 MCP browser 工具或其他图像工具）检查每张主图：

1. **清晰度**：图片清晰，无模糊
2. **违规信息**：无违规文字、图案
3. **平台信息**：无淘宝、京东、抖音、唯品会等平台标识或水印
4. **完整性**：商品完整展示，无遮挡

#### 6.4 图片完整性检测

使用图像查看能力（如 MCP browser 工具或其他图像工具）查看 `gallery` 字段中的图片 URL，检查是否包含以下类型：

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

抠图的目标是生成干净的白底商品图，因此源图片必须展示完整的商品主体。在第六步图片检测中已识别出每张主图的类型，这里利用这些信息筛选和排序。

**可抠图判断标准**

先使用图像查看能力（如 MCP browser 工具或其他图像工具）遍历 `gallery` 中所有主图，根据图片类型标记是否适合抠图：

| 图片类型           | 可抠图 | 原因                                   |
| ------------------ | ------ | -------------------------------------- |
| 正面图（纯色背景） | ✅     | 背景简单，商品完整，抠图效果最佳       |
| 正面图（复杂背景） | ✅     | 商品完整，但复杂背景可能影响边缘质量   |
| 背面图（纯色背景） | ✅     | 可作为备选，展示完整商品背面           |
| 背面图（复杂背景） | ✅     | 可用，但优先级低于纯色背景             |
| 颜色图             | ✅     | 展示完整商品，可用于该色系的白底图     |
| 模特图（纯色背景） | ✅     | 适合服装类，人+商品一起抠出效果好      |
| 模特图（复杂背景） | ⚠️     | 勉强可用，背景复杂容易残留，优先级最低 |
| 细节图             | ❌     | 仅展示局部，无法生成完整商品白底图     |
| 吊牌图             | ❌     | 非商品主体，不适合作为白底图           |
| 尺码表图           | ❌     | 信息图表，非商品实拍                   |
| 手拍图             | ❌     | 第六步已标记不通过，背景杂乱且不专业   |
| 模糊/遮挡图        | ❌     | 无法保证抠图质量                       |

**优先级选择逻辑**

在标记为可抠图（✅）的图片中，按以下优先级选择源图片：

1. **纯色背景正面图** — 背景干净、商品完整居中，抠图成功率最高
2. **纯色背景模特图** — 适合服装品类，人模搭配展示效果好
3. **纯色背景背面图** — 备选方案，适用于正面图缺失的情况
4. **复杂背景正面图** — 商品完整但背景复杂，抠图可能需要后续校验
5. **颜色图** — 通常背景较简单，可作为补充
6. **复杂背景模特图（⚠️）** — 最后手段，使用时需额外关注抠图质量

如果所有主图均不可抠图（全部为细节图、吊牌图等），标记该商品"无可用抠图源"并跳过抠图步骤，在最终报告中说明原因。

```python
def select_cutout_source(gallery_images, image_types):
    """
    gallery_images: gallery URL 列表
    image_types: 第六步中识别的每张图的类型信息列表，
                 每项包含 {'url': str, 'type': str, 'bg': 'pure'|'complex'|'unknown'}
    """
    priority_order = [
        lambda img: img['type'] == '正面图' and img['bg'] == 'pure',
        lambda img: img['type'] == '模特图' and img['bg'] == 'pure',
        lambda img: img['type'] == '背面图' and img['bg'] == 'pure',
        lambda img: img['type'] == '正面图' and img['bg'] == 'complex',
        lambda img: img['type'] == '颜色图',
        lambda img: img['type'] == '模特图' and img['bg'] == 'complex',
    ]

    not_suitable = {'细节图', '吊牌图', '尺码表图', '手拍图'}

    for check in priority_order:
        for img in image_types:
            if img['type'] not in not_suitable and check(img):
                return img['url']

    return None  # 无可用抠图源
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

使用图像查看能力（如 MCP browser 工具或其他图像工具）打开 `processed_pic_url`，检查：

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

审核结果分两部分输出：**文字总结**给用户快速了解全局，**Excel 报告**提供每个商品的完整审核详情。使用 `scripts/export_audit_result.py` 完成生成和导出。

在审核过程中（第五步到第八步），逐步为每个商品构建如下结构的审核结果数据，供本步骤使用：

```python
all_goods_results = [
    {
        "goodsSn": "R2401001",
        "name": "商品名称",
        "passed": True,
        "fail_reasons": [],
        "checks": [
            {"name": "基本信息完整性", "passed": True, "detail": ""},
            {"name": "价格合规性", "passed": True, "detail": ""},
            {"name": "主图数量", "passed": False, "detail": "当前2张，要求至少3张"},
        ],
    },
]
```

#### 9.1 生成 Excel 报告并输出文字总结

调用前确保已安装依赖：`pip install openpyxl`（`requests` 同理，其他步骤已在使用）。

```python
from scripts.export_audit_result import export_audit_result, generate_summary_text

excel_path = export_audit_result(all_goods_results, store_name, shop_name)
summary = generate_summary_text(store_name, shop_name, all_goods_results)
print(summary)
```

`export_audit_result()` 生成 Excel 报告（单个 Sheet）并返回文件路径。**不要把文件路径展示给用户**，而是将该文件作为附件发送给用户（例如通过 `present_files` 工具或平台的附件发送机制）。

**审核报告** — 每行一个商品，每个检查项透视为独立列

| 列类型               | 列名                                                                      | 内容                                               |
| -------------------- | ------------------------------------------------------------------------- | -------------------------------------------------- |
| 固定列               | 序号                                                                      | 从 1 开始编号                                      |
| 固定列               | SPU编码                                                                   | `goodsSn`                                          |
| 固定列               | 商品名称                                                                  | `name`                                             |
| 固定列               | 审核结果                                                                  | "通过"（绿色）或 "不通过"（红色）                  |
| 检查项列（动态生成） | 基本信息完整性、价格合规性、敏感词检测、属性一致性、主图数量、详情图数量… | 通过显示"通过"（绿色），不通过显示具体原因（红色） |
| 汇总列               | 不通过原因汇总                                                            | 所有不通过原因用分号分隔，通过则留空               |

检查项列名从 `all_goods_results` 中动态收集（遍历所有商品的 `checks` 数组取唯一 `name` 值），保持首次出现顺序。

`generate_summary_text()` 返回格式化的文字总结，直接输出给用户即可，示例效果：

```
【审核完成】

门店：宁波店 | 店铺：LE COQ SPORTIF(乐卡克公鸡)
商品总数：15 款

✅ 审核通过：10 款
❌ 审核不通过：5 款

详细审核报告见附件 Excel 文件。
```

如有 API 端审核失败的商品（本地检测通过但后端拒绝），文字总结中会额外提示，例如："⚠️ 其中 2 款商品本地检测通过但后端审核被拒，具体原因见 Excel 报告"。

## 错误处理

### 门店名称不匹配

`get_plaza_code()` 返回 `None` 时，列出所有支持的门店名称让用户选择。

### 店铺匹配异常

`find_matching_shops()` 返回空列表时，提示用户确认：

1. 店铺/品牌名称是否正确
2. 该店铺是否已在该门店开业
3. 是否有该店铺的查看权限

可调用 `get_all_shops(plaza_code)` 获取该门店下全部店铺列表供用户参考。

`find_matching_shops()` 返回多个结果时，说明同一门店下存在多个匹配的店铺（如同品牌在不同楼层或区域），将匹配列表展示给用户并请其选择目标店铺后再继续。

### API 调用失败

所有脚本在 API 返回 `errcode != 0` 时会抛出 `Exception`。捕获异常后：

1. 记录具体的错误信息
2. 判断是否为网络问题、权限问题（Cookie 过期）或数据问题
3. 如果是 Cookie 过期，提示用户重新提供 Cookie

## 脚本函数速查

| 脚本文件                 | 函数                                                              | 参数             | 返回值                                   |
| ------------------------ | ----------------------------------------------------------------- | ---------------- | ---------------------------------------- |
| `plaza_code_map.py`      | `get_plaza_code(store_name)`                                      | `str`            | `str \| None`                            |
| `plaza_code_map.py`      | `get_all_plaza_codes()`                                           | 无               | `dict`                                   |
| `get_shop_id.py`         | `find_matching_shops(plaza_code, shop_name)`                      | `str, str`       | `list[dict]`（每项含 id, name）          |
| `get_shop_id.py`         | `get_shop_id(plaza_code, shop_name)`                              | `str, str`       | `int \| None`（向后兼容，返回首个匹配）  |
| `get_shop_id.py`         | `get_all_shops(plaza_code)`                                       | `str`            | `list`                                   |
| `query_goods.py`         | `query_goods_list(plaza_code, shop_id, goods_sn=None)`            | `str, int, str?` | `list[dict]`                             |
| `query_goods.py`         | `find_goods_by_sn(plaza_code, shop_id, goods_sn)`                 | `str, int, str`  | `dict \| None`                           |
| `query_goods.py`         | `find_goods_by_name(plaza_code, shop_id, goods_name)`             | `str, int, str`  | `dict \| None`                           |
| `query_goods.py`         | `extract_goods_info(goods)`                                       | `dict`           | `dict` (含 galleryCount, detailImgCount) |
| `query_template.py`      | `query_template_category(goods_id)`                               | `int`            | `str`                                    |
| `remove_background.py`   | `remove_background(goods_id, pic_url, template_name)`             | `int, str, str`  | `str`                                    |
| `update_gallery.py`      | `update_gallery(goods_id, processed_pic_url, template_category)`  | `int, str, str`  | `bool`                                   |
| `mark_white_pic.py`      | `mark_white_pic(goods_id, force_override=False)`                  | `int, bool`      | `bool`                                   |
| `approve_goods.py`       | `approve_goods(goods_ids, approve_status="Y")`                    | `list[int], str` | `tuple[int, list[str]]`                  |
| `check_cookie.py`        | `check_and_set_cookie(cookie_value=None)`                         | `str \| None`    | `str`                                    |
| `export_audit_result.py` | `export_audit_result(all_goods_results, store_name, shop_name)`   | `list, str, str` | `str` (生成的文件路径，用于附件发送)     |
| `export_audit_result.py` | `generate_summary_text(store_name, shop_name, all_goods_results)` | `str, str, list` | `str` (格式化文字总结)                   |

## 参考文档

- `references/sensitive_words.md`: 敏感词词典、检测规则和示例检测函数
