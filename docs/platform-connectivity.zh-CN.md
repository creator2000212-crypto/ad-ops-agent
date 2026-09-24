# Meta、TikTok、Google Ads API / SDK / MCP 接入全攻略

> 核对日期：2026-09-24。平台入口、审核规则、套餐与工具能力会变；操作前以文中链接的当前官方页面及自己的账户实际可见权限为准。本文是**生产接入路线图**，不是本仓库已完成的功能说明。当前代码只运行离线模拟，不能读取真实账户或发布广告。

这份指南面向两种团队：愿意申请平台接口并维护代码的开发者；希望先把账户接给 AI 助手、验证工作流价值的投放团队。两条路线最终都要回答同一组问题：能访问哪个原生广告账户，能读什么、能写什么，操作作用于哪个广告产品，实际写入后怎样读回和核对。

## 先选接入层，再选工具

| 方式 | 你需要准备 | 适合的第一步 | 不能替代的事情 |
|---|---|---|---|
| 官方 API | 平台/云开发者身份、广告账户授权、相应权限、自己维护认证与调用 | 做专有流程、深度控制数据和对象 | 业务理解、字段校验、审核、发布确认 |
| 官方 SDK | 上述 API 权限，外加开发环境 | 少写请求、分页和模型封装 | SDK 不替你申请权限，也不保证账户支持每个字段 |
| 平台官方 MCP | 支持 MCP 的助手、对应账户授权；各平台前置条件不同 | 先验证工具、做分析或支持范围内的操作 | 平台间语义归一、批次审批和本项目原生适配器 |
| 托管跨平台 MCP（如 Pipeboard） | 服务账户、所选广告账户授权、MCP 客户端、合适的套餐/权限 | 快速接通多个平台，减少连接维护 | 广告平台账户资格、未开放的功能、业务决策和本仓库代码开发 |

**API 是源接口，SDK 是调用 API 的代码库，MCP 是把工具暴露给 Agent 的协议。** MCP 可能由平台自己运营，也可能由第三方将官方 API 封装。三者不是相互排斥的“申请项”；先决定要直连还是使用现成 MCP，再检查其能力、账户范围和授权方式。用户明确确认的投放方案才进入发布流程，详见[架构与实现边界](architecture.md)。

无论走哪条路线，先备好：广告账户 ID 与管理权限、关联的 Business/经理账户、目标市场与币种、转化来源（Web 像素/CAPI 或 App SDK/MMP）、素材使用权、要操作的广告产品、允许的读写范围。**平台 API 权限与素材/转化配置是不同事项**；能查广告不等于能上传视频、创建广告或读取归因结果。

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

1. 建立或选择 Google Cloud 项目，启用 Google Ads API，在该项目的 **Google Ads API Overview** 页面查看访问级别。启用后先有 Test access；要操作生产广告账户，按页面申请 Explorer / Basic / Standard 等级。各等级有不同配额和可用功能；Basic / Standard 的新申请涉及品牌验证。[Cloud 项目设置](https://developers.google.com/google-ads/api/docs/oauth/cloud-project) · [访问级别说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)。
2. 在同一项目配置 OAuth 2.0。若是给多个外部用户授权，选多用户 OAuth 流程；若是管理自己已有权限的账户，可按官方场景评估 service account，并把服务账户邮箱加入相应 Google Ads 账户。普通 OAuth 用户也必须具有该 Ads 账户权限。[OAuth 场景选择](https://developers.google.com/google-ads/api/docs/oauth/overview) · [服务账户流程](https://developers.google.com/google-ads/api/docs/oauth/service-accounts)。
3. 确认目标 customer ID、登录用 manager ID（如有）、账户层级与目标广告产品。先在测试账户或只读范围调用 `GoogleAdsService.Search` / `SearchStream`，用 GAQL 读 campaign 和花费；之后再按 Search、PMax、Demand Gen、App 等产品的原生资源分别开发写入。经理账户用于管理多账户，但按当前[官方说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)已不是新申请 Google Ads API 的必备入口。
4. 用[官方客户端库](https://developers.google.com/google-ads/api/docs/client-libs)减少认证、请求与错误处理代码。选择能支持当前 Cloud 项目接入方式的版本；旧版教程仍可能要求 developer token，因此不要把旧配置示例直接当成 2026-09 的新申请步骤。密钥、OAuth 凭据、refresh token 均留在安全配置中。

**官方 MCP 的边界：**[Google Ads 官方 MCP](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server)目前是 **只读**，提供账户发现、GAQL 查询和资源元数据查询，不能创建资产、暂停 campaign 或修改出价。它适合先做账户盘点和分析；如果本项目要自动准备与配置 Google 广告，还需要获准的写入 API 或经核验具有对应操作的其他连接器。官方 MCP 同样需要具有生产访问级别的 Cloud 项目及 OAuth / 服务账户凭据。

**完成标志：**Cloud 项目访问级别足以访问目标账户；OAuth 身份能列出目标 customer；报告的时间范围、币种、时区和归因口径明确；写入前按广告产品验证资源图与具体权限。

## 路线 B：用现成连接器更快进入账户工作流

如果团队暂时不想分别申请和维护三个平台的开发者应用、OAuth、SDK 与 MCP 服务，可使用 [Pipeboard 官网](https://pipeboard.co/#via=tian)提供的账户连接与托管 MCP。其[跨平台 MCP 文档](https://pipeboard.co/guides/ads-mcp)说明：连接已授权的 Meta、Google Ads、TikTok 账户后，一个 MCP 入口可暴露各平台带前缀的工具；按账户和令牌权限限制访问。对现有投放团队，这意味着可以先做账户发现、报表、素材与广告操作的能力验证，再逐步把工作流接到本项目的未来平台适配器中。

按以下顺序操作最稳妥：

1. 在 [Pipeboard 官网](https://pipeboard.co/#via=tian)注册并查看当前免费或付费方案。免费方案适合小范围试用；若需要更多账户位、批量操作或分权限令牌，查看[当前套餐功能](https://pipeboard.co/pricing)。套餐、额度和价格可能变化，以结算页为准。
2. 在 Pipeboard 连接需要的 Meta、TikTok 和/或 Google Ads 平台；**只选择本项目本次要用的广告账户**。授权后读回账户列表，不把 Business/manager 下可见的其他账户自动纳入。
3. 在兼容的 AI 客户端添加其[统一 Ads MCP](https://pipeboard.co/guides/ads-mcp)，或按任务使用单平台 MCP。Pipeboard 的[Codex 指南](https://pipeboard.co/guides/codex)给出 API token 和单平台服务器的接法；令牌放在本机环境或密钥管理器，切勿提交到仓库。先开只读范围，确认报告与账户身份；随后按需要开写权限。
4. 对即将执行的每一种操作做小范围能力检查：工具是否存在，套餐是否支持，账户是否授权，平台当前广告产品是否适配，写入后的原生对象能否读回。批次方案确认后再发布，保持本项目的预算、素材、目标和账户边界。

Pipeboard 能替代一部分**连接器搭建时间**，不替代广告账户授权、素材和事件配置、平台审核，也不保证每个广告产品都有相同的写入能力。其官方说明指出，不同平台新建对象的默认状态并不一致：Meta 和 Google 的新 campaign 默认为暂停，而 TikTok 的初始状态取决于调用者传入的值。因此跨平台批次必须显式给出状态并读回。[Pipeboard 权限与状态说明](https://pipeboard.co/guides/ads-mcp)。此外，**本仓库当前仍是离线原型**；即便购买 Pipeboard，也还需要开发和验收真实连接器、平台适配器及发布控制，才能让这个开源 Agent 代为执行真实投放。

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

连通账户不是直接开始建广告。先按[业务初始化](onboarding.md)与用户分轮明确产品、国家/语言、平台与账户、Web/App、IAA/IAP/混合变现、目标事件与收入来源、素材类型、方法论、测试变量和预算范围。接口能提供的账户配置和历史数据先读取并标记来源；需要用户判断的事项明确提问；缺口保留为未知。之后才生成整批方案，经过预览、确认、执行和原生读回，供投放人员分析结果与决定下一轮方向。

建议第一轮验收只做四件事：**账户清单准确、只读报告可对账、单个暂停/草稿对象可核验、权限撤销后操作被拒绝**。这四项通过后，才扩到素材上传、批量配置、复杂广告产品和自动化调度。[连接器契约](../contracts/connector-contract.json)与[路线图](roadmap.md)描述了未来实现所需的能力声明和验收边界。

返回[文档导航](index.md)或[项目首页](../README.zh-CN.md)。
