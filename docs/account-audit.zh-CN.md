# 账户审计：在一轮判定之前、任何写入之前做的检查

[English](account-audit.md) · [建单质检](build-qa.zh-CN.md) · [案例](case-studies.zh-CN.md) · [实际是怎么跑的](how-it-ran.zh-CN.md)

2026 年 9 月 27 日至 10 月 29 日，我继续用 WorkBuddy（腾讯的桌面 AI Agent；本项目与其无关联）操作 Meta 与 TikTok 线索投放账户。10 月的事故和 9 月不一样。9 月的问题出在建单过程中：重试的批次、没有批准的激活、照抄方案的回执。10 月的问题出在已经在跑的账户上：预算写错了单位，名称不再描述广告组实际在做什么，外部工具在两轮之间改预算，“满一天”按错了午夜。

[`account_audit.py`](../account_audit.py) 是这些事故在私有实盘巡检里新增检查的离线、带测试版本。它读取一份已保存的账户读数、变更流水和本轮准备发送的写入请求，不调用任何平台。样例数据均为虚构。

## 在流程中的位置

| 时机 | 模块 | 回答的问题 |
|---|---|---|
| 建单之前 | [`preflight.py`](../preflight.py) | 清单是否自相矛盾、是否违背平台规则？ |
| 以暂停状态创建之后 | [`readback.py`](../readback.py) | 平台存下的是不是方案要求的？ |
| 每轮开始、任何写入之前 | `account_audit.py` | 这份读数能不能拿来判定？每个写入请求能不能发？ |
| 每次写入之前 | [`operating_rules.py`](../operating_rules.py) 中的 `gate()` | 字段是否仍等于提出方案时的基线？ |

审计放行的请求仍要经过写前闸门，并且只能进入用户批准的批次（[AGENTS.md](../AGENTS.md) R1、R2）。“放行”只表示通过了这些检查。

## 为什么要有这些检查

| 日期（2026） | 实盘上发生了什么 | 现在的检查做什么 | 案例 |
|---|---|---|---|
| 10-25 | 另一条工作流把按美分算的预算写进了以美元计的连接器字段；三个广告组以 20–200 倍预算跑了约 1.6 小时 | 没有显式单位的金额拒绝；加到硬上限及以上拒绝；超过加价倍数必须写明理由；回滚失控预算从不等待；每轮先跑预算哨兵 | [WB-11](case-studies.zh-CN.md#wb-11) |
| 10-24 至 10-27 | 名称写的是一个 offer，落地链接却是另一个（一个账户当天 91% 的花费）；名称里的预算与字段相差 30 倍 | offer 以落地链接为准，不看名称；名称里的预算与字段对照 | [WB-12](case-studies.zh-CN.md#wb-12) |
| 10-24 至 10-29 | 预算在两轮之间反复被改，10 月 27 日起来自一个不在我名单里的应用（48 小时 22 次，单个广告组净变化 −95% 到 +900%）；没有广告组能在同一档预算上满一天，12 小时巡检连续 8 轮零晋级 | 流水里每次变更都归到写入方；外部写入方报 P1，它写的值不作为本轮基线 | [WB-13](case-studies.zh-CN.md#wb-13) |
| 10-25 至 10-26 | 昨天下午生效的预算被算作满一天；账户时区变成 UTC−1 之后，日界仍写死为 UTC+0 | 满一天要求预算不晚于前一天 00:00（账户时区，按名称）生效；流水回溯不够远时给出“未知” | [WB-14](case-studies.zh-CN.md#wb-14) |
| 10-02、10-25 | 广告全部停了的广告组仍被算作在投、算作产能 | 在投要求账户、campaign、广告组和至少一条广告同时开启；开启但没有开启广告的广告组是空壳 | [WB-15](case-studies.zh-CN.md#wb-15) |
| 10-07、10-12、10-21 | 给已有广告组换 pixel 被拒；给已有 campaign 补类别后广告错误清不掉；只传一个字段的定向更新会替换其余定向 | 创建时固定的字段拒绝写入（改为新建对象）；整体替换的字段必须带上现有全部键 | [WB-16](case-studies.zh-CN.md#wb-16) |
| 10-28 | 一个暂停批次与同账户在投广告组同 offer、同素材；原样激活会让账户日预算变成约 2.5 倍 | 暂停广告组与在投广告组同 offer、同素材时报警，并给出预算变化 | [WB-17](case-studies.zh-CN.md#wb-17) |
| 10-21 | 傍晚把预算降到低于已花金额，广告组当天剩余时段停投 | 降到不高于今日已花时等到账户次日 | [WB-20](case-studies.zh-CN.md#wb-20) |
| 10-10 | 用户手动暂停的 campaign 在一句笼统的“上线”指令下被恢复 | 拒绝恢复人工暂停的对象 | [WB-21](case-studies.zh-CN.md#wb-21) |
| 10-21 至 10-27 | 向停用账户写入失败 | 发往停用账户的请求进入等待；账户报 P0 | [WB-22](case-studies.zh-CN.md#wb-22) |

## 检查什么

### 账户上的发现

| 代码 | 级别 | 触发条件 | 怎么处理 |
|---|---|---|---|
| `ACCOUNT_DISABLED` | P0 | 账户状态不是开启 | 不发送任何写入；恢复后先重新读取状态 |
| `BUDGET_CANARY` | P0 | 开启或暂停的广告组日预算达到或超过 P0 线 | 本轮做任何事之前先确认单位和意图 |
| `BUDGET_NO_SPEND` | P1 | 在投广告组预算高于 P1 线，最近几个完整日花费为零 | 先查投放，再把预算当作产能 |
| `BUDGET_FAR_ABOVE_SPEND` | P1 | 在投广告组预算超过最近平均花费的规则倍数 | 确认预算是否有意为之；大幅加价也会让满一天重新计算 |
| `OFFER_LINK_MISMATCH` | P1 | 名称里的 offer 与落地链接里的不一致 | 按链接对应 offer 的 T 判定；修正名称或链接 |
| `EXTERNAL_WRITER` | P1 | 窗口内有不在本人名单里的写入方改过对象 | 不把它写的值当作基线；是否保留它的写权限由用户决定 |
| `DUPLICATE_ACTIVATION` | P1 | 暂停的广告组激活后会与同账户在投广告组跑同一 offer、同一素材 | 激活前删掉重复项或暂停在投副本 |
| `SHELL_ADSET` | P2 | 开启的广告组下没有开启的广告 | 不算在投；它的预算不是投放产能 |
| `NAME_BUDGET_STALE` | P2 | 名称里的预算与字段不一致 | 以字段为准；改名 |
| `OFFER_LINK_UNREADABLE` | P2 | 任何落地链接里都没有 offer 代码 | offer 未经核实 |
| `OFFER_NOT_DECLARED` | P2 | 名称里没有写 offer | 补上，或不纳入按 offer 的报表 |

报告还会列出窗口内谁改了什么及每个对象的预算净变化，以及每个在投广告组的预算档：当前预算按账户时间何时生效、是否已满一天（是、否或未知）。变更流水回溯不够远，或流水最后的值与预算字段不一致（说明有未记录的改动）时，答案是“未知”。

### 写入请求的结论

| 代码 | 结论 | 条件 |
|---|---|---|
| `UNIT_MISSING` | 拒绝 | 金额没有写 `minor` 或 `major` 单位 |
| `UNIT_INVALID` | 拒绝 | 不是整数个最小单位 |
| `ABOVE_CEILING` | 拒绝 | 加预算，加到达到或超过硬上限；不接受覆盖 |
| `RAISE_TOO_LARGE` | 拒绝 | 加价超过倍数且没有写理由 |
| `RAISE_OVERRIDE` | 放行 | 加价超过倍数但写明了理由，报告里显示理由 |
| `RUNAWAY_CUT` | 放行 | 从达到或超过硬上限、或 P0 线的预算往下降；从不等到次日 |
| `INTRADAY_CUT` | 等待 | 其他降到不高于今日已花的降幅；等到账户次日 |
| `SPEND_UNKNOWN` | 等待 | 降预算但读数里没有今日已花；先读取 |
| `LOCKED_FIELD` | 拒绝 | 平台在创建时固定该字段；改为新建对象 |
| `PARTIAL_REPLACE` | 拒绝 | 平台整体替换该字段，这个值会清掉现有的键 |
| `CURRENT_UNKNOWN` | 拒绝 | 读数里没有当前值：整体替换字段，或者对象的预算没有被读取 |
| `RESUME_HUMAN_PAUSE` | 拒绝 | 对象是人手动暂停的；是否恢复由用户决定（[AGENTS.md](../AGENTS.md) R5） |
| `PAUSE_UNATTRIBUTED` | 等待 | 对象处于暂停，但流水看不出是用户暂停的（没有记录，或来自外部写入方）；先问用户 |
| `ACCOUNT_DISABLED` | 等待 | 账户已停用 |
| `UNKNOWN_OBJECT` | 拒绝 | 读数里没有这个对象 |
| `INVALID_REQUEST` | 拒绝 | 请求本身格式有误（例如值的类型不对）；审计其余部分照常运行 |
| `ACCOUNT_MISMATCH` | 拒绝 | 请求写的账户与对象所属账户不一致 |
| `BUDGET_OK`、`OK`、`NO_RULE` | 放行 | 通过，或没有适用的审计规则；写前闸门照常适用 |

## 输入

**快照**（[`examples/audit/snapshot.json`](../examples/audit/snapshot.json)）：带 UTC 偏移的读取时间 `as_of`、币种，以及每个账户的状态、IANA 时区名 `timezone_name` 和变更流水起点 `activity_since`；campaign 与广告组的状态、`created_at`、`daily_budget_minor`、按账户当地日的花费和今日已花；广告的状态、`creative_fingerprint` 和 `destination_url`。`activity` 是变更流水：时间、账户、对象、写入方（平台报告的应用名）、事件以及修改前后的值。`write_requests` 是本轮准备发送的写入。

**规则**（[`examples/audit/policy.json`](../examples/audit/policy.json)）：哨兵线与倍数，写入硬上限与加价倍数，从链接和名称里找 offer 代码的正则，本人的写入方及其身份（手动或 Agent）与时间窗口，以及各平台的金额字段、创建时固定的字段和整体替换的字段。字段清单来自实盘观察，并注明观察日期；请对照你所用 API 版本的平台文档重新核实。

金额按最小单位读取，币种的小数位来自规则文件；不认识的币种、规则文件里没有字段规则的平台，都直接拒绝。`accounts` 为空时按读取失败拒绝，不报告为一切正常。某天没有花费读数时跳过花费检查，花费占比记为“未知”，不按零计算。硬上限和加价倍数适用于 `budget_writes.fields` 里列出的金额字段，作用于广告组以及读数里带预算的广告系列；其他金额字段只检查单位。

## 运行

```bash
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json \
    --check examples/audit/expected/audit.md
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json \
    --lang zh-CN --check examples/audit/expected/audit.zh-CN.md
python3 -m unittest tests.test_account_audit -v
```

`--json` 打印结果，`--report` 写出 Markdown，`--strict` 在有 P0 发现时以退出码 3 结束。样例报告见 [`examples/audit/expected/audit.zh-CN.md`](../examples/audit/expected/audit.zh-CN.md)：P0 2 条、P1 5 条、P2 3 条；12 个写入请求中放行 4 个、拒绝 6 个、等待 2 个。

## 局限

- 它读取已保存的文件，不会自己拉取变更流水，所以写入方归因只和你保存的流水一样完整；平台保留的历史有限，而且按平台自己的日界过滤。
- 它能点名外部写入方，但拦不住它。10 月的解决办法在用户手里：收回那个应用的写权限。
- 哨兵线、硬上限和加价倍数是本项目的约定，不是平台规则。倍数 2.0 刚好放行一步阶梯。降预算从不被拒绝，最多是等待。
- 它只检查交给它的请求。通过其他途径发出的写入不在它的范围内，所以每次写入前仍要重新读取状态并经过写前闸门。
- “放行”不是批准；审计干净也不代表投放效果好。
