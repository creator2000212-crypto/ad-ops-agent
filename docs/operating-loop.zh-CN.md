# 投放快循环 — 12 小时检查的离线实现

本页是规则、数据依赖与 CLI 的技术参考。样例结果见[一轮检查的具体案例](../demo/README.zh-CN.md)；
[从零搭建](build-from-zero.zh-CN.md) 说明架构与搭建顺序。

这些规则移植自我在 2026 年 9 月 22–26 日用 WorkBuddy（腾讯的桌面 AI Agent；本项目与其无关联）
定时任务、在真实 Meta 与 TikTok 线索投放账户上运行的只读 12 小时检查。搭建是交互式完成的：
暂停状态创建 → 逐字段回读 → 激活。本仓库是它的离线、带测试版本。

**范围：**本模块按设计离线运行。它读取 JSON 文件，平台调用次数为 0，输出建议、报告和只追加的台账。
`ready` 表示差异通过了状态核对，不表示有人批准；后置快照匹配只是文件比较，不证明真实修改已生效。

## 每道防线防的是什么

| 事故 | 表现 | 对应的防线 |
|---|---|---|
| 拿不够的样本下结论 | 零线索组只花了几美元就被判死 | 样本关：展示地板**与**止损线同时满足才判死 |
| 别处有问题还在加量 | 素材刚触发熔断，组预算却翻倍 | 规则优先级：`LADDER_HOLD` 取代晋级；每个广告组每轮只做一项变更 |
| 计划写了不该写的字段 | 建议的目标字段不属于该对象类型 | `WRITABLE_FIELDS`：闸门抛出 `RuleError`，整轮停止 |
| 覆盖了别人的修改 | 当前预算既非基线也非目标 | `conflict`：隔离该行；数值本身不能说明是谁改的 |
| 把目标值当成实际状态 | 计划把预算设为 40，后置快照仍是 20 | 回读对照：该行以 `verified_not_effective` 保持未闭合 |
| 把「没有台账」当成「没有待办」 | 台账路径写错，`open` 却报 0 条 | 台账缺失抛出 `LoopError`（退出码 2） |

## 模块职责

| 文件 | 职责 |
|---|---|
| `operating_rules.py` | 纯判定层。用 `Decimal` 解析数字、推导指标、把 CPA 差距拆成 CPM/CTR/CVR 三项、评估素材规则、逐组定性、应用规则优先级并执行写前闸门。除加载方法论文档外不做文件 IO。 |
| `operating_loop.py` | 编排与 IO：快照校验、账户信号、台账、报告与命令行入口。 |
| `examples/operating/methodology-reference.json` | 阈值与经济参数即数据：目标 ROAS、线索通过率、阶梯、样本关、晋级条件、止损、利用率档位、素材规则、余额警示线、素材条数上界，以及动作目录（每条动作自带验收与止步条件）。 |
| `examples/operating/snapshot-primary.json` | 一个已结算的观察窗口：3 个虚构 Meta 账户、12 个广告组。 |
| `examples/operating/writeback-snapshot.json` | 提供的写前状态：a9 的预算被人手动改成 30，b2 缺失。 |
| `examples/operating/after-snapshot.json` | 提供的后置状态：a10 仍是旧预算。它不是 `apply` 生成的。 |
| `examples/operating/settlement-daily.json` | 结算行，用于平台口径与结算口径互相核对。 |
| `tests/test_operating_loop.py` | 每条规则、每种闸门状态、每项修复的契约测试。 |
| `scripts/demo_operating_loop.py` | 带断言的端到端运行（同一台账跑两轮）。 |

## 五个步骤及其数据

```
1  diagnose：观察快照 + 方法论            -> findings.json
2  gate：findings + 写前状态              -> gate.json / 差异计划
3  apply：gate                           -> application.json / 台账事件
4  verify：gate + 后置状态 + 台账         -> reconciliation.json / 台账事件
5  open：读取台账                        -> 未闭合行；round 另生成 report.md
```

`apply` 登记拟改字段；`verify` 把它们与提供的后置快照比较。`round` 依次执行全部步骤并写出报告；
它不会在开始时回验上一轮，也不会重试 `open` 中的行。可选的结算文件在报告中加一张平台与结算对照表。

样例共产生 18 条账户／广告组／素材层发现。4 条进入差异计划（a1、a4、a8、a10）；
其中 3 条与后置快照匹配，a10 不匹配。

### 目标成本与阶梯

`T = 每条线索价值 × 线索通过率 ÷ 目标 ROAS`，在方法论中分别对应 `offer.unit_price`（按账户）、
`quality_factor` 与 `target_roas`。参考口径使用 10.00 的线索价值、0.90 的通过率和 1.25 的目标，
所以 `T = 10.00 × 0.90 ÷ 1.25 = 7.20`；账户 B 的线索价值 8.00 得到 `T = 5.76`。
T 必须低于每条线索的价值，否则按目标成本拿到的每条线索都在亏钱。
所有价格均为虚构；规则结构与阈值是我实际使用的。

阶梯按数组声明，`T`／`2T`／`3T` 自动变成乘数 1／2／3；止损线以 `T` 的倍数声明
（账户 A 的 3T = 21.60）。价格或通过率变化时，T 及所有由它派生的阈值都会重新计算。

### 指标

从快照读 `spend`／`impressions`／`clicks`／`results`／`value`／`frequency`，推导
`CPM`／`CTR`／`CPC`／`CVR`／`CPA`／`ROAS`／利用率／期望转化数／超成本余量。
推导不出来的值是 `None`，记为缺证据。

零分母不等于零指标：1000 次展示没人点击，`CTR` 是真零；而 `CPC` 没有分母，是 `None`。

### 成本差距分解

`CPA = CPM ÷ (1000 × CTR × CVR)`，取对数后差距可加：

```
log(CPA / CPA基准) = Δlog(CPM) − Δlog(CTR) − Δlog(CVR)
```

三个带符号项说明 CPA 差距中有多少随 CPM、CTR、CVR 变化，并给出各项在绝对值总和中的占比。
这是会计恒等式，不是因果结论。残差不为零说明输入不严格满足恒等式（取整、窗口或口径不同）。

### 判定顺序

先看账户信号：没有任何在投配置的广告组（`ACC_STOPPED`）、有在投配置但今日消耗为 0
（`ACC_NO_DELIVERY`）、余额不高于 `balance_alert_below`（`ACC_BALANCE_LOW`）。然后逐个广告组：

1. 素材提示（熔断、衰竭、超上界）。
2. 拒审（`AD_STATUS`）与链路／回传失败（`LINK_OR_TRACKING_BAD`）结束该组的判定。
3. 缺少花费、展示或转化时该组无法判定，不做猜测。
4. 零线索：展示地板**与**止损线同时满足才 `TEST_STOP_NOCONV`；否则检查声明的 CPC／CTR 早停阈值
   （`TEST_EARLY_STOP`，暂停并复核钩子）；再否则 `TEST_UNDERTESTED`。
5. 有线索：依次检查超成本止损、最低线索数、利用率（花不动）和晋级条件。

具体见 `decide_account` 与 `_classify_adset`。

### 规则优先级：先 hold，再晋级

晋级条件已满足的组，若同组有 `CREATIVE_BREAKER`、`CREATIVE_OVERFLOW` 或 `name_mismatch`
结构提示，或所在账户有任何 P0 级 `ACC_*` 发现，则改为仅建议的 `LADDER_HOLD`，证据中列出全部阻断项。
先处理素材、结构或账户问题，本轮预算不变，下一轮重新判定。每个广告组每轮只做一项变更，
因果才看得清。单独的素材衰竭不阻断晋级。样例中 a6 因素材熔断被 hold，b1 因素材条数超上界
和账户 B 的两条 P0 发现被 hold。

### 素材级规则

* **熔断**（`CREATIVE_BREAKER`，对象类型 `creative`）—— 花费占比超过声明上限**且** CPA 超过 T 的声明倍数，
  且组内至少两条素材。
* **衰竭**（`CREATIVE_FATIGUE`，对象类型 `creative`）—— 频次、CTR 降幅、CVR 降幅三条同时满足。
* **超上界**（`CREATIVE_OVERFLOW`，对象类型 `adset`）—— 素材条数超过 `max_creatives_per_adset`。

素材级发现以素材为 `object_key`、以广告组为 `parent_key`，所以报告会把它们留在所属广告组那一行。

### 写前闸门：五种状态

**只有 `ready` 行进入差异计划。**

| 状态 | 含义 | 处置 |
|---|---|---|
| `ready` | 每个待改字段仍是基线值 | 只把这些字段加入待审计划 |
| `satisfied` | 当前状态已等于目标 | 不写；重复写入只会增加风险和噪音 |
| `conflict` | 某个当前字段既非基线也非目标 | 隔离该行，查明变更来源 |
| `unknown` | 读回中缺少对象或目标字段，或待改字段没有具体基线 | 重新读取状态或追溯原方案基线；缺失绝不等于相等 |
| `advisory` | 该发现不声明任何字段修改 | 无需过闸门；单独计数 |

比较之前，每个目标字段都必须是 `WRITABLE_FIELDS` 允许该 `object_type` 修改的字段：`adset` 可改
`daily_budget`、`status`、`bid_strategy`、`bid_amount`；`creative` 只能改 `status`；`account` 不能改任何字段。
超出范围的字段会抛出 `RuleError` 并停止整轮——这是计划本身有误，不是第六种状态。

已等于目标的字段不需要基线，因为不会修改它。其余字段都需要具体基线；字段缺失与明确为 `null`
都判为 `unknown`。数值 `0` 是具体值。数值按 `Decimal` 比较（`10`、`10.0`、`'10.00'` 相等）；
布尔值永远不等于数字。一个字段未知就把整条建议挡在计划之外；其他建议独立核对。
缺失的基线要从原方案找回，不能用新读到的当前值回填。

### 后置快照核对

`verify` 把 `ready` 行的目标值与 `--after` 文件比较。文件中有该对象则计为 `checked`；
全部目标字段匹配记为 `effective`，否则记为不匹配；缺少对象则不计为已核对。
样例中 a10 的目标预算是 40，后置快照仍是 20。

### 台账

只追加的 JSONL 保存提案、跳过与核对事件；每一行的当前状态由事件流折叠得到。`open` 列出
`pending_write` 与 `verified_not_effective` 行。`conflict` 与 `unknown` 记为 `skipped`，不在 `open` 中，
所以交接时两份清单都要给：样例中唯一的未闭合行是 a10，另外两条需要人处理的是 a9 冲突和 b2 缺少写前状态。

即使没有登记任何事件，`apply` 也会创建台账。台账路径不存在时，`read_events`、`open` 与 `verify`
抛出 `LoopError`，不会报告一份空历史。损坏的 JSON 行会变成 `corrupt` 记录，而不是消失。

## 怎么跑

```bash
# 带断言的端到端运行
python3 scripts/demo_operating_loop.py

# 跑一整轮，产出 findings / gate / reconciliation / report
python3 operating_loop.py round \
    --snapshot examples/operating/snapshot-primary.json \
    --writeback examples/operating/writeback-snapshot.json \
    --after examples/operating/after-snapshot.json \
    --methodology examples/operating/methodology-reference.json \
    --settlement examples/operating/settlement-daily.json \
    --out runs/operating-demo

# 分步运行
python3 operating_loop.py diagnose --snapshot <快照> --methodology <方法论> --out <目录>
python3 operating_loop.py gate     --findings <目录>/findings.json --writeback <写前快照> --out <目录>
python3 operating_loop.py apply    --gate <目录>/gate.json --ledger <台账> --out <目录>
python3 operating_loop.py verify   --gate <目录>/gate.json --after <写后快照> --ledger <台账> --out <目录>
python3 operating_loop.py open     --ledger <台账>

# 测试
python3 -m unittest tests.test_operating_loop -v
```

`round`、`apply`、`verify` 接受 `--at` 固定事件时间戳（默认当前时间）；它不改变快照中的观察日期。
`round` 另接受 `--settlement` 与 `--ledger`；不传 `--ledger` 时使用输出目录中的 `ledger.jsonl`。
输入被拦截时退出码为 2，并在 stderr 输出 JSON 错误。

## 换成你自己的阈值

复制 `examples/operating/methodology-reference.json`，改数字，用 `--methodology` 传入。阈值只来自这份文档：
`balance_alert_below` 与 `max_creatives_per_adset` 是必填项，缺失时直接拒绝，不会被代码默认值替代。
唯一的可选值是 `quality_factor`：省略时视为不扣量（1），提供时必须在 (0, 1] 之间。
配置改变的是参数，不是判定顺序或可写字段范围。

## 边界

* 不连平台、不持凭据、不写账户；输出是给人审阅的清单。
* 不理解媒体内容；素材只按声明的身份引用。
* 规则触发是决策依据，不是原因的证明。

真实使用需要自己的取数、对象映射、权限、审批、提交与回读；我在实盘中通过 WorkBuddy 的连接器、
在我的审批下完成这些步骤。`knowledge/catalog.json` 仍是建议层，`contracts/` 仍是运行时不加载的设计参考。

返回 [文档索引](index.md)。
