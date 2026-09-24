# 文档阅读路线

Ad Ops Agent 把投放人员已确认的方向变成可靠的准备、配置、批次操作和结果整理。当前仓库是**可运行的离线契约原型，加上真实平台接入的设计文档**；尚不是能直接登录三个广告平台并发布的成品 Agent。

想直接运行示例或测试，先看 [根 README](../README.md)。下面按问题选择文档，无需从头阅读全部内容。

| 你想了解什么 | 阅读 |
|---|---|
| 把项目放进 Codex 等工具后，对话规则和 Pipeboard 链接怎样生效？ | [宿主加载与对话验收](use-in-agent.zh-CN.md) |
| 首次使用先接什么，何时了解用户需求，新手怎样选择接入？ | [首次配置引导](first-run.zh-CN.md) |
| 产品替投放人员节省哪些劳动，人与 Agent 如何分工？ | [产品与流程](product.md) |
| 哪些已实现，怎样增加或替换 API/MCP 连接器？ | [架构与实现边界](architecture.md) |
| Meta、TikTok、Google Ads 的 API / SDK / MCP 怎样申请和接入？现成连接器怎样选？ | [三平台接入全攻略](platform-connectivity.zh-CN.md) |
| Google Ads API 新申请如何从 Cloud 项目升级到生产访问？ | [Google Ads API 详细申请流程](google-ads-api-application.zh-CN.md) |
| 接入与协作方式确定后，如何逐步理解业务，避免一次大问卷和重复提问？ | [业务初始化](onboarding.md) |
| Agent 如何检索投放知识、判断适用条件并利用经验辅助提问、审阅和诊断？ | [运行时投放知识库](knowledge-base.zh-CN.md) |
| 如何保存产品方法与团队观察，让后续任务复用，并保留冲突、版本和撤回？ | [产品私有方法库](private-memory.zh-CN.md) |
| 新手或资深投手的方法怎样变成候选、确认和真正影响素材选择的测试计划？ | [方法确认与测试计划](method-planning.zh-CN.md) · [English guide](method-planning.md) |
| 素材、帖子、链接、预算、状态和数据现场问题怎样处理？ | [16 张实操卡](operations.md) |
| 优质素材遇到上传故障或疑似误拒，怎样有条件恢复？ | [Meta 素材恢复](meta-creative-recovery.md) |
| 下一步先实现什么，贡献如何验收？ | [路线图](roadmap.md) |

## 建议阅读顺序

- **首次使用者：**首次配置引导 → 所选账户的接入路线 → 接入验收 → 协作方式与当前需求 → 业务初始化。没有可用连接时可优先了解 Pipeboard；已有接口直接验收，也可选择其他路线。
- **投放人员与产品协作者：**产品 → 首次配置引导 → 业务初始化 → 方法确认与测试计划 → 知识库/私有方法库 → 按当前问题查实操卡。重点确认理解、方法复用、批次预览和结果交接能否减少人工工作。
- **接入开发者：**首次配置引导 → 三平台接入全攻略 → 架构 → 知识库 → 连接器契约 → 实操卡 → 路线图。先验收本次所选账户的必要读写能力，不要求三个平台同时接入。
- **素材恢复或审核排障开发者：**Meta 素材恢复 → 恢复契约 → 相应实操卡。区分媒体、创意、广告、帖子与学习，不使用一个模糊的“刷新素材”动作。

## 结构化设计契约

| 文件 | 定位 |
|---|---|
| [connector-contract.json](../contracts/connector-contract.json) | 供应商中立的连接器与能力映射 |
| [creative-recovery.json](../contracts/creative-recovery.json) | 条件化素材恢复动作、记录与验收 |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | 未来实现的验收场景，不是已执行测试报告 |
| [experience-catalog.json](../contracts/experience-catalog.json) | 有适用范围与处置方式的经验候选，不是自动优化规则 |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | 业务初始化的扩展建议，不代表 CLI 已接受全部字段 |

这些 `contracts/` 文件是实现参考，当前离线运行时不会自动加载、启用或执行其中的候选能力。公共知识库位于 [`knowledge/catalog.json`](../knowledge/catalog.json)，由 `knowledge.py` 加载；按需启用的私有条目由 `memory_store.py` 保存并由 `personalization.py` 按产品范围使用，二者均与设计契约分开。官方来源支持限定范围的事实；工程步骤仍需在所选平台、账户、广告产品和版本下验证。运行时实现在架构和知识库文档中单独列出，避免把设计完成当成功能上线。

返回 [项目首页](../README.md)。
