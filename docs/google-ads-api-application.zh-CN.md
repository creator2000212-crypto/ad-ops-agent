# Google Ads API 新申请流程：从 Google Cloud 项目到生产账户

> 核对日期：2026-09-24。本文针对 **Google Ads API** 的新申请，不等同于 Google Ads 广告账户开户，也不适用于另有例外的 App Conversion Tracking API。Google 已于 2026-09-09 将新申请和访问级别管理迁到 Google Cloud 项目；旧教程中“去经理账户 API Center 申请 developer token”的步骤不再适用于新申请。[Google 迁移说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)

本文说明的是**如何申请与验收**，不会代用户创建 Cloud 项目、提交申请或获取凭据。本仓库当前仍是离线原型；申请到 API 权限也不会自动让它接通或发布广告。

## 先决定申请到哪一级

| Cloud 项目级别 | 能访问的账户 | 官方列出的操作量 | 何时选它 |
|---|---|---|---|
| Test | 仅测试账户 | 每日 15,000 次 | 开发认证、对象结构和调用流程；不会产生真实投放数据 |
| Explorer | 测试和生产账户 | 生产账户每日 2,880 次；测试账户每日 15,000 次 | 第一版真实账户联调与常规自动化；账号创建、用户管理、部分规划和账单接口受限 |
| Basic | 测试和生产账户 | 每日 15,000 次 | Explorer 的限制或调用量已不够；申请前完成 Cloud 项目的品牌验证 |
| Standard | 测试和生产账户 | 不设通用每日操作量上限，仍有具体接口限制 | 多客户或大规模工具；需人工审核，并满足获批的 permissible use |

数字及 Explorer 受限服务以[Google 当前访问级别表](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)为准。对本项目，**先争取 Explorer 并做真实账户只读联调**是合理起点；Google 的 Explorer 受限清单未把一般 campaign 管理整体列为受限，但具体写入仍须按 API 方法、广告产品和账户权限逐项验证。若只是研究代码，Test 即可。不要为“看起来更正式”直接申请 Standard。

## 申请前准备四类信息

1. **Google Cloud 项目：**准备能创建/选择项目的 Google 身份，记录项目 ID 和项目编号。一个项目管理自己的 Google Ads API 访问级别；OAuth client 或 service account 必须属于你实际申请的项目。[项目准备说明](https://developers.google.com/google-ads/api/docs/oauth/cloud-project)
2. **项目 IAM 权限：**能启用 API，并具备管理配额/访问级别的权限。Google 列出的默认具备所需配额管理权限的角色包括 Owner、Editor、Quota Administrator、Service Usage Admin；没有权限时让项目管理员配置，而不是换一个不相关的项目反复申请。[Google IAM 说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)
3. **Google Ads 账户访问：**确定目标生产账户的 10 位 customer ID，以及谁有该账户的管理员权限。Cloud 项目批准**不会自动授予任何广告账户访问权**；之后仍需把 OAuth 用户或 service account 加入对应 Ads 账户。经理账户在管理多个客户账户时有用，但新申请 Google Ads API 不再要求必须拥有经理账户。[Google 迁移说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) · [服务账户授权](https://developers.google.com/google-ads/api/docs/oauth/service-accounts)
4. **用途说明：**准备真实、具体的应用说明：内部自用还是外部客户；只做报表还是会创建/修改广告；预计账户数量、操作量、权限范围、人工确认和撤销方式。若申请 Standard，还要准备可演示的功能及符合其要求的材料。[Standard 审核说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)

不要把“代码仓库公开”“已有 Google Ads 广告账户”“已经连接 Pipeboard”当成 Google 对**这个 Cloud 项目**的 API 生产访问批准。

如果申请界面要求描述工具，可以根据实际阶段改写下面这段，不要填写尚未实现的能力为已上线：

> Ad Ops Agent 是面向投放团队的工作流项目。Google Ads 接入拟先在获得账户授权后读取账户结构、广告状态和指定日期的效果数据，用于人工分析与方案准备；后续写入能力只针对明确授权的账户，在用户确认整批配置后创建暂停对象，并读取原生对象核验。当前开源仓库是离线原型，真实 Google Ads 适配器仍在开发中。

如实际申请仅用于内部账户、仅做只读报表或已经交付了某些生产功能，应据实删改。Google 的表单字段和审核问题以申请时显示的版本为准。

## 第一阶段：创建项目并取得 Test 访问

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)，在页面顶部选择已有项目或创建项目。若团队已有正式用于 Ads API 的项目，先检查它当前的访问级别和 OAuth 凭据归属，避免无意中新建项目导致原有批准无法沿用。Google 说明，Cloud 项目启用计费是可选项；Google Ads API 本身不按调用收费，但有配额。[Cloud 项目设置](https://developers.google.com/google-ads/api/docs/oauth/cloud-project)
2. 在该项目进入 **APIs & Services → Library（API 库）**，搜索 **Google Ads API**，打开它并点 **Enable（启用）**。操作时确认页面顶部显示的是预期项目。[Google 官方启用步骤](https://developers.google.com/google-ads/api/docs/oauth/cloud-project)
3. 打开该项目的 **Google Ads API Overview** 页面，读出当前 **API access level**。首次启用后应为 **Test**；把项目 ID、级别及检查日期记入接入记录。若看不到升级入口，先核对项目是否正确、API 是否启用以及自己是否具备配额管理权限。[访问级别说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)
4. 如需在等待生产权限时先测试，可依[官方测试账户指南](https://developers.google.com/google-ads/api/docs/best-practices/test-accounts)创建独立的 test manager 和 test client，在测试 client 中建样例对象。测试账户不能与生产账户混在同一层级，不产生真实展示、花费或转化；不要用它的零指标判断真实投放效果。

**这一阶段的验收：**Overview 显示 Test。完成下文的 OAuth 身份配置后，再用该项目的认证身份对测试 customer 发出成功请求。Test 级别调用生产账户会被拒绝，这不是 OAuth 凭据已经坏了。

## 第二阶段：在 Cloud 项目申请 Explorer 生产访问

1. 仍在同一项目的 **Google Ads API Overview**，确认当前级别是 **Test**。
2. 展开 **Upgrade access level**（部分官方文档称 *Apply for next access level*）。核对 **Next access level = Explorer**，点击 **Apply for access**。页面若出现项目或用途问题，按实际产品与拟用功能填写；表单字段可能调整，不要照搬别人的答案。[Google Explorer 申请步骤](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)
3. 提交后返回 Overview **重新读取当前级别**，不要仅凭按钮已点击就认为获批。Google 说明多数 Explorer 申请会自动审核升级，但实际结果以页面状态和可用的生产账户调用为准。[官方项目接入说明](https://developers.google.com/google-ads/api/docs/oauth/cloud-project)
4. 获批后只对已授权的生产 Ads 账户做最小只读调用，例如列可访问 customer，或用 `GoogleAdsService.Search` 读取一条 campaign 的 ID、名称与状态。把返回的 customer ID 与 Ads 后台所见账户核对；再考虑是否测试创建**暂停**对象。[官方客户端库](https://developers.google.com/google-ads/api/docs/client-libs) · [Google Ads MCP](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server)

**这一阶段的验收：**Cloud Overview 明确显示 Explorer 或更高。完成下文的 OAuth 身份与 Ads 账户授权后，才继续验证能否读取目标生产 customer；只看到 Explorer 还不够。Google 官方 MCP 目前只读，可用于首轮账户与报表核验，不能证明写入能力。[官方 MCP 边界](https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server)

## 第三阶段：选对 OAuth 身份，授权具体广告账户

API 访问级别与 Ads 账户授权是两道不同的门。先决定应用的实际使用方式，再创建凭据：

| 场景 | 优先阅读的官方方案 | 账户授权动作 |
|---|---|---|
| 后台服务管理自己或已获授权的一组账户 | [Service account workflow](https://developers.google.com/google-ads/api/docs/oauth/service-accounts) | 在 Google Ads 后台 **Admin → Access and security → Users** 添加 service account 邮箱并授予所需角色；多账户可考虑加到 manager |
| 少数内部用户，组织政策不便使用 service account | [Single-user workflow](https://developers.google.com/google-ads/api/docs/oauth/single-user-authentication) | 用户本人先拥有目标 Ads 账户访问，再完成 OAuth 授权 |
| 产品要让多个外部客户各自授权账户 | [Multi-user workflow](https://developers.google.com/google-ads/api/docs/oauth/multi-user-authentication) | 每个用户经你的 OAuth 流程授予其有权访问的账户；记录撤销和令牌更新 |

1. 在**已申请权限的同一个 Cloud 项目**创建相应 OAuth client 或 service account。若是 service account，Google 文档仍展示 JSON 密钥流程；私钥只放密钥管理系统，不放仓库或终端共享记录。若是用户 OAuth，配置同意屏幕和必要的授权范围，按官方流程取得令牌。[OAuth 场景选择](https://developers.google.com/google-ads/api/docs/oauth/overview)
2. 在 Google Ads 账户里授予该身份所需的最低角色。Service account 的具体添加路径和界面按钮见[Google 官方图文步骤](https://developers.google.com/google-ads/api/docs/oauth/service-accounts)；普通用户也必须先有对应 Ads 账户权限。
3. 记录目标 **customer ID**；如果调用经 manager 账户进入子账户，按官方客户端库要求配置相应的 **login customer ID**。不要把 Cloud project ID、OAuth client ID、service account 邮箱、manager customer ID 和投放 client customer ID 当成同一个标识。[Google Ads 访问模型](https://developers.google.com/google-ads/api/docs/oauth/overview)
4. 用当前版本[官方客户端库](https://developers.google.com/google-ads/api/docs/client-libs)或官方只读 MCP 做首次请求。Google 已说明新版库可不传旧 developer token；部分旧页面仍保留 token 字段，遇到冲突时以[2026-09 迁移说明](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)及所用库的当前版本说明为准。

**这一阶段的验收：**请求所用凭据属于获批的 Cloud 项目，原生 customer ID 正确，权限与目标动作匹配。不要保存访问令牌正文作为验收证据，只保存经脱敏的配置项、调用时间、请求 ID、对象 ID 和状态。

## 需要 Basic 时：先做品牌验证，再申请升级

Explorer 的生产调用量或受限方法不够时，再申请 Basic。Google 要求**新的 Basic / Standard 申请先完成该 Cloud 项目的品牌验证**。即便应用只服务内部用户，Google 针对 Basic 审核的专门说明仍要求将 OAuth Audience 设为 External、发布状态设为 In production；不要把其他 OAuth 页面“Internal / Testing 无需验证”的一般说明误套到这项申请。[品牌验证专页](https://developers.google.com/google-ads/api/docs/api-policy/brand-verification)

按[Google 当前品牌验证步骤](https://developers.google.com/google-ads/api/docs/api-policy/brand-verification)操作：

1. Cloud Console 选中该项目，进入 **APIs & Services → OAuth consent screen**。在 **Overview** 点 **Get Started**，填真实的应用与联系信息并创建。
2. 在 **Audience** 核对用户类型与发布状态。Workspace 项目若显示 Internal，按官方该流程转为 External，并切到 **In production**；个人项目通常已是 External，若仍在 Testing，则执行 Publish app。发布 OAuth 应用是独立的外部状态变化，应由项目所有者核对用户范围和同意屏幕内容。
3. 在 **Branding** 填完整品牌资料并保存，点击 **Verify Branding**。若页面列出错误，按当前反馈修复；验证成功后点击 **Publish branding**。回到页面确认项目确实显示已验证。
4. 再到 **Google Ads API Overview**，确认当前级别 **Explorer**，展开升级区，确认 **Next access level = Basic**，且无品牌验证缺口提示，然后点 **Apply for access**。提交后回页读回级别。Google 说明 Basic 在品牌验证与提交后通常自动审核；不要把“申请已送出”写成“已批准”。[Basic 申请步骤](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)

**这一阶段的验收：**品牌状态已验证、Overview 显示 Basic、生产账户请求符合预期；若是为某个受限接口升级，还要实际测试该接口的权限。

## 需要 Standard 时：准备可审核的真实产品

只有 Basic 不足以支撑调用量或产品需求时，才在 Overview 的升级区申请 Standard：确认当前 Basic，**Next access level = Standard**，点 **Start application**。这是 Google 的人工审核，可能要求说明工具功能、目标用户，以及供外部用户登录的演示入口；Standard 还有 [Required Minimum Functionality](https://developers.google.com/google-ads/api/docs/api-policy/rmf) 和获批的 **permissible use** 范围。Google 文档列出通常约 **10 个工作日**的审核时间，但不保证每个申请的结果和时长。[Standard 申请说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)

申请材料可按真实进度组织：用途（报表、广告创建/管理、关键词研究）、用户类型、目标账户授权方法、具体 UI 或 Agent 交互、写入前确认与撤销、日志和错误恢复、演示账户与联系人。**本仓库目前只实现离线模拟**；在没有真实适配器和可用演示前，不应把设计文档描述成已经上线的广告管理功能。Standard 获批后还要核对 permissible use；仅获批 Reporting 的项目不能据此假定能执行广告写入。[permissible use 说明](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)

## 申请失败或调用失败：按错误归因

| 现象 | 优先检查 | 处理方向 |
|---|---|---|
| Overview 找不到升级按钮 | 当前项目、API 启用状态、IAM 配额管理权限 | 回到项目选择与 API Library；让项目管理员核对角色 |
| Test 项目调用生产账户报 `CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` | 当前 Cloud 项目仍是 Test；凭据是否属于另一项目 | 在使用中的项目申请 Explorer，不靠更换旧 token 解决 |
| 显示 Explorer/Basic，仍读不到 customer | OAuth / service account 是否在该 Ads 账户有访问、customer ID 与 manager 层级 | 先查 Ads 后台 Access and security，再查身份和目标 ID |
| Basic 申请称品牌未验证 | Audience 是否 External / In production；Branding 是否完成验证和发布 | 按[品牌验证专页](https://developers.google.com/google-ads/api/docs/api-policy/brand-verification)完成并读回状态 |
| Explorer / Basic 申请被拒，理由似乎与品牌或资格不符 | Cloud 项目是否处于 Free Trial、计费暂停/禁用状态 | Google 将其列为迁移期已知问题；先核对[官方已知问题](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)，不要盲目更改现有项目的计费配置 |
| 老项目升级后仍报授权错误 | 是否属于 2026-09-09 前使用旧 token 的迁移场景 | 查[Google 迁移说明的已知问题](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)，保留项目 ID、错误码和请求 ID，按其当前建议处理 |
| 读得到报告，但写入报权限或产品错误 | 访问级别、账户角色、具体 API 方法、广告产品约束、Standard 的 permissible use | 用最小测试对象分层排查，不能把只读成功当写入许可 |

## 给本项目的最小验收记录

申请时只记录可复核的非密钥信息，不上传证件、密钥或 OAuth 凭据到开源仓库：

```text
Cloud project ID / number: [仅在私有运行记录中填写]
Google Ads API enabled: yes/no + checked_at
Access level: Test / Explorer / Basic / Standard + checked_at
OAuth identity type: service account / single-user / multi-user
Target customer ID: [仅在私有运行记录中填写]
First test call: method + status + request ID + checked_at
First production readback: native customer/campaign ID + date range + status
Approved write scope: account + operation + budget bound + approver + expiry
```

这个记录区分“启用 API”“提交申请”“显示获批”“可以读某账户”和“可以写某对象”五个不同事实。接入本项目时，再按[连接器契约](../contracts/connector-contract.json)映射原生身份与能力；批次发布仍需具体计划和用户确认。返回[三平台接入总览](platform-connectivity.zh-CN.md)。
