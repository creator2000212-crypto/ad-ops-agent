# 搭建回执 — 回放，数值均为虚构

TikTok · 账户 `fictional-tiktok-account-a` · 币种 USD · 计划 `tiktok-plan.json` · 回读 `tiktok-readback.json`

> 离线回放已保存的文件，没有调用任何平台。「回读值」一列全部来自回读文件；平台没有返回的字段一律记为不一致。

## 时间线

**暂停创建 5/5 → 回读 27/27 个字段 → ACTIVATE**

| 步骤 | 时间 | 结果 |
|---|---|---|
| 暂停创建 | 2026-09-23T02:10:00Z | 计划中 5 个对象有 5 个返回；5 个回读为 `DISABLE` |
| 回读 | 2026-09-23T02:12:00Z | 27 个字段中 27 个与计划一致 |
| 结论 | — | ACTIVATE：所有字段一致，所有对象均为暂停 |

## 字段

| 层级 | 对象 | 字段 | 计划值 | 回读值 | 一致 |
|---|---|---|---|---|:---:|
| 账户 | `fictional-tiktok-account-a` | 账户币种 | `USD` | `USD` | ✓ |
| 广告系列 | `cmp-t-quote-01` | 目标 | `WEB_CONVERSIONS` | `WEB_CONVERSIONS` | ✓ |
| 广告系列 | `cmp-t-quote-01` | 状态 | `DISABLE` | `DISABLE` | ✓ |
| 广告组 | `ag-t1` | 优化目标 | `CONVERT` | `CONVERT` | ✓ |
| 广告组 | `ag-t1` | 优化事件 | `FORM` | `FORM` | ✓ |
| 广告组 | `ag-t1` | 日预算 | `30.00 USD` | `30.00 USD` | ✓ |
| 广告组 | `ag-t1` | 出价策略 | `BID_TYPE_NO_BID` | `BID_TYPE_NO_BID` | ✓ |
| 广告组 | `ag-t1` | 归因设置 | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| 广告组 | `ag-t1` | 地区 | `6252001` | `6252001` | ✓ |
| 广告组 | `ag-t1` | 版位 | `PLACEMENT_TIKTOK` | `PLACEMENT_TIKTOK` | ✓ |
| 广告组 | `ag-t1` | 状态 | `DISABLE` | `DISABLE` | ✓ |
| 广告组 | `ag-t2` | 优化目标 | `CONVERT` | `CONVERT` | ✓ |
| 广告组 | `ag-t2` | 优化事件 | `FORM` | `FORM` | ✓ |
| 广告组 | `ag-t2` | 日预算 | `30.00 USD` | `30.00 USD` | ✓ |
| 广告组 | `ag-t2` | 出价策略 | `BID_TYPE_NO_BID` | `BID_TYPE_NO_BID` | ✓ |
| 广告组 | `ag-t2` | 归因设置 | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| 广告组 | `ag-t2` | 地区 | `6252001` | `6252001` | ✓ |
| 广告组 | `ag-t2` | 版位 | `PLACEMENT_TIKTOK` | `PLACEMENT_TIKTOK` | ✓ |
| 广告组 | `ag-t2` | 状态 | `DISABLE` | `DISABLE` | ✓ |
| 广告 | `ad-t1` | 落地页 | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| 广告 | `ad-t1` | 链接参数 | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | ✓ |
| 广告 | `ad-t1` | 行动号召 | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| 广告 | `ad-t1` | 状态 | `DISABLE` | `DISABLE` | ✓ |
| 广告 | `ad-t2` | 落地页 | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| 广告 | `ad-t2` | 链接参数 | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | ✓ |
| 广告 | `ad-t2` | 行动号召 | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| 广告 | `ad-t2` | 状态 | `DISABLE` | `DISABLE` | ✓ |

## 下一步

ACTIVATE：配置与计划一致。启用仍需负责人批准这一批次；之后分阶段启用、回读状态并跟进审核。本回执不等于批准。
