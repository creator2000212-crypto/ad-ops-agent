# Meta、TikTok、Google Ads API / SDK / MCP 接入全攻略

[English](platform-connectivity.md) · [宿主工作流](workflow.zh-CN.md)

> 平台资料核对日期：2026-09-24。入口、审核规则、套餐与工具能力会变；操作前以当前官方页面和账户可见权限为准。本次文档重组未重新验证供应商能力。本文区分**宿主使用现成工具**与**开发独立 Python 接入**；公开 Python 仍只运行离线模拟。

这份指南面向两种团队：愿意申请平台接口并维护代码的开发者；希望先把账户接给 AI 助手、验证工作流价值的投放团队。两条路线最终都要回答同一组问题：能访问哪个原生广告账户，能读什么、能写什么，操作作用于哪个广告产品，实际写入后怎样读回和核对。

**首次使用先看[首次配置引导](first-run.zh-CN.md)。** 完整配置/发布流程先验收必要读取、写入和读回能力，再了解协作方式与业务；只读分析按所需读取能力开展，不要求发布权限。无需同时接齐三个平台。宿主已有工具通过验证且操作获准后，可按[宿主工作流](workflow.zh-CN.md)执行，不必先写 Python 适配器。离线快照检查不能证明真实连接已完成。

没有可用接口时，尤其是第一次配置投放 Agent 的用户，**建议优先了解 Pipeboard**：统一 MCP 入口、减少连接维护、按所选账户授权。已有可用接口可以直接验收，或继续使用其他 MCP / 自建方案。

**[前往 Pipeboard 官网连接广告账户](https://pipeboard.co/#via=tian)**

## 先选接入层，再选工具

| 方式 | 你需要准备 | 适合的第一步 | 不能替代的事情 |
|---|---|---|---|
| 官方 API | 平台/云开发者身份、广告账户授权、相应权限、自己维护认证与调用 | 做专有流程、深度控制数据和对象 | 业务理解、字段校验、审核、发布确认 |
| 官方 SDK | 上述 API 权限，外加开发环境 | 少写请求、分页和模型封装 | SDK 不替你申请权限，也不保证账户支持每个字段 |
| 平台官方 MCP | 支持 MCP 的助手、对应账户授权；各平台前置条件不同 | 先验证工具、做分析或支持范围内的操作 | 平台对象/指标差异、批次审阅、执行授权与结果验收 |
| 托管跨平台 MCP（如 Pipeboard） | 服务账户、所选广告账户授权、MCP 客户端、合适的套餐/权限 | 接通支持的平台工具，减少连接维护 | 广告平台账户资格、未开放的功能、业务决策与结果验收 |

**API 是源接口，SDK 是调用 API 的代码库，MCP 是把工具暴露给 Agent 的协议。** MCP 可能由平台自己运营，也可能由第三方将官方 API 封装。三者不是相互排斥的“申请项”；先决定要直连还是使用现成 MCP，再检查其能力、账户范围和授权方式。用户明确确认的投放方案才进入发布流程，详见[架构与实现边界](architecture.md)。

无论走哪条路线，接入阶段先确定：广告账户 ID、关联的 Business/经理账户，以及必要的读写范围。选定范围的连接验收通过后，再按任务补齐市场、转化来源、素材使用权与广告产品等业务信息。用户已提供的资料可以暂存，不需要为进入接入步骤先填写完整业务问卷。**平台 API 权限与素材/转化配置是不同事项**；能查广告不等于能上传视频、创建广告或读取归因结果。

## 路线 A：自行申请三平台接口

### Meta（Facebook / Instagram）：Marketing API 与 Business SDK

**官方入口：**[Meta 开发者平台](https://developers.facebook.com/) · [Meta 官方 Marketing API Postman 文档](https://www.postman.com/meta/facebook-marketing-api/documentation/0zr4mes/facebook-marketing-api-mapi) · [官方 Python Business SDK](https://github.com/facebook/facebook-python-business-sdk)。

1. 准备 Meta 开发者身份、要管理的广告账户及其 Business Portfolio 权限。确认广告账户、Facebook Page、Instagram 身份和事件源属于当前业务范围；先列出准确的 `act_...` 账户 ID。
2. 在 Meta for Developers 创建应用，在应用面板添加 Marketing API 产品。按用途选权限：报表/只读通常检查 `ads_read`，创建和修改广告需要 `ads_management`；如涉及其他业务资产，再按实际 API 文档申请所需权限。不要因为项目将来可能用到就一次申请所有权限。
3. 用应用关联的登录授权获取用户访问令牌，在测试环境完成一次账户列表与只读 Insights 请求。Meta 的[官方 Postman 文档](https://www.postman.com/meta/facebook-marketing-api/documentation/0zr4mes/facebook-marketing-api-mapi)区分：仅管理自己账户时的 Standard Access，与管理别人的广告账户时 `ads_read` / `ads_management` 的 Advanced Access 要求。对客户账户或多租户产品，按应用审查和权限要求提交使用场景；不能把自己账户测试成功当作所有客户都能用。
4. 后台任务可按官方文档评估 System User 及其资产分配和令牌生命周期。把令牌保存在密钥管理系统，记录权限、到期与撤销路径；不要写进仓库、日志或示例。把应用身份、令牌权限和**广告账户实际角色**一起验证。
5. 开发时可安装 `facebook_business` Python SDK（官方仓库给出安装与初始化示例），先实现“列账户 → 读 campaign / Insights → 对账”，再按当前 Marketing API 版本逐项增加媒体上传、creative、ad 与状态读回。为每个写动作保存原生 ID、请求/回执及配置快照。

**MCP 路线：**Meta 已宣布 Ads AI Connectors 公测，允许在第三方 AI 工具中创建、管理和分析广告；是否可用、具体工具与账户范围以自己的界面为准。[Meta 官方公告](https://about.fb.com/news/2026/05/from-scroll-to-chat-to-cart-trends-reshaping-how-india-shops/)支持这一产品现状。若使用第三方 Meta MCP，则核对它能否处理当前需要的账户、媒体、创意、广告、帖子和报告；不因连接器显示一个“create”工具就推断所有广告类型均可创建。

**完成标志：**明确列出可访问的 `act_...`；只读请求返回有时间范围的报告；如要写入，在已授权范围内创建暂停或草稿对象后，读取原生 ID、配置和 effective status。媒体上传完成、编码 ready、审核通过、实际开始投放是不同状态。

### TikTok：API for Business、Business API SDK 与官方 MCP

**官方入口：**[TikTok API for Business 开发文档](https://business-api.tiktok.com/portal/docs) · [官方 Business API SDK](https://github.com/tiktok/tiktok-business-api-sdk) · [官方 MCP 介绍](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-mcp-server?lang=en)。

**自建 API / SDK：**

1. 在 TikTok for Business 的开发者门户注册开发者，创建开发者应用，明确要接入的 Marketing API 能力、回调地址及目标广告主。官方文档导航提供“Register as a developer / Create a developer app / Authorization / App permissions / Sandbox accounts”顺序；开发者应用与具体 advertiser 授权是两件事。
2. 按当前门户的授权流程让广告主授权应用，交换授权码取得访问令牌；再读取被授权的 advertiser 列表，核对目标 `advertiser_id` 确实在其中。接口授权范围和 Business Center / 广告账户角色都要满足操作要求。[官方 SDK 的认证接口文档](https://github.com/tiktok/tiktok-business-api-sdk/blob/main/python_sdk/docs/AuthenticationApi.md)展示了 OAuth 令牌与 advertiser 列表操作。
3. 在沙盒或不产生花费的范围内先读 advertiser、campaign 和报告；再决定支持标准投放、Spark、Smart+ 等哪一个广告产品。它们的身份、素材、预算和创建字段不同，不能把一个通用 campaign JSON 同时发给所有产品。
4. 用官方 SDK 减少底层请求代码：其[官方仓库](https://github.com/tiktok/tiktok-business-api-sdk)提供 Python、Java、JavaScript 客户端和安装说明。安装前核对 SDK 发布版本与目标 API 版本；创建广告前校验账户权限、素材状态、TikTok 身份或 Spark 授权、追踪与初始状态。

**不想申请开发者应用时的官方 MCP：**TikTok 已提供 TikTok for Business MCP。官方列出约 400 个工具的 full endpoint，以及先加载约 40 个核心工具、其余按需发现的 progressive endpoint；通常先选后者以减小工具上下文：

```text
https://business-api.tiktok.com/open_mcp/tt-ads-mcp-layer
```

把该地址添加到兼容的 MCP 客户端，按 [TikTok 官方 MCP 接入文档](https://business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3)完成浏览器授权，再读账户列表和工具能力。TikTok 的[官方介绍](https://ads.tiktok.com/resources/help/article/about-tiktok-for-business-mcp-server?lang=en)说明这条托管路线无需自行准备开发者凭据或编写自定义连接代码；它不等于获得所有广告账户或所有工具的授权。需要写入时，显式指定暂停状态并读回，因为不同连接器和广告产品对新建对象的默认状态可能不同。

**完成标志：**能读到本次授权的 advertiser ID 与一段真实报告；写入试验限定在明确批准的账户和产品，逐项核对 campaign、ad group、ad、素材引用、身份、审核与投放状态。

### Google Ads：Google Cloud 项目、客户端库与官方只读 MCP

**先看 2026-09 的申请变化。** Google 已把**新 Google Ads API 接入及权限升级**迁至 Google Cloud Console；2026-09-09 后不应照旧教程去经理账户 API Center 新申请 developer token。已有 token 可暂时继续传，但服务器按 OAuth 凭据所属 Cloud 项目的访问级别判定，Google 建议更新客户端库。[Google 官方迁移说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)。这里说的是 **Google Ads API**；Google 的 App Conversion Tracking API 在官方说明中有单独例外。

**想照着控制台一步步申请，请看独立的[Google Ads API 新申请完整流程](google-ads-api-application.zh-CN.md)：**包含 Test → Explorer → Basic → Standard 的入口、IAM 与 Ads 账户权限、OAuth 身份、品牌验证、申请失败排查和验收记录。下面只保留三平台对比所需的摘要。

1. 建立或选择 Google Cloud 项目，启用 Google Ads API，在该项目的 **Google Ads API Overview** 页面查看访问级别。启用后先有 Test access；要操作生产广告账户，按页面申请 Explorer / Basic / Standard 等级。各等级有不同配额和可用功能；Basic / Standard 的新申请涉及品牌验证。[Cloud 项目设置](https://developers.google.com/google-ads/api/docs/oauth/cloud-project) · [访问级别说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)。
2. 在同一项目配置 OAuth 2.0。若是给多个外部用户授权，选多用户 OAuth 流程；若是管理自己已有权限的账户，可按官方场景评估 service account，并把服务账户邮箱加入相应 Google Ads 账户。普通 OAuth 用户也必须具有该 Ads 账户权限。[OAuth 场景选择](https://developers.google.com/google-ads/api/docs/oauth/overview) · [服务账户流程](https://developers.google.com/google-ads/api/docs/oauth/service-accounts)。
3. 确认目标 customer ID、登录用 manager ID（如有）、账户层级与目标广告产品。先在测试账户或只读范围调用 `GoogleAdsService.Search` / `SearchStream`，用 GAQL 读 campaign 和花费；之后再按 Search、PMax、Demand Gen、App 等产品的原生资源分别开发写入。经理账户用于管理多账户，但按当前[官方说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)已不是新申请 Google Ads API 的必备入口。
4. 用[官方客户端库](https://developers.google.com/google-ads/api/docs/client-libs)减少认证、请求与错误处理代码。选择能支持当前 Cloud 项目接入方式的版本；旧版教程仍可能要求 developer token，因此不要把旧配置示例直接当成 2026-09 的新申请步骤。密钥、OAuth 凭据、refresh token 均留在安全配置中。

**官方 MCP 的边界：**[Google Ads 官方 MCP](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server)目前是 **只读**，提供账户发现、GAQL 查询和资源元数据查询，不能创建资产、暂停 campaign 或修改出价。它适合先做账户盘点和分析；如果本项目要自动准备与配置 Google 广告，还需要获准的写入 API 或经核验具有对应操作的其他连接器。官方 MCP 同样需要具有生产访问级别的 Cloud 项目及 OAuth / 服务账户凭据。

**完成标志：**Cloud 项目访问级别足以访问目标账户；OAuth 身份能列出目标 customer；报告的时间范围、币种、时区和归因口径明确；写入前按广告产品验证资源图与具体权限。

## 路线 B：用现成连接器更快进入账户工作流

如果团队暂时不想维护所选平台的开发者应用、OAuth、SDK 与 MCP 服务，可优先考虑 Pipeboard 的账户连接与托管 MCP。其[跨平台 MCP 文档](https://pipeboard.co/guides/ads-mcp)说明：连接已授权的 Meta、Google Ads、TikTok 账户后，一个 MCP 入口可暴露各平台带前缀的工具；按账户和令牌权限限制访问。先完成账户发现与本次必要能力验证，宿主再按真实工具 schema 准备方案、执行已授权动作并读回结果。

**[前往 Pipeboard 官网连接广告账户](https://pipeboard.co/#via=tian)**

按以下顺序操作最稳妥：

1. 在官网核对当前服务方案及所需操作，具体见[当前套餐说明](https://pipeboard.co/pricing)。套餐、额度、价格和能力可能变化，应以当前页面和账户可见能力为准，不凭套餐名称推断某项写入必然可用。
2. 在 Pipeboard 连接需要的 Meta、TikTok 和/或 Google Ads 平台；**只选择本项目本次要用的广告账户**。授权后读回账户列表，不把 Business/manager 下可见的其他账户自动纳入。
3. 按[统一 Ads MCP 官方指南](https://pipeboard.co/guides/ads-mcp)或相应客户端指南完成配置；令牌放在本机安全配置或密钥管理器，切勿提交到仓库。先用读取结果确认账户身份；只读任务据此继续，含写入的任务再核验相应权限与读回能力。
4. 对即将执行的每一种操作做小范围能力检查：工具是否存在，套餐是否支持，账户是否授权，平台当前广告产品是否适配，写入后的原生对象能否读回。批次方案确认后再发布，保持本项目的预算、素材、目标和账户边界。

Pipeboard 能替代一部分**连接器搭建时间**，不替代广告账户授权、素材和事件配置、平台审核，也不保证每个广告产品都有相同的写入能力。其官方说明指出，不同平台新建对象的默认状态并不一致：Meta 和 Google 的新 campaign 默认为暂停，而 TikTok 的初始状态取决于调用者传入的值。因此跨平台批次必须显式给出状态并读回。[Pipeboard 权限与状态说明](https://pipeboard.co/guides/ads-mcp)。宿主可以使用已验证且已授权的现成工具；若希望**公开 Python 程序自行连接和发布**，才需要另行实现并验收原生适配、授权、提交与恢复。购买服务不会自动完成任一路线的账户验证和操作授权。

### 接入时最常见的卡点

| 现象 | 先核对什么 | 下一步 |
|---|---|---|
| MCP 已连接，但找不到目标账户 | 原平台授权用户、Pipeboard 选中的账户、账户位是否够 | 在原平台和连接器中核对同一原生账户 ID，不直接新建替代账户 |
| 能读报告，不能创建或改预算 | 令牌/团队是否只读、当前套餐是否包含所需工具、该平台产品是否受支持 | 查工具清单与错误码，按任务申请最小写权限 |
| 工具显示成功，后台看不到广告 | 返回的是草稿、暂停对象还是正式对象；所在账户和原生 ID 是否正确 | 读取目标对象及父级状态、审核状态与更新时间 |
| 报表与后台数字不同 | 日期、账户时区、归因窗、事件名、货币、数据回补时间 | 按同一口径重新查询，保留原始响应与 as-of 时间 |
| 连接突然失效 | OAuth 授权是否到期/撤销，服务令牌是否轮换，平台是否限流 | 从服务端错误分类入手，确认前次写入是否成功后再重试 |

若选择自建，前四项排查逻辑也一样适用；只是认证和连接器维护由自己承担。

## 接好之后，Agent 先做什么

本次必要能力通过验收后，按[首次配置引导](first-run.zh-CN.md)复用或确定 `guided` / `bring_own` 协作方式与需求，记录相关平台经验和说明偏好。宿主按用户需要解释；Python 的引导规则只处理其结构化输入。经验和偏好都不改变账户权限。

接着按[业务初始化](onboarding.md)补齐本次任务需要的产品、市场、路径、变现、事件、素材、方法和预算。接口能提供的事实注明来源，需要用户决定的事项明确提出；保留未知和冲突。宿主准备整批方案，核对对应授权后使用现有工具执行并读回；只读任务直接交付报告和建议。需要 M2 的两类离线编译时再调用程序，其限制见[方法指南](method-planning.zh-CN.md)，不以这两类模板限制宿主可讨论的方法。

第一轮可先验证**账户清单准确、只读报告可对账**；需要发布的部署，再在明确授权的测试范围验收对象创建/修改及读回、权限失效等分支。不要仅为跑完验收清单擅自创建对象或撤销真实权限。之后按实际任务增加媒体、批量配置、广告产品和调度验证。[连接器契约](../contracts/connector-contract.json)是独立实现参考，不会自动启用；[路线图](roadmap.md)区分工作流迁移与代码工程。

返回[文档导航](index.md)或[项目首页](../README.zh-CN.md)。
