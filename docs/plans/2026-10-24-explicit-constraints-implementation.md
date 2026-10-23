---
change: 2026-10-24-explicit-constraints
stage: plan
---
# 显式适用约束纵向切片：中文实现计划

日期：2026-10-24。状态：**用户已在本聊天明确回复“开始吧”，本实现计划获得本人确认；实施仍须仓库认可流程通过。**

配套 [技术设计](2026-10-24-explicit-constraints-design.md) 为本计划的候选规范。产品架构始终优先。本轮只编写文档，未启动新 Change、未修改实现、未迁移数据、未创建审批证据。

## 待确认的有限承诺

| ID | 完成后应有的行为 |
|---|---|
| K1 | 稳定 product/knowledge identity、不可变正文版本、独立状态/权威/适用性；认可前 candidate 无约束权威，无 check 的 constraint 仍有效。 |
| K2 | 对全局/显式规则及认可适用判断求得有限约束集，持久供应确切版本，说明未匹配/unknown/语义覆盖边界。 |
| K3 | 新进程 resume 恢复当时供应、当前知识、批准引用、争议、影响、执行状态和缺失获取观测；交付、获取、自报、检查事实分离。 |
| K4 | v2 替代/退休/适用范围变化后保留 A 的 v1 依据，暴露已记录影响；有权裁定 continue/adjust/reapprove/not_applicable，并验证处理结果。 |
| K5 | 严格拒绝失败/空/过时/未认可/损坏证据与并发冲突；知识纠正不能绕过工作授权，旧批准不因 HEAD/新文件自动失效。 |
| K6 | CLI、emit validation、done 与纯 Git attestation 使用同一知识前置条件，保留旧协议历史及现有门禁；真实隔离 E2E 证明 PostgreSQL 主线和负路径。 |

限制：单仓库 CLI 首发；不实现完整召回、完整语义授权、跨仓库知识共享、全面原生 hook 拦截或外部产品集成。分阶段为实现顺序，不能只完成前两阶段就宣称 K1–K6 全部交付。

## 0. 本人确认后的治理准备

1. 再核实 checkout/远端 main/HEAD/import，保护 `.superpowers/` 与 `docs/research/`。不复用历史 READY_TO_MERGE Change。
2. 以 `2026-10-24-explicit-constraints` 为拟议新 slug，按当前原生命令建立 Change；必要时从已核实 main 创建 `codex/explicit-constraints` 分支。本人确认不自动替代仓库认可 review。
3. 正式采用设计与实现计划的精确快照、承诺 K1–K6，按 CLI 支持的 artifact/subject 流程标记和冻结计划，保留本人确认的原始消息来源。不得自写“人已批准”的模拟证据。
4. 当前 recognition policy 要求外部独立 Codex subagent plan/code review；到该阶段按实际策略取得精确结论，再 import。外部 review 不替代本次本人确认。外部 review pending 时不编辑。
5. 本次不激活本仓库知识 policy。实现提供验证和隔离 fixture；实际 owner policy/首次激活是独立明确授权事项。若用户希望把激活纳入本次交付，先给出精确策略候选及权限差异，再取得本人确认。

## 1. 版本、事件与严格核心

新增 `src/keepsail/core/knowledge.py`，以纯函数提供规范记录验证、knowledge fold、显式匹配、impact 派生和 shared preconditions。复用现有 canonical JSON、摘要、scope matcher、文件锁。新增事件/固定 informational 声明，并在锁内验证 current revision、幂等 operation、前驱、policy 和证据引用；单个权威操作为一个自包含事件。不会新建存储框架或泛化全部 approval。

完成判据：相同版本可复算，旧正文不会变化；不同 authority/selector 变成不同 subject；candidate 无权威；错误对象/摘要/重复 key/坏前驱/并发替代拒绝；重放相同 operation 幂等，异文冲突；新协议损坏不能被 tolerant reducer 吞成空知识。

## 2. CLI 交付与恢复

新增 `src/keepsail/cli/knowledge.py`，注册 propose/import/deliver/record/show/check；复用根全局选项、六键 envelope、错误格式和已有 exit codes。propose/import 输入显式 JSON，保留原件和 digest。strict matching 支持 global、repo/change ID、paths；缺字段为 unknown，scope/coverage/manifest 变动重新求值。

扩展 `cli/change.py` resume：保留旧字段/无 active 行为，新增完整知识恢复数据；show/resume 不写供应日志。delivery 保存 prepared，再输出；异常或管道断裂留下真实不确定状态。获取 receipt 与 agent 声明有独立类别。

完成判据：S1/S2/S3/S5/S6/S8/S9 CLI 行为和 stdout/stderr/exit code 可验证。新进程只读产物可看到有效批准摘要、v1 全文、当前版本及所有未决事项，不局限近期事件。

## 3. 影响裁定、执行与授权接点

实现认可 v2 后的记录关联影响和新显式规则求值；新增 disposition import、执行报告、必要证据绑定。continue 明示版本，adjust 跟踪实际义务，reapprove 关联新计划批准；challenge 保持约束且支持局部等待。不得凭 agent 自报 not_applicable 或 unchanged 放松约束。

将知识 basis 与新 plan/implementation/verification/code subject 关联；完成前重验 basis，结合现有 assessment、check、review/new approval 验证 execution。无检查知识仍交付并由认可过程判断，不能为追求机械化编造 check。

完成判据：pending 不隐式 revocation 或 continuation；独立工作可继续；受影响动作等待；adjust 失败、未检查、无结论不可 resolved；新 commit 调整仍需有效 code review；新增文件在承诺内沿用 approval；过期裁定不覆盖新变化。

## 4. 完成门禁、兼容和纯 Git 验收

在 plan ready/implementation start、done、emit_validation 与 attestation 接入同一谓词，精确 subject/ledger/policy basis 保留到证据。新增知识相关事件必须属于不可通过 skip_validation 绕过的 new-contract 集。policy 由 trusted base/owner activation 约束，不能让 candidate 自己扩大权限。

无知识协议的旧 Change 保持原流程，输出 not_recorded 而非“已满足”。新协议启用后必需配置/版本/证据缺失明确失败。不修改现有 ratified decision 正文，不自动迁移旧 decisions、events、attestations，不重新解释历史 skip。旧二进制/CI 升级作为激活条件记录。

完成判据：直接写事件的正常公开入口与 CLI 一致拒绝无授权操作；纯 Git attestation 可重建完整知识依据；本地 cache 损坏不能洗掉义务；旧 plan/code subject 和 attestation 回归通过。

## 预计文件范围

以下是估计，不是以路径代替已批准承诺；承诺内新增必要 fixture/文件通过 implementation record 更新 actual coverage。

| 文件 | 预计变化 |
|---|---|
| `src/keepsail/core/knowledge.py`（新） | 版本/策略/证据/匹配/纯 fold/影响/前置条件。 |
| `src/keepsail/cli/knowledge.py`（新）、`cli/__init__.py` | 新 CLI 和 lazy 注册。 |
| `core/events.py`、`core/transitions.py`、`core/emit_validation.py` | 声明事件类型、不改变生命周期转换语义、锁内前置条件。 |
| `core/approval.py`、`core/state.py`、`core/reducer.py` | 新协议 basis 关联与恢复 projection；不变更历史 digest。 |
| `core/paths.py` | 知识策略路径 helper。 |
| `cli/change.py`、`cli/plan.py`、`cli/implementation.py`、`cli/done.py` | 恢复及既有命令前置条件；如其公共共享调用点已覆盖则不重复改。 |
| `engineering/attestation.py`、实际冻结 verification subject 的模块 | 知识证据/basis 保留和纯 Git 验收；先追踪调用点，按 coverage 记录真实文件。 |
| `tests/unit/core/test_knowledge.py`、`tests/unit/cli/test_knowledge.py`（新） | 纯模型、错误、规则、CLI 合同及重放。 |
| `tests/integration/lifecycle/test_knowledge_delivery.py`（新） | 真实临时 Git、独立进程、并发、主线与拒绝路径。 |
| 现有 approval/events/state/change/implementation/attestation/lifecycle 测试 | 在实际接点补必要回归，复用 fixture。 |
| `docs/ARCHITECTURE.md`、`docs/limitations.md`、`docs/product-architecture-coverage.md` | 更新实现证据与范围；纠正 tier-3 降权文案，保留历史审计标识；规范产品架构不改。 |
| `docs/cli-reference.md`、测试 fixtures 中的知识 policy/记录 | 用现有生成命令更新 CLI 文档；只在隔离 fixture 提供 owner policy。 |

若发现必须修改 daemon/adapter、基础 writer 原子性、全面 snapshot 策略或 product architecture，先报告必要性和批准差异，重新确认；不偷偷扩大本切片。涉及已 ratified anchors 的实现改动完成后走实际 reconcile/betray 处理，不手编记录、不默认旧语义仍成立。

## 验证计划

| 验证层 | 必须有的反例/证据 |
|---|---|
| 核心 | 版本不可覆盖、状态/权威独立、selector AND/OR/unknown、paths 变化、证据 kind/policy/对象匹配、挑战不失权、影响仅关联已记录对象。 |
| CLI | 六键 envelope、空匹配/unknown、reject 导入成功但无权威、错误 stdout/stderr 和 0–5 码；prepared/emitted/acquired/statement/checked 不混同。 |
| 故障/并发 | 双进程 expected_revision 冲突、同 operation 幂等/异文冲突、尾部截断、证据缺失、管道失败、重启在 prepared 后恢复、版本变化与 close 并发。 |
| 主线 E2E | 临时产品和 Change A：v1 PostgreSQL 认可→匹配→交付→新进程恢复→v2 纠正→A 仍保留 v1→裁定 adjust→真实命令失败→修复后通过→有效 review/必要新批准→恢复 resolved。所有审批 fixture 明示测试来源，不作为本仓库真实证据。 |
| 授权负例 | 任意 agent 自报不采纳、候选自动赋权、错误 policy、空/失败结论、知识更新跳过 acceptance、旧 approval/code review 覆盖新对象必须失败。独立工作允许的正例并列。 |
| 兼容 | 历史无知识协议、旧 decision/sentinel/check、plan authority、resume 原字段/无 active、assessment 新增文件、mixed-history attestation；不回填观测。 |
| 最终治理 | `keepsail decision check --changed` 在自然检查点，最终 full decision/doc check、项目要求 lint/mypy/pytest 与 `keepsail done <slug>` 的 verify；精确代码 review 与 attestation 分层报告。 |

测试使用 `.venv/Scripts/python.exe -X utf8 -B` 及 `-p no:cacheprovider`；先确认 import 路径。初轮运行新测试及实际受影响回归（approval、events、state、change、plan authority、attestation），再执行仓库正式 verify。不能把手工 emit verification_passed 当实际检查；必须保留真实运行命令、对象和结果。无需为文档候选运行整套实现测试；本轮仅做文档/链接/差异检查。

## 完成、风险与确认边界

完整交付需 K1–K6、S1–S10 及相关回归全部有证据；仅写记录或能打印 v1 不算完成。每阶段可形成可审阅 commit，但外部 review pending 不编辑。执行本计划不包含 merge、发布、修改外部项目或启动更多用户 session；这些需要另有明确任务范围。

主要风险：批准/verification/attestation 接点较多，可信策略激活与旧客户端兼容容易造成假保证；完整获取观测受宿主限制；语义风险分类仍依赖认可过程。只承诺已实现、已验证的 CLI/事件/纯 Git 覆盖，不泛化为所有 agent 写入、跨 repo 或完整召回。

用户本人已明确确认本实现计划。已有产品讨论、外部 review、自动流程与沉默均不能替代本人确认。若承诺、限制、权威或风险边界实质变化，先展示差异并重新请求本人确认。
