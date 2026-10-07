# 搭建回执 — 回放，数值均为虚构

Meta · 账户 `fictional-meta-account-a` · 币种 USD · 计划 `meta-plan.json` · 回读 `meta-readback.json`

> 离线回放已保存的文件，没有调用任何平台。「回读值」一列全部来自回读文件；平台没有返回的字段一律记为不一致。

## 时间线

**暂停创建 7/7 → 回读 39/40 个字段 → HOLD**

| 步骤 | 时间 | 结果 |
|---|---|---|
| 暂停创建 | 2026-09-23T02:00:00Z | 计划中 7 个对象有 7 个返回；7 个回读为 `PAUSED` |
| 回读 | 2026-09-23T02:03:00Z | 40 个字段中 39 个与计划一致 |
| 结论 | — | HOLD：1 个问题；不启用任何对象 |

## 问题

- `ad-h3` · 链接参数：缺少必需参数：`utm_content`

## 字段

| 层级 | 对象 | 字段 | 计划值 | 回读值 | 一致 |
|---|---|---|---|---|:---:|
| 账户 | `fictional-meta-account-a` | 账户币种 | `USD` | `USD` | ✓ |
| 广告系列 | `cmp-quote-01` | 目标 | `OUTCOME_LEADS` | `OUTCOME_LEADS` | ✓ |
| 广告系列 | `cmp-quote-01` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告组 | `as-h1` | 优化目标 | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| 广告组 | `as-h1` | 优化事件 | `LEAD` | `LEAD` | ✓ |
| 广告组 | `as-h1` | 日预算 | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| 广告组 | `as-h1` | 出价策略 | `LOWEST_COST_WITHOUT_CAP` | `LOWEST_COST_WITHOUT_CAP` | ✓ |
| 广告组 | `as-h1` | 归因设置 | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| 广告组 | `as-h1` | 地区 | `US` | `US` | ✓ |
| 广告组 | `as-h1` | 版位 | `facebook, instagram` | `facebook, instagram` | ✓ |
| 广告组 | `as-h1` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告组 | `as-h2` | 优化目标 | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| 广告组 | `as-h2` | 优化事件 | `LEAD` | `LEAD` | ✓ |
| 广告组 | `as-h2` | 日预算 | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| 广告组 | `as-h2` | 出价策略 | `LOWEST_COST_WITHOUT_CAP` | `LOWEST_COST_WITHOUT_CAP` | ✓ |
| 广告组 | `as-h2` | 归因设置 | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| 广告组 | `as-h2` | 地区 | `US` | `US` | ✓ |
| 广告组 | `as-h2` | 版位 | `facebook, instagram` | `facebook, instagram` | ✓ |
| 广告组 | `as-h2` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告组 | `as-h3` | 优化目标 | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| 广告组 | `as-h3` | 优化事件 | `LEAD` | `LEAD` | ✓ |
| 广告组 | `as-h3` | 日预算 | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| 广告组 | `as-h3` | 出价策略 | `COST_CAP` | `COST_CAP` | ✓ |
| 广告组 | `as-h3` | 出价金额 | `6.50 USD` | `6.50 USD (raw 650)` | ✓ |
| 广告组 | `as-h3` | 归因设置 | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| 广告组 | `as-h3` | 地区 | `US` | `US` | ✓ |
| 广告组 | `as-h3` | 版位 | `facebook, instagram` | `facebook, instagram` | ✓ |
| 广告组 | `as-h3` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告 | `ad-h1` | 落地页 | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| 广告 | `ad-h1` | 链接参数 | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | ✓ |
| 广告 | `ad-h1` | 行动号召 | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| 广告 | `ad-h1` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告 | `ad-h2` | 落地页 | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| 广告 | `ad-h2` | 链接参数 | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | ✓ |
| 广告 | `ad-h2` | 行动号召 | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| 广告 | `ad-h2` | 状态 | `PAUSED` | `PAUSED` | ✓ |
| 广告 | `ad-h3` | 落地页 | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| 广告 | `ad-h3` | 链接参数 | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}` | ✗ |
| 广告 | `ad-h3` | 行动号召 | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| 广告 | `ad-h3` | 状态 | `PAUSED` | `PAUSED` | ✓ |

## 不参与判定：回读时的审核与投放状态

上表已判定配置状态。下列值来自平台的审核与投放处理，只记录、不比较。

| 对象 | 字段 | 值 |
|---|---|---|
| `cmp-quote-01` | effective_status | `PAUSED` |
| `as-h1` | effective_status | `PAUSED` |
| `as-h2` | effective_status | `PAUSED` |
| `as-h3` | effective_status | `PAUSED` |
| `ad-h1` | effective_status | `IN_PROCESS` |
| `ad-h2` | effective_status | `IN_PROCESS` |
| `ad-h3` | effective_status | `IN_PROCESS` |

## 下一步

HOLD：先在平台上修正上面列出的字段，重新回读全部对象后再跑一次本检查。HOLD 回执永远不会进入启用。
