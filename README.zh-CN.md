# Ad Ops Agent · 三平台投放 Agent

**面向 Meta（FB）、TikTok（TK）、Google Ads（GG）的通用投放 Agent 底座。**

[English](README.md) · [文档导航](docs/index.md) · [开发路线](docs/roadmap.md) · [MIT 许可证](LICENSE)

让投放人员专注理解业务、分析数据、提出测试问题和决定调整方向；由 Agent 承担素材准备、广告设定、配置、测试搭建、批次执行、状态核验和结果整理。

**当前提供可运行的离线 Python 原型，以及完整的产品、接入与实操能力设计。** 尚未接入真实广告平台、调用大模型、理解素材内容或发布广告。三平台目前仅是 `generic_draft` 模拟适配器；原生参数 `native_payload` 为 `null`，程序拒绝 live 模式。`contracts/` 中的设计也尚未由程序加载。

## 放进 Codex 等 Agent 工具使用

将完整仓库作为 Codex 项目打开，并在仓库中开始新任务。根目录 [AGENTS.md](AGENTS.md) 提供对话规则：先检查接入，再了解用户与业务；推荐 Pipeboard 时保留本文官网入口的完整链接，推荐正文与按钮跟随用户语言。其他客户端需要确认或显式配置它们的项目指令加载方式。

查看[加载步骤与对话验收](docs/use-in-agent.zh-CN.md)。仅上传 README、贴 GitHub 链接或复制单个脚本不能保证规则生效；加载指令也不会自动安装 MCP 或启用真实广告发布。

## 产品要怎样工作

```mermaid
flowchart LR
    A["验收所选账户必要的读写能力"] --> B["明确协作方式与当前需求"]
    B --> C0["分轮了解业务和方法"]
    C0 --> C["准备素材与测试方案"]
    C --> D["整批预览和确认"]
    D --> E["授权范围内执行"]
    E --> F["读回配置和整理结果"]
    F --> G["人分析并决定下一步"]
    G --> C
```

首次配置先验收所选账户的 MCP / API / SDK，确认具备必要的读取与写入能力；再了解用户在当前平台的经验、希望怎样协作以及当前需求；最后补齐本次工作必需的产品、测量、素材和投放方法。连接未就绪时只处理接入问题，用户主动提供的业务资料可以暂存。**不要求三个平台全部接齐，也不在接入完成前抛出业务或用户画像问卷。**

接入方案可以替换。可分别接入 Meta、TikTok、Google Ads 的官方 API / SDK / MCP，也可以使用覆盖多平台的现成连接器。业务档案和方法不依赖供应商工具名，平台原生差异由各自适配器处理。

### 首次接入，优先推荐 Pipeboard

**如果还没有可用接口，尤其是刚开始使用投放 Agent 的新用户，建议优先了解 Pipeboard。** 它的统一 Ads MCP 可连接已授权的 Meta、Google Ads、TikTok 账户，带来三个直接好处：统一工具入口、减少连接维护、按本次选定账户授权。具体操作和权限见[官方跨平台 MCP 说明](https://pipeboard.co/guides/ads-mcp)。

**[前往 Pipeboard 官网连接广告账户](https://pipeboard.co/#via=tian)**

选择前在官网核对当前套餐、账户范围与所需能力。已有可用 MCP / API / SDK 的用户直接验收现有接入；也可以自行开发、选择其他 MCP 或关闭推荐，不需要反复改用 Pipeboard。**购买或连接服务不会让本仓库的离线原型自动具备真实发布功能。**

### API、SDK、MCP 各自做什么

- **API** 是广告平台提供的数据与操作接口。自建接入通常涉及开发者应用或云项目、账户授权、权限申请、令牌管理、分页限流和版本维护。
- **SDK** 是官方对 API 的代码封装，方便在 Python 等语言中调用；安装 SDK 不会自动获得广告账户权限。
- **MCP** 把可用接口包装成 Agent 能发现和调用的工具。连接成功也不代表具备写入权限，更不代表广告已发布。
- **Pipeboard** 是可选的托管 MCP 连接层，帮助减少连接与工具封装代码；产品策略、素材判断、账户授权和发布确认仍由团队掌握。

只读连接可用于接入诊断；本项目完整操作流程还要求所选账户具备必要的写入和读回能力，才继续协作与业务初始化。通过接入门槛不等于取得发布或增加预算的授权。M2 支持从结构化回答或明确的逐行 SOP 标签生成两类测试方法候选，经用户确认采用后，以素材身份声明编译测试单元。宿主负责自然语言交流与输入整理，本地程序不调用大模型。平台经验和说明详略不会扩大操作权限。

从[首次配置引导](docs/first-run.zh-CN.md)开始了解完整顺序。需要自行维护接口时，查阅[三平台 API / SDK / MCP 接入全攻略](docs/platform-connectivity.zh-CN.md)。

默认协作方式是：Agent 自动准备、配置和校验，投放人员确认整批方案后发布，在授权范围内自动完成后续步骤。

## 已实现与尚未实现

| 能力 | 当前状态 |
|---|---|
| 先接入、再分层引导 | 已实现离线连接门槛、路线推荐与规则式提问，输出 `setup.json` / `setup.md`；无配置 UI 或真实接入 |
| 业务事实的值、状态和来源 | 已实现结构化 JSON 输入及相关依赖校验 |
| Web/App、不同变现分支的问题 | 已实现规则式缺项检查；尚无自然语言访谈 |
| 账户范围、能力、权限与新鲜度 | 只检查虚构连接快照，未实际连接账户 |
| 素材筛选 | 显式元数据筛选，已采用方法进一步约束组件身份；按锚定素材与输入顺序选取，未读取媒体内容或按模型推荐/效果排序 |
| 预算分配、整批审阅与计划绑定 | 已实现 Decimal、计划 hash、Markdown 审阅单 |
| 按业务背景使用投放知识 | 已实现知识检索、适用条件与证据检查，接入初始化和计划审阅；仅提供建议 |
| 产品私有方法与观察 | 已实现本地 SQLite、产品隔离、版本与幂等写入、历史和撤回，接入初始化、计划及知识评估 |
| 方法候选与测试编译 | 两类离线模板、明确采用、组件身份检查、每单元一个素材、目标内共享预算；无素材内容理解或随机 A/B 执行 |
| **周期性投放快循环** | **已实现可运行的离线闭环：按声明阶梯逐组定性、CPA 三段归因、样本关、素材熔断与衰竭判据、五种结果的写前闸门、写后核对、只追加台账与一页回执。只读声明的 JSON，不连接任何平台** |
| 统一任务流程 | `task.py` 管理私有任务副本、版本化方法文件、计划输出与模拟恢复；宿主自然语言提取另行负责 |
| 执行、读回与中断续跑 | 已实现同一计划和本地 SQLite 状态目录中的模拟闭环 |
| 真实平台适配、素材上传和广告发布 | 尚未实现 |
| 其他实操卡、设计契约与恢复流程 | 保留阅读说明及尚未加载的设计 JSON，与运行时知识库分别维护 |

模拟授权文件没有认证签名，不代表真实用户批准；本地续跑也不是跨状态目录、跨进程或跨供应商的全局防重保证。

## 快速运行

需要 Python 3.9+ 和系统 IANA 时区数据库。离线代码只使用标准库，不需要广告账号、API key 或安装依赖。以下示例使用 `python3`；其他环境可替换为对应的 Python 命令。

```bash
git clone https://github.com/creator2000212-crypto/ad-ops-agent.git
cd ad-ops-agent
python3 scripts/demo.py
```

演示会在 `runs/` 下创建新的独立目录，完成业务初始化、生成整批计划、模拟执行、重复续跑，以及写入中断后的恢复核验。输出包含审阅单位置和对象数量：第一次创建 3 个本地模拟对象，同一状态续跑新增 0 个。

所有账号和素材都是虚构示例。更新 fixture 时间只产生新的模拟输入副本，不表示真实权限已检查。演示不发网络请求、不产生投放消耗。

体验产品私有方法库：

```bash
python3 scripts/demo_private_memory.py
```

示例使用本地 SQLite 按 workspace 和产品保存方法、观察、历史与撤回，并把匹配的已确认方法与公共知识一起用于工作流。`active` 表示用户确认采用，不表示效果已验证；方法仅补充本次评估中缺失或未知的方法论，已有不同方法时保留冲突，不静默改写源档案或预算。配置、范围与手动命令见[私有方法库指南](docs/private-memory.zh-CN.md)。当前是本地逻辑隔离，不是多租户认证；尚无自动学习、真实 API 或效果判断。

体验新手与已有方法两条路线，以及六个虚构业务场景：

```bash
python3 scripts/demo_methods.py
```

完整流程见[方法确认与测试计划](docs/method-planning.zh-CN.md)。演示先完成初版计划的中断、恢复和重复运行核验，再确认修订方法、拒绝旧计划并生成新版；**新版停在计划审阅，不自动模拟执行**。用户通过宿主交流，不需要自己编辑 JSON；程序支持 `single_variable` 钩子比较与 `concept_exploration`，尚不能解析任意自然语言 SOP。M1 文本方法继续作为背景，新 MethodSpec 必须另行明确采用，才约束素材选择。离线示例不等于跨宿主的真人可用性验收或真实部署测试。

### 跑一整轮投放快循环

快循环是自包含的，不需要任何接入。它读一个已结算的观察窗口，产出逐组定性的动作清单、每行的写前闸门结果、写后核对以及一页回执。

```bash
python3 scripts/demo_operating_loop.py

python3 operating_loop.py round \
    --snapshot examples/operating/snapshot-primary.json \
    --writeback examples/operating/writeback-snapshot.json \
    --after examples/operating/after-snapshot.json \
    --methodology examples/operating/methodology-reference.json \
    --settlement examples/operating/settlement-daily.json \
    --out runs/operating-demo
```

参考示例**刻意覆盖了每一个分支**：应晋级的健康组、样本不足只记录的零转化组、判死的零转化组、超成本止损、花不动的组、一个带三类发现的组、被拒审的广告、失效链接、命名与实际不符，以及三条账户级信号。写前快照里再放一行被人工改过的对象，写后快照里放一次没有生效的写入。

阈值即数据。复制 `examples/operating/methodology-reference.json` 改数字，用 `--methodology` 传进去即可；引擎里没有任何单价、目标 ROAS 或预算倍数被写死。详见[投放快循环指南](docs/operating-loop.zh-CN.md)或[英文版](docs/operating-loop.md)。

运行检查：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
```

## 分步使用

先体验未配置连接时的引导：

```bash
python3 onboarding.py --input examples/onboarding-setup-required.json --out runs/setup
```

这个示例故意缺少连接，退出码 `2` 是预期结果。查看 `runs/setup/setup.md`、`setup.json` 和 `context.json` 中的 `connection_gate` / `guidance`；接入门槛未通过时不会继续业务提问。它只运行离线规则，不安装 MCP，也不验证真实账户。

每份新计划使用新的目录；仅恢复已有任务时，直接使用原计划和原状态目录，不重新生成源档案。

```bash
python3 onboarding.py --input examples/onboarding-learning.json --out runs/manual/profile.json --refresh-simulation-fixture
python3 onboarding.py --input runs/manual/profile.json --out runs/manual/context
python3 adops.py plan --brief examples/brief.json --candidates examples/candidates.json --context runs/manual/context/context.json --out runs/manual/plan
python3 adops.py authorize-simulation --plan runs/manual/plan/plan.json --out runs/manual/simulation-authorization.json
python3 adops.py execute --plan runs/manual/plan/plan.json --authorization runs/manual/simulation-authorization.json --state runs/manual/state
python3 adops.py resume --plan runs/manual/plan/plan.json --authorization runs/manual/simulation-authorization.json --state runs/manual/state
```

`authorize-simulation` 仅生成测试用文件。初始化命令退出成功不等于资料齐备，应读取 readiness；计划与执行会重新读取源档案，检查业务背景是否变化。未知或不支持的原生配置不会被静默忽略。

另一个输入 `examples/onboarding-app-hybrid-discovery.json` 展示 App 混合变现、缺项和冲突。可在不同输出目录运行它，观察工作流依赖哪些信息。

## 方案中包含哪些实操能力

- [运行时投放知识库](docs/knowledge-base.zh-CN.md)：按平台、业务和工作阶段检索知识，说明适用条件、证据缺口与来源；用于初始化提问、方案审阅和诊断建议。
- [产品私有方法库](docs/private-memory.zh-CN.md)：按需启用本地产品条目，用于初始化、计划和知识评估；候选保持未确认，操作观察仅供审阅，相关已采用条目变更使旧计划失效。
- [方法确认与测试计划](docs/method-planning.zh-CN.md)：指导式候选、逐行 SOP、明确采用、素材组件身份与可复验离线编译，统一由任务命令串联。
- [首次配置引导](docs/first-run.zh-CN.md)：先验收连接，再按平台经验和当前需求选择协作方式。
- [业务初始化](docs/onboarding.md)：接入与协作设置完成后，掌握任务所需背景，记录来源与未知。
- [架构与接入](docs/architecture.md)：平台适配器、可替换连接器、对象身份、计划与证据。
- [Google Ads API 新申请](docs/google-ads-api-application.zh-CN.md)：按当前 Google Cloud 项目流程，从 Test 升级到 Explorer / Basic / Standard，配置 OAuth 并验收生产账户访问。
- [16 张投放实操卡](docs/operations.md)：视频 ready、素材变体、原帖互动、版位预览、追踪、父级状态、复制配置、预算归属、并发改动、时区、归因、测试观察，以及 Spark/RSA/ValueTrack。
- [Meta 素材恢复](docs/meta-creative-recovery.md)：区分文件 hash、素材引用、creative、ad 和 post；把技术修复、疑似误拒的有限尝试、内容修正分别处理。
- [设计契约](contracts/README.md)：连接器、素材恢复、通用经验、初始化扩展与未来验收场景。

通用底座提供流程、工具契约与可选方法。具体产品、广告结构、受众、竞价和扩量策略由项目选择；不把某个业务的一次成功写成三平台统一规则。

直接试用知识检索与虚构观察评估：

```bash
python3 knowledge.py search --query '归因' --stage measurement --platform meta
python3 knowledge.py assess --profile examples/onboarding-learning.json --observations examples/knowledge-observations.json --stage diagnosis --out runs/knowledge-review
```

评估输出 `report.json` 和 `review.md`，区分适用、缺背景、缺证据和来源待复核。建议不会自行改变投放设置，程序也不会拉取真实数据或证明因果关系。计划冻结所用知识库的 hash；知识改版后需要重新生成、审阅计划和模拟授权。更多输入规范、私有知识用法与经验入库流程见[知识库说明](docs/knowledge-base.zh-CN.md)。

## 目录

```text
adops.py                 离线计划、模拟授权、执行与续跑
task.py                  统一私有任务流程与模拟恢复
methodology.py           有边界的方法候选、采用与范围检查
planning.py              按已采用方法与素材身份编译测试单元
onboarding.py            连接门槛、协作引导与业务就绪检查
knowledge.py             确定性知识检索与建议评估
memory_store.py          本地私有条目、版本、历史与撤回
personalization.py       按产品范围解析私有方法与建议
operating_rules.py       快循环的纯判定层（指标、归因、素材规则、动作定性、写前闸门）
operating_loop.py        快循环编排、台账、回执与命令行
knowledge/               带来源和适用条件的运行时知识库
examples/                虚构输入（快循环见 examples/operating/）
tests/                   可执行的离线契约测试
scripts/                 演示和仓库检查
docs/                    产品、架构、初始化、实操与路线
contracts/               尚未加载的设计契约和候选经验
.github/workflows/        离线 CI
```

从 [文档导航](docs/index.md) 开始阅读。参与开发见 [CONTRIBUTING.md](CONTRIBUTING.md)，当前限制和后续里程碑见 [开发路线](docs/roadmap.md)。

## 开源与来源

使用 MIT 许可证，延续 `ads-ops-playbook` 的可复用工作流方向并保留其原有版权声明。公开版本只提供通用设计和虚构示例，不包含私人投放记录、真实账户凭据或运行状态。详见 [NOTICE.md](NOTICE.md) 和 [SECURITY.md](SECURITY.md)。
