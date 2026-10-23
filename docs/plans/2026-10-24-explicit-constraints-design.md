# 显式适用约束的交付、版本追溯与变更影响：技术设计

日期：2026-10-24（Asia/Shanghai）。状态：设计候选，等待用户本人确认配套实现计划。

本文件不授予实施、知识认可、策略激活或风险放宽权限。未加 `change:`/`stage:` 标记，避免被观察器解释为已提交计划。确认后在新的 Change 中正式采用两份文档，再走仓库认可流程。产品基石是 [product-architecture.md](../product-architecture.md)，本文不得改写它。

## 1. 现场与证据

当前目录 `E:/Work/keepsail`；本轮核实本地 main、HEAD、远端 main 均为 `bdf3aad6ae86249b9df15b893c7a4266ded3d32c`（远端用 `git ls-remote`）。`.venv/Scripts/python.exe -X utf8 -B` 的 keepsail 与 keepsail.cli 导入路径均在当前 `src/keepsail`。原有未跟踪 `.superpowers/`、`docs/research/` 保留。当前 status 返回历史 `2026-09-15-plan-authority-alignment / READY_TO_MERGE`；不复用或重开它。status 同时警告三条历史 `l1_update_completed` 未识别事件，本轮不修复或重写。

已读取根 AGENTS、规范架构、旧 coverage 和以下研究原件：

- [比较报告](../research/2026-10-24-keepsail-related-projects.md)、[当前实现证据](../research/2026-10-24-keepsail-current-evidence.md)。
- [一手证据](../research/2026-10-24-related-projects-primary-evidence.md)、[其他项目证据](../research/2026-10-24-related-projects-secondary-evidence.md)、[原始出处](../research/2026-10-24-related-projects-provenance.md)。

源码核实：`core/approval.py` 提供规范 JSON、digest、冻结 plan/code subject 和证据校验；`core/writer.py` 在文件锁内验证再追加，提供 emit_many；`core/reducer.py` 派生 Change 状态；`cli/change.py` resume 目前仅状态、近期事件、scope、空 pending_sensors；`core/decisions.py` 的状态/检查层级尚无独立通用知识权威；`core/state_snapshot.py` 的损坏降级不能作为新知识路径的故障语义。`.harness/review-recognition.yaml` 仅认可 plan/code，不授权知识认可或影响裁定。

旧 coverage 的 233 项和研究的 113 项通过记录都是历史证据。本轮未运行这些回归，不宣称本设计或完整 C1–C6 已实现。

## 2. 切片与验收

首个交付面为本地单仓库 CLI，延续最近 `.harness` 的 workspace 解析。产品身份不从目录名推导。示例里的 PostgreSQL 是测试产品的真实语义约束，不是将 Keepsail 存储迁移到 PostgreSQL。

主线：有权过程认可 `database-choice` v1「持久化统一 PostgreSQL」为 constraint → 全局或明确规则匹配 Change A → CLI 持久保存并输出 v1 正文与来源 → 另一进程恢复 → 认可 v2「业务持久化 PostgreSQL，特定测试场景允许例外」及替代关系 → A 的 v1 供应记录不变，出现待处理影响 → 有权过程裁定继续/调整/重审 → 记录实际处理及证据 → 新进程恢复全部关系。

| 场景 ID | 可观察验收 |
|---|---|
| S1 正常链 | 约束无 executable check 也以 constraint 交付；每步有 ID、版本摘要、来源；v2 不覆盖 A 的 v1 正文；影响处理可从日志重建。 |
| S2 未匹配 | 非全局规则明确不匹配 A，输出 evaluated/non_matching 和输入摘要；不交付该项；未知语义相关性显示未评估，不宣称无相关知识。空匹配集也是完整的有限规则求值结果。 |
| S3 无结论/失败 | 空结论、失败、skip、未认可 issuer、错误 policy digest、错对象不可产生有效知识/适用或批准；无写入。已执行失败过程可保留 observation，仍不能认可。 |
| S4 争议 | agent 挑战 v1 并说明依赖动作；v1 仍有效。声明依赖该约束的动作等待裁定；明确独立动作仍可进行。缺少动作依赖信息不伪造独立性。 |
| S5 损坏/冲突 | 重复 JSON key、坏摘要、缺失版本/证据、截断新协议事件、同 ID 不同正文、过期 expected revision、不同请求复用 operation ID 被拒绝；不退化为空知识/成功。旧无知识数据与已启用后数据丢失不同。 |
| S6 跨会话 | 新进程只读持久产物，恢复 effective approval 引用、实际供应 v1、当前 v2、未决 challenge/impact、执行状态及缺失获取观测；不依赖聊天和最近 20 条事件。 |
| S7 权限边界 | 普通知识认可不能放松 A 的承诺或风险边界；判为需新批准时，原 approval 保留历史但受影响动作/完成等待新批准。文件增补且承诺未变沿用现有 assessment。 |
| S8 时序与并发 | 两进程同时替代 v1 仅一个成功；重复相同 operation 返回同一收据；交付后 stdout 管道失败保留 prepared 记录，不能写成已读；v2 与交付/关闭并发时旧 basis 不能完成。 |
| S9 新规则与实际覆盖 | 新增全局/规则扩大或 A 的实际文件变化触发重新求值；不能只检索旧 delivery 关系；规则缩小产生撤销/不再适用裁定需求，不删除旧关联。 |
| S10 完成与重审 | pending impact、未完成 adjustment、required check failed/unchecked/no-conclusion 不可宣称闭环。旧 code review/verification 不能覆盖调整后的代码。 |

## 3. 领域词汇与记录

本文候选词汇不另建全局 CONTEXT；正式采用后只在项目需要时提取纯领域术语，避免候选设计成为第二套产品定义。

| 对象 | 稳定身份、必需内容与关系 |
|---|---|
| ProductBinding | owner 设定的 product_id、repository_id 和 schema version；本切片一个绑定对应本地事件账本。身份跨路径稳定，不证明已支持跨仓库共享。 |
| KnowledgeVersion | `(product_id, knowledge_id, version_digest)`；schema、全文、理由、来源引用/保留内容、显式 selector、拟议 authority、previous_version；正文和规范字段 canonical JSON SHA256。v1/v2 只是显示标签，不能用作身份。 |
| Recognition | evidence_id、精确 KnowledgeVersion subject、decision（recognize/reject）、获授 authority（guidance/constraint）、process id/version、issuer、policy_digest、原始结论和 provenance。candidate 的拟议 authority 不生效。 |
| KnowledgeState | 从事件派生 candidate/effective/superseded/retired；challenge 单独保存未决状态并显示 challenged，仍保留原有效权威，不能把 challenged 当自动失效。状态、适用性、权威分别表达。 |
| ApplicabilityBasis | product/repository/change identity、显式规则及规则 digest、有限求值输入、关系来源（global/rule/recognized-judgment）、版本引用；机器匹配只执行已认可 selector。recognized judgment 对例外/撤销有明确目标和权限。 |
| Delivery | delivery_id、operation_id、Change、完整有限约束集及正文版本、basis_digest、policy_digest、账本 revision、发起者/时间、目标 session（可缺省）；保存当时全部依据。 |
| Observation / Statement | 获取 observation 的 producer、delivery/version、操作返回内容摘要/原始 receipt；agent statement 的 adopt/reject/challenge、理由和依赖动作。二者分开；CLI 自报 received 只能是 statement。 |
| Impact | impact_id = 旧关系 + 新版本/状态事件身份；关联 Change、旧供应/适用版本、新版本、触发理由、当前 approval_id/plan subject、pending/decided/executing/resolved 和精确裁定引用。 |
| Disposition / Execution | recognized disposition 为 continue/adjust/reapprove/not_applicable，绑定 impact 和期望 basis；execution 记录所做动作、当前 code subject、assessment、checks/review/new approval 引用与结果。自报完成与验证完成不同。 |

关联必须使用 ID 和 digest，不能只保存可变文件路径。保留原始证据正文或字节内容及摘要；URI 是来源补充，不能代替需保留的原件。禁止把 secret 或任意绝对路径文件自动打包；只接收显式输入，限制路径到 workspace，拒绝穿越和逃逸 symlink。内容作为数据，不执行知识正文中的命令。

每个变更命令输入 `schema_version`、`operation_id`、`expected_revision`；相同 operation+相同规范请求幂等返回，异文冲突。先识别已完成 operation，再校验新操作的 expected revision，保证重试不会被自身的追加误拒绝。revision 使用完整事件账本已验证前缀的摘要，而不是时间戳；basis_digest 只涵盖相关知识/规则/策略、Change 输入、批准和未决影响，排除纯交付/读取 telemetry，避免每条 observation 都使原依据失效。版本内容不可覆盖；状态变化追加事件。保留原始字节摘要和规范 subject 摘要，两者用途不同。

## 4. 权威与状态转换

1. propose 创建 candidate 快照，不赋权，不变更批准。新版本必须引用当前前驱；同时认可一个替代事件，将前驱标记 superseded，原版本仍可查询。
2. import recognition 只认可 owner policy 已列出的过程、kind、issuer、对象、原件、结论；reject 保留结论但不激活 candidate。retire 也需认可结论和精确对象。状态变更与影响触发位于同一事件中，影响列表由 fold 派生，避免跨多个事件的半完成更新。
3. selector 支持 `global: true`，或明确 `repository_ids`、`change_ids`、`paths`。维度间 AND、维度内 OR；global 与其他维度互斥。paths 采用现有 `covered_by_scope` 的 segment-aware prefix 语义（文件自身或目录后代），严格 POSIX 相对路径，不引入 glob/正则；`src/db` 不匹配 `src/db2`。这只是适用集合选择，不复用它作为 attestation 的精确授权覆盖判断。未知语法拒绝；空 selector 拒绝。缺少匹配必需字段产生 unknown，不当作不匹配。
4. paths 对计划 scope 与实际 coverage/当前代码 manifest 的并集求值，并记录来源。初始 scope 是估计，不把它当授权边界；后续文件增补重新求值，不因此自动撤销批准。
5. 显式匹配产生应供应集，recognized applicability judgment 可以追加语义关联；排除有效 constraint 或放松已认可 selector 需要该 kind 的权限，若涉及承诺/风险放松仍须人类授权。agent 普通声明不能覆盖匹配结果。
6. deliver 在锁内核实版本、策略和 Change basis 后持久化 prepared Delivery，再输出正文。成功写 stdout 最多增加 emitted 观测；崩溃、管道断裂或 emitted 事件写失败留下 prepared/unknown。stdout 交付不等于接收者读取，emit 成功也不等于理解。resume/show 是纯读，不暗中创建交付记录；需要新交付时给出 deliver 提示。
7. record 可以追加 agent 声明、challenge、带来源的 acquisition receipt 和执行报告；只按类型标识事实。用户没有提供可观察获取接口时，acquisition 为 not_observed，不补成 received。
8. 认可新版本、退休、selector/authority 改变，暴露已记录关系上的 impact；check/deliver/恢复还对当前有限规则和 Change 输入重新求值，补显新的全局/显式关系。只描述已记录关联和显式规则覆盖，不能称完整语义影响分析。
9. pending impact 不推导所有 approval 作废，也不推导自动继续。依赖争议动作先等裁定；不依赖它的工作保留授权。continue 必须明确针对 A 继续用 v1 还是切至 v2；adjust 必须列处理义务；reapprove 保留原批准并走现有新 plan candidate；not_applicable 必须有权裁定，不能只写 agent 不采纳。
10. import disposition 不等于执行成功。continue/not_applicable 的纯记录处理可验证绑定后完成；adjust 只有实际 assessment、精确 code subject、要求的 check 结果和 review 齐备才 resolved；reapprove 还需对应新 approval。绑定失效、执行失败/no-conclusion 留在未完成状态。检查输入变化后重新计算 basis，旧裁定不能覆盖新的影响。

人的责任：设 policy、批准目标/基础/权威/风险变化、本次实现计划确认。认可过程的责任：常规知识/适用/影响语义判断。Keepsail 的责任：检验授权范围和对象引用，记录并应用明确结论；不替过程理解“这是风险变化吗”。证据须明确 `authorization_effect: unchanged|requires-human-authorization`，涉及权限扩大时必须引用 owner 授权；无法确认时不得用 unchanged 默认值通行。无法机械证明语义分类正确的限制必须披露。

## 5. 持久化与模块

沿用 `.harness/events.jsonl` 作为唯一事实源，不引入数据库、知识 daemon 或第二权威存储。新增 `knowledge_*` 事件；Event.change_id 是发起该记录的治理 Change，payload 单独携带 product_id 与目标 change_id，不能用虚构 Change 充当产品。产品历史记录在发起 Change 结束后仍可读取；后续修订由新的治理 Change 追加。知识 fold 从全账本读取，不能仅按发起 change_id 过滤。

用 `core/knowledge.py` 隐藏版本、规则、纯 fold、影响及前置条件，用 `cli/knowledge.py` 处理文件/展示。复用 writer 的锁、approval 的 canonical/digest/重复 key 校验、paths 和 output；不为只有一个实现的存储创建接口层。增长后再按真实职责拆文件。

knowledge 事件为固定声明的 informational 类型，不改变 Change lifecycle 状态；emit_validation 在 writer 锁内调用知识前置条件。authorizing/new-contract guard 覆盖认可、适用例外、裁定等事件，不能用 skip_validation 获权。派生 projection 可附在 state 中，但新路径以严格 fold 为准；不得沿用损坏 snapshot→None→ALLOW 的行为。严格解析只针对绑定启用后的新协议记录和其证据；已知无关历史事件按既有语义处理并披露警告，不能借历史噪声静默忽略新协议损坏。

不将 emit_many 描述为电源故障下的数据库事务：现 writer 一次 os.write 多行并未保证所有故障的原子性。主权威操作设计为单条自包含事件；发现尾部截断则明确失败，不自动截断/修复日志。projection/输出失败不撤销已持久事实，幂等重试可恢复原收据。

新增 `.harness/knowledge-recognition.yaml` 是 owner 控制的独立知识 kind 策略，不能修改现有 review-recognition 的 plan/code 含义。复用校验模式，不宽化现有 validate_evidence 的 kind。ProductBinding 在策略内声明，同时固定启用版本；策略与绑定需 trusted Git/base 校验，未提交/当前候选不能自行授权自身。首次激活要求 owner 明确记录，不能将本次代码计划确认自动当作运行时知识 policy 认可。测试使用隔离 owner fixture；本仓库实际 policy 激活另行取得明确授权。

## 6. CLI 与可观察契约（拟新增，当前不可执行）

根选项沿用 `keepsail --workspace <path> --json ...`。成功 stdout 为人可读文本或现有六键单行 JSON envelope：command/version/status/exit_code/data/errors；不增加另一 envelope。人类错误用现有 format_error 写 stderr；JSON 模式 stdout 保持单一 envelope，stderr 只容纳诊断，不混入第二份 JSON。执行失败/业务拒绝必须与进程 exit_code 一致。

| 命令 | 输入与输出 |
|---|---|
| `knowledge propose --record <json>` | 输入 KnowledgeVersion 与治理 Change；返回 candidate/version_digest/revision，不认可。 |
| `knowledge import --evidence <json>` | kind = recognition/applicability/disposition；返回所导入 evidence、实际状态变化及 affected links。精确 kind/权限校验；无结论拒绝，不包装成批准。 |
| `knowledge deliver <change> --operation-id <id> --expected-revision <digest>` | 输出 prepared delivery、完整有效有限约束集和理由；无匹配返回空集及有限规则覆盖。相同请求重试返回原快照，若已过时同时标注 stale 并要求新 operation，不能把旧包当当前包。 |
| `knowledge record --record <json>` | typed acquisition/statement/challenge/execution；记录原件及 producer，不把 statement 提升为 observed/verified。 |
| `knowledge show [<id>] [--version <digest>]` | 当前/历史版本、认可证据、关联、影响、revision 和 missing_observations；纯读。 |
| `knowledge check <change> [--paths <relative-path> ...]` | 默认完成前置检查；paths 模式检查声明动作的依赖，可明确显示独立动作可继续。返回 obligations、pending impacts、disputes、blocking_reasons、coverage limits、basis_digest。它不授予工具执行权限。 |
| 现有 `change resume <change>` | 增加 knowledge 字段：供应历史及原文、当前约束、effective approval 摘要/引用、未决裁定/执行、缺失观测、需刷新交付标志。保留原有键和无 active change 的空 stdout 行为。 |

退出码遵循当前 `keepsail/exit_codes.py`：0 已成功（只读可带 warning/pending）；1 未分类 I/O/内部故障；2 非法输入、未认可结论、必需 check 失败或未满足治理前置条件；3 未初始化/启用后缺必需配置或配置损坏；4 真正外部工具执行故障；5 锁/expected_revision/幂等冲突。show/resume 的 pending 可 0+warning；check 对阻断义务用 2；损坏记录用 2+`knowledge_corrupt`，读取 I/O 故障用 1，绝不 0+空集。recognized reject 导入成功为 0，但 data.decision=reject 与 effective=false；不是批准。

示意 JSON 的 data（digest 省略仅供阅读；正式记录必须完整）：

```json
{"schema_version":"knowledge-delivery/v1","change_id":"change-a","delivery_id":"delivery-01","basis_digest":"sha256:...","revision":"sha256:...","supply_status":"prepared","constraints":[{"knowledge_id":"database-choice","version_digest":"sha256:...","authority":"constraint","body":"持久化统一 PostgreSQL","relation_source":"global","recognition_evidence_id":"recognition-01"}],"missing_observations":["recipient-acquisition","understanding","compliance"],"limits":["explicit-rules-only","single-repository"]}
```

## 7. 现有链路复用、控制与兼容

- decision 的 ratified/anchors/check 原样保留，绝不批量迁移或推断为 guidance。新知识可以显式引用 decision ID、当时正文摘要和 Git revision；不自动导入其权威。若同时存在冲突，展示并要求认可裁定，不能出现两套记录各自覆盖对方。tier 只表达可检查性。
- 在启用知识协议后，plan ready/implementation start、done 和 attestation 的现有前置链调用同一知识谓词，emit_validation 同样校验，防止只守 CLI。plan 绑定当时 knowledge basis；approval schema 通过版本化新增关联，不改历史 approval digest。新代码 subject/verification 关联对应知识 basis；后续变化使完成检查需要新裁定/证据，而不是篡改旧批准。
- completion 默认要求当前有限约束集已保存交付、所有相关影响已裁定并完成要求动作、必要检查有结果；不强制 agent 自报 adopt，更不以自报代替合规判断。可设置过程要求获取收据，但无观测时应明确缺失并按 policy 处理，不能猜测接收。
- 挑战只在声明依赖动作的 CLI 检查及完成门禁上阻断。paths 与 selector 明确无交集的独立动作可继续；global constraint 的动作独立性需有权 applicability 结论，不能靠路径自证。此次不声称原生编辑工具或 shell 全面被拦截；现有 tool gate 生命周期机制保留。
- attestation 保留知识版本/供应/影响/裁定/执行证据与 basis 摘要；trusted base 规定的 policy 及 ledger 数据进入纯 Git 校验，禁止仅靠本地 derived state。并发更新须重验 basis。没有启用知识协议的历史 Change 走既有路径，并标记 knowledge coverage=not_recorded，不能补写历史 received 或 grandfather 成 complete。
- 默认无需数据迁移；新增事件向前兼容旧数据读取，但旧二进制不能消费新义务。启用绑定要求最低 reader protocol，新旧混用必须明确拒绝受控操作；不能指望旧二进制自行理解未来协议。CI/可信验收端升级是激活前置条件，配置存在不证明 hooks/保护已启用。

## 8. 规范追溯与未覆盖边界

| 设计义务 | 架构对应 | 验收与边界 |
|---|---|---|
| 完整持久恢复版本、批准关联、影响与未决事项 | C1、F2；Change/challenge/recovery | S6/S8；恢复已记录事实，不恢复全部推理。 |
| 知识与工作授权分开；承诺内新增文件只更新 assessment | C2、F1；selected plan authority | S7/S10；语义是否越权依赖认可过程。 |
| 有限 global/explicit rules 求值并供应所有命中约束 | C3；omitted recall | S1/S2/S9；不覆盖未知语义相关性。 |
| candidate 无权威，独立 state/authority/applicability；认可纠正可追溯 | C4、F3；domain meanings | S1/S3/S5；跨 repo 共享/完整知识采集尚未实现。 |
| challenge 不解除约束；故障显式，动作局部等待 | C5、F1；authorization bypass | S3/S4/S5/S10；CLI/emit/attest 覆盖，不承诺全部工具写入。 |
| 当时正文+digest、交付/获取/声明/check 分开 | C6、F1/F2；trace and guarantee boundaries | S1/S6/S8；缺失观测不伪造，身份不是密码学认证。 |
| 变化反馈、continue/adjust/reapprove 及执行结果 | C1/C2/C4/C5/C6；in-flight choice change | S7/S9/S10；只暴露已记录关系和有限显式规则。 |
| 产品 ID 独立于仓库，执行 harness 不持权威 | F4、purpose and positioning | 单仓库切片；跨仓库产品权威仍是必须履行的后续义务。 |
| 人决定 recognition policy 与风险；外部例行判断 | Responsibility and trust、F1 | S3/S7；现有 plan/code policy 不被隐式扩权。 |

明确未包含：完整语义检索/知识图谱、自动学习与自认可、所有知识载体自动摄取、完整 agent loop、跨仓库同步/共享事务、供应商连接器、原生 hook 的全面知识动作判定、历史 decision 批量迁移、基础 event/snapshot 全面重构、发布/远端 branch protection 修改。以上是切片覆盖边界，不删除规范义务。

## 9. 外部系统未来 seam

外部检索返回内容及来源，转换成 candidate 或保留的检索 observation；trace 只证明指定请求返回指定内容；测试 receipt 归属精确 code/config/version，不变为认可；recognized conclusion 才可由 policy 授予指定权威。外部内部 ID 映射到 Keepsail identity/version，不能成为第二套批准事实源。

本次不新增 Signet/Waykeep/Throughline/SpecGate 依赖，不复制其代码。前述研究只提供快照、明确关联、冲突拒绝和事实分层的设计输入。未来接入需验证版本映射、访问边界、证据保留、失败/空结果/重放和冲突，不因检索 confidence 或测试通过自动认可。

## 10. 风险与假设

主要风险是已有事件链、批准和 attestation 的接点多于表面六个 CLI 命令；分阶段验收必须贯穿真实链，不能只做漂亮 JSON。严格新协议与容忍旧事件需清晰隔离；旧二进制和未升级 CI 不能承担新约束。记录数量随交付增长，本切片线性 fold，待真实规模证明需要再索引。仓库权限与 owner policy 是信任根，不提供防恶意改 Git 或密码学身份保证。

假设本地受支持文件系统、同一账本内串行写入；不支持网络盘并发。策略激活、风险放松和新产品权威仍由 owner 决定。若现有正式接口/治理发现与本文无法兼容，应展示具体差异并修订计划，再请求本人确认，不能以实现便利降低产品基石。
