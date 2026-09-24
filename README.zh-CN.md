# Ad Ops Agent · 三平台投放 Agent

**面向 Meta（FB）、TikTok（TK）、Google Ads（GG）的通用投放 Agent 底座。**

[English](README.md) · [文档导航](docs/index.md) · [开发路线](docs/roadmap.md) · [MIT 许可证](LICENSE)

让投放人员专注理解业务、分析数据、提出测试问题和决定调整方向；由 Agent 承担素材准备、广告设定、配置、测试搭建、批次执行、状态核验和结果整理。

**当前提供可运行的离线 Python 原型，以及完整的产品、接入与实操能力设计。** 尚未接入真实广告平台、调用大模型、理解素材内容或发布广告。三平台目前仅是 `generic_draft` 模拟适配器；原生参数 `native_payload` 为 `null`，程序拒绝 live 模式。`contracts/` 中的设计也尚未由程序加载。

## 产品要怎样工作

```mermaid
flowchart LR
    A["连接已授权 API / MCP"] --> B["分轮了解业务"]
    B --> C["准备素材与测试方案"]
    C --> D["整批预览和确认"]
    D --> E["授权范围内执行"]
    E --> F["读回配置和整理结果"]
    F --> G["人分析并决定下一步"]
    G --> C
```

工作流开始前，先了解产品、国家与语言、人群、目标平台、Web/App、IAA/IAP/混合变现、转化路径、测量口径、素材方向和投放方法。能从已授权接口读取的事实先读取，需要人判断的事项再提问；未知值保留未知，后续任务继承已确认的背景。

接入方案可以替换。Pipeboard 是一种可选连接器，也可以使用其他 MCP 或官方 API；业务档案和方法不依赖供应商工具名，FB/TK/GG 的原生差异由各自平台适配器处理。

如需使用 Pipeboard，可前往[Pipeboard 官网](https://pipeboard.co/#via=tian)查看方案并选择合适的套餐。

默认协作方式是：Agent 自动准备、配置和校验，投放人员确认整批方案后发布，在授权范围内自动完成后续步骤。

## 已实现与尚未实现

| 能力 | 当前状态 |
|---|---|
| 业务事实的值、状态和来源 | 已实现结构化 JSON 输入及相关依赖校验 |
| Web/App、不同变现分支的问题 | 已实现规则式缺项检查；尚无自然语言访谈 |
| 账户范围、能力、权限与新鲜度 | 只检查虚构连接快照，未实际连接账户 |
| 素材筛选 | 只按显式元数据筛选并按输入顺序选取，未读取图片视频 |
| 预算分配、整批审阅与计划绑定 | 已实现 Decimal、计划 hash、Markdown 审阅单 |
| 执行、读回与中断续跑 | 已实现同一计划和本地 SQLite 状态目录中的模拟闭环 |
| 真实平台适配、素材上传和广告发布 | 尚未实现 |
| 16 张实操卡、经验库与恢复流程 | 已整理设计；尚未接入运行时 |

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

运行检查：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
```

## 分步使用

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

- [业务初始化](docs/onboarding.md)：先掌握背景、记录来源与未知，再开展相关工作。
- [架构与接入](docs/architecture.md)：平台适配器、可替换连接器、对象身份、计划与证据。
- [16 张投放实操卡](docs/operations.md)：视频 ready、素材变体、原帖互动、版位预览、追踪、父级状态、复制配置、预算归属、并发改动、时区、归因、测试观察，以及 Spark/RSA/ValueTrack。
- [Meta 素材恢复](docs/meta-creative-recovery.md)：区分文件 hash、素材引用、creative、ad 和 post；把技术修复、疑似误拒的有限尝试、内容修正分别处理。
- [设计契约](contracts/README.md)：连接器、素材恢复、通用经验、初始化扩展与未来验收场景。

通用底座提供流程、工具契约与可选方法。具体产品、广告结构、受众、竞价和扩量策略由项目选择；不把某个业务的一次成功写成三平台统一规则。

## 目录

```text
adops.py                 离线计划、模拟授权、执行与续跑
onboarding.py            业务资料与就绪检查
examples/                虚构输入
tests/                   可执行的离线契约测试
scripts/                 演示和仓库检查
docs/                    产品、架构、初始化、实操与路线
contracts/               尚未加载的设计契约和候选经验
.github/workflows/        离线 CI
```

从 [文档导航](docs/index.md) 开始阅读。参与开发见 [CONTRIBUTING.md](CONTRIBUTING.md)，当前限制和后续里程碑见 [开发路线](docs/roadmap.md)。

## 开源与来源

使用 MIT 许可证，延续 `ads-ops-playbook` 的可复用工作流方向并保留其原有版权声明。公开版本只提供通用设计和虚构示例，不包含私人投放记录、真实账户凭据或运行状态。详见 [NOTICE.md](NOTICE.md) 和 [SECURITY.md](SECURITY.md)。
