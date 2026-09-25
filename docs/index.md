# 文档导航

[中文首页](../README.zh-CN.md) · [English overview](../README.md) · [能力范围](capability-status.zh-CN.md)

**先选你要做的事，不必从第一篇技术文档开始读。**

## 看作品 / 了解项目

从 [Meta 素材与方案准备](case-studies.zh-CN.md#meta-task) 和 [TikTok 建单与状态交接](case-studies.zh-CN.md#tiktok-task) 开始，再看 [六个工作案例](case-studies.zh-CN.md) 与 [产品设计](product.md)。案例是历史记录的脱敏整理，原始私有资料不公开。

## 开始用 / 完成一项任务

第一次可从[Agent 工具 + Pipeboard 的 Meta 只读检查教程](first-check.zh-CN.md)开始：打开项目、核对连接、选择一个账户，再交付并核对第一份报告。页面分别记录官方资料核对与尚待完成的实测范围。

[首次配置](first-run.zh-CN.md) → [加载与验收](use-in-agent.zh-CN.md) → [宿主工作流](workflow.zh-CN.md) → [任务记录模板](../templates/task-record.zh-CN.md)。先核对本次任务的账户、工具及授权，沿用已知业务资料和方法，再补缺项。

## 看实现 / 运行公开代码

[离线示例](../demo/README.zh-CN.md) → [命令与能力范围](capability-status.zh-CN.md) → [实现架构](architecture.md) → [开发路线](roadmap.md)。公开 Python 使用虚构输入，不代表真实平台执行。

## 按问题查找

### 业务与投放方法

| 你要解决的问题 | 文档 |
| --- | --- |
| 从具体业务与素材搭建一轮工作流程 | [搭建例子](build-from-zero.zh-CN.md) · [English](build-from-zero.md) |
| 理解业务、保留来源，避免重复访谈 | [业务初始化](onboarding.md) |
| 组织用户 SOP、确认方法并生成测试计划 | [方法与测试](method-planning.zh-CN.md) · [两种方法对照](method-comparison.zh-CN.md) · [English](method-planning.md) |
| 检索知识、判断适用条件与证据缺口 | [知识库](knowledge-base.zh-CN.md) |
| 保存、修订、撤回产品范围内的私有方法 | [私有方法库](private-memory.zh-CN.md) |

### 连接与首次使用

| 你要解决的问题 | 文档 |
| --- | --- |
| 跟着一条路线拿到第一份只读结果 | [首次只读检查](first-check.zh-CN.md) · [English](first-check.md) |
| 尚未接入，或第一次配置 | [首次配置](first-run.zh-CN.md) · [English](first-run.md) |
| 确认宿主加载了项目指令 | [加载与对话验收](use-in-agent.zh-CN.md) · [English](use-in-agent.md) |
| 了解 Meta、TikTok、Google 连接路线 | [平台接入](platform-connectivity.zh-CN.md) · [English](platform-connectivity.md) |
| 申请 Google Ads API | [申请指南](google-ads-api-application.zh-CN.md) |

### 执行、检查与复盘

| 你要解决的问题 | 文档 |
| --- | --- |
| 准备、确认、执行、读回和交接 | [宿主工作流](workflow.zh-CN.md) · [English](workflow.md) |
| 在私有目录记录方案、确认与下轮待办 | [任务模板](../templates/task-record.zh-CN.md) · [English](../templates/task-record.md) |
| 检查素材、帖子、链接、预算及状态 | [16 张实操卡](operations.md) · [Meta 素材恢复](meta-creative-recovery.md) |
| 查看离线巡检的字段、公式和命令 | [技术参考](operating-loop.zh-CN.md) · [English](operating-loop.md) |

### 证据、实现与贡献

| 你要了解的问题 | 文档 |
| --- | --- |
| 真实工作中的过程及证据范围 | [脱敏案例](case-studies.zh-CN.md) · [English](case-studies.md) |
| 实际业务、宿主工具、公开 Python 的区别 | [能力矩阵](capability-status.zh-CN.md) · [English](capability-status.md) |
| 模块分工与后续开发方向 | [架构](architecture.md) · [开发路线](roadmap.md) |
| 贡献可复用流程或原生适配器 | [贡献说明](../CONTRIBUTING.md) |

<details>
<summary><strong>结构化设计契约</strong></summary>

| 文件 | 定位 |
| --- | --- |
| [connector-contract.json](../contracts/connector-contract.json) | 供应商中立的连接器与能力映射 |
| [creative-recovery.json](../contracts/creative-recovery.json) | 条件化恢复动作、记录与验收 |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | 集成验收场景，不是已执行测试报告 |
| [experience-catalog.json](../contracts/experience-catalog.json) | 有适用范围的经验候选，不是自动优化规则 |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | 字段扩展建议，不代表 CLI 接受全部字段 |

`contracts/` 是实现参考，离线程序不会因文件存在而自动加载其中的设计。公共知识数据位于 [knowledge/catalog.json](../knowledge/catalog.json)；私有方法由显式启用的本地存储按产品范围使用。
</details>

### 使用原则

只读任务只检查所需读取能力；新建、调整或迁移需要具体方案、操作范围与用户确认。相关上一轮待办先回验，未执行不能写成效果无效。首次接入可参考托管或自建路线；已有接口直接核验。实际能力以当前宿主、工具、账户和广告产品的验收为准。
