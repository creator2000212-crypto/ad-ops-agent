# 投放快循环 — 一个可运行的离线实现

仓库里其它部分负责准备、审阅与接入。这个模块是投手**真正按周期在跑**的那一段：
拿一个已结算的观察窗口 → 逐条给广告组定性 → 输出带证据的动作清单 → 确认脚下没被改过
→ 记录到底发生了什么。

它完全离线运行：读声明的 JSON、套声明的规则、写可审阅的产物和一份只追加的台账。
它不连接任何平台。

## 为什么这个循环比「看一眼数」长这么多

在周期性的投放循环里，造成损失最重的是下面三类事故，而它们**没有一个是算错数**：

| 事故 | 表现 | 对应的闸门 |
|---|---|---|
| 拿不够的样本下结论 | 一个零转化组花了 $3 就被判死 | 样本关：展示地板与止损线**同时**满足才判死 |
| 把没生效的写入当成生效 | 预算「调了」，平台其实没执行 | 写后核对：拿回读与声明的目标值比对 |
| 覆盖掉人工并发改动 | 出方案期间投手自己改了预算 | 写前闸门：冲突行**只隔离**，不覆盖 |

所以这个循环的步骤比算术需要的多，多出来的每一步都只是为了把其中一类事故**变得可见**。

## 模块职责

| 文件 | 职责 |
|---|---|
| `operating_rules.py` | 纯判定层。解析数字、推导指标、把 CPA 差距拆成 CPM/CTR/CVR 三段贡献、评估素材级规则、逐组定性、执行写前闸门。除加载方法论文档外不做文件 IO。 |
| `operating_loop.py` | 编排与 IO。快照校验、账户信号、台账、回执渲染、命令行入口。 |
| `examples/operating/methodology-reference.json` | 阈值即数据：目标 ROAS、阶梯、样本关、晋级条件、止损、利用率档位、素材规则，以及动作目录（每条动作自带「验收」与「止步」）。 |
| `examples/operating/snapshot-primary.json` | 一个已结算的观察窗口（虚构）。 |
| `examples/operating/writeback-snapshot.json` | 写入前复拉的状态，其中一行已被人工改过。 |
| `examples/operating/after-snapshot.json` | 写入后回读的状态，其中一次写入没有生效。 |
| `examples/operating/settlement-daily.json` | 结算行，用于盘面与结算口径互校。 |
| `tests/test_operating_loop.py` | 每条规则、每种闸门结果的契约测试。 |
| `scripts/demo_operating_loop.py` | 带断言的端到端演示。 |

## 循环的六个步骤

```
0  回验上一轮提出的动作          -> 台账里仍挂着的行
1  取一个已结算的观察窗口        -> 快照 JSON
2  逐组按阶梯定性                -> diagnose / decide
3  把发现变成带证据的动作        -> findings.json
4  动任何东西之前先过写前闸门    -> gate.json
5  把本轮记进只追加的台账        -> apply
6  核对到底写没写成，再出回执    -> report.md
```

### 目标成本与阶梯

`T = 单价 × 质量系数 ÷ 目标 ROAS`。无扣量时质量系数为 1，所以单价 4.00、目标 85% 时
`T = 4.71`。阶梯按数组声明，`T`／`2T`／`3T` 自动变成乘数 1／2／3；止损线以 `T` 的倍数声明
而不是写死金额 —— 这样单价变了，整套阈值仍然自洽。

### 指标

从快照读 `spend`／`impressions`／`clicks`／`results`／`value`／`frequency`，推导
`CPM`／`CTR`／`CPC`／`CVR`／`CPA`／`ROAS`／利用率／期望转化数／超成本余量。
**推导不出来的值一律是 `None`，记为「缺证据」。**

零分母不等于零指标：1000 次展示没人点击，`CTR` 是真零；而 `CPC` 没有分母，是 `None`。
引擎不会拿其中一个当另一个。

### 成本归因

`CPA = CPM ÷ (1000 × CTR × CVR)`，取对数后差距可加：

```
log(CPA / CPA基准) = Δlog(CPM) − Δlog(CTR) − Δlog(CVR)
```

三个带符号项连同各自在绝对值总和里的占比一起输出。它回答的是
**「漏斗哪一段把成本推高了」**，而不是「哪个数字看起来最大」。
残差不为零说明引用的指标之间不严格满足恒等式 —— 通常是公布前做过四舍五入，这本身值得知道。

### 样本关

零转化组只有在**展示地板与止损线同时越过**时才判死。未过地板的一律记为「未测充分」。
贵点击或 CTR 异常低会触发早停：**停新增花费，但不判素材无效** —— 高 CPC 的上游通常是低 CTR，
要修的是钩子，不是出价。

### 素材级规则

* **熔断** —— 需要花费占比超限**且**成本超过声明倍数，**且**组内至少两条素材。
  单素材组里「它吃掉了全部花费」是恒真的废话，那种情况由组级止损伤覆盖。
* **衰竭** —— 频次、CTR 降幅、CVR 降幅三条**同时**成立才判。满足一两条属于噪音。
* **超上界** —— 素材条数超过声明上界，在谈扩量之前先检查。

### 写前闸门

每条动作给出五种结果之一。**只有 `ready` 行可写，且只写真正不同的那些字段**：

| 结果 | 含义 | 处置 |
|---|---|---|
| `ready` | 字段仍等于基线值 | 只发差异字段 |
| `satisfied` | 目标值已经就位 | **不写** —— 再写一次是 significant edit，会重置学习期 |
| `conflict` | 现值既非基线也非目标 | 隔离这一行；不覆盖人工改动，也不让整批重做 |
| `unknown` | 没读到写前状态，或字段不在读取结果里 | 先复拉。**缺失不等于相等** |
| `advisory` | 该发现不涉及写入字段 | 无需过闸门；单独计数，避免虚增需要人处理的行数 |

「字段读不到」被故意判成 `unknown` 而不是放行。今天还没有 bid_amount 的组，正是盲写一个出价最危险的地方。

### 写后核对

写入之后再读一次，与声明的目标值比对。不一致的记为**未真正生效**，并且该行**继续挂着**。
发出去的写入不等于发生了的写入。

### 台账

只追加的 JSONL。提案、跳过、核对三类事件累积，状态由事件流折叠得出，历史从不被改写。
一行损坏会以 `corrupt` 事件显式暴露，而不是消失 —— 一个静默蒸发的动作比一个明显坏掉的动作更糟。

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

`round` 与各子命令都接受 `--at`，可以把一次运行钉在固定时间上；不传则用当前时间，
差异只体现在台账的时间戳里。

## 换成你自己的阈值

复制 `examples/operating/methodology-reference.json`，改数字，用 `--methodology` 传进去。
**动作目录跟着阈值一起走**，所以每条动作永远自带它的「验收」与「止步」条件。
引擎里没有任何单价、目标 ROAS、预算倍数被写死。

## 这个模块刻意不做的事

* 不连平台、不持凭据、不写账户。输出是给人看的动作清单，不是已执行的指令。
* 不读媒体内容。素材只按声明的身份被引用。
* 不自动决策。每条规则都产出带证据的建议，闸门和人始终在路径上。
* 不宣称某个账户的结果可推广。规则触发不等于证明了原因，修好了一行也不等于证明了修法有效。

## 与仓库其它部分的关系

`knowledge/catalog.json` 仍是上下文建议层，`contracts/` 下的文件仍是**运行时不加载**的设计参考。
本模块是可执行的、自包含的：它不读契约，也不向任何平台写入。
将来若接入真实连接器，它替换的是边缘的快照文件 —— 定性、闸门与核对逻辑不变。

返回 [文档索引](index.md)。
