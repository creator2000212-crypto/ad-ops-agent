# 快循环回执 · demo-20260924-1150

> OFFLINE ANALYSIS ONLY — 不连接任何广告平台、不写任何账户、不上传素材。输出的动作清单是给人审阅的建议，不是已执行的指令。

**数据截止：** 2026-09-24T11:50:00+08:00　|　**口径：** reference-1n1-ladder v2026-10-07.3　|　**快照指纹：** `52ff73b9f09b`

**观察窗口：** 2026-09-23（settled_day，覆盖完整投放日：是） — 自然日桶。小时级明细在本连接下不可用，所以判定窗口只能到自然日，近似性在此声明。

## 本轮结果

- 诊断产生 **20 条发现**，覆盖账户、广告组和素材；同一对象可以触发多条规则，所以不代表 20 个不同对象。全部 14 个广告组见「判定明细」。
- `ready` **4 条**：差异计划通过当前状态核对、可供审阅；`ready` 不等于获得操作授权。
- `apply` 仅向本地台账登记 **4 条差异计划 / 4 个拟改字段**；没有向任何平台发送。
- 对照输入的 `after` 快照：**3 条匹配、1 条不匹配**。
- 平台与结算对账：RECON_SCOPE 2　·　RECON_TZ 1　·　RECON_GAP 1　·　RECON_OK 1。数字对齐之前降为仅建议的成本类建议：**1 条**。

## 先处理这些待办

**闸门待确认 2 条**（见 `gate.json`）：

- `fictional-adset-a9` · LADDER_PROMOTE · **冲突隔离** — daily_budget：当前值 30.00 与基线 20.00、目标 40.00 均不一致 ⇒ 隔离该行，暂缓修改并核对变更来源。
- `fictional-adset-b2` · TEST_EARLY_STOP · **未知** — 写前状态里没有 'fictional-adset-b2' 的记录 ⇒ 先复拉，不要盲写。

**快照对照不匹配 1 条**（见 `reconciliation.json`）：

- `fictional-adset-a10` · LADDER_PROMOTE — 写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：daily_budget：期望 40.00，实读 20.00

**口径未对齐 1 条**（见 `findings.json` 与「平台与结算对账」）：

- `fictional-adgroup-d1` · LADDER_PROMOTE · RECON_GAP — 结算认可 3/7 条线索；按声明通过率 0.90 应为 6.3（-52.4%，容差 ±20.0%）。平台数与结算数对齐之前仅作建议，本轮不改预算或状态。

`open` 只列台账中待对照或已对照但不匹配的行；**不包含被闸门隔离的冲突、缺失行，不能视为完整待办**。交接时应合并查看以上各组待办。

## 账户信号

| 账户 | 平台 | offer | 单价 | configured 在投 | effective 可投 | 总组 | 今日消耗 | 余额 | 额度 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|
| `fictional-meta-account-a` | meta | fictional-offer-alpha | 10.00 | 10 | 9 | 10 | 28.40 | 820.00 | 6000.00 | 1 个组配置为在投但实际不可投 |
| `fictional-meta-account-b` | meta | fictional-offer-beta | 8.00 | 2 | 2 | 2 | 0.00 | 41.20 | — | spend_cap 读回为 null，余量预警不可用 |
| `fictional-meta-account-c` | meta | fictional-offer-gamma | 10.00 | 0 | 0 | 0 | 0.00 | 300.00 | 2000.00 | — |
| `fictional-tiktok-account-d` | tiktok | fictional-offer-delta | 12.00 | 2 | 2 | 2 | 17.80 | 640.00 | 3000.00 | — |

## 平台与结算对账

结算日期 2026-09-23　|　时区 Etc/GMT　|　币种 USD　|　容差：花费 ±2.0%，结算线索数 ±20.0%（基准 = 平台线索数 × 通过率 0.90）　|　目标 ROAS 1.25

| 账户 | 花费：平台 → 结算 | 线索：平台 → 结算（应有） | CPA：平台 / 结算 | T / 结算口径目标 | 结算 ROAS | 状态 |
|---|---|---|---|---|---|---|
| `fictional-meta-account-a` | 176.30 → 176.12 (-0.1%) | 21 → 19 (18.9, +0.5%) | 8.40 / 9.27 | 7.20 / 8.00 | 1.0788 | **RECON_OK** |
| `fictional-meta-account-b` | 24.70 → 22.90 (-7.3%) | 3 → 3 (2.7, +11.1%) | 8.23 / 7.63 | 5.76 / 6.40 | 1.0480 | **RECON_TZ** |
| `fictional-meta-account-c` | — → — | — → — | — / — | 7.20 / 8.00 | — | **RECON_SCOPE** |
| `fictional-tiktok-account-d` | 29.40 → 29.40 (+0.0%) | 7 → 3 (6.3, -52.4%) | 4.20 / 9.80 | 8.64 / 9.60 | 1.2245 | **RECON_GAP** |
| `fictional-meta-account-e` | — → 12.50 | — → 1 | — / 12.50 | — / — | — | **RECON_SCOPE** |

- `fictional-meta-account-b` · RECON_TZ — 账户时区 Etc/GMT+5 与结算时区 Etc/GMT 不同，自然日切分不一致，差额无法解读；先对齐时区。
- `fictional-meta-account-c` · RECON_SCOPE — 快照里有、结算导出里没有：不在结算范围内；按缺失报告，不补零。
- `fictional-tiktok-account-d` · RECON_GAP — 结算认可 3/7 条线索；按声明通过率 0.90 应为 6.3（-52.4%，容差 ±20.0%）。
- `fictional-meta-account-e` · RECON_SCOPE — 结算导出里有、平台拉取没有返回：平台侧是缺失，不是零；先复拉再看合计。

结算 CPA 是每条「被认可线索」的花费，所以和结算口径目标（T ÷ 通过率 = 线索价值 ÷ 目标 ROAS）比较，而不是和 T 比较。只在一侧存在的行按缺失显示，绝不补零。状态为 RECON_GAP、RECON_TZ、RECON_WINDOW 的账户，LADDER_PROMOTE、TEST_STOP_OVERCOST 降为仅建议（口径未对齐）。

## 判定明细（按广告组）

| 广告组 | 阶段 | 花费 | 展示 | 转化 | CPA | T | 止损线 | 利用率 | 判据 |
|---|---|---|---|---|---|---|---|---|---|
| `fictional-adset-a1` | T | 19.80 | 4600 | 3 | 6.60 | 7.20 | 21.60 | 99.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-a2` | T | 4.60 | 210 | 0 | — | 7.20 | 21.60 | 46.0% | TEST_UNDERTESTED(P2) |
| `fictional-adset-a3` | T | 22.40 | 640 | 0 | — | 7.20 | 21.60 | 112.0% | TEST_STOP_NOCONV(P0) |
| `fictional-adset-a4` | 2T | 40.00 | 9300 | 2 | 20.00 | 7.20 | 21.60 | 100.0% | TEST_STOP_OVERCOST(P0) |
| `fictional-adset-a5` | T | 8.40 | 1900 | 3 | 2.80 | 7.20 | 21.60 | 42.0% | TEST_UNDERTESTED(P2) |
| `fictional-adset-a6` | T | 21.00 | 4900 | 4 | 5.25 | 7.20 | 21.60 | 105.0% | CREATIVE_BREAKER(P1)；CREATIVE_FATIGUE(P2)；LADDER_HOLD(P2) |
| `fictional-adset-a7` | T | 6.10 | 1100 | 0 | — | 7.20 | 21.60 | 30.5% | AD_STATUS(P0) |
| `fictional-adset-a8` | T | 14.20 | 2700 | 2 | 7.10 | 7.20 | 21.60 | 71.0% | LINK_OR_TRACKING_BAD(P0) |
| `fictional-adset-a9` | T | 19.20 | 4300 | 3 | 6.40 | 7.20 | 21.60 | 96.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-a10` | T | 20.60 | 4800 | 4 | 5.15 | 7.20 | 21.60 | 103.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-b1` | T | 15.60 | 3700 | 3 | 5.20 | 5.76 | 17.28 | 78.0% | CREATIVE_OVERFLOW(P2)；LADDER_HOLD(P2) |
| `fictional-adset-b2` | T | 9.10 | 190 | 0 | — | 5.76 | 17.28 | 45.5% | TEST_EARLY_STOP(P1) |
| `fictional-adgroup-d1` | T | 19.60 | 5800 | 5 | 3.92 | 8.64 | 25.92 | 98.0% | LADDER_PROMOTE(P1, 仅建议：口径未对齐) |
| `fictional-adgroup-d2` | T | 9.80 | 2600 | 2 | 4.90 | 8.64 | 25.92 | 49.0% | TEST_UNDERTESTED(P2) |

## CPA 为什么变了

CPA = CPM ÷ (1000 × CTR × CVR)，所以 CPA 的对数变化可以精确拆成 CPM、CTR、CVR 三项。每格是该项的对数点（100 × 自然对数变化；正数把 CPA 往上推，负数往下拉）及其在总变动中的占比。残差是报出的上期 CPA 无法解释的部分（取整）。这是会计恒等式，不是因果结论。

| 广告组 | 上期窗口 | CPA：上期 → 本期 | Δ log CPA | CPM 贡献 | CTR 贡献 | CVR 贡献 | 残差 | 主因 |
|---|---|---|---|---|---|---|---|---|
| `fictional-adset-a1` | 2026-09-22 | 7.03 → 6.60 | -6.3 | +2.5 (22%) | -6.7 (60%) | -2.0 (18%) | -0.1 | **CTR** |
| `fictional-adset-a4` | 2026-09-22 | 5.41 → 20.00 | +130.8 | +9.8 (7%) | +3.2 (2%) | +117.7 (90%) | +0.1 | **CVR** |
| `fictional-adset-a10` | 2026-09-22 | 5.38 → 5.15 | — | — | — | — | — | 未拆分：缺少 上期 CVR |
| `fictional-adgroup-d1` | 2026-09-22 | 7.21 → 3.92 | -60.9 | +3.9 (5%) | +2.5 (3%) | -67.3 (91%) | -0.1 | **CVR** |

先看占比最大的一项：CVR 指向点击之后（落地页、表单、线索质量），CTR 指向钩子，CPM 指向竞价。

## 闸门结果与已登记的差异计划

| 结果 | 条数 | 含义 |
|---|---|---|
| 待审差异计划（ready） | 4 | 现值与基线一致；只列差异字段，尚未获得执行授权 |
| 已满足 | 1 | 目标值已就位，跳过不写 |
| 冲突隔离 | 1 | 现值既非基线也非目标，数值本身不能说明修改者；隔离并确认 |
| 未知 | 1 | 没读到写前状态、字段缺失或没有可用基线，先复拉 |
| 仅建议 | 13 | 该发现不涉及写入字段或已被降级，不过闸门 |

下表是 `apply` 登记的拟改字段，不是已经提交的操作：

| 对象 | 规则 | 拟改字段 |
|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | `daily_budget` → 40.00 |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | `status` → PAUSED |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | `status` → PAUSED |
| `fictional-adset-a10` | LADDER_PROMOTE | `daily_budget` → 40.00 |

仅建议（13 条，不涉及写入，不需要过闸门）：`fictional-adset-a2`·TEST_UNDERTESTED、`fictional-adset-a5`·TEST_UNDERTESTED、`a6-c1`·CREATIVE_BREAKER、`a6-c2`·CREATIVE_FATIGUE、`fictional-adset-a6`·LADDER_HOLD、`fictional-adset-a7`·AD_STATUS、`fictional-meta-account-b`·ACC_NO_DELIVERY、`fictional-meta-account-b`·ACC_BALANCE_LOW、`fictional-adset-b1`·CREATIVE_OVERFLOW、`fictional-adset-b1`·LADDER_HOLD、`fictional-meta-account-c`·ACC_STOPPED、`fictional-adgroup-d1`·LADDER_PROMOTE、`fictional-adgroup-d2`·TEST_UNDERTESTED

## 与 after 快照逐条对照

这里对比目标值与输入的 after 文件，不执行平台写入。

| 对象 | 规则 | 快照是否匹配 | 原始判据 |
|---|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | 匹配 | 写后回读与目标一致。 |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | 匹配 | 写后回读与目标一致。 |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | 匹配 | 写后回读与目标一致。 |
| `fictional-adset-a10` | LADDER_PROMOTE | **不匹配** | 写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：daily_budget：期望 40.00，实读 20.00 |

**本轮未对照 16 条，完整列出如下：**

- `fictional-adset-a2` · TEST_UNDERTESTED — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a3` · TEST_STOP_NOCONV — 闸门为 已满足，本轮未写入。
- `fictional-adset-a5` · TEST_UNDERTESTED — 闸门为 仅建议，本轮未写入。
- `a6-c1` · CREATIVE_BREAKER — 闸门为 仅建议，本轮未写入。
- `a6-c2` · CREATIVE_FATIGUE — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a6` · LADDER_HOLD — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a7` · AD_STATUS — 闸门为 仅建议，本轮未写入。
- `fictional-adset-a9` · LADDER_PROMOTE — 闸门为 冲突隔离，本轮未写入。
- `fictional-meta-account-b` · ACC_NO_DELIVERY — 闸门为 仅建议，本轮未写入。
- `fictional-meta-account-b` · ACC_BALANCE_LOW — 闸门为 仅建议，本轮未写入。
- `fictional-adset-b1` · CREATIVE_OVERFLOW — 闸门为 仅建议，本轮未写入。
- `fictional-adset-b1` · LADDER_HOLD — 闸门为 仅建议，本轮未写入。
- `fictional-adset-b2` · TEST_EARLY_STOP — 闸门为 未知，本轮未写入。
- `fictional-meta-account-c` · ACC_STOPPED — 闸门为 仅建议，本轮未写入。
- `fictional-adgroup-d1` · LADDER_PROMOTE — 闸门为 仅建议，本轮未写入。
- `fictional-adgroup-d2` · TEST_UNDERTESTED — 闸门为 仅建议，本轮未写入。

## 结构警告（不产生动作，但会影响判定可信度）

- `fictional-adset-a5` — 组名写「MAX」但实际 bid_strategy = LOWEST_COST_WITH_COST_CAP（5.00）⇒ 命名与实际不符，读结构一律以详情接口的 bid_strategy 为准。
- `fictional-adset-a7` — configured_status=ACTIVE 但 effective_status=DISAPPROVED ⇒ 判「能不能投」必须看 effective_status。
- `fictional-meta-account-b` — spend_cap 读回为 null ⇒ 余量预警无法计算，如实标注，不得用 balance 反推。

## 交接规则

- 「已满足」不产生差异计划；「冲突」隔离并确认原因，数值本身不能说明是谁改的。
- 样本不足（展示未达判死门槛）不判素材好坏，只记录。
- 能力缺口如实说明（如额度字段读回为 null），不用推断填空。
- 平台数与结算数对不上时，先修口径；对齐之前不按平台数改预算或暂停。
- 审批、提交与实盘回读不在这一轮离线检查之内。

