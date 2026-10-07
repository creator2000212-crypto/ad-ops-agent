# 文档导航

[中文首页](../README.zh-CN.md) · [English overview](../README.md) · [实盘与演示对照](capability-status.zh-CN.md)

**先选你要做的事，不必从第一篇技术文档开始读。**

## 看作品 / 了解项目

从[实际是怎么跑的](how-it-ran.zh-CN.md)开始：2026 年 9 月在 WorkBuddy 中对 Meta 与 TikTok 实盘账户跑了什么、定时任务的运行记录，以及每一部分在仓库里对应什么。接着看[十个案例](case-studies.zh-CN.md)、[方法演变](methodology-history.zh-CN.md)和[实盘与演示对照](capability-status.zh-CN.md)。想看检查实际运行，试试[离线示例](../demo/README.zh-CN.md)、[建单质检](build-qa.zh-CN.md)和[决策矩阵](decision-matrix.md)（英文）。原始私有资料不公开。

## 开始用 / 完成一项任务

**第一次统一从[拿到第一份结果](first-check.zh-CN.md)开始。** 这是首次使用主路径：打开项目 → 核对连接与账户 → 说明需求 → 选择投放准备、账户检查或 SOP 核对 → 检查交付。已经完成且仍适用的步骤可跳过，不要求先读其他页面。

只在对应问题出现时查阅：

- 读不到文件或项目规则：[打开项目与加载排查](use-in-agent.zh-CN.md)，解决后返回教程原步骤。
- 不知道该提供哪些业务信息：[业务与合作方式](first-run.zh-CN.md)。
- 需要其他连接或平台：[接入参考](platform-connectivity.zh-CN.md)。
- 已拿到第一份结果，准备处理日常工作：[日常工作流](workflow.zh-CN.md)；Agent 可按实际证据整理[任务记录](../templates/task-record.zh-CN.md)，保存在你授权的私有位置。

## 看实现 / 运行公开代码

[离线示例](../demo/README.zh-CN.md) → [建单质检](build-qa.zh-CN.md) → [实盘与演示对照](capability-status.zh-CN.md) → [实现架构](architecture.md) → [开发路线](roadmap.md)。公开 Python 使用虚构输入，不代表真实平台执行。

## 按问题查找

### 业务与投放方法

| 你要解决的问题 | 文档 |
| --- | --- |
| 从具体业务与素材搭建一轮工作流程 | [搭建例子](build-from-zero.zh-CN.md) · [English](build-from-zero.md) |
| 告诉 Agent 业务背景、目标与合作方式 | [业务与合作方式](first-run.zh-CN.md) |
| 带入 SOP，或理解不同测试方法 | [日常工作流](workflow.zh-CN.md) · [两种方法对照](method-comparison.zh-CN.md) |
| 检索知识、判断适用条件与证据缺口 | [知识库](knowledge-base.zh-CN.md) |
| 保存、修订、撤回产品范围内的私有方法 | [私有方法库](private-memory.zh-CN.md) |

### 连接与首次使用

| 你要解决的问题 | 文档 |
| --- | --- |
| 跟着一条路线拿到第一份结果 | [首次使用](first-check.zh-CN.md) · [English](first-check.md) |
| 连接后，补齐本次业务信息 | [业务与合作方式](first-run.zh-CN.md) · [English](first-run.md) |
| 确认宿主加载了项目指令 | [打开项目与加载排查](use-in-agent.zh-CN.md) · [English](use-in-agent.md) |
| 了解 Meta、TikTok、Google 连接路线 | [平台接入](platform-connectivity.zh-CN.md) · [English](platform-connectivity.md) |
| 申请 Google Ads API | [申请指南](google-ads-api-application.zh-CN.md) |

### 执行、检查与复盘

| 你要解决的问题 | 文档 |
| --- | --- |
| 准备、确认、执行、读回和交接 | [宿主工作流](workflow.zh-CN.md) · [English](workflow.md) |
| 在私有目录记录方案、确认与下轮待办 | [任务模板](../templates/task-record.zh-CN.md) · [English](../templates/task-record.md) |
| 检查素材、帖子、链接、预算及状态 | [16 张实操卡](operations.md) |
| 处理拒审或素材上传失败 | [拒审分诊：修正或申诉](disapproval-triage.zh-CN.md) · [English](disapproval-triage.md) |
| 建单前预检；激活前核对读回 | [建单质检](build-qa.zh-CN.md) · [English](build-qa.md) |
| 查看每个动作的响应窗口、验收标准与停止条件 | [决策矩阵（英文）](decision-matrix.md) |
| 查看离线巡检的字段、公式和命令 | [技术参考](operating-loop.zh-CN.md) · [English](operating-loop.md) |

### 证据、实现与贡献

| 你要了解的问题 | 文档 |
| --- | --- |
| 实盘跑了什么、运行记录与不足 | [实际是怎么跑的](how-it-ran.zh-CN.md) · [English](how-it-ran.md) |
| 每个案例及其带来的护栏 | [案例](case-studies.zh-CN.md) · [English](case-studies.md) |
| 方法怎样变化、为什么变化 | [方法演变](methodology-history.zh-CN.md) · [English](methodology-history.md) |
| 区分实盘运行过的与这里能运行的 | [实盘与演示对照](capability-status.zh-CN.md) · [English](capability-status.md) |
| 模块分工与后续开发方向 | [架构](architecture.md) · [开发路线](roadmap.md) |
| 贡献可复用流程或原生适配器 | [贡献说明](../CONTRIBUTING.md) |

开发参考：[Python 方法编排](method-planning.zh-CN.md) · [业务初始化状态设计](onboarding.md)。这些文档不是使用宿主工作流的前置课程。

<details>
<summary><strong>结构化设计契约</strong></summary>

| 文件 | 定位 |
| --- | --- |
| [connector-contract.json](../contracts/connector-contract.json) | 供应商中立的连接器与能力映射 |
| [creative-recovery.json](../contracts/creative-recovery.json) | 拒审分诊路线、禁止动作、记录与停止条件 |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | 集成验收场景，不是已执行测试报告 |
| [experience-catalog.json](../contracts/experience-catalog.json) | 有适用范围的经验候选，不是自动优化规则 |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | 字段扩展建议，不代表 CLI 接受全部字段 |

`contracts/` 是实现参考，离线程序不会因文件存在而自动加载其中的设计。公共知识数据位于 [knowledge/catalog.json](../knowledge/catalog.json)；私有方法由显式启用的本地存储按产品范围使用。
</details>

### 使用原则

只读任务只检查所需读取能力；新建、调整或重组结构需要具体方案、操作范围与用户确认。相关上一轮待办先回验，未执行不能写成效果无效。首次接入可参考托管或自建路线；已有接口直接核验。实际能力以当前宿主、工具、账户和广告产品的验收为准。
