# 快循环回执 · demo-20260924-1150

> OFFLINE ANALYSIS ONLY — 不连接任何广告平台、不写任何账户、不上传素材。输出的动作清单是给人审阅的建议，不是已执行的指令。

**数据截止：** 2026-09-24T11:50:00+08:00　|　**口径：** reference-1n1-ladder v2026-09-24.1　|　**快照指纹：** `e00210a0777f`

**观察窗口：** 2026-09-23（settled_day，覆盖完整投放日：是） — 自然日桶。小时级明细在本连接下不可用，所以判定窗口只能到自然日，近似性在此声明。

## 本轮结果

- 诊断产生 **16 条发现**，不代表 16 个不同对象。发现覆盖账户、广告组和素材；同一对象可以触发多条规则，下方列出全部 10 个广告组的诊断。
- `ready` **4 条**表示差异计划通过当前快照核对、可供审阅，**不表示已获操作授权**。
- `apply` 仅向本地台账登记 **4 条差异计划 / 4 个拟改字段**；没有调用平台或写入广告账户。
- 对照输入的 `after` 快照：**3 条匹配、1 条不匹配**。演示使用预置快照，这些结果不证明真实修改已经生效。

## 先处理这些待办

**闸门待确认 2 条**（见 `gate.json`）：

- `fictional-adset-a9` · LADDER_PROMOTE · **冲突隔离** — daily_budget：现值 30.00 既非基线 10.00 也非目标 20.00 ⇒ 人工改过，隔离该行。
- `fictional-adset-b1` · LADDER_PROMOTE · **未知** — 写前状态里没有 'fictional-adset-b1' 的记录 ⇒ 先复拉，不要盲写。

以上保留规则的原始判据。出现“人工改过”时，实际只检测到现值与基线、目标不一致；无法据此判定是谁修改，也不能直接覆盖。

**快照对照不匹配 1 条**（见 `reconciliation.json`）：

- `fictional-adset-a6` · LADDER_PROMOTE — 写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：daily_budget：期望 40.00，实读 20.00

`open` 只列台账中待对照或已对照但不匹配的行；**不包含被闸门隔离的冲突、缺失行，不能视为完整待办**。交接时应合并查看以上两组待办。规则原文中的“生效/未生效”仅指本次快照值是否匹配。

## 账户信号

| 账户 | offer | 单价 | configured 在投 | effective 可投 | 总组 | 今日消耗 | 余额 | 额度 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| `fictional-meta-account-a` | fictional-offer-alpha | 4.000 | 9 | 8 | 9 | 143.20 | 820.00 | 6000.00 | 1 个组配置为在投但实际不可投 |
| `fictional-meta-account-b` | fictional-offer-beta | 3.143 | 1 | 1 | 1 | 0.00 | 41.20 | — | spend_cap 读回为 null，余量预警不可用 |
| `fictional-meta-account-c` | fictional-offer-gamma | 4.000 | 0 | 0 | 0 | 0.00 | 300.00 | 2000.00 | — |

## 判定明细（按 ad set）

| ad set | 阶段 | 花费 | 展示 | 转化 | CPA | T | 止损线 | 利用率 | 判据 |
|---|---|---|---|---|---|---|---|---|---|
| `fictional-adset-a1` | T | 12.40 | 3200 | 3 | 4.13 | 4.71 | 14.12 | 1.2400 | LADDER_PROMOTE(P1) |
| `fictional-adset-a2` | T | 3.10 | 180 | 0 | — | 4.71 | 14.12 | 0.6200 | TEST_UNDERTESTED(P2) |
| `fictional-adset-a3` | T | 15.30 | 420 | 0 | — | 4.71 | 14.12 | 1.5300 | TEST_STOP_NOCONV(P0) |
| `fictional-adset-a4` | 2T | 30.00 | 9100 | 3 | 10.00 | 4.71 | 14.12 | 1.0000 | TEST_STOP_OVERCOST(P0) |
| `fictional-adset-a5` | T | 6.40 | 1500 | 4 | 1.60 | 4.71 | 14.12 | 0.3200 | TEST_UNDERTESTED(P2) |
| `fictional-adset-a6` | T | 22.00 | 5100 | 5 | 4.40 | 4.71 | 14.12 | 1.1000 | CREATIVE_BREAKER(P1)；CREATIVE_FATIGUE(P2)；LADDER_PROMOTE(P1) |
| `fictional-adset-a7` | T | 5.00 | 900 | 0 | — | 4.71 | 14.12 | 0.5000 | AD_STATUS(P0) |
| `fictional-adset-a8` | T | 7.20 | 1400 | 2 | 3.60 | 4.71 | 14.12 | 0.7200 | LINK_OR_TRACKING_BAD(P0) |
| `fictional-adset-a9` | T | 9.80 | 2400 | 3 | 3.27 | 4.71 | 14.12 | 0.9800 | LADDER_PROMOTE(P1) |
| `fictional-adset-b1` | T | 8.30 | 2600 | 3 | 2.77 | 3.70 | 11.09 | 0.8300 | CREATIVE_OVERFLOW(P2)；LADDER_PROMOTE(P1) |

## 闸门结果与已登记的差异计划

| 结果 | 条数 | 含义 |
|---|---|---|
| 待审差异计划（ready） | 4 | 现值与基线一致；只列差异字段，尚未获得执行授权 |
| 已满足 | 1 | 目标值已就位，跳过不写 |
| 冲突隔离 | 1 | 检测到状态不一致，无法判定修改者；隔离并确认 |
| 未知 | 1 | 没读到写前状态或字段缺失，先复拉 |
| 仅建议 | 9 | 该发现不涉及写入字段，不过闸门 |

下表是 `apply` 登记的拟改字段，不是已经提交的操作：

| 对象 | 规则 | 拟改字段 |
|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | `daily_budget` → 20.00 |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | `status` → PAUSED |
| `fictional-adset-a6` | LADDER_PROMOTE | `daily_budget` → 40.00 |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | `status` → PAUSED |

仅建议（9 条，不涉及写入，不需要过闸门）：`fictional-adset-a2`·TEST_UNDERTESTED、`fictional-adset-a5`·TEST_UNDERTESTED、`a6-c1`·CREATIVE_BREAKER、`fictional-adset-a6`·CREATIVE_FATIGUE、`fictional-adset-a7`·AD_STATUS、`fictional-meta-account-b`·ACC_NO_DELIVERY、`fictional-meta-account-b`·ACC_BALANCE_LOW、`fictional-adset-b1`·CREATIVE_OVERFLOW、`fictional-meta-account-c`·ACC_STOPPED

## 与 after 快照逐条对照

这里对比目标值与输入快照，不执行平台写入。说明列保留原始判据，其中“生效”不代表真实操作已完成。

| 对象 | 规则 | 快照是否匹配 | 原始判据 |
|---|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | 匹配 | 写后回读与目标一致。 |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | 匹配 | 写后回读与目标一致。 |
| `fictional-adset-a6` | LADDER_PROMOTE | **不匹配** | 写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：daily_budget：期望 40.00，实读 20.00 |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | 匹配 | 写后回读与目标一致。 |

**本轮未对照 12 条，完整列出如下：**

- `fictional-adset-a2` · TEST_UNDERTESTED — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a3` · TEST_STOP_NOCONV — 闸门为 已满足，本轮未写入。
- `fictional-adset-a5` · TEST_UNDERTESTED — 闸门为 仅建议，本轮未写入。
- `a6-c1` · CREATIVE_BREAKER — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a6` · CREATIVE_FATIGUE — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a7` · AD_STATUS — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a9` · LADDER_PROMOTE — 闸门为 冲突隔离，本轮未写入。
- `fictional-meta-account-b` · ACC_NO_DELIVERY — 闸门为 仅建议，本轮未写入。
- `fictional-meta-account-b` · ACC_BALANCE_LOW — 闸门为 仅建议，本轮未写入。
- `fictional-adset-b1` · CREATIVE_OVERFLOW — 闸门为 仅建议，本轮未写入。
- `fictional-adset-b1` · LADDER_PROMOTE — 闸门为 未知，本轮未写入。
- `fictional-meta-account-c` · ACC_STOPPED — 闸门为 仅建议，本轮未写入。

## 结算口径对账

日期 2026-09-23　|　目标 ROAS 0.85　|　混量成本 1.00/转化

| 平台 | 账户 | 单价 | 花费 | 转化 | 收入 | 盘面 CPA | 目标 CPA(T) | ROAS |
|---|---|---|---|---|---|---|---|---|
| meta | `fictional-meta-account-a` | 4.000 | 143.20 | 33 | 132.00 | 4.34 | 4.71 | 0.9218 |
| meta | `fictional-meta-account-b` | 3.143 | 88.60 | 24 | 75.43 | 3.69 | 3.70 | 0.8514 |
| meta | `fictional-meta-account-c` | 4.000 | 0.00 | 0 | 0.00 | — | 4.71 | — |

- 先看口径是否一致：账户时区、归因窗口、转化去重、结算单价来源。
- 盘面与结算对不上时，先修口径，不要先改预算。
- 收入未经结算成熟前，ROAS 只能标「截至某时、尚待成熟」。

## 结构警告（不产生动作，但会影响判定可信度）

- `fictional-adset-a7` — configured_status=ACTIVE 但 effective_status=DISAPPROVED ⇒ 判「能不能投」必须看 effective_status。
- `fictional-adset-a9` — 组名写「MAX」但实际 bid_strategy = LOWEST_COST_WITH_COST_CAP（4.70）⇒ 命名与实际不符，读结构一律以详情接口的 bid_strategy 为准。
- `fictional-meta-account-b` — spend_cap 读回为 null ⇒ 余量预警无法计算，如实标注，不得用 balance 反推。

## 交接边界

- 本轮只生成建议、登记本地台账并对照快照；真实 API 接入、操作授权、提交和平台回读仍需后续独立实现。
- 「已满足」不产生差异计划；「冲突」隔离并确认原因，不推断修改者。
- 样本不足（展示未达判死门槛）不判素材好坏，只记录。
- 能力缺口如实说明（如额度字段读回为 null），不用推断填空。

