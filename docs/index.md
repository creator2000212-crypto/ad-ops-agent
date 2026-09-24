# 文档阅读路线

Ad Ops Agent 从 WorkBuddy 实际投放工作中提炼可复用的任务流程。**真实使用案例、宿主工具工作流、公开 Python 离线验证**分别展示；先选择你要了解或开展的工作，不必从技术文档第一篇开始读。

[中文首页](../README.zh-CN.md) · [English overview](../README.md)

## 三个起点

- **想看这个项目解决过什么问题：**[六个真实工作案例](case-studies.zh-CN.md) → [产品设计](product.md)。案例经过脱敏，保留未完成和证据冲突；不公开私有原始资料。
- **想在自己的 Agent 环境使用：**[首次配置](first-run.zh-CN.md) → [宿主工作流](workflow.zh-CN.md) → [任务记录模板](../templates/task-record.zh-CN.md)。先核验本任务连接，再理解业务、准备方案和核对结果。
- **想先运行可检查的代码：**[离线示例](../demo/README.zh-CN.md) → [能力范围与命令](capability-status.zh-CN.md) → [实现架构](architecture.md)。模拟结果不代表真实平台状态。

## 按问题找文档

| 你想了解什么 | 阅读 |
|---|---|
| 哪些来自真实工作，历史记录证明到哪？ | [脱敏案例](case-studies.zh-CN.md) · [English](case-studies.md) |
| 一项真实任务怎样准备、确认、执行、读回和交接？ | [宿主工作流](workflow.zh-CN.md) · [English](workflow.md) |
| 怎样在私有目录记录方案、批准、回执和下轮待办？ | [任务模板](../templates/task-record.zh-CN.md) · [English](../templates/task-record.md) |
| WorkBuddy 实践、宿主工具和 Python 分别能做什么？ | [能力矩阵](capability-status.zh-CN.md) · [English](capability-status.md) |
| 怎样从一个具体业务搭建工作流，新人和熟手如何选择方法？ | [搭建例子](build-from-zero.zh-CN.md) · [English](build-from-zero.md) |
| 导入项目后，怎样确认宿主加载了指令？ | [加载与对话验收](use-in-agent.zh-CN.md) · [English](use-in-agent.md) |
| 接口未配好时从哪里开始？ | [首次配置](first-run.zh-CN.md) · [English](first-run.md) |
| Meta、TikTok、Google 如何接入，现成连接器怎样选？ | [三平台接入](platform-connectivity.zh-CN.md) · [English](platform-connectivity.md) |
| Google Ads API 新申请流程在哪里？ | [详细申请指南](google-ads-api-application.zh-CN.md) |
| 如何理解业务，避免重复访谈？ | [业务初始化](onboarding.md) |
| 如何组织用户方法，公开代码能编排哪些测试？ | [方法与测试计划](method-planning.zh-CN.md) · [English](method-planning.md) |
| 如何检索知识、判断条件和保留证据缺口？ | [知识库](knowledge-base.zh-CN.md) |
| 私有方法与观察怎样保存、修订和撤回？ | [产品私有方法库](private-memory.zh-CN.md) |
| 素材、帖子、链接、预算、状态等操作细节怎样检查？ | [16 张实操卡](operations.md) · [Meta 素材恢复](meta-creative-recovery.md) |
| 怎样查看离线巡检的字段、公式和命令？ | [技术参考](operating-loop.zh-CN.md) · [English](operating-loop.md) |
| 怎样贡献可复用流程或原生适配器？ | [架构](architecture.md) · [双线开发路线](roadmap.md) · [贡献说明](../CONTRIBUTING.md) |

## 按任务使用

日报和分析只需本任务足够的读取能力；不要先要求发布权限。新建、调整或迁移需要操作范围、具体整批方案和用户确认。已有资料和方法可以复用；只补影响当前任务的缺项。相关上一轮待办先回验，未执行不能写成效果无效。

首次完整配置时，没有可用连接可以了解 Pipeboard 等方案；已有接口直接核验，选择其他路线后不重复推荐。接入不等于授权，示例文件也不能代替实际工具证据。

## 结构化设计契约

| 文件 | 定位 |
|---|---|
| [connector-contract.json](../contracts/connector-contract.json) | 供应商中立的连接器与能力映射 |
| [creative-recovery.json](../contracts/creative-recovery.json) | 条件化恢复动作、记录与验收 |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | 集成验收场景，不是已执行测试报告 |
| [experience-catalog.json](../contracts/experience-catalog.json) | 有适用范围的经验候选，不是自动优化规则 |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | 字段扩展建议，不代表 CLI 接受全部字段 |

`contracts/` 是实现参考，离线程序不会自动加载或执行其中的设计。公共知识数据在 [knowledge/catalog.json](../knowledge/catalog.json)，私有方法由显式启用的本地存储按产品范围使用。历史案例说明需求从哪里来；当前环境的操作能力仍以工具、账户、广告产品和实际验收为准。
