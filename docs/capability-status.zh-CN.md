# 实盘与演示对照

[English](capability-status.md) · [项目首页](../README.zh-CN.md) · [实际是怎么跑的](how-it-ran.zh-CN.md) · [案例](case-studies.zh-CN.md)

哪些在实盘账户上跑过、本仓库实现了什么、怎么运行。实盘工作是 2026 年 9 月通过 WorkBuddy（腾讯的桌面 AI Agent；本项目与其无关联）进行的 Meta 与 TikTok 线索投放；日期和运行记录见[运行记录](how-it-ran.zh-CN.md)。

**范围。** 本仓库按设计离线运行：所有模块只读取本地文件（JSON；原型的模拟与私有记忆库使用 SQLite），发起的平台调用为 0。实盘读写通过 WorkBuddy 的连接器完成，上线和预算调整由我批准（[WB-08](case-studies.zh-CN.md#wb-08) 是这一点被打破的一次，也是批准成为显式关卡的原因）。在 Agent 中打开本项目不会连接任何广告账户。

## 对照表

| 能力 | 实盘运行（2026） | 公开代码 | 在这里运行 |
|---|---|---|---|
| 激活前逐字段读回 | 9 月 10—27 日的交互建单遵循暂停创建 → 读回 → 激活（[WB-06](case-studies.zh-CN.md#wb-06)：有一批缺少保存的最终读回；[WB-08](case-studies.zh-CN.md#wb-08)：有一次未经批准的激活） | [`readback.py`](../readback.py)：`verify_build()`，HOLD/ACTIVATE 回执 | `python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json` |
| 建单清单预检 | 本仓库新增；实盘建单依赖读回 | [`preflight.py`](../preflight.py)：命名与配置、URL 参数、特殊类别声明、归因、重复文件 | `python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json` |
| 按结算表 20 列格式每日取数 | 每日任务，9 月 21—26 日；9 月 20 日与结算导出做过一次比对并修正范围（[WB-09](case-studies.zh-CN.md#wb-09)） | [`operating_rules.py`](../operating_rules.py) 中的结算对账：花费、结果数、CPA 差异；范围缺口绝不补零 | `python3 demo/run_demo.py --lang zh-CN`（“平台与结算对账”一节） |
| 按 T 阶梯给广告组分类 | 12 小时任务，9 月 22—26 日 | [`operating_rules.py`](../operating_rules.py) 的 `decide_account()`，阈值来自 [`methodology-reference.json`](../examples/operating/methodology-reference.json) | `python3 demo/run_demo.py` |
| 先回验上一轮 | 每轮 12 小时巡检，9 月 22—26 日 | [`operating_loop.py`](../operating_loop.py) 的只追加台账：`apply`、`verify`、`open` | `python3 scripts/demo_operating_loop.py` |
| 五态写入关卡与写后核对 | 9 月 24 日移植进私有实盘巡检 | [`operating_rules.py`](../operating_rules.py) 的 `gate()` 与 `reconcile()` | `python3 demo/run_demo.py --steps` |
| 每个动作的验收标准与停止条件 | 9 月 24 日起覆盖每个动作 | 方法文件中的动作目录，由 `scripts/render_decision_matrix.py` 渲染 | [决策矩阵](decision-matrix.md)（英文） |
| CPA 为什么变化（CPM、CTR、CVR） | 本仓库新增 | [`operating_rules.py`](../operating_rules.py) 的 `cpa_driver_decomposition()` | `python3 demo/run_demo.py --lang zh-CN`（“CPA 为什么变了”一节） |
| 读写广告账户 | 通过 WorkBuddy 的连接器：Meta 走托管 MCP 连接器，TikTok 走 Agent 按我的要求编写的 TikTok API for Business 客户端 | 无：平台调用为 0 | — |
| 定时调度 | WorkBuddy 本地调度器，9 月 20—26 日；9 月 26 日起暂停 | 无 | — |

Google Ads 只出现在接入说明和模拟适配器中；实盘工作只涉及 Meta 与 TikTok。

## 上线前原型

以下模块来自一个独立的规划与初始化原型，不属于实盘运行的部分，使用虚构输入运行。

| 模块 | 实现了 | 不做 |
|---|---|---|
| `onboarding.py` / `guidance.py` | 结构化业务事实、缺项检查、虚构连接快照、规则式引导 | 验证真实连接或安装连接器 |
| `methodology.py` / `task.py` | 两类方法模板、明确采用、私有任务副本与版本 | 解析任意自然语言 SOP |
| `planning.py` | 按已声明组件身份生成测试单元、预算与计划 | 理解媒体内容、排序效果或随机 A/B 分配 |
| `knowledge.py` | 带适用条件、来源与证据缺口的版本化知识 | 验证平台事实或下因果结论 |
| `memory_store.py` / `personalization.py` | 按产品范围的私有记录，含版本、历史与撤回 | 自动学习或认证效果 |
| `adops.py` | 模拟批次计划、模拟授权、SQLite 对象、同一状态目录的恢复 | 向平台提交；`native_payload` 始终为 `null` |

```bash
python3 scripts/demo.py                  # 模拟批次、中断与恢复
python3 scripts/demo_private_memory.py   # 私有方法的保存、修订与复用
python3 scripts/demo_methods.py          # 六个虚构输入，两种方法路线
```

## 检查

只需 Python 3.9+ 与标准库，无需账户或 API 密钥。

```bash
python3 -m unittest discover -s tests -v
python3 demo/run_demo.py --check
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json \
    --check examples/readback/expected/meta-receipt.md
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json \
    --check examples/preflight/expected/checklist.md
python3 scripts/check_repository.py
```

这些检查通过说明离线逻辑自洽，不说明任何实盘账户的情况。

## 用在你自己的账户上

使用已验证且获授权的工具，按[宿主工作流](workflow.zh-CN.md)操作，并为每个批次保留一份[任务记录](../templates/task-record.zh-CN.md)：范围内的账户与工具及读取时间、已确认的业务背景与方法、具体批次及其预算影响和你的批准、逐对象读回（审核、可投、实际投放分开），以及交接时的未完成项。只读任务只需要读取权限，不要为了填满清单而写入账户。
