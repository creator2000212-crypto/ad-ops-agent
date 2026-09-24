# 投放实操手册

资料核对日期：2026-09-24。16 张操作卡覆盖素材准备、配置、测试搭建和结果整理。它们是平台适配器的实现参考，当前离线运行时尚未实现媒体上传、真实预览、平台写入或在线诊断。使用操作卡前，应先完成相关业务上下文与能力发现；实现状态见 [路线图](roadmap.md)。

Pipeboard 是可以替换的 MCP 入口。操作卡使用平台原生的账户、媒体、创意、帖子、广告和报告标识；可由直连 API、其他 MCP 或有验证能力的后台操作适配。同一原生对象从两个入口读到时应合并为同一对象，不重新创建。

证据标记：**【官方·SDK】**只确认官方 SDK 暴露的字段、方法和类型，不保证特定账户全部可用；**【官方·产品文档】**支持所述广告产品范围内的行为；**【工程推导】**是建议实现的操作步骤与验收办法。下列“尝试、验收、止步”除另有标注外均属于工程推导。Meta SDK 来源统一固定到官方提交 [`5286888addfe3ba3718db65fbf132bd66de3ddfe`](https://github.com/facebook/facebook-python-business-sdk/commit/5286888addfe3ba3718db65fbf132bd66de3ddfe)（提交页日期 2026-09-04）；本文已核对下述方法和字段在该提交中存在，未核实的子模型能力单独收窄，不沿用浮动分支或另一个包版本的能力声明。生产适配仍需固定实际 API/SDK 版本并核验账户能力。部分 Meta Business Help 页跳转登录或返回 429，本文不据此推断学习阈值、日预算浮动百分比或完整宏清单。

| 工作阶段 | 对应操作卡 | Agent 交付给投放人员的东西 |
|---|---|---|
| 准备素材 | OP-01、02、04、13、14 | 可用媒体清单、重复/变体关系、版位预览、真实身份与授权状态 |
| 搭建广告 | OP-03、05、06、07、08、15、16 | 明确的对象关系、链接、预算/排期和可一次确认的批次差异 |
| 执行调整 | OP-09、12 | 与最新人工改动相容的操作清单、变更影响与观察窗 |
| 读数与测素材 | OP-10、11、12 | 口径一致的对象/素材事实表、成熟度与样本说明、下一步选项 |

授权执行以已确认的整批方案为边界。媒体准备、计划编译和预检可先完成；整批确认后，范围内的依赖创建、素材引用、读回与可恢复续跑不用逐条再问。某行出现新身份、额外预算、关键配置冲突或不同业务承诺，单独隔离该行，其余独立行继续完成。

## OP-01　上传视频后等待可用，再创建素材引用

**范围/证据：**Meta 账户视频上传，以上固定提交的可见结构。官方上传器将上传完成与等待编码分开，编码检查读取 `status.video_status`，`processing` 继续等待，`ready` 才返回就绪；默认调用并不自动等待编码。【官方·SDK】[VideoUploader](https://github.com/facebook/facebook-python-business-sdk/blob/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/video_uploader.py)

- **触发与读取：**上传新视频、恢复中断批次或广告创建提示媒体不可用时，读取本地文件字节数、时长、画幅、音轨、哈希；取上传会话、原生 `video_id`、`status` 及接口实际返回的处理进度/错误；未返回的细节保持未知。上传 ID 与广告 ID 分栏保存。
- **具体尝试：**先登记素材再上传，取得 ID 后进入 `processing` 队列；对已有 ID 轮询编码，其他已就绪素材先继续。发生上传超时先按会话/回执定位已上传资产；明确文件损坏或格式不合适时，保留原件并生成可播放派生文件，再走上传。只有编码超时且对象仍存在时，优先续等或诊断，不立刻再传同一文件。
- **验收：**就绪状态＋实际时长/缩略图/画幅相符＋目标账户可引用；再创建创意，并读回其 `video_id`。示例：12 条中 10 条 ready、2 条 processing，应交付“10 条可建、2 条待处理”，不是全批失败或宣布 12 条成功。
- **影响：**重传可能生成新媒体 ID；仅上传媒体且不变更投放对象，不会由该动作启用广告。但以非暂停状态创建广告，在父级、排期、审核等条件允许时可能开始消耗，不能等到另一条启用请求才计入执行影响。新媒体 ID 不代表新创意概念，也不能据此宣称保留旧帖互动；后续对象变更的预算、归因和学习影响分别核对。
- **止步：**明确处理失败、受支持规格不满足或目标账户不能引用时，阻断依赖该媒体的行；达到任务等待期限仍未 ready，保留可续跑状态。编码 ready 不代表审核通过。

## OP-02　把“完全重复”“版位适配”“创意变体”分开选材

**范围/证据：**Meta 图片/视频素材库；方法可复用至 TK/GG。官方图片模型具有账户、hash、尺寸及引用创意字段，创意模型分别引用 image hash/video ID；它们不是 Agent 本地文件哈希或创意概念 ID。【官方·SDK】[AdImage](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adimage.py)。

- **触发与读取：**用户说“选 10 条新素材”、一次上传多个目录或复用历史素材时，读原件哈希、文件名、时长、关键帧/OCR、语言、产品档位、历史概念 ID 及已有平台引用。
- **具体尝试：**字节相同归为完全重复；裁切/压缩/字幕安全区调整归入同概念的版位适配；换开头、叙事、人物或主张则记录为明确变体。自动准备代表文件和对比图，让投放人员看到“10 个文件实际为 6 个概念、2 个语言版本、2 个重复”，并给出可补的空缺，而不是用重复文件凑数。
- **验收：**每个候选都有 `concept_id → variant_id → rendition_id → native_media_id`；平台取回的内容对应正确版本，变体差异可看见，复用资产对目标账户有效。感知相似度用于候选聚类，不能自动删除或合并不同内容。
- **影响：**原生媒体、创意和广告 ID 分别追踪；重用同媒体不保证同 post/social proof。测试结果同时保留变体层与概念层，避免不同裁切被当作独立胜出证据。选材本身不改预算/归因，新增广告可能改变组合内分配与学习表现。
- **止步：**无法确认奖品/产品档位、使用权或变体差异时只列待核项；不能把“文件 hash 新”直接标为“从未测过的新创意”。被拒素材的受控重传与对象重建见 [Meta 素材恢复](meta-creative-recovery.md)。

## OP-03　复用已有 post 时，先保住正确帖子身份

**范围/证据：**Meta 支持的现有帖子/现有 Reel 广告。官方创意模型区分 `object_story_id`、`effective_object_story_id`、`effective_instagram_media_id` 与 `object_story_spec`；Meta Reels 产品页的官方索引正文说明可选择 Use existing post。【官方·SDK/产品索引】[AdCreative](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreative.py)、[Meta Reels ads](https://www.facebook.com/business/ads/facebook-instagram-reels-ads)。产品页直接访问受限，不能由此扩展出所有格式的复用保证。

- **触发与读取：**用户要求复制赢家、保留评论/点赞或用品牌/创作者原帖时，读取源 ad→creative→实际 Facebook post/IG media 的完整引用、Page/IG 身份、原帖正文/媒体、可用权限和原有链接。
- **具体尝试：**内容、身份和目标用途相容时，使用受支持的“已有帖子”方式构建新广告；不用下载同一视频再上传来冒充原帖复用。若只需保留媒体但必须换文案/身份，给出“新创意/新帖”的明确分支。先在草稿中验证能否引用原帖，避免创建后才发现选的是另一条同名帖子。
- **验收：**读回新的 `ad_id`、`creative_id` 和实际 post/media ID，核对预览显示的身份、正文与评论入口；分别验证 FB/IG，不承诺两边互动自动合并。预览不能看到互动时标记“帖子引用一致，互动展示尚未验证”。
- **影响：**新广告 ID 可以引用旧帖，但历史广告报表仍留在旧广告；同帖互动身份可以保持，具体展示由版位决定。不能据此宣称新 ad/ad set 继承旧对象的学习状态，应单独读取新对象。归因、预算和受众来自目标方案，不能从帖子一起默认复制。
- **止步：**权限、帖子格式、目的地或身份不兼容，或者用户同时要求改不可兼容的原帖内容与保留原互动时，展示真实取舍；不悄悄切到新帖并声称已保住 social proof。

## OP-04　按版位预览实际创意，并显式决定自动增强

**范围/证据：**Meta 当前支持的创意/版位。固定提交中的 `Ad.get_previews()` 接收 `ad_format`、`creative_feature` 等参数，`AdCreative` 模型包含 `degrees_of_freedom_spec`。【官方·SDK】[预览请求方法](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)、[创意字段](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreative.py)。本文的证据范围不包括该提交的 AdPreview 枚举与增强子模型正文，因此不把特定增强预览或文本/图片/视频变换子配置列为已证实能力；具体版位与增强开关按当前接口实际支持范围预检。

- **触发与读取：**横版素材投竖版、复制旧广告、使用 Advantage+ creative 或含价格/资格声明时，读取已选版位、各版位素材、crop、字幕/CTA、所有可读自动增强开关和实际身份。
- **具体尝试：**按当前入口支持的预计投放格式生成预览矩阵；例如支持时对同一视频的 Feed、Story、Reel 逐张检查，优先调整安全区、裁切、封面或替换对应版位派生素材。将“沿用原件、使用适配版、启用哪项增强”作为可审阅选择；精确素材实验可关闭会改变核心测试变量的功能，日常组合投放则使用已确认的增强配置，不一律全关。
- **验收：**检查金额、产品、字幕、必要条件、品牌和 CTA 是否完整可读；读回实际开关并保存代表预览与不支持预览的项。生成预览仅代表该样例，不声称穷尽个性化展示。
- **影响：**裁切/增强可能保持媒体引用但改变展示；若产生新创意/帖子要更新对应 ID 和互动关联。变化会影响“测的究竟是什么”；预算/归因不必改变，但不能把多种增强混合结果称为原素材单变量效果。
- **止步：**关键承诺被裁掉、自动生成内容改错产品事实或无法确认关键增强状态时，单独调整/替换素材或去掉不适配版位，并让方案显示相应覆盖变化。

## OP-05　链接和追踪参数在三层验证，避免同域名串 Offer

**范围/证据：**Meta Web 目的地与其他平台各自的 URL 能力。Meta SDK 暴露 `url_tags`、目的地及 deep link 等独立字段；这不能证明任意连接器支持所有动态宏。【官方·SDK】[创意 URL 字段](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcreative.py)。

- **触发与读取：**跨账户复制、换 Offer/国家、链接有多次跳转或加 UTM 时，读原始目的地、URL 参数模板、已有 query/fragment、跳转链、业务 Offer ID、App/Web 回退目标及 tracker 必需参数。
- **具体尝试：**先本地解析合并 query，保留必要参数并检查重复 key、二次转义和 `#` 位置；再做不会提交表单/转换的目的地核查；最后在受支持的预览或测试模式核验参数展开。未能核实某宏的入口，不复制另一平台语法；可使用已确认的静态非敏感 `batch_key/creative_key`，并在广告创建后将它们关联到原生 ID。
- **验收：**分别确认“保存的模板正确”“实际打开的目的地与 Offer 相符”“测试入口收到期望参数”。例如同一域名 `/offer/a` 与 `/offer/b` 必须分别映射，URL 可访问但参数丢失仍不算追踪通过。动态名称仅作可读辅助，稳定 ID/业务键负责关联。
- **影响：**改 URL/tag 是否需新创意或重审取决于原生操作；若重建便更新广告/帖子关系。参数能改善数据映射，不能改变平台归因窗口或证明真实转化回传。测试不应产生真实转化/消费；上线流量继续受原预算约束。
- **止步：**目的地不一致、关键参数被吞、宏原样落地、深链回退错误时，暂停相应行发布。无法模拟实际广告点击时，明确保留“模板已检、展开待验”，不伪装端到端验证。

## OP-06　按依赖创建并检查父级状态，解释“广告开了却没跑”

**范围/证据：**Meta campaign→ad set→ad。官方 `Ad` 将 configured/effective status 分开，effective 包括 `CAMPAIGN_PAUSED`、`ADSET_PAUSED`、`PENDING_REVIEW`、`PENDING_BILLING_INFO` 等。【官方·SDK】[Ad 状态](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)

- **触发与读取：**批量发布、复制、恢复中断或单条显示 ACTIVE 却无投放时，读三个层级的 ID/状态、开始结束时间、媒体 ready、审核反馈和 delivery issues。
- **具体尝试：**按依赖图准备对象：媒体→创意→广告，并确保目标 campaign/ad set 存在。批准后仅对计划中的父子对象变更状态；若父级故意保持暂停，则完成子级配置并解释阻塞。若流程要求先建齐并读回再启用，应显式以暂停状态创建或复制；若计划允许直接以非暂停状态创建，则创建本身就属于可能产生投放效果的执行动作。已有运行 campaign 中只加新 ad，不必把整个 campaign 重新开关一遍。
- **验收：**逐行检查父链和实际状态，区分“已建”“已启用”“审核中”“具备投放条件”“已观察到展示/消耗”。空系列、0 广告组、部分创建失败可直接定位到缺少哪条依赖，不用全批重做。
- **影响：**创建新对象形成新 ID，状态更新通常不需要新 ID；历史数据仍随原对象保留。开启父级可能让其他已 active 子级一起开始消耗，因此先列出其所有受影响子级。状态读回不能证明学习完成或未来投放；归因配置不会因 ACTIVE 自动统一。
- **止步：**启用父级会超出批准子对象范围、预算缺失或已过结束时间时，给出具体补救方案；不能为让一条广告跑起来擅自启用整账户旧广告。

## OP-07　复制广告时重新编译默认值，不照抄整个对象

**范围/证据：**Meta 支持的 copy 或重新创建路径。官方 `Ad.create_copy` 暴露目标 ad set、creative parameters、rename options 和 status option；status option 含沿用原状态或明确暂停/启用。【官方·SDK】[Ad copy](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)。目标、优化目标、目的地与 promoted object 是分层字段。【官方·SDK】[AdSet](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adset.py)

- **触发与读取：**“按这个再建一批”、跨账户/国家复制或旧模板升级时，读源对象的原生配置、父链、优化事件/价值目标、归因、预算归属、身份、自动化开关、URL 和 copy 支持能力。
- **具体尝试：**生成“继承/替换/重新验证”三列表：视觉与文案可继承；新国家/账户/链接按新需求替换；身份、事件和媒体权限重新验证。只编译允许创建/修改的字段，不把返回对象中的只读 ID、历史状态和推荐值全量发回。显式指定目标父级与新对象初始状态，避免 copy 默默继承源 ACTIVE。
- **验收：**比较规范化计划与新对象实际值，特别查优化目标、promoted object、SAC、归因、版位、增强及默认预算。字段缺省、`null`、清除值和显式 false 分开处理；连接器若不支持关键字段，应明确指出在哪个原生步骤补齐。
- **影响：**新广告/组/系列的 ID 和历史分别保存，不与原对象合并；帖子能否复用走 OP-03。改事件/目标使测试含义变化，新复制不继承旧学习结论。即使媒体完全相同，目标预算和归因也可能不同。
- **止步：**读回发现关键字段被默认覆盖，先修正受影响对象或切换已验证的原生入口；不得为“创建成功率”静默换优化目标、移除类别或选择连接器默认出价。

## OP-08　计算本批新增预算承诺，并核对预算究竟属于谁

**范围/证据：**Meta campaign/ad set 的日预算、总预算及受支持共享方式。固定提交的 Campaign 明确包含 `daily_budget`、`lifetime_budget`、`spend_cap`、`start_time`、`stop_time` 和 `is_adset_budget_sharing_enabled`；AdSet 另有自身预算和排期字段。共享字段位于 Campaign，不能由字段存在推断任意共享组合都可启用。【官方·SDK】[Campaign](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/campaign.py)、[AdSet](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adset.py)

- **触发与读取：**增加广告组、把 ABO 模板迁为 campaign budget、延长排期或多账户复制时，读预算 owner、日/总预算、币种/单位、共享关系、上限、当前正在运行的兄弟对象和排期。
- **具体尝试：**按唯一预算 owner 求和，分开显示“现有承诺、本批新增、替换后承诺”和新旧同时运行的重叠期。示例只是算术：两个独立组各 100/日为配置 200/日；一个 campaign 共用 100/日、下有两组，不算成 200，也不承诺每组分到 50。若总预算相同，可给人比较独立测试预算与共享分配的可观测性差异。
- **验收：**读回真实预算 owner、金额、币种、单位和排期，与批准的总承诺核对；重建时确认原预算对象是否仍 active。预算是配置约束，实际消耗按平台节奏另报；不能将日预算当绝对逐日消费保证。
- **影响：**单纯预算更新通常不创建新 ID/post，调整预算归属可能需要结构变更；预算/共享方式改变会影响各素材得到的量和学习环境，社交证明不会因此自动迁移。归因不应随预算编辑顺带改变。
- **止步：**未知单位、同币种尚未归一、预算共享关系不明或切换期间会额外花费且未在计划内时，给出精确差额与切换选择。保留已确认授权，只有实际超范围变更才需更新方案。

## OP-09　写入前处理人工并发改动，只跳过冲突部分

**范围/证据：**三平台通用执行层。Meta 暴露 `updated_time`、`last_updated_by_app_id` 等可读证据；它们不构成原子比较更新保证。【官方·SDK】[Ad 对象](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/ad.py)。以下冲突处理为【工程推导】，不声称 Meta 有通用 ETag/If-Match。

- **触发与读取：**方案等待确认、执行中断续跑、用户和 Agent 同时编辑时，保存计划基线 A、写前最新状态 B、目标 C；按字段和父链读取，不仅比较时间戳。
- **具体尝试：**若 A→B 仅改名称，而本次只改预算，则保留新名称、只发预算差异；若用户已经把计划中的 ACTIVE 改为 PAUSED，隔离这条并展示冲突；若目标值已由人设成 C，则标“已满足”，避免再写。只串行化同一共享预算/父级的相关操作，独立行继续执行。
- **验收：**写后读到 D，确认本次目标字段为 C，未涉及的人改字段仍为 B；当前对象、回执和活动记录对齐。不能靠 `updated_time` 没变证明绝无竞争：最后一读到写入之间仍有窗口，疑似竞争再次联核，结果保持 uncertain。
- **影响：**字段级 patch 尽量保留原 ID、帖子、预算和归因的无关部分；学习影响需结合本次变更、同时发生的人工/平台操作和实际状态观察，不能承诺无关字段不变就必然保留学习。自动“回滚整份旧对象”可能覆盖人工改动，应改为经过当前状态复核的补偿操作。
- **止步：**目标账户、素材、事件、身份、预算或状态发生实质冲突时暂停该依赖分支；不覆盖用户刚做的暂停，也不因为一条冲突让 30 条无关操作从头重做。

## OP-10　按真实账户时区排期与切日，不用设备日期代替

**范围/证据：**Meta 账户时区字段与 Insights 广告主/受众时区小时维度；跨平台报告各自保留原生时区。【官方·SDK】[AdAccount](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adaccount.py)、[AdsInsights](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adsinsights.py)

- **触发与读取：**用户说“明天零点上”“今天的数据”、跨时区复制或跨户日报时，读账户 IANA 时区、API 时间类型、计划开始结束值、业务报告时区和当前数据截止时间。
- **具体尝试：**将人的本地时间转换为明确的账户当地时间与 UTC 瞬间，两者一起展示。遇夏令时切换的重复/不存在时间先消歧。报表若要同一真实 24 小时，使用可用小时粒度重组；只有账户日汇总时，分别给本地日，不靠把日期改成同一天就强行相加。
- **验收：**读回开始/结束时间与预期 UTC 一致，检查复制是否沿用过去的结束时间。日报注明每个账户日的 UTC 边界、已覆盖小时与数据拉取时刻；小时明细必须确实返回小时维度。
- **影响：**排期编辑通常保持广告和帖子身份，但会改变实际曝光时长、预算可花时间及测试可比性；新组冷启动不能与全天老组直接排名。时区转换不改变平台归因配置，也不能修补回传延迟。
- **止步：**时间语义未知、DST 歧义或数据仅能提供不一致的日界线时，展示可行的分开报告/改排期选项；不要把设备当前时区写回账户设置。

## OP-11　归因设置、报告时间与数据成熟度一起读

**范围/证据：**Meta Insights。固定提交的 `AdSet.get_insights()` 声明 `action_attribution_windows`、`use_account_attribution_setting`、`use_unified_attribution_setting` 及 `action_report_time`，后者的枚举包含 impression/conversion；只证明接口模型有这些选择，具体优先级/支持组合需适配确认。【官方·SDK】[AdSet Insights](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adset.py)、[AdsInsights 时间枚举](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adsinsights.py)

- **触发与读取：**对比两个组、汇报今日 CPA、检查 tracker 对账或判断一次调整后果时，读对象归因配置、优化事件、报告请求实际参数、事件日期口径、时区、配置生效时间与回传/结算延迟。
- **具体尝试：**把原生配置与报告口径分别存下；支持统一查询时生成可比视图，不支持时分列。保存同一历史 cohort 多次提取的 as-of 快照，列出转化/收入后续增补，而不是无声覆盖。今日先输出“截至某时、尚待成熟”的描述性结果，成熟 cohort 再用于策略比较。
- **验收：**响应日期、层级、事件、分页完整；查询改变是否被支持有证据，而不只看请求参数；原始结果与标准化事实表可追溯。零转化 CPA 为 null 并注明原因，跨平台报告转化不直接求和为去重用户。
- **影响：**仅查询不改变对象 ID、学习、互动、投放预算或实际归因配置。为统一报表而修改广告组归因是另一项有实质影响的变更，不应混在读数任务中。报表数值改善不等于收入增加。
- **止步：**配置未知、查询被忽略、回传未成熟或价值事件无法解释时继续输出可靠的花费/展示等字段，但停止对受影响 CPA/ROAS 作确定性排名或停投建议。

## OP-12　把冷启动样本预算与编辑影响转成可观察计划

**范围/证据：**Meta 学习信息按对象实际可见字段读取。固定提交的学习结构确有 `status`、`conversions`、`last_sig_edit_ts`、`dynamic_lp_conversions_threshold`、`dynamic_lp_days_threshold`、`current_budget_prediction` 与 `recommended_budget_prediction`。这里仅确认字段及声明类型；预算预测的内部结构、金额单位、阈值适用性及账户是否返回均须另验，缺失值不能当零或反推已完成学习，也没有所有账户统一“改 20% 必重置”的保证。【官方·SDK】[学习信息模型](https://raw.githubusercontent.com/facebook/facebook-python-business-sdk/5286888addfe3ba3718db65fbf132bd66de3ddfe/facebook_business/adobjects/adcampaignlearningstageinfo.py)。早期学习需耐心和报告判断是官方培训主题，具体课程介绍未提供精确门槛。[Meta Blueprint](https://www.facebookblueprint.com/student/activity/718472-getting-started-with-your-first-ad-on-meta-technologies)

- **触发与读取：**新组没量、预算太小、频繁调价或要测新素材时，读实际学习状态、可得的重大编辑时间、已花费/事件数、事件成熟度、预算利用、投放资格和最近同时变化因素。
- **具体尝试：**先把目标事件、素材问题与可承受成本写清。可用“预期事件数×成本基线”估算试验资金，并给低/中/高基线情景；没有成本基线就做有上限的探索阶段，不伪造精确毕业预算。欠投先排查父级/媒体/审核/排期/限额，再把出价、事件质量或预算不足作为可比较的下一步选项。一次主要测试变量保持清楚，必要故障修复单独记时。
- **验收：**实际学习状态与编辑时间有记录；每次调整有前后配置、成熟观察窗和结果。固定预算并不保证平均分配给每条素材；没有获得足够曝光的素材标“未测充分”，不作差素材。评估获量、事件质量和成本，不只看是否显示毕业。
- **影响：**编辑或新建对学习的影响以当前对象与平台信号为准；新 ID 不继承旧组的证据。新素材若产生新帖需追踪互动身份；原有归因应保持可比。任何新增预算在计划里明示，不从模型预测自动追加。
- **止步：**达到已确认探索支出/时间边界但信息仍不足时，给人“继续、缩范围、补事件或停止”的具体选项。前后 CPA 变化不是预算/结构改动的因果证明，不将某次冷启动经验固化为三平台默认策略。

## OP-13　TikTok Spark：选原帖、对授权、再核对排期

**范围/证据：**现有帖子 Pull 路径；Spark 概述更新于 2026-06，Smart+ 创建帮助更新于 2025-10。官方说明广告互动归原帖，现有帖子标题沿原帖，授权后不可修改；授权码存在可选期限，必须核对实际授权结果。【官方·产品文档】[Spark 创建与授权](https://ads.tiktok.com/resources/help/article/how-to-create-spark-ads-for-smart-campaigns-on-tiktok-ads-manager?lang=en)、[Spark 概述](https://ads.tiktok.com/resources/help/article/spark-ads?lang=en)、[授权错误与排期](https://ads.tiktok.com/help/article/about-spark-ads-code-error-notifications-in-tiktok-ads-manager?lang=en)

- **触发与读取：**用户希望继续用创作者原帖、原帖互动或已经授权的 Spark 素材时，读发布账号、post ID、原帖标题/媒体、授权来源与实际到期、当前广告和拟定结束时间。业务档案只存授权引用与到期元数据，不存明文授权凭据。
- **具体尝试：**在已授权身份下选择正确原帖建立 Spark 广告，并把广告排期限定在可用授权范围；缺期限时先展示“需延长授权”或“缩短这批排期”的选择。若用户要求修改原帖标题，转入适用的新内容/新帖流程，而不是在 Pull 请求中塞入不同标题。Push 新建路径与 Pull 复用路径分别编译。
- **验收：**新广告引用的账号、post ID、标题、预览一致，授权覆盖计划排期；发布后读回广告/组状态。互动入口回到原帖，不把另一个同文案帖当作同一条。预览和当前授权通过后才称“可以发布”，尚未观察投放则单独记录。
- **影响：**新广告 ID 与原帖 ID 并存；可沿用原帖互动身份，不代表继承原广告的学习、报表和转化。预算和归因由目标广告组/活动决定；素材授权期限不是允许追加预算的授权。
- **止步：**原帖不可用、无权使用、授权覆盖不足或必须改标题但又要求原帖身份不变时，隔离该素材给出实际选项；不自动替用户发新帖子或重新发起授权。

## OP-14　TikTok：按投放产品验视频规格，不能用一张通用表

**范围/证据：**2026-06 的 TikTok Auction In-Feed **Non-Spark** 文档列：竖版至少 540×960、横版至少 960×540、方版至少 640×640，文件不超过 500 MB、码率至少 516 kbps、最长 10 分钟。Global App Bundle 则有不同的时长范围；不能互用。【官方·产品文档】[In-Feed 规格](https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en)、[Global App Bundle](https://ads.tiktok.com/resources/help/article/global-app-bundle-video-ad-specifications?lang=en)

- **触发与读取：**素材无法选择、广告预览异常或跨产品复制时，先确认是 In-Feed Non-Spark、Spark、Global App Bundle 还是其他产品，再读视频封装、分辨率、方向、时长、码率、字幕安全区、封面及上传入口权限。
- **具体尝试：**对明确不适配的文件生成派生版本：合理裁切/补边、符合规格的转码、选封面与调整字幕区域；保留原件及适配目的。素材进入库后先打开详情、完整播放和目标版位预览，再在广告中选择相应媒体。不要为了满足推荐风格把所有长视频默认截到 60 秒。
- **验收：**本地规格→素材详情→目标广告预览三者相符；媒体可用于目标广告产品且绑定的是该派生版本。素材库“已上传”不单独证明已处理完成或可投放。[素材库上传/预览](https://ads.tiktok.com/resources/help/article/how-to-upload-creatives-to-creative-library?lang=en)、[广告预览与检查](https://ads.tiktok.com/resources/help/article/ad-set-up?lang=en)
- **影响：**派生视频可能生成新媒体 ID；Non-Spark 入库不会生成 Spark 原帖互动。单纯媒体入库不启用广告；若以非暂停状态创建广告，在其余投放条件允许时可能开始消耗，创建动作就须计入授权与执行影响；学习与归因不从素材规格推断，按目标对象读回。
- **止步：**处理失败或必要信息被裁掉时阻断该素材。官方 Spark 概述与 In-Feed 页对 Pull 时长存在“10 分钟/无限制”的差异，本文保留该冲突；目标为 Spark 时读取当前产品界面/接口校验，不把本卡 Non-Spark 上限硬套过去。

## OP-15　Google RSA：把素材池编成不会互相矛盾的组合

**范围/证据：**Responsive Search Ads，官方帮助页按 2026-09-24 核查版本。需 3–15 条标题和 2–4 条描述，上限分别为 30/90 字符；中文等双宽字符按 2 计。固定位置会限制组合，预览不显示全部可能排列。【官方·产品文档】[RSA 资产与固定位置](https://support.google.com/google-ads/answer/7684791?hl=en)

- **触发与读取：**新建搜索广告、批量上传标题/描述、补充必显说明或修改 RSA 时，读全部资产、固定位置、最终 URL、现有版本、当前审核与预览。将产品/国家/价格档位分开，避免跨 Offer 自动混搭。 在适用 Enhanced Flexibility 的 RSA 中，同组另一广告未使用的标题/描述可作为链接类资产展示并指向被借用 RSA 的 final URL，因此组合一致性检查还须覆盖同组其他可参与资产及目的地，尤其避免不同 Offer/档位混组；该能力只适用于 active 广告和资产，敏感垂类不适用资产共享。[官方 Enhanced Flexibility](https://support.google.com/google-ads/answer/7684791?hl=en)
- **具体尝试：**自动检查字符计数、重复、语法衔接和承诺冲突；生成差异明确且可以任意组合的文案。业务要求始终出现的说明优先安排到适合的固定位置，例如 Description 1；不能靠 Headline 3 或 Description 2 必定展示。给出“更多组合自由”和“固定必要说明”的实际取舍，而不是只追求资产数量或界面评分。
- **验收：**读回文本与 pinned field；对可生成的代表组合检查产品、价格、期限和指代一致性，确认核心意思不依赖一条可能不显示的资产。保存广告 ID、版本及审核状态；编辑保存产生版本历史，不把已保存等于可投放。[版本历史](https://support.google.com/google-ads/answer/7502216?hl=en)
- **影响：**广告资源与版本需分别追踪，不把文案改动看成文件改名。组合空间会变化，学习/效果不保证继承或一定重置；RSA 不存在与 Meta post 相同的社交证明迁移逻辑。本卡只改批准的文案/固定位置，预算、归因和 URL 独立保留。
- **止步：**任一合理组合产生不同产品承诺、必要说明缺失或超字符限制时，先改资产/固定方案；不为通过数量检查填入同义重复或未经确认的优惠事实。

## OP-16　Google ValueTrack：先解出实际生效模板，再查并行追踪

**范围/证据：**Google Ads 搜索广告，官方帮助页按 2026-09-24 核查版本。追踪模板按更具体层级覆盖；搜索广告使用并行追踪，用户可直达最终 URL，测量请求走后台。模板/重定向须满足对应 HTTPS 与服务器跳转要求。【官方·产品文档】[追踪与层级覆盖](https://support.google.com/google-ads/answer/6076199?hl=en)、[ValueTrack 配置](https://support.google.com/google-ads/answer/6305348?hl=en)

- **触发与读取：**落地页能打开但 tracker 少点击、参数为空、广告改模板无效果时，读关键词、广告、组、系列、账户层的模板和覆盖来源、final URL、final URL suffix、自定义参数、供应商对并行追踪的支持。
- **具体尝试：**先展示“本广告实际生效的是哪一层”，再在获批层级修正 `{lpurl}`、转义与适用参数；保留 URL 后缀功能的职责，不把全部参数机械拼成多重嵌套。用平台 Test 检查解析，再结合合法测试流量的落地参数及测量端回执；不要只用浏览器地址栏是否经过 tracker 判断并行追踪是否工作。[Test 能检查什么](https://support.google.com/google-ads/answer/6328603?hl=en)
- **验收：**保存后读回准确层级和值，目标页面匹配，测量端收到预期标识；Test 通过仍要记录其未覆盖的并行追踪问题。64 位 ValueTrack ID 按字符串保存，避免 JavaScript 数值精度截断。[ValueTrack 概述](https://support.google.com/google-ads/answer/2375447?hl=en)
- **影响：**本卡优先更新支持的追踪配置，不为修 URL 自动重建整套广告。广告/关键词层追踪改动可能触发审核，实际第三方归因可能变化；预算与出价保持原范围。官方说明变更传播可能需 24–48 小时，应记录改动时间，不能立刻重复覆盖来“催生效”。
- **止步：**模板供应商不支持所需并行路径、域名不匹配、测试回执缺失或平台 Test 异常时，不扩大应用到全部系列；先修正在测层级。涉及跟踪服务切换、额外账号访问或费用时，作为新的具体变更呈现。

## 实现时的最小连接器能力映射

以下是产品内部能力名，不是已存在的运行时函数。一个可替换 MCP 只要能给出同等可核验输入/输出即可，不要求复刻 Pipeboard 的工具名。

| 内部能力 | 至少需要返回什么 | 缺能力时仍能继续什么 |
|---|---|---|
| `inspect_media / upload_media / get_media_state` | 账户作用域、原生媒体 ID、处理状态、文件/派生关系、结构化错误 | 本地规格和选材整理；未就绪媒体行暂不发布 |
| `resolve_creative_and_post` | 创意 ID、真实 post/media 引用、身份、文案、目的地、可用权限 | 预览候选；不能声称互动保留 |
| `preview_by_placement` | 目标格式、使用的素材、可见内容与可读增强配置 | 生成适配素材；未验证项在批次里具体列出 |
| `get_entity / patch_entity / create_or_copy_entity` | 类型化原生 ID、父链、实际配置、逐对象结果和不确定状态 | 编译计划与差异；换成另一个已验证入口完成同一原生对象操作 |
| `read_budget_and_schedule` | 预算 owner、金额单位/币种、共享关系、时间语义 | 输出金额/排期缺口；不猜单位写入 |
| `read_report_with_contract` | 实际账户/对象覆盖、时区、日期、粒度、事件/归因、提取时间和分页 | 输出可靠子集，并把不成熟/不可比较项分开 |

最先落地的闭环可以很具体：用户给一批素材并指定既有账户/产品 → Agent 去重和适配 → 等媒体 ready → 编译源帖子/新创意分支及链接、预算、排期 → 按版位出预览和整批差异 → 一次确认后创建并读回 → 输出“可投放、待处理、冲突”逐行结果 → 用同口径成熟数据供人判断下一轮。素材恢复和拒审处置接入[Meta 素材恢复流程](meta-creative-recovery.md)，不由本手册推断文件变化与审核结果的因果。

**实现与证据边界：**这些操作步骤需要生产适配器实现和账户范围内的能力验证。官方字段存在不代表当前账户可写；预览、媒体 ready、审核通过和实际投放是不同验收状态。连接器字段契约见 [connector-contract.json](../contracts/connector-contract.json)，素材恢复动作见 [creative-recovery.json](../contracts/creative-recovery.json)，未来验收用例见 [acceptance-scenarios.json](../contracts/acceptance-scenarios.json)。这些契约与操作卡不会被离线运行时自动加载或启用。

返回 [文档索引](index.md)。
