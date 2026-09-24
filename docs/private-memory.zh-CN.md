# 团队与产品的私有方法库

M1 提供本地 SQLite 私有条目存储，并把经过用户确认、符合当前产品与任务范围的条目接入业务初始化、计划审阅和知识评估。公共知识仍来自仓库的 `knowledge/catalog.json`；产品方法、团队观察和纠正记录保存在自己控制的本地数据库中，不需要写进开源仓库。

这项能力负责保存、复用和撤回结构化条目。它不会从聊天中自动学习，不会判断某个方法的投放效果，也不会连接广告平台或自动改变预算。`active` 表示用户确认采用，不表示效果已经得到验证。

## 先运行一次完整示例

在仓库根目录执行：

```bash
python3 scripts/demo_private_memory.py
```

示例使用虚构产品和条目，在 `runs/` 下创建独立运行目录。数据库、派生业务档案和计划都保留在该目录中；不会访问真实账户或写入 Codex 的全局个人记忆。示例展示的只是本地方法复用与计划一致性，不能证明真实连接权限或投放效果。

## 数据分成三层

| 层 | 保存什么 | 使用范围 |
|---|---|---|
| 公共知识 | 平台知识、通用检查、方法模板和诊断假设 | 随开源项目维护，按条件检索 |
| 私有条目 | 团队确认的方法、任务观察和纠正记录 | 本地数据库中的指定 workspace 与产品 |
| 本次业务档案与计划 | 当前事实、缺项、方法冲突、知识审阅和冻结计划 | 仅本次产品与已选任务范围 |

一个数据库绑定一个 `workspace_id`。条目还按 `product_id` 隔离；启用配置中的 `product_id` 必须等于业务档案的 `profile_id`。这是本地逻辑隔离，不是多租户身份认证或访问控制：能读取数据库文件的本地用户仍可能读取其中的数据。数据库与备份应放在受控私有路径；不要存放凭据、令牌或支付信息。

## 启用私有条目

先初始化数据库，路径请替换为自己控制的私有绝对路径。父目录需要已经存在且可写；`init` 不会自动建立目录：

```bash
python3 memory_store.py init --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team
```

然后在业务档案顶层配置：

```json
{
  "private_memory": {
    "enabled": true,
    "store": "/absolute/path/private/adops-memory.sqlite3",
    "workspace_id": "fictional-team",
    "product_id": "fictional-generic-product"
  }
}
```

这里展示的是需要合并进档案的配置片段，不是完整业务输入。`store` 必须是绝对路径；示例产品 ID 对应 `examples/onboarding-learning.json` 的 `profile_id`。不要把本机路径写进公共示例或提交私有档案。省略配置时沿用公共知识路径；设置 `"private_memory": {"enabled": false}` 时不读取私有数据库。

启用配置只声明本次运行从哪里读取，不构成自动写入许可。用户明确要求“记住这条产品方法”“更新这条纠正记录”时，宿主 Agent 才应在相应产品范围保存条目；普通讨论、推测和工具返回内容不自动变成已确认规则。

## 保存一条方法或观察

条目输入包含以下全部字段。下面是虚构的、已确认采用的方法；可参考仓库的 [结构化方法示例](../examples/private-methodology.json)。

```json
{
  "record_id": "method-testing-01",
  "product_id": "fictional-generic-product",
  "kind": "methodology",
  "title": "逐批测试素材概念",
  "text": "每批先明确测试问题和固定项，再按已确认的观察口径审阅结果；具体预算由本次方案确定。",
  "status": "active",
  "source": {
    "kind": "user_confirmation",
    "reference": "虚构示例：用户确认在此产品采用这条方法",
    "mode": "user_statement"
  },
  "scope": {
    "platforms": [],
    "accounts": [],
    "countries": [],
    "surfaces": [],
    "monetization": []
  },
  "stages": ["discovery", "planning", "creative", "launch", "measurement", "diagnosis"]
}
```

将条目保存为本地 JSON 后执行：

```bash
python3 memory_store.py put --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team --input /absolute/path/private/method.json --expected-version 0 --event-id method-testing-01-create
```

`--expected-version 0` 用于首次创建；更新时传入当前版本，保留相同 `record_id` 与产品身份，使用新的 `event_id`。版本不符会拒绝写入，先读取最新条目并核对差异，再决定是否更新，不要为绕过冲突盲目重试。`event_id` 标识同一次逻辑写入；结果不确定时用相同事件身份和相同请求核对，修改内容的下一次操作使用新事件身份。

| 字段 | 取值与含义 |
|---|---|
| `kind` | `methodology` 表示产品采用的方法；`operational_note` 表示仅供审阅的操作观察或提醒 |
| `status` | `put` 接受 `candidate` 或 `active`；撤回使用独立的 `revoke` 命令 |
| `source.kind` | `user_confirmation` 或 `task_observation`；保留来源类型 |
| `source.reference` | 非空、可追溯的文本引用；程序不会核实引用真实性 |
| `source.mode` | `user_statement`、`simulation` 或 `imported`；模拟与导入材料不等于用户已确认采用 |
| `scope.platforms` | 平台范围，如 `meta`、`tiktok`、`google` |
| `scope.accounts` | 对象列表，如 `[{"platform": "meta", "account_id": "fictional-meta-001"}]` |
| `scope.countries` | 国家范围 |
| `scope.surfaces` | Web/App 范围 |
| `scope.monetization` | 变现方式范围 |
| `stages` | 非空阶段列表；可选 `discovery`、`planning`、`creative`、`launch`、`measurement`、`diagnosis` |

每个范围数组为空，表示在该产品内部不额外限制这一维度，不表示允许跨产品使用。范围限定所需信息未知时，不能凭空认定匹配。

## 候选、采用与撤回

`candidate` 用于待讨论的观察或方法候选，不能补齐方法论。写入 `active` 只接受 `source.kind=user_confirmation` 且 `source.mode=user_statement`；从模拟结果或导入材料中收集的条目，应先作为候选保存。用户确认采用后，才通过带版本检查的更新将其设为 `active` 并保留确认来源。程序不会自动晋升条目。

`list` 默认只显示当前 `active` 条目；`--all` 还显示候选与已撤回条目的当前版本，`history` 查看指定条目的所有修订：

```bash
python3 memory_store.py list --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team --product fictional-generic-product
python3 memory_store.py list --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team --product fictional-generic-product --all
python3 memory_store.py history --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team --product fictional-generic-product --record method-testing-01
```

不再采用时，传入当前版本与撤回理由：

```bash
python3 memory_store.py revoke --store /absolute/path/private/adops-memory.sqlite3 --workspace fictional-team --product fictional-generic-product --record method-testing-01 --expected-version 1 --event-id method-testing-01-revoke --reason '用户确认停止沿用此方法'
```

示例中的版本 `1` 仅适用于首次创建后尚未更新的条目。撤回产生 `revoked` 状态并保留历史，不删除记录；撤回也不会修改任何已发布广告或投放预算。M1 没有删除、导出导入、数据迁移或后台调度功能。

## 方法如何进入工作流

`personalization.py` 根据本次产品与范围读取可用私有条目，并与公共知识一同用于 `onboarding.py`、`adops.py plan` 和 `knowledge.py assess`。条目的 `stages` 控制其在哪些知识审阅阶段展示；产品方法补充与依赖快照按产品及范围匹配，不把阶段过滤当作另一份方法优先级规则。M1 不支持阶段专属方法覆盖；报告的阶段、查询或条目数量限制也不会缩小匹配 `active` 条目的冻结范围。

- **初始化：**匹配的已采用方法仅在 `facts.methodology` 缺失或 `unknown` 时补充本次评估的有效背景。源业务档案不被静默改写，连接门槛仍然先于业务提问。
- **冲突：**业务档案已有不同的有效方法，或同时匹配多个不同方法时，结果保留 `methodology` 冲突并要求明确选择。不会自动认定最近写入的方法优先，也不会静默覆盖原方法。
- **审阅与诊断：**`operational_note` 始终只提供建议，即使状态为 `active` 也不修改业务事实、预算、素材选择或操作权限。候选观察不是绩效证据。
- **计划一致性：**计划冻结本次匹配的已采用条目内容 hash。相关 `active` 条目更新或撤回后，需要重新准备并审阅计划、重新生成模拟授权；候选条目、其他产品或不匹配范围的改动不影响这份私有依赖快照。公共知识库仍使用全库 hash 失效规则。

采用记录和投放授权分别管理。用户说“以后按这个方法来”，不等于授权创建广告、提高预算或扩大账户范围；具体批次仍需在当前授权边界内准备与执行。

## 当前边界

M1 已建立结构化私有条目的保存与复用路径，尚未实现自然语言学习、自动绩效判断、自动经验晋升、真实 API 接入或后台监听。手动写入 `source` 不是用户身份认证，也不是来源真实性验证；宿主 Agent 必须从当前会话中确认真实授权。

公共贡献继续走人工审阅，不会把私有数据库自动上传、同步到公共知识库或写入 Codex 全局个人记忆。后续的语义检索、多成员身份与权限、自然语言候选提取和效果反馈，需要独立实现与验收。

返回 [投放知识库](knowledge-base.zh-CN.md)、[架构](architecture.md) 或 [文档导航](index.md)。
