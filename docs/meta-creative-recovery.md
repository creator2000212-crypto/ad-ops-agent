# Meta 素材恢复与对象身份

素材恢复覆盖三类现场问题：文件/上传/关联故障，具有合理证据的疑似误拒，以及需要修改真实内容或配置的问题。重新导出、重传和新建对象可以是正常排障的一部分；项目以原因、实际差异、执行范围和验收证据选择动作，不把所有重传一概排除，也不提供无限刷新直到过审的循环。

**实现状态：**本文与 [creative-recovery.json](../contracts/creative-recovery.json) 是生产流程设计。离线运行时尚未上传媒体、重建 creative、替换广告关联、提交复核或轮询审核。流程与连接器供应商无关，Pipeboard、其他 MCP 或官方 API 都需要满足同一对象与证据契约。

## 六层身份分别记录

| 身份 | 含义 | 不能据此推断 |
|---|---|---|
| `local_content_hash` | 对本地文件字节计算的摘要 | 不等于 Meta image hash 或内部审核指纹 |
| `image_hash` | 平台返回、供图片创意引用的标识 | 不能修改字符串来创造新图片；需保留账户范围 |
| `video_id` | 平台视频资产 | 不等于 creative/ad，取得 ID 不等于已处理完 |
| `creative_id` | 媒体、文案、链接、CTA 和身份等引用的组合 | 新 creative 不自动替换现有广告 |
| `ad_id` | 属于广告组并关联创意的广告对象 | 保持 ID 不保证学习或互动保持 |
| `object_story_id` / `effective_object_story_id` | 帖文关联与实际帖文身份 | 不等于广告 ID；FB/IG 互动不默认互相合并 |

Meta 官方 SDK 固定提交 [`5286888addfe3ba3718db65fbf132bd66de3ddfe`](https://github.com/facebook/facebook-python-business-sdk/commit/5286888addfe3ba3718db65fbf132bd66de3ddfe) 提供这些模型与请求构造证据。SDK 存在字段不意味着每个账户、广告产品都具有写权限。[图片引用处理](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/helpers/adimagemixin.py)、[创意模型](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreative.py)

视频创意也可能有 `image_hash/image_url`，用于其中的图片引用；它不能替代视频本体的 `video_id`。[视频创意数据模型](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreativevideodata.py)

## 选择最小有效动作

| 动作 | 直接结果 | 后续必须确认 |
|---|---|---|
| 修复或重新导出本地媒体 | 文件/派生版本和实际内容差异 | 能解码、尺寸/时长/音频正确，尚无新平台资产 |
| 重新上传媒体 | 平台实际返回的 image hash/video ID，可能被去重 | 目标账户可用、视频 ready，尚未自动替换广告 |
| 创建新 creative | 回执与读回确认的 creative ID | 正确媒体、文案、链接、发布身份、实际帖子与预览 |
| 原 ad 换 creative | 原广告对象的关联变更 | 关联成功、审核/有效状态、父级、帖文与学习观测 |
| 创建替代 ad | 新广告对象及其 ID | 父级、配置、追踪，以及新旧广告的并行/切换安排 |

官方 SDK 将图片、创意和广告的创建请求分开，`Ad.api_update()` 接受 creative 引用。固定版本的 `AdCreative.api_update()` 没有通用的 image/video 原地替换参数，因此不能把读取模型中的任意字段都当作更新参数。具体编辑能力仍需按部署版本与广告产品验证。[账户创建接口](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adaccount.py)、[广告更新接口](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)

## 分诊与恢复步骤

### 1. 固定现场

记录文件版本、全部关联 ID、实际文案/封面/目的地、身份、市场、拒登理由、最近改动、父级状态及历史表现窗口。过去表现好或其他广告通过，是值得保留和排查的线索，不单独证明当前拒登错误。

操作计划说明希望保留什么：文件内容、原广告、原帖互动、追踪参数或预算。它们不是同一个目标，有时需要取舍。

### 2. 技术故障走对应层修复

上传中断先查询原会话/回执；已有视频 ID 且仍 processing 时有界等待。可解码性或规格失败时修复媒体，保留原件并上传派生版本；引用或身份错配时修正对应对象关联，不顺带更换账户、事件和预算。

官方上传器默认 `wait_for_encoding=False`，编码检查另读 `status.video_status`，只有 ready 才通过该阶段。SDK 中的轮询间隔和超时是代码参数，不是平台 SLA。[上传与编码检查器](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/video_uploader.py)

### 3. 疑似误拒采用有限、可检验的分支

已有内容与目的地核对证据、拒登原因不清或与实际内容不符时，可准备平台支持的复核材料。若仍存在合理的资产或创意关联故障假设，可以把重传、新 creative 或替代 ad 纳入有上限的诊断计划。

计划具体写明：测试哪一层、保持哪些变量、允许几次尝试、总时间与预算范围、是否允许新帖、哪些结果停止。次数由项目与任务确定，不写成平台统一规则；也不强制所有技术修复都先走申诉。

等待上一次操作明确回执或完成核对后再开新尝试。区分“文件变了”“平台资产不同”“creative 被接受”“广告当前通过审核”，不要压成一句“换 hash 救回”。同一政策原因持续存在、内容问题未解决、范围到达上限或出现账户限制时停止该分支。

### 4. 明确内容问题先修改实际问题

若画面、文案、目的地或业务本身已经存在明确问题，修改实质内容并重新核验。仅换字节、媒体 ID、creative ID 或账户不是内容修复；替换主体、支付或域名以绕过已有账户限制不属于此恢复能力。

## 授权与部分失败

一份整批计划可以预先覆盖媒体处理、创建新创意、原广告换绑或替代广告创建、读回和有限恢复步骤；范围内连续执行，不对每个机械步骤重新询问。新素材主张、身份、目的地、事件、额外预算或未列入的对象变更应先呈现具体差异。

新对象可能在父级、排期和审核条件允许时开始消耗，计划应显式定义初始状态与启用顺序。不要在替代对象尚未验收时自动关闭健康原投放，也不要让新旧并行时间产生未说明的资金承诺。测试要求同步起跑时，部分成功不能自行改变该设计。

## 六层验收

| 层次 | 所需证据 | 不代表什么 |
|---|---|---|
| 媒体 | 原生媒体引用、可读性、ready 与实际内容 | 不等于审核通过 |
| 配置 | creative/ad/post、身份、链接、父级和预算读回 | 不等于有效投放 |
| 当前审核 | 带时间的反馈与有效状态 | 不等于永久批准 |
| 实际交付 | 当前可投状态与所需的展示/消耗证据 | 不等于达到原表现 |
| 数据有效性 | 素材绑定生效时间、事件、归因、成熟度与覆盖 | 不等于因果可识别 |
| 业务结果 | 同口径成本/结果及不确定性 | 不能仅凭恢复后的回升证明重传有效 |

Meta 将配置状态与 effective status 分开；广告自身 active 仍可能处于父级暂停、审核中或其他不可投状态。[广告状态模型](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)

保留 ad ID 仅证明对象连续，不保证学习连续。学习字段不可读时保持 unknown；已换素材的广告历史应按关联生效时间分段。社交证明按实际帖子/IG media 身份与可见互动核对，不能由同一个视频或同一段文案推断。[广告组学习字段](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adset.py)、[Post 模型](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/post.py)

## 记录用于复盘的完整样本

每次尝试保存原因分类、假设、变更前后身份、内容差异、控制变量、尝试范围、请求/回执、时间、当前状态、学习与互动观测及花费。未知写入先核对，不能作为失败直接重试；跨连接器也保留相同业务操作身份。

记录成功、失败和未决尝试，而不仅收集恢复成功的素材。同期内容、账户、文案、链接或时间变化保留为其他解释。经验可以逐步成为有范围的方法模板，但单次前后变化不能证明平台内部审核指纹机制。

相关日常流程见 [操作卡](operations.md)，连接器要求见 [架构](architecture.md)，待实现验收见 [acceptance-scenarios.json](../contracts/acceptance-scenarios.json)。

返回 [文档索引](index.md)。
