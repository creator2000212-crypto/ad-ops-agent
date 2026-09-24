# 投放快循环 — 一个可运行的离线实现

本页是规则、数据依赖与 CLI 的技术参考。先看 [一轮投放检查的具体案例](../demo/README.zh-CN.md)
了解人与 Agent 的分工和样例结果；[从零搭建](build-from-zero.zh-CN.md) 说明架构与搭建顺序。

这个模块读取声明为已结算的观察窗口和方法参数，生成带证据的建议，比较输入文件中的字段，
再写出报告和只追加的台账。它完全离线：不采集平台数据、不提交广告修改、不检查用户操作授权，
也没有后台调度器。所有状态都基于调用者提供的 JSON。

## 为什么这个循环比「看一眼数」长这么多

这份样例演示下面三类问题的检查方式：

| 事故 | 表现 | 对应的闸门 |
|---|---|---|
| 拿不够的样本下结论 | 一个零转化组花了 $3 就被判死 | 样本关：展示地板与止损线**同时**满足才判死 |
| 把目标值当成实际状态 | 计划要求预算40，提供的后置快照仍为20 | 比较后置快照与目标值；本例没有实际写入 |
| 未察觉现值已经变化 | 当前字段既非基线也非目标 | 写前比较隔离冲突行；差异本身不能证明是谁修改的 |

这些检查把建议、状态差异和待核对事项分别保留下来，供用户审阅。

## 模块职责

| 文件 | 职责 |
|---|---|
| `operating_rules.py` | 纯判定层。解析数字、推导指标、把 CPA 差距拆成 CPM/CTR/CVR 三段贡献、评估素材级规则、逐组定性、执行写前闸门。除加载方法论文档外不做文件 IO。 |
| `operating_loop.py` | 编排与 IO。快照校验、账户信号、台账、回执渲染、命令行入口。 |
| `examples/operating/methodology-reference.json` | 阈值即数据：目标 ROAS、阶梯、样本关、晋级条件、止损、利用率档位、素材规则，以及动作目录（每条动作自带「验收」与「止步」）。 |
| `examples/operating/snapshot-primary.json` | 一个已结算的观察窗口（虚构）。 |
| `examples/operating/writeback-snapshot.json` | 独立提供的写前状态样例，其中一行与基线不同。程序不会复拉账户。 |
| `examples/operating/after-snapshot.json` | 独立提供的后置状态样例，其中一个拟改对象与目标不匹配；不是 `apply` 生成的结果。 |
| `examples/operating/settlement-daily.json` | 结算行，用于盘面与结算口径互校。 |
| `tests/test_operating_loop.py` | 每条规则、每种闸门结果的契约测试。 |
| `scripts/demo_operating_loop.py` | 带断言的端到端演示。 |

## 与 demo 对应的五步及数据依赖

```
1  diagnose：观察快照 + 方法参数          -> findings.json
2  gate：findings + 写前状态样例          -> gate.json / 差异计划
3  apply：gate                           -> application.json / 追加台账
4  verify：gate + 后置状态样例 + 台账     -> reconciliation.json / 追加核对事件
5  open：读取台账                        -> 未闭合行；round 另生成 report.md
```

`apply` 只登记拟改字段，不发送修改请求。`verify` 比较调用者提供的后置快照，不从平台取数。
`round` 依次执行上述计算与登记，最后输出报告和未闭合行数量；它不会在开始时自动回验上一轮，
也不会根据 `open` 自动重试。结算文件提供报告中的结算数据与口径说明，不自动解释数据差异。

样例含3个 Meta 账户、10个广告组，共16条账户／广告组／素材层发现；4条进入差异计划，
后置样例中3条匹配、1条不匹配。`ready` 不等于授权，快照匹配不等于真实修改成功。

### 目标成本与阶梯

`T = 单价 × 质量系数 ÷ 目标 ROAS`。无扣量时质量系数为 1，所以单价 4.00、目标 85% 时
`T = 4.71`。阶梯按数组声明，`T`／`2T`／`3T` 自动变成乘数 1／2／3；止损线以 `T` 的倍数声明
而不是固定金额；单价变化时，目标成本与相关止损阈值会重新计算。

### 指标

从快照读 `spend`／`impressions`／`clicks`／`results`／`value`／`frequency`，推导
`CPM`／`CTR`／`CPC`／`CVR`／`CPA`／`ROAS`／利用率／期望转化数／超成本余量。
**推导不出来的值一律是 `None`，记为「缺证据」。**

零分母不等于零指标：1000 次展示没人点击，`CTR` 是真零；而 `CPC` 没有分母，是 `None`。
引擎不会拿其中一个当另一个。

### 成本差距分解

`CPA = CPM ÷ (1000 × CTR × CVR)`，取对数后差距可加：

```
log(CPA / CPA基准) = Δlog(CPM) − Δlog(CTR) − Δlog(CVR)
```

在指标为正且口径可比时，三个带符号项描述 CPA 差距与 CPM、CTR、CVR 数值变化的数学关系，
并输出各项在绝对值总和里的占比。**这不是因果归因，也不能证明修改某项会改善结果。**
残差不为零表示输入指标不严格满足恒等式，应检查精度、观察窗口和统计口径；程序不判断具体原因。

### 样本关

零转化分支只有在**展示地板与止损线同时满足**时才产生 `TEST_STOP_NOCONV`。
未触发该条件时，程序再检查声明的 CPC／CTR 早停阈值，命中则提出暂停建议，
不下「素材无效」结论；否则返回 `TEST_UNDERTESTED`。这些建议都不会自行停止账户花费。

样本关不是所有规则的统一第一步：账户信号单独产生；逐组先记录素材提示，再检查拒登、链路异常
和必要指标缺失。有转化分支依次检查超成本止损、最低转化数、利用率和晋级条件。
具体顺序见 `decide_account` 与 `_classify_adset`，不能概括为「样本不足时所有后续规则都不运行」。

### 素材级规则

* **熔断提示** —— 需要花费占比超限**且**成本超过声明倍数，**且**组内至少两条素材。
  单素材组不触发这条素材规则，仍可进入组级判断。
* **衰竭提示** —— 频次、CTR 降幅、CVR 降幅三条**同时**成立才触发；未触发不证明素材没有问题。
* **超上界提示** —— 素材条数超过声明上界时记录建议。

素材提示与组级建议是分别生成的，提示不会自动阻断晋级。样例中的 a6 同时有素材提示和晋级候选。

### 写前闸门

每条建议给出五种结果之一。**只有 `ready` 行进入差异计划；这不是用户授权或执行回执**：

| 结果 | 含义 | 处置 |
|---|---|---|
| `ready` | 当前实现的字段比较通过，仍有差异字段 | 将差异字段加入待审阅计划，本模块不提交 |
| `satisfied` | 输入的当前状态已是目标值 | 不生成重复修改；程序不判断学习期是否会重置 |
| `conflict` | 现值既非基线也非目标 | 隔离这一行并查明差异来源，不推断修改者 |
| `unknown` | 输入中没有该对象，或缺少目标字段 | 先补充当前状态；缺失不等于相等 |
| `advisory` | 该发现不涉及写入字段 | 无需过闸门；单独计数，避免虚增需要人处理的行数 |

样例中 `ready` 行的现值与已声明基线一致。通用函数在基线值为 `None` 时也可能产生 `ready`，
因此该标签不能代替完整的基线、授权或平台能力检查。

### 后置快照核对

`verify` 只比较 `ready` 行的目标值与 `--after` 文件。对象存在时计入 `checked`，全部目标字段匹配
记为 `effective`，否则记为不匹配；缺少对象则不计入已核对。这里的 `effective` 是快照比较结果，
不证明发送过真实请求，更不证明广告投放或业务效果。样例 a6 的目标预算为40，后置值为20。

### 台账

只追加的 JSONL 保存提案、跳过和核对事件，当前状态由事件流折叠得到。`open` 只列出
`pending_write` 和 `verified_not_effective`；它不执行回验、重试或下一轮调度。
`conflict`／`unknown` 记录为 `skipped`，不在 `open` 中；`advisory` 不登记动作事件。
样例的1条未闭合行是 a6，另2条需人工核对的是 a9 冲突和 b1 缺快照，应分别查看。

`read_events` 会为损坏的 JSON 行返回 `corrupt` 记录，但 `open` 不是完整事件或损坏记录清单。

## 怎么跑

```bash
# 带断言的端到端演示
python3 scripts/demo_operating_loop.py

# 跑一整轮，产出 findings / gate / reconciliation / report
python3 operating_loop.py round \
    --snapshot examples/operating/snapshot-primary.json \
    --writeback examples/operating/writeback-snapshot.json \
    --after examples/operating/after-snapshot.json \
    --methodology examples/operating/methodology-reference.json \
    --settlement examples/operating/settlement-daily.json \
    --out runs/operating-demo

# 也可以分步跑
python3 operating_loop.py diagnose --snapshot <快照> --methodology <方法论> --out <目录>
python3 operating_loop.py gate     --findings <目录>/findings.json --writeback <写前快照> --out <目录>
python3 operating_loop.py apply    --gate <目录>/gate.json --ledger <台账> --out <目录>
python3 operating_loop.py verify   --gate <目录>/gate.json --after <写后快照> --ledger <台账> --out <目录>
python3 operating_loop.py open     --ledger <台账>

# 测试
python3 -m unittest tests.test_operating_loop -v
```

只有 `round`、`apply`、`verify` 接受可选 `--at`，用于事件及 application／reconciliation 产物的时间戳；
省略时使用当前时间。`diagnose`、`gate`、`open` 不接受这个参数。它不会修改输入快照的观察日期。
`round` 的 `--settlement` 和 `--ledger` 也是可选项；不传 `--ledger` 时使用输出目录中的 `ledger.jsonl`。

## 换成你自己的阈值

复制 `examples/operating/methodology-reference.json`，改数字，用 `--methodology` 传进去。
动作目录提供建议的验收与止步说明；这些文字不是独立的执行授权检查。
配置修改仅覆盖实现已支持的参数，不能改变 Python 中的分支顺序或增加新的平台动作。
实现中仍有默认值，例如缺少 `quality_factor` 时采用1；不能假定所有行为都由配置文件定义。

## 这个模块刻意不做的事

* 不连平台、不持凭据、不写账户。输出是给人看的动作清单，不是已执行的指令。
* 不读媒体内容。素材只按声明的身份被引用。
* 不自动操作账户。规则会自动分类并生成建议，但本模块没有用户审批、发布或后台调度实现。
* 不宣称某个账户的结果可推广。规则触发不等于证明了原因，修好了一行也不等于证明了修法有效。

## 与仓库其它部分的关系

`knowledge/catalog.json` 仍是上下文建议层，`contracts/` 下的文件仍是**运行时不加载**的设计参考。
本模块是可执行的、自包含的：它不读契约，也不向任何平台写入。
真实接入需要独立设计取数口径、对象映射、权限、授权、提交与回读流程，并重新验收适用的规则；
不能把文件输入直接替换为连接器就视为完成上线。

返回 [文档索引](index.md)。
