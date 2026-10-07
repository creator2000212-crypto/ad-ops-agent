# 搭建质检：搭建前检查与回读回执

[English](build-qa.md)

2026 年 9 月 10 日至 27 日，我用 WorkBuddy（腾讯的桌面 AI 智能体；与本项目无关联）以对话方式搭建 Meta 和 TikTok 线索广告。搭建遵循同一套流程：所有对象先以暂停状态创建，逐个对象、逐个字段回读，然后启用；9 月 22 日之后，启用还需要我对这一批次的明确批准。本仓库的两个模块是这套流程前后检查的离线、带测试版本：

- [`preflight.py`](../preflight.py)：在创建任何对象之前检查搭建清单。
- [`readback.py`](../readback.py)：创建之后，把计划与平台返回的内容逐字段比对，写出结论为 HOLD 或 ACTIVATE 的回执。

两者只读取 JSON 文件，不调用任何平台。示例中的 ID、名称、金额和 `example.com` 链接都是虚构的。

## 流程：实盘与本仓库

| 阶段 | 实盘账户上（2026 年 9 月） | 本仓库 |
|---|---|---|
| 1. 搭建前检查 | — | `preflight.py`：对清单做命名、链接、类别声明、归因和重复文件检查 |
| 2. 暂停创建 | 广告系列、广告组、广告一律以 `PAUSED` 创建 | 计划中要求其他状态会被拒绝 |
| 3. 逐字段回读 | 每个对象回读后与计划比对 | `readback.py`：每个字段一行，任何不一致即 HOLD |
| 4. 分阶段启用 | 分阶段启用（9 月 22 日之后须经我明确批准），之后再次回读状态 | 不回放。ACTIVATE 回执表示“具备启用条件”，不表示“已批准” |
| 5. 跟进审核 | 启用后轮询平台审核状态 | 不回放。回执记录 `effective_status`，但不参与判定 |

搭建前检查是本仓库新增的：把后面阶段才会发现的矛盾，提前到创建之前检查。

## 这些检查从哪里来

| 日期（2026） | 发生了什么 | 现在的检查 |
|---|---|---|
| 09-10 | 一批 25 个素材请求超时；重试前先核对了已经存在的对象 | 回读中出现计划里没有的对象（例如重试留下的重复对象）即 HOLD |
| 09-17 | 批量启用后有 8 条广告仍未启用；启用后的逐字段回读发现了这一点 | 本仓库不回放启用，但启用前同样遵循这条规则：状态逐个对象回读，绝不根据请求推断 |
| 09-18 | 我把归因口径统一为 7 天点击 + 1 天浏览，使成本可以横向比较 | 同一广告系列内各广告组归因设置不一致时，搭建前检查判为不通过 |
| 09-22 | 智能体创建的自动规则把阈值写成了美元，而接口要求美分，阈值小了 100 倍，导致广告组被暂停 | 金额按平台对该账户回读币种规定的货币偏移换算，没有默认 x100 |
| 09-22 | 我只回答了一个像素问题，智能体就启用了一批广告组 | 回执写明：启用仍需负责人批准这一批次 |
| 09-25 | 回执生成器把状态硬编码为 `ACTIVE`，而保存的回读结果是 `PAUSED` / `IN_PROCESS` | 「回读值」全部来自回读文件；缺失字段记为“未返回” |

## `readback.py` 检查什么

`verify_build(plan, readback)` 返回 `{rows, decision, reasons, ...}`。每一行是 `{level, object_key, field, planned, read_back, match}`；平台没有返回该字段时 `read_back` 为 `None`。只有所有行都一致、且没有缺失或多出的对象时，结论才是 `activate`。

| 字段 | Meta 返回路径 | TikTok 返回路径 |
|---|---|---|
| 账户币种 | 广告账户 `currency` | 广告主 `currency` |
| 目标 | `objective` | `objective_type` |
| 优化目标 / 事件 | `optimization_goal`、`promoted_object.custom_event_type` | `optimization_goal`、`optimization_event` |
| 日预算 | `daily_budget`（最小货币单位） | `budget_mode` 为 `BUDGET_MODE_DAY` 时的 `budget`（主货币单位） |
| 出价策略 / 金额 | `bid_strategy`、`bid_amount`（最小货币单位） | `bid_type`、`conversion_bid_price` |
| 归因设置 | `attribution_spec`（点击与浏览天数） | `click_attribution_window`、`view_attribution_window` |
| 地区 / 版位 | `targeting.geo_locations.countries`、`targeting.publisher_platforms` | `location_ids`、`placements` |
| 落地页 | `creative.object_story_spec.link_data.link` | `landing_page_url` |
| 链接参数 | 链接中的查询参数加上 `creative.url_tags` | `landing_page_url` 中的查询参数 |
| 行动号召 | `link_data.call_to_action.type` | `call_to_action` |
| 状态 | `status` 必须为 `PAUSED` | `operation_status` 必须为 `DISABLE` |

比对遵循以下规则：

- **缺失不等于一致。** 计划中写明、回读中没有的字段记为不一致，显示为“未返回”。
- **单位以平台为准，不用默认值。** Meta 以最小货币单位返回金额。`readback.py` 中的偏移表摘自 Meta 的[货币说明](https://developers.facebook.com/docs/marketing-api/currencies)（2026-10-07 核对）：USD 两位小数，JPY 没有小数；TWD 和 HUF 在 ISO 4217 中有两位小数，但在 Meta 上没有。表中没有的币种直接拒绝。账户币种也会回读，所以按 USD 写的计划放到 JPY 账户上会判为不一致，而不是悄悄差 100 倍。
- **链接参数按名称和值检查。** 每个必需参数都必须存在且等于计划值；允许有额外参数。
- **配置状态参与判定，审核状态只记录。** 配置状态必须是暂停。Meta 的 `effective_status`（例如 `IN_PROCESS`）列在“不参与判定”一节，因为它反映的是审核与投放处理，而不是配置。

## `preflight.py` 检查什么

清单是 JSON：广告系列包含广告组，广告组包含广告。平台相关的事实写在规则文件中，每个列表都附有来源和核对日期；更新规则文件即可改变判定，无需改代码。

| 检查 | 层级 | 不通过 | 警告 |
|---|---|---|---|
| 名称 ↔ 出价 | 广告组 | 名称写 `MAX` 但出价策略是成本上限（或反之）；名称中的上限（`CC6.50`）与 `bid_amount` 不同 | 名称不符合命名规范，或出价标记不认识 |
| 名称 ↔ 预算 | 广告组 | 名称中的预算（`$20`）与 `daily_budget` 不同 | 名称中读不出预算 |
| HTTPS | 广告 | 落地页不是 `https` 或不是完整 URL | — |
| 链接参数 | 广告 | 缺少必需参数；宏不在平台文档列出的范围内 | 参数值与规则不同 |
| 特殊广告类别 | 广告系列 | 产品类别需要声明（例如 `job_listings` → `EMPLOYMENT`）而广告系列没有声明 | 没有写产品类别，或规则文件没有该平台带来源的对照表 |
| 归因一致 | 广告系列 | 同一广告系列内各广告组归因设置不同 | 某个广告组没有归因设置 |
| 重复素材 | 广告组 | 同一广告组内两条广告使用同一个文件（按 SHA-256） | 某条广告没有文件哈希 |

特殊广告类别检查只确认声明是否存在，不判断某个产品是否属于该类别；那仍然由人决定。

运营循环会对在投广告组标记同样的名称与出价矛盾（[`operating_rules.py`](../operating_rules.py) 中的 `name_mismatch`）。搭建前检查在广告组存在之前就能发现它。

## 运行

```bash
# 回读：打印回执，或与已提交的样例比对
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json \
    --check examples/readback/expected/meta-receipt.md
python3 readback.py --plan examples/readback/tiktok-plan.json --readback examples/readback/tiktok-readback.json \
    --lang zh-CN --check examples/readback/expected/tiktok-receipt.zh-CN.md

# 搭建前检查
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json \
    --check examples/preflight/expected/checklist.md

# 测试
python3 -m unittest tests.test_readback tests.test_preflight -v
```

两个命令共有的选项：`--lang en|zh-CN`（默认 `en`）、`--json` 输出机器可读结果、`--receipt` / `--report` 写出 Markdown 文件、`--strict` 在 HOLD 或 FAIL 时以 3 退出。退出码：0 表示已输出（或与样例一致），1 表示与样例不一致（会打印统一 diff），2 表示输入无效。

有意修改之后，用 `--receipt`（回读）或 `--report`（搭建前检查）重新生成样例，审阅 diff，再运行 `--check`。

## 回执示例

摘自 [`examples/readback/expected/meta-receipt.zh-CN.md`](../examples/readback/expected/meta-receipt.zh-CN.md)。Meta 示例恰好有一处不一致：一条广告的链接参数缺少 `utm_content`，所以结论是 HOLD。[TikTok 回执](../examples/readback/expected/tiktok-receipt.zh-CN.md)所有字段一致，结论是 ACTIVATE。

**暂停创建 7/7 → 回读 39/40 个字段 → HOLD**

| 步骤 | 时间 | 结果 |
|---|---|---|
| 暂停创建 | 2026-09-23T02:00:00Z | 计划中 7 个对象有 7 个返回；7 个回读为 `PAUSED` |
| 回读 | 2026-09-23T02:03:00Z | 40 个字段中 39 个与计划一致 |
| 结论 | — | HOLD：1 个问题；不启用任何对象 |

- `ad-h3` · 链接参数：缺少必需参数：`utm_content`

| 层级 | 对象 | 字段 | 计划值 | 回读值 | 一致 |
|---|---|---|---|---|:---:|
| 广告组 | `as-h1` | 日预算 | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| 广告组 | `as-h3` | 出价金额 | `6.50 USD` | `6.50 USD (raw 650)` | ✓ |
| 广告 | `ad-h3` | 链接参数 | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}` | ✗ |
| 广告 | `ad-h3` | 状态 | `PAUSED` | `PAUSED` | ✓ |

示例清单的搭建前检查报告见 [`examples/preflight/expected/checklist.zh-CN.md`](../examples/preflight/expected/checklist.zh-CN.md)：不通过 7、警告 3、通过 21。

## 局限

- 返回路径表（`readback.py` 中的 `ADAPTERS`）依据公开的 Meta Marketing API 与 TikTok API for Business 文档整理，使用前请对照你所用的 API 版本核对。Meta 的映射从 `link_data` 读取落地页；视频广告的落地页在 `video_data.call_to_action.value.link` 下，目前尚未映射。
- 回读示例是按接口返回结构编写的虚构数据，不是真实账户的抓取结果。
- 搭建前检查通过、回执为 ACTIVATE，都不是平台审核结果，也不代表可以启用。批准权始终在这一批次的负责人手里。
