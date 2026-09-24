# 从 0 开始：一个投手、3 个在投账户、10 个广告组

读引擎代码回答的是「**它怎么算**」。这一份回答的是「**它怎么落地**」—— 从你手上那堆原始数字开始，
一步一步走到一份可以直接发出去的回执，中间每一步谁做了什么判断、又拒绝了什么判断。

> 想边看边跑：`python3 demo/run_demo.py --steps` —— 终端会按下面这个顺序逐步展开。
> 不想跑任何命令：本目录 [`expected/report.md`](expected/report.md) 就是最终那份回执。

---

## 第 0 步 · 起点：先把「不做」的成本摆出来

北京时间 11:50。你手上有：

- 3 个在投账户（两个 Meta 户 + 一个已断档的）
- 10 个广告组，分布在 T / 2T 两个阶梯档
- 昨天（9/23）的数据刚结算完
- 一张写好的方法论：目标 ROAS 85%、阶梯 `T → 2T → 3T`、止损 `3T`

你要回答的只有一个问题：**今天该动哪个？**

手工做这件事，是这五步：

1. 逐个算 CPA、CTR、CVR、预算利用率；
2. 判断哪些该加预算、哪些该停、**哪些样本还不够所以不能判**；
3. 回想哪些组昨天已经被自己改过 —— 别把人工改动覆盖掉；
4. 改完之后确认平台**真的改上了**；
5. 写一页日报。

第 2、3、4 步是**最容易做错且不自知**的三步。下面每一步走到时，会告诉你这套东西在那里做了什么。

**数据接入长什么样**（这就是「取数」这一层要产出的东西，把 API 返回整理成可审阅的快照）：

```json
{
  "kind": "operating_snapshot",
  "as_of": "2026-09-24T11:50:00+08:00",
  "observation": {"kind": "settled_day", "date": "2026-09-23", "complete_delivery_day": true},
  "accounts": [{
    "account_key": "fictional-meta-account-a",
    "account_timezone": "Etc/GMT",
    "offer": {"offer_key": "fictional-offer-alpha", "unit_price": "4.000"},
    "adsets": [{
      "adset_key": "fictional-adset-a1",
      "name": "1n1 | A1 | MAX | $10",
      "configured_status": "ACTIVE", "effective_status": "ACTIVE",
      "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
      "daily_budget": "10.00", "ladder_stage": "T",
      "spend": "12.40", "impressions": 3200, "clicks": 210, "results": 3, "frequency": "1.18"
    }]
  }]
}
```

**为什么第一件事是写 `as_of` 和观察窗口**：不知道数据截止到什么时候，就没法谈「成熟度」，
后面所有判定都是空的。「覆盖完整投放日」这一位还直接决定能不能晋级 —— 落在盘中的档窗口不算数。

---

## 第 1 步 · 定性：把 10 个组变成「谁该动」

```bash
python3 operating_loop.py diagnose \
    --snapshot examples/operating/snapshot-primary.json \
    --methodology examples/operating/methodology-reference.json \
    --out demo/out/steps/1-diagnose
```

```
{"kind": "operating_findings", "accounts": 3, "proposals": 16, "structure_findings": 3}
→ 16 条发现，覆盖 12 类判据
```

### 这一步真正的设计：**判定顺序本身就是判据**

引擎不是把所有指标算出来一起看，而是**按固定顺序过 7 道关卡，先过的先赢**：

| # | 关卡 | 不过会怎样 |
|---|---|---|
| 1 | 账户健康（断档 / 零消耗 / 余额） | 账户级信号先报，不逐组扯 |
| 2 | 硬异常（被拒审？链接失效？） | 立即处理，不等观察期 |
| 3 | **指标算得出吗** | 算不出 ⇒ 缺证据，**不是 0** |
| 4 | **样本关**（零转化先看展示够不够） | 样本不够 ⇒ 只记录，**不判素材好坏** |
| 5 | 止损线（`花费 − T×转化 ≥ 3T`） | 过了就停 |
| 6 | 预算利用率（花不动 / 顶满） | 花不动 ⇒ 先解决能不能花 |
| 7 | **才轮到晋级** | 前六关都过才谈加预算 |

把顺序倒过来会怎样？—— 你会先看到「a5 的 CPA 只有 $1.60，比目标 $4.71 好太多，该加预算」，
但它预算利用率只有 **32%**。**它的问题不是贵，是花不动。** 顺序保证你先看到这个。

### 同一批数据里，两条看起来一样的数据得到相反结论

| 组 | 数据 | 引擎结论 | 理由 |
|---|---|---|---|
| `a3` | 花 $15.30 / **420 展示** / 0 转化 | `TEST_STOP_NOCONV`（P0 暂停） | 420 **过了判死门槛 300**，且 15.30 **过了止损线 14.12** |
| `a2` | 花 $3.10 / **180 展示** / 0 转化 | `TEST_UNDERTESTED`（只记录） | 180 **未过门槛** ⇒ 样本不足，不得判素材好坏 |

两个组的转化数都是 0。**只有顺序正确的引擎才敢对其中一个说「我不知道」。**

---

## 第 2 步 · 从「发现」到「动作」：每条动作必须自带验收与止步

`diagnose` 产出的不是一句话建议，而是一个**可审阅的对象**。这是「agent 在干活」与「agent 在给建议」的分界：

```json
{
  "code": "LADDER_PROMOTE",
  "level": "P1",
  "object_key": "fictional-adset-a1",
  "parent_key": "fictional-adset-a1",
  "action": "原组预算 x2（T -> 2T -> 3T）",
  "window": "2-3 个完整投放日",
  "acceptance": "回读 daily_budget = 目标档位金额，且变更流水可查。两者不一致视为未执行。",
  "stop_condition": "回读发现 bid_strategy / bid_amount 被默认覆盖，或该档未覆盖完整投放日 -> 本轮不晋级。",
  "baseline": {"daily_budget": "10.00"},
  "target":   {"daily_budget": "20.00"},
  "evidence": ["转化 3 >= 3、覆盖完整投放日 = True、CPA 4.13 <= T 4.71。"]
}
```

三个字段值得单独说：

- **`acceptance`（验收）** —— 怎么算「做完了」。没有它，动作永远停在「我说了」。
- **`stop_condition`（止步）** —— 什么情况下**不许做**。比如「改哈希重传只试 1 次」、
  「不得为创建成功率静默换优化目标」。这是防止 agent 越界的唯一办法。
- **`baseline` / `target`** —— 出方案那一刻读到什么、要改成什么。**下一步的闸门靠这两个字段工作。**

16 条发现各自带着这三样东西，`evidence` 里放着「为什么是它」。

---

## 第 3 步 · 写前闸门：动手之前，先确认脚下没被改过

```bash
python3 operating_loop.py gate \
    --findings demo/out/steps/1-diagnose/findings.json \
    --writeback examples/operating/writeback-snapshot.json \
    --out demo/out/steps/2-gate
```

产出 **16 条 → 只有 4 条可写**。5 种结果：

| 结果 | 数量 | 含义 |
|---|---|---|
| `ready` 可执行 | **4** | 现值与基线一致 ⇒ 只发差异字段 |
| `satisfied` 已满足 | 1 | 目标值已就位 ⇒ **跳过不写**（写了是 significant edit，会重置学习期） |
| `conflict` 冲突隔离 | 1 | **人工改过 ⇒ 只隔这一行** |
| `unknown` 未知 | 1 | 写前状态没读到 ⇒ **先复拉**（缺失≠相等，绝不放行） |
| `advisory` 仅建议 | 9 | 素材级/账户级发现，不涉及写入 ⇒ 无需过闸门 |

真实的两条需要人处理：

```
⚠ fictional-adset-a9 · LADDER_PROMOTE · 冲突隔离
   — daily_budget：现值 30.00 既非基线 10.00 也非目标 20.00 ⇒ 人工改过，隔离该行。
⚠ fictional-adset-b1 · LADDER_PROMOTE · 未知
   — 写前状态里没有 'fictional-adset-b1' 的记录 ⇒ 先复拉，不要盲写。
```

**为什么这一步必须存在**：从取数到你动手，中间隔了几分钟——现实里是几十分钟。
这段时间里投手很可能已经在 Ads Manager 里改过。

- 不比对就写 ⇒ **覆盖掉人工改动**；
- 一条冲突就让整批重做 ⇒ 另外 15 条白等一轮。

所以规则是：**只隔离冲突那一行，其余行独立执行。**

---

## 第 4 步 · 执行：只发差异字段，并把本轮记进只追加台账

```bash
python3 operating_loop.py apply \
    --gate demo/out/steps/2-gate/gate.json \
    --ledger demo/out/steps/ledger.jsonl --out demo/out/steps/3-apply
```

```
{"planned_writes": 4, "recorded_events": 7, "not_written": 12}
  → fictional-adset-a1  LADDER_PROMOTE       只发 {'daily_budget': '20.00'}
  → fictional-adset-a4  TEST_STOP_OVERCOST   只发 {'status': 'PAUSED'}
  → fictional-adset-a6  LADDER_PROMOTE       只发 {'daily_budget': '40.00'}
  → fictional-adset-a8  LINK_OR_TRACKING_BAD 只发 {'status': 'PAUSED'}
```

两个细节：

- **只发差异字段。** 不是把整个对象写回去 —— 那样等于把方案里没打算改的字段也重写一遍。
- **台账只追加。** 状态由事件流折叠得出，历史从不被改写。一行损坏会以 `corrupt` 事件暴露，不会消失。

> 真实环境里，`apply` 的位置换成连接器调用，**其余逻辑一字不变**。这一步在离线版里只记录决定。

---

## 第 5 步 · 写后核对：确认「发出去的」变成了「发生了的」

```bash
python3 operating_loop.py verify \
    --gate demo/out/steps/2-gate/gate.json \
    --after examples/operating/after-snapshot.json \
    --ledger demo/out/steps/ledger.jsonl --out demo/out/steps/4-verify
```

```
{"checked": 4, "effective": 3, "ineffective": 1}
  ✗ fictional-adset-a6 未生效 — 写后回读与目标不一致：
    daily_budget：期望 40.00，实读 20.00
```

**这是最容易被跳过、也最容易吃亏的一步。** 接口返回成功 ≠ 字段变了。
回读一次再比对，不一致就记「未真正生效」，并且 **这一行继续挂着**，
不会被当作已完成而推进下一档。

---

## 第 6 步 · 回执：一页纸，给人看

前五步的产物合起来 → [`expected/report.md`](expected/report.md)。

它包含：一句话结论 → 账户信号（含能力缺口）→ 逐组判定明细 → 闸门五态 → 需要人处理的行 →
写后核对 → 结算口径对账 → 结构警告 → 纪律。

一份可以直接发出去的日报，不需要你再排版。

---

## 第 7 步 · 闭环：回到第 0 步

```bash
python3 operating_loop.py open --ledger demo/out/steps/ledger.jsonl
```

```
{"open": 1, "rows": [{"object_key": "fictional-adset-a6",
                      "status": "verified_not_effective",
                      "patch": {"daily_budget": "40.00"}}]}
```

下一轮开头**先回验这一轮没做完的**，再出新动作。

**没有这一步，动作就永远悬空** —— 这是「系统」与「零散优化」的分界：
上一轮让改预算，这一轮没人确认改没改、改了有没有用，于是每轮重新列一遍同样的清单。

于是循环闭合：**第 0 步 → … → 第 7 步 → 第 0 步**。

---

## 跑起来

```bash
python3 demo/run_demo.py            # 一次跑完，打印回执
python3 demo/run_demo.py --steps    # 按上面 7 步逐步展开（推荐第一次看）
python3 demo/run_demo.py --check    # 校验仓库里的样例是否仍与真实运行一致
python3 demo/run_demo.py --refresh  # 从一次真实运行重新生成 demo/expected/
```

`--steps` 走完之后照样会生成完整回执，所以「逐步看」与「直接看结果」得到的是同一个东西。

### 换成你自己的账户与阈值

```bash
# 1. 把取数结果整理成同结构的快照（照 examples/operating/snapshot-primary.json 的形状）
# 2. 复制方法论改数字
cp examples/operating/methodology-reference.json my-methodology.json
# 3. 跑
python3 operating_loop.py diagnose --snapshot my-snapshot.json \
    --methodology my-methodology.json --out runs/my-round
```

引擎里**没有任何单价、目标 ROAS 或预算倍数被写死**。动作目录跟着阈值一起走，
所以每条动作永远自带它的「验收」与「止步」。

---

## 这个文件夹里有什么

| 路径 | 作用 |
|---|---|
| `README.zh-CN.md` | 你正在读的这份：从 0 到闭环的线性走查 |
| `README.md` | 同样的内容，英文 |
| `run_demo.py` | 一条命令跑通；`--steps` 逐步展开；负责 `expected/` 的生成与漂移校验 |
| `expected/report.md` | **一轮真实运行的回执**，不用跑就能看 |
| `expected/summary.json` | 同一轮的确定性摘要（闸门计数、写计划、核对结果） |

引擎在仓库约定的位置（根目录 `operating_rules.py` / `operating_loop.py`），
fixture 在 `examples/operating/`。这个文件夹是**展示层**，不复制任何逻辑。

> **为什么 `expected/` 要有漂移校验**：一份比代码说得更多的样例，比没有样例更糟。
> CI 跑了 `--check`，样例一旦与代码脱节就会红。

---

## 它刻意不做什么

- **不连接任何平台、不持凭据、不写任何账户。** 输出是给人审阅的动作清单，不是已执行的指令。
- **不读素材内容。** 素材只按声明的身份被引用。
- **不自动决策。** 每条规则都产出带证据的建议，闸门和人始终在路径上。
- **不宣称结果可推广。** 规则触发不等于证明了原因；修好了一行也不等于证明了修法有效。

下一步读：[投放快循环完整说明](../docs/operating-loop.zh-CN.md) —— 口径、归因公式、
五种闸门结果的完整规则、以及怎么替换成你自己的阈值。

返回 [项目首页](../README.zh-CN.md)。
