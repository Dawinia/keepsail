---
change: 2026-10-27-harness-knowledge-context
stage: plan
---

# Confirmed implementation authority

On 2026-10-27 the owner replied “确认” in chat `01a17d4a-2fff-7cc0-9558-39ce65fb006d` to the complete implementation plan (SHA256 `cea4d2932f05801146f5a80286e095ee6c0a36f4c03abfb4b1183d4db256c1dc`) and its three choices. This authorizes the bounded implementation, current-contract reviews, and local opt-in described below. It does not recognize a knowledge version or disposition, authorize new user sessions, policy migration, push, PR publication, merge or release. The following investigation-stage wording is retained as the reviewed proposal; this paragraph records the subsequent actual confirmation.

# Keepsail 单一 harness 的知识上下文交付与恢复集成：待确认实现计划

日期：2026-10-27（Asia/Shanghai）。调查聊天：`01a17d4a-2fff-7cc0-9558-39ce65fb006d`。

**本文件是实施候选，不是批准。** 本轮仅现场读取、运行既有代码的隔离验证、编写聊天目录内的调查与计划文件。未建立新 Change，未修改源代码、正式文档、真实策略、hook 配置或账本。未启动评审、迁移、合并或发布，也未创建其他用户聊天。规范基石为 `E:/Work/keepsail/docs/product-architecture.md`，其义务不因本次切片边界而缩减。

建议新 Change：`2026-10-27-harness-knowledge-context`。这是待立项标识，目前不存在对应实施授权；不恢复已归档基线，不借用历史残留 Change。

确认后冻结的有限承诺如下，后续 assessment 使用这些稳定 ID：

| ID | 承诺 |
|---|---|
| H1 | 仅一个 Claude Code 入口，显式绑定 Change/session/entry；开始、继续与恢复正确恢复当前权威及未决事项。 |
| H2 | 复用原生知识、批准和影响模型；完整交付当前有限约束及冻结承诺/限制，不创建平行权威或缩减架构。 |
| H3 | 供应、实际 CLI 获取、agent 声明和实际检查四事实分离；原始证据、完整正文、版本、session/entry 可追溯。 |
| H4 | 恢复与知识变化重新核实当前依据，保存旧依据；知识纠正、challenge 或刷新不绕过承诺变更批准。 |
| H5 | 在选定编辑工具边界按当前供应/获取、原授权和依赖控制；相关工作等待、可证独立工作继续，错误不默认就绪。 |
| H6 | 有界摘要/分页、幂等与失效策略可日用，明确安装影响与撤回；不扩跨 harness/跨仓库/策略迁移。 |
| H7 | 用真实开发任务、用户手动开启的两个真实 Claude session 和真实认可演进完成 A1–A12；隔离进程不代替跨 session。 |
| H8 | 更新 dated 架构覆盖与公开用法，完成当前精确实现的测试/外部认可 review/attestation，披露成本与未验证边界。 |

## 1. 已核实基线

证据：本目录 `baseline.json`、`audit-commands.json`、各命令的独立 stdout/stderr、`before-snapshot.json`。所列状态是本轮查询事实；不是引用交接报告代替核实。

| 项目 | 本轮核实结果 |
|---|---|
| 本地 HEAD / main / origin/main | 均为 `bb69097dffee4e782568da4ea688d06b5773cbf4`；`git ls-remote origin refs/heads/main` 返回同一 SHA，未 fetch 或切换分支。 |
| 实际 trusted base | 原生 `keepsail.core.approval.resolve_contract_base` 返回同一 `bb69097...`；实际 `policy_configuration` 返回已激活 policy、无 candidate。 |
| #129 | MERGED，`7e2e6f8b7a41821721f877dca84316424fb632bc`：显式约束、交付与知识影响生命周期。 |
| #130 | MERGED，`202171797aaf6899a1a44e51ef1451b0f13a6384`：首策略与有边界试点准备。 |
| #131 | MERGED，`e8eb70c09c557165fe4012017194ad45cb2aa50f`：coverage 更新后保留精确影响裁定。 |
| #132 | MERGED，`586c9314f8a4e68ece9d11bfb46a0335986288b1`：真实 CLI 试点材料与验收收口。 |
| #133 | MERGED，`bb69097...`；GitHub mergedAt 为 `2026-10-27T11:30:30Z`，即上海时间 19:30:30。 |
| 归档状态 | `2026-09-04-product-baseline`、`2026-10-25-knowledge-policy-bootstrap`、`2026-10-25-knowledge-cli-pilot`、`2026-10-27-historical-change-recovery` 均为 ARCHIVED。 |
| 范围外残留 | `2026-09-15-plan-authority-alignment` 与 `2026-10-26-stable-knowledge-impact` 仍为 READY_TO_MERGE。只报告，不收口、不合并其账本、不混入本 Change。 |
| 工作树 | 无 tracked diff；未跟踪 `.harness/.events-7byibijm.tmp`、`.harness/.events-ka23hzgu.tmp`、`.superpowers/`、`docs/research/` 原样保留。 |
| PATH 上 CLI | `C:/Users/DawiniaLo/.venvs/super-harness/Scripts/keepsail.exe`；该环境的 Python 实际 import 指向 `E:/Work/keepsail/src/keepsail`，旧目录名不能直接推出旧代码。 |
| 本次选定 CLI | `E:/Work/keepsail/.venv/Scripts/keepsail.exe`；Python 为同目录 `python.exe`，`keepsail`、`keepsail.cli`、`keepsail.core.knowledge` 都导入当前仓库。入口是 `keepsail.cli:main`。 |
| 原生工具 | Claude Code `2.1.228`，Codex CLI `0.46.0`；`D:/Git/bin/bash.exe` 存在，实际从 Git Bash 成功运行显式 `.venv/Scripts/keepsail.exe --version`。未开启任何 Claude/Codex 新 session。 |
| adapter 登记与实际配置 | `.harness/adapters.yaml` 登记 superpowers、claude-code 为 enabled；仓库实际没有 `.claude/` 或 `.codex/`。登记/AGENTS 模板不能证明 hook 已安装或已触发。 |
| 默认恢复对象 | 原生无 slug `change resume` 选中残留 `2026-10-26-stable-knowledge-impact`。本项必须显式绑定 Change，不能自动继承它。 |

PR 查询使用 `gh pr view`；原始结果分别见 `pr-129.stdout.txt` 至 `pr-133.stdout.txt`。

### 当前政策与精确适用范围

- Policy 为 `knowledge-recognition/v1`，digest `8837f4d7a4fede285eef7d8a15ab450ee70ea779e0580ac90f27cf9efbb86337`，product=`keepsail`，repository=`Dawinia/keepsail`。
- 知识认可、适用性与影响裁定由 `keepsail-product-owner`、`keepsail-owner-knowledge/1` 提供；唯一 observation issuer 是 `keepsail-cli-observer`。
- `docs/knowledge-pilot.md:19-20` 将该 observer 限定为实际保留的 CLI 返回内容。不能把同一 label 用于未经认可的原生 Read 观察，更不能把 SessionStart stdout 当作获取证明。
- 当前两版知识都叫 `delivery-evidence-boundary`：v1=`0f240f5f1e72ee8bc72665e18ad16ad0d3b06615e0e9fd371007ff8531bb04cb`，当前 v2=`1212230c5189d0e10f7b9b2b75eec372cdaf80115a0e9162ed2063d42a4e93cc`。
- 两版 selector 都是 repository AND `2026-10-25-knowledge-cli-pilot`。它们不会自动成为本项约束；但已激活的仓库协议仍要求本项记录当前准确的空集供应。
- 真实知识账本本轮 revision=`4f1efcdc2383b5a1ecaba06809e11bdd607b5db5fc9b7af0c5a1776d0363839f`。试点 `knowledge check` 成功、无 blocking reasons、v2 影响已 resolved；这不证明本项入口完成。
- `.harness/review-recognition.yaml` 当前认可 `codex-subagent-review/v1`、issuer=`codex-subagent`，plan/code 都须精确冻结 subject、原始证据、provenance 与显式 approve/reject。执行失败、空结果和 skip 均非批准。调查用 research 子 agent 没有做评审，也不产生审查批准。

## 2. 架构义务、现有能力与缺口

以下行号以本次 `bb69097` 为准。源码/文档路径均相对 `E:/Work/keepsail/`。

| 义务 | 已有能力和实际入口 | 当前证据 | 本项缺口及补齐方式 |
|---|---|---|---|
| C1 连续性 | `change resume` 已恢复 state、scope、最近事件与 `knowledge.report`；后者**已经包含完整 effective_approval**，不是没有批准数据。 | `cli/change.py:421-470`；`core/knowledge.py:1061-1113`。 | 新增日常入口投影，直接展示有效承诺、限制原文来源、未决事项和下一有效步骤；当前数据已有但淹没于嵌套 JSON。 |
| C2 批准内自主工作 | 冻结 plan subject 有 artifact 原文/digest、稳定 commitment ID/text 与有效批准引用；coverage assessment 区分实施调整与承诺变化。 | `core/approval.py:136-179,232-298`；`cli/status.py:299-321`。 | 直接复用冻结 subject，不从当前磁盘计划或 scope 重新推断授权；限制未结构化时交付冻结原文，不能用摘要假装已完整提取。 |
| C3 有限适用与交付 | 显式/global selector、认可 applicability、unknown/non_matching 分离；`knowledge deliver` 保存准确版本、正文、适用依据和原始认可。 | `core/knowledge.py:621-644,820-843,1116-1211`；`cli/knowledge.py:164-219`。 | 开始/恢复时有明确 Change，触发原生供应，真实 CLI 工具检索，按返回内容观察获取。保留有限语义覆盖声明。 |
| C4 知识演进 | 保留历史供应/版本，生成影响与认可裁定；#131 固定原始触发 context/approval，coverage 变化不冒充新义务。 | `core/knowledge.py:844-1003`；`docs/plans/2026-10-26-stable-knowledge-impact.md`。 | 每次恢复重新核对当前依据，同时交付历史依据差异；不覆盖旧供应，不因刷新自动接受 continue/adjust/reapprove。 |
| C5 有界控制 | 原有 lifecycle gate；`knowledge check --paths` 对相关 impact 保守依赖筛选。 | `gates/pre_tool_use.py:66-174`；`core/knowledge.py:1456-1497`。 | 只在选定 Claude 编辑工具边界叠加上下文就绪前置条件；完整供应、当前 entry 获取、局部知识依赖、原工作授权分别求值。 |
| C6 事实区分 | 原生 ledger 分开 delivery、observation、statement/challenge、execution/check；original_receipt 可保留额外 session/tool 信息。 | `core/knowledge.py:545-589,1014-1057`；`docs/product-architecture.md:155-169`。 | 增加真实 CLI 返回观察器与上下文页 receipt；不把生成 hash、打印、声明或 gate 通过升级为理解/合规。 |

额外义务：架构 `90-99` 不许知识纠正绕过承诺；`142-151` 不许所有争议全局阻断或默认继续；`169` 以后保留共享权威/跨仓库及全面召回边界。本项不削减这些义务。

### 现有命令的准确职责

| 接口 | 可复用内容 | 本项不得作出的推论 |
|---|---|---|
| `change start` | 原生声明新 Change；发事件、刷新派生 state。 | 立项不是 plan 批准；现有命令不自动建立 session 上下文。 |
| `change resume [slug]` | 只读恢复；含知识全报告、完整冻结 approval、20 条最近事件。 | exit 0 不是已供应、已获取或可执行；无 slug 的最近活跃选择不是本任务身份确认。 |
| `status [slug]` | state、effective approval、pending revision、assessment/coverage、现有 `SUGGESTIONS`。 | 状态提示不是新批准，scope 估计不是承诺全文。 |
| `knowledge show` | 现有/历史版本、原始认可、delivery/observation/statement；revision。 | 全仓库 dump 不是适用性判定，也不是本 session 读取证明。 |
| `knowledge deliver` | 先原生保存准确六成员供应，再输出；CAS 和 operation 幂等。 | prepared 或返回成功不是 acquisition。外围分页不得更改原生六成员 delivery 结构。 |
| `knowledge record` | 现有 observer acquisition、agent statement/challenge、处理 execution。 | 核心当前只校验 observer、receipt 非空、正文 digest 等，不验证真实宿主工具返回；不能只填已知 hash。 |
| `knowledge check` | 当前供应与影响前置条件；`--paths` 是局部依赖检查。 | `--paths` 分支跳过 exact retained delivery 检查；现有任何分支都不强制本 session acquisition。 |

### 体积实测与历史跨会话边界

- 当前 `resume-default` JSON stdout 为 945,531 UTF-8 bytes；`resume-pilot` 为 871,957 bytes。主要体积来自最近事件的完整 payload（默认对象约 852,640 bytes 的紧凑序列化）；不能把近 1 MB dump 直接升级为日常入口。
- 试点知识检查报告原始 stdout 147,825 bytes；其中 observations 的紧凑序列化约 76,732 bytes，完整 effective_approval 约 26,974 bytes。必须去除历史 receipt/事件递归展开，并保留按 ID/digest 的检索。
- 历史手动 CLI 试点确有真实替换聊天：`docs/knowledge-pilot/acceptance.md:72-100`，替换聊天 `01a17370-b6fa-7893-a319-7aaba9d8cb8e`，来源聊天 `01a1726b-5486-7e40-adee-1f6d2d37c474`；保留实际 acquisition/adoption/批准内文档操作。这证明旧试点的范围，不证明新 hook 集成。
- `tests/integration/lifecycle/test_knowledge_delivery.py` 的 new_session 是独立 CLI processes；本项只能将其作为补充。

## 3. 选定 harness、触发入口与最小路径

**建议选 Claude Code，本项仅集成这一种 harness。** 理由：仓库已有 canonical adapter、机器已安装可执行版本、实际 Git Bash 可调用显式 Keepsail CLI，SessionStart/PreToolUse 接点已经存在。不以未证实的 Codex Desktop hook 能力为前提，不建设跨 harness 通用框架。

外部契约核对：[Anthropic Hooks reference](https://code.claude.com/docs/en/hooks#sessionstart)。官方文档规定 SessionStart 的 startup/resume/clear/compact 与工具后置回调；PostToolUse 可获得 tool_input/tool_response/tool_use_id，Bash 输出有 stdout/stderr/interrupted。**文档及本地类型定义不是本机真实 hook 已触发的证据**；本机 2.1.228 的实际 payload、登录可用性和项目信任仍需在实施后由用户打开真实 Claude session 验证。不依赖官方文档标记为更高版本才有的字段，不升级宿主。

本机类型证据为 `C:/Users/DawiniaLo/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/sdk-tools.d.ts:2945` 的 `BashOutput`；它支持 stdout/stderr/interrupted，以及大输出 rawOutputPath 等字段。本项不依赖读取任意 rawOutputPath 补造模型实际收到内容；出现落盘/截断就保留缺失并取更小页。

最小闭环为：

1. 用户启动/恢复既有 Claude 开发任务时，沿用已有 `KEEPSAIL_CHANGE_ID` 显式固定本 Change；hook 从 stdin 读取真实 session_id、source 和 cwd。无显式标识时提示选择，不从残留 Change 自动猜测。
2. `SessionStart` 生成新的 entry epoch，并注入有界上下文摘要、缺项状态及一个绝对路径 CLI 获取指令。该输出仅是供应/提示，不能记录 acquisition。resume/clear/compact 即使 session_id 相同也建立新 epoch。
3. 执行者在真实 Bash 工具中调用新增 `keepsail --json change context <slug> --entry <entry_id> [--page N]`。它复用原生 `knowledge deliver`，输出当前上下文的确定性页。现有 `resume`、`status`、`show` 保持只读语义。
4. 选定 Claude 的 `PostToolUse` Bash observer 严格核对实际调用和返回页、entry/session/root、manifest/page/body digest，再用原生 `knowledge record` 保留真实 acquisition。保留原 callback receipt；不可观察或截断时保持缺失，不造成功。
5. 执行者通过现有 `knowledge record` 明确提交 adopt/reject/challenge 与理由；可由新增命令的 `--statement <record-path>` 仅转交显式记录以降低手工 CAS 成本。没有声明时显示未声明，不自动 adopt；声明本身不证明合规。
6. 选定 Claude 的受管 PreToolUse 编辑边界，在原有生命周期 gate 基础上查询当前 entry 就绪与动作相关影响，返回精确理由和获取/处理命令。读取、诊断、合法计划准备与有依据的独立工作仍能推进。
7. `UserPromptSubmit` 只做轻量 fingerprint 刷新/提醒，不整轮阻断 prompt；PreToolUse 在实际编辑前再次读取当前依据，捕获同一轮外部变更。源代码执行、语义判断及任务规划仍归 harness。

没有自动创建新用户聊天、代用户启动 Claude 或跨 session 自行发消息的动作。替换会话由用户手动开启，根聊天继续跟踪验收。

## 4. 上下文接口与数据设计

### 接口（拟新增，当前不可执行）

`change context <slug> --entry <entry_id> [--page N] [--statement <record-path>]`：显式可写准备/检索入口，输出标准 CLI envelope，data.schema_version=`agent-context/v1`。仅接受有效 session 绑定；不能用传入的任意 session 名冒充宿主 callback。错误沿用 CLI 0–5 分类，具体机器码包括 `entry_unbound`、`context_stale`、`page_incomplete`、`context_unavailable`；这些是显示状态，不是新 Change 生命周期。

`change context <slug> --preview`：纯读诊断，明确 `not_supplied/not_observed`；不创建 delivery、entry 或批准。`gate check` 增加可选 `--agent claude-code --session-id ...`，调用与 hook 相同的 snapshot/纯 gate，用于复现同一动作的理由。

### 单一上下文投影

新增 `core/context.py` 只组合现有权威，不能导入 cli/gates/sensors/engineering：

- identity：真实 root、product/repository、Change/state、session/entry/source、当前 HEAD 与 trusted base。
- authorization：effective approval ID/evidence/subject、稳定 commitment ID 与原文；冻结批准 artifact 及 digest；pending candidate 与有效批准明确分开。未结构化的限制以完整冻结 artifact 原文交付，不从当前文件或模型提炼替代。
- knowledge：完整当前有限约束集的 ID/version/body/authority/selector、匹配依据、精确认可引用；non_matching、unknown、未激活/错误分别呈现。
- project conventions：复用 `core.decisions.load_decisions/compute_body_hash`，保留 AGENTS 要求遵守的 ratified decisions 的 ID、ratified_text_hash、正文、来源 blob/状态和必要 review/check 条件；不把 superseded/retired/proposed 当当前约束。它们保持 decision 子系统身份，不假装自动获得 knowledge-version 身份或认可。原文完整进入上下文页，获取事实由外围 context receipt 记录；检查仍是现有 decision check。hash 漂移/解析错误显示具体缺口，不能略掉受约束规范后宣称完整。
- recovery：当时供应的 delivery/version/approval、当前版本/授权及差异、未决 challenge/impact、认可 disposition 与执行检查状态。
- readiness：供应、当前 epoch 的观察覆盖、agent 声明、知识依赖、工作授权分别显示；当前动作未指定时不宣称动作已授权。下一命令由上层复用 `gates.decisions.SUGGESTIONS` 与已有知识错误理由组合，core 不向上层反向依赖。
- trace：每类事实只列 ID/digest、覆盖与缺失；完整原始证据按 locator 可查，不把所有 ledger 历史内嵌到每次 prompt。

不新建知识库、Change 状态机、批准来源、适用性算法或 reviewer 执行器。

### 分页与体积

- SessionStart 摘要初始预算 8 KiB，逐页完整输出预算 24 KiB（包含 envelope）；使用 UTF-8 字节精确计量，同时报告实际 token 估计，不能将 bytes 宣称 tokens。
- 摘要保留身份、有效 approval ID、就绪/阻塞类别、当前约束 ID/version、未决事项数量与必要动作；更多原文由确定性 manifest 分页承载。超过摘要预算时明确 `more_required` 与页定位，不静默省略后宣称完整。
- manifest 包含所有必需上下文对象、字节范围/顺序、各页 digest 与重组原文 digest。冻结批准原文可能跨页；知识正文也允许字节安全分页。
- 原生知识 acquisition 仍是**完整一个版本正文**。观察器只有在同一 entry/manifest 的所有相关实际工具返回片段已完整重组、正文 SHA256 精确一致后才提交该版本 acquisition。部分页只保留外围 receipt，不冒充整版本 acquisition；无须增加新知识事件或 chunk 权威。
- 空匹配仍有原生准确空集供应和本 entry 上下文工具返回 receipt；没有知识版本可写 acquisition 时，不伪造虚拟版本。摘要明确 `empty_set_observed` 只描述上下文 receipt，不能当作 core knowledge acquisition。

### 新增外围数据及恢复

复用既有 gitignored `.harness/operation-logs/context/`，保存内容寻址且不可覆盖的 manifest、page bodies、实际工具返回 receipts 与 session entry 绑定。无需新 gitignore 允许区，不把这些目录加入产品编辑白名单。

这些文件是可重建投影、原始观测载体及缓存，**不是批准或知识事实权威**：

- native ledger 仍是 knowledge supply/acquisition/statement/disposition 的权威；完整知识 observation 的 original_receipt 留存精确页/回调原文或自包含内容，不仅是会丢失的本机绝对路径。
- approval/限制等上下文的获取 receipt 作为独立观测载体，不强塞进严格六成员 knowledge delivery；验收时导出到正式 evidence 目录，并与 manifest digest 关联。
- 只保存该上下文调用所需的 hook 字段和实际 stdout/stderr，不扫整份聊天记录、凭证或用户 prompt；保留 session/tool IDs 和原 callback 的必要字段，说明未收集部分。
- session entry 绑定以 workspace realpath + Change + session + entry epoch 为键，防目录穿越、symlink、其他仓库/任务/session 复用；当前指针可原子更新，但不能覆盖 immutable receipts。
- raw receipt/page 文件丢失或损坏则重新获取；不能仅凭 cache flag 放行。重启可从 retained receipt 和 ledger 重建，不能回填旧 session 的“已获取”。
- 对 approval/ratified conventions 或空知识集的显式采用/异议，可保留 `entry-statement/v1` 的独立自报载体（Change/entry/manifest、actor、对象 ID/digest、decision/reason），不冒充知识认可或 native knowledge statement。真正 knowledge-version 的声明仍通过原生 `knowledge record`；异议不释放 decision 或承诺。

### 失效与重复

- authority fingerprint 包含当前 policy digest、有效 approval subject、ratified decision 集合及其正文 hash、知识 basis/版本/认可适用性、scope/coverage 相关性、pending impact/disposition 和 entry epoch。HEAD 记录于快照；HEAD 或授权来源变化至少触发重新核对，不因普通批准内文件新增自动要求新 plan。
- ledger revision 用于 CAS 与审计，**不直接作为整包失效键**。本入口自己的 delivery/acquisition/statement 追加不能形成“读一次即失效”的死循环；trace summary 可单独刷新。
- 同 entry、同内容 manifest 重复检索复用供应 operation；页返回按 tool_use_id + page digest 幂等保留，既不重复造获取，也不改写旧 observation。
- 复用 delivery operation 时，沿用其已保留原始 request/expected_revision 做幂等重放，不用当前 ledger revision 拼出“同 ID 异文”请求。新供应才取当前 CAS revision。
- 不同 session 或 resume/clear/compact 新 epoch 必须重新建立当前获取；历史采用声明和 receipt 继续可见，但不能当本次 observation。
- 旧 session B 的本次 entry 之前已有获取记录，即使 session_id 没变，也不能跳过新 epoch 复核。UserPromptSubmit 不能反复创建 epoch；只检查现有 binding 和 authority fingerprint。
- 供应 CAS 冲突后重算最多有限次数；知识/授权已变则把未完成 manifest 标为失效并返回明确 refresh 命令，保留全部旧页/receipt/供应。已观察到的旧内容仍可留作当时获取事实，但不得据此声明当前就绪。不能把失败重试记录成成功。

## 5. 控制语义与授权边界

仅为显式启用且绑定的 Claude integration 增加上下文前置条件。既有跨 harness lifecycle policy 继续来自 `gates.decisions`，不得在 hook/CLI 另写一套按 state/path 的规则。

实现方式：新增 immutable context readiness snapshot；`PreToolUseGate` 接受可选 snapshot，在既有 lifecycle 判定和硬编码 authoring allowances 基础上，经 `gates.decisions` 的单一声明规则处理选定入口的前置条件。hook 与 `gate check` 走同一读取/判定链路；未启用本集成的 Codex、plain 及既有调用保持原合同。core 不导入 gate。

| 情况 | 本项应有行为 |
|---|---|
| 无任务绑定、绑定未知或错误 root | 显示选择/修正步骤，不自动恢复历史残留。读取和诊断可用；已选择的受管产品编辑不能据此获准。 |
| 没有批准、intent/rejected plan 阶段 | 准确显示缺失与 candidate，保留现有合法 plan authoring 和 scratch 规则；不能把没有 effective approval 解释成 plan 准备也全局冻结。source 编辑仍按既有 gate 阻断。 |
| 当前完整供应缺失/陈旧，或当前 entry 必需上下文未完整返回 | 相关受管产品编辑暂停并给出 retrieval/refresh；不禁止读取、诊断或解除阻塞操作，不写 approval。 |
| 仅 unknown guidance | 不因 guidance 未判定把独立工作全球阻断；明确未评估。 |
| unknown constraint / 全局争议 / 无依赖证明 | 需要该约束的动作保守等待认可结论，不凭 agent “独立”自述放行。 |
| 有路径依赖的未决 impact | 分别做准确供应检查与 `knowledge.check(paths=[canonical_action_path])`；能证明独立且原批准仍覆盖的动作可继续。保留未决项，不默认全部批准仍有效。 |
| no matching | 明确 empty match 与有限语义范围，保留准确空集供应和上下文 receipt；不能推断该任务完全无知识。 |
| 认可来源缺失、失败、空结论、skip | 缺认可就显示未决，不能获得约束权威/批准/影响裁定。 |
| v2/退休/适用性变化 | 保留历史 v1/原批准；当前差异与 impact 暴露。continue、adjust、reapprove、not_applicable 只应用认可原结论；知识修改不绕过承诺变更批准。 |
| hook/解析/工具返回损坏 | 在已启用、已绑定的受管编辑路径将 readiness 标为 unavailable 并给修复步骤；不能沿旧 fail-open 路径默默变成 ready。无关工具及未启用适配器错误策略不变。 |
| agent 尚未声明 adopt | 展示未声明，不能自动生成 adopt。必要的有效约束不因自报 reject 消失；challenge 的控制依赖仍走现有知识链路。 |

PreToolUse 的 mutation 覆盖维持当前 Claude Edit/Write/MultiEdit/NotebookEdit；Bash mutation、MCP、其他外部进程写入仍非全面实时拦截范围。PostToolUse Bash 只观察本 CLI context 检索，不分析通用 shell 写入或承诺完整执行控制。merge floor 继续由现有完整检查、精确 review 与 pure-Git attestation 提供；不能声称它会证明所有 session 获取或语义遵从。

## 6. 具体文件与接口影响

以下是 initial coverage 估计，不替代批准承诺；增加 fixture/文件仍按 `implementation record --assessment` 更新 actual coverage。未列出的重大权威/状态机变化需展示计划差异并重新确认。

| 文件（仓库相对路径） | 预期修改 |
|---|---|
| 新 `src/keepsail/core/context.py` | 组合权威投影、确定性分页/manifest、fingerprint 与 receipt 完整性读模型；复用 approval/knowledge/path helpers，stdlib 优先。 |
| `src/keepsail/cli/change.py` | 新 `context` 子命令；旧 resume 只读行为和 JSON 原字段兼容。 |
| `src/keepsail/cli/knowledge.py` | 将现有原生 submit/deliver 编排抽成同层可复用函数，保持原命令合同/CAS/事件不变；context CLI 与 hook 都复用，不复制 writer 校验。 |
| 新 `src/keepsail/daemon/context_hook.py` | Claude entry/session binding、实际 Bash stdout observer、页 receipt 聚合、触发原生 acquisition/显式 statement 提交。 |
| `src/keepsail/daemon/hook_entry.py` | 显式分派 session-start/user-prompt-submit/post-tool-use；保留 stop 行为；未知事件不得误落入 PreToolUse shim（当前非 stop 全落入该分支）。 |
| `src/keepsail/adapters/agent/claude_code.py` | 选定集成的 hook 命令/marker、绝对 pinned CLI、上下文使用说明；只改 Claude。 |
| `src/keepsail/adapters/agent/_settings_merge.py` | 以可选参数扩展同一 settings transaction，支持新 PostToolUse/UserPromptSubmit；移除旧 `change resume` SessionStart marker，更新卸载；保留无关 hooks、backup/CAS/symlink 防护，Codex 默认三 hook 不变。 |
| `src/keepsail/gates/decisions.py`、`src/keepsail/gates/pre_tool_use.py` | 单一上下文前置规则及可选 snapshot 接点，不新增 lifecycle states、不按 gitignore 放行。 |
| `src/keepsail/cli/gate.py` | 为选定 entry 提供与 hook 相同的诊断查询，复用同一判定。 |
| `tests/unit/core/test_context.py`（新） | 快照、冻结批准原文/限制、ratified decision 身份/文本 hash/错误分类、分页重组、fingerprint 与上下文事实区分。 |
| `tests/integration/cli/test_change.py` | 新入口/preview、旧 resume 兼容、empty/unknown/stale/CAS/错误码。 |
| `tests/unit/adapters/test_claude_code.py`、`test_settings_merge.py` | 安装/升级/重复/卸载、一事务备份、外部配置保留；Codex 既有测试作回归。 |
| `tests/unit/daemon/test_context_hook.py`（新）、`tests/integration/adapter/test_claude_context.py`（新） | 真实工具 payload fixture、跨 entry 观测、局部动作 gate/原授权、进程补充测试。 |
| 既有 gate / hook / knowledge / attestation 回归 | 仅在实际接点补必要案例；不修改核心知识历史含义、writer/events/reducer/transitions。 |
| `docs/plans/2026-10-27-harness-knowledge-context.md`（确认后建立） | 本计划的受治理冻结版本，含承诺、限制与验收；按 plan_paths 原生命令纳管。 |
| `docs/product-architecture-coverage.md` | 增加本轮 dated audit 与证据映射，更新失效的“策略未激活”现时措辞，保留历史审计与边界。 |
| `docs/knowledge-context.md`（新）、`docs/adapters/claude-code.md`、`docs/knowledge.md`、`docs/limitations.md`、`docs/README.md` | 真实入口步骤、四事实、refresh/paging、人工成本、降级/撤回与未覆盖范围。 |
| `docs/cli-reference.md`、`AGENTS.md` | 通过当前支持的生成/sync 流程更新 CLI 与受管 instructions；不手改 marker block。 |
| 新 `docs/evidence/harness-knowledge-context/` | 原生操作、真实宿主 callback/工具返回、替换 session 身份、结果/失败重试/成本表与导出 receipt。 |

预计不改：规范产品架构正文、recognition policy 文件、knowledge event schema、state/reducer/transitions、纯 Git merge verifier。若新设计实际需要改这些边界，先最小重现/解释影响并提交计划修订，不默默扩大。

## 7. 策略、认可、真实项目影响与撤回

### 需要的明确决定

1. 确认本计划的实施承诺，并允许此 Change 的原生 lifecycle 立项、冻结、认可 plan review 和批准内实现；计划确认本身不替代 exact subject 的外部 review。
2. 确认选 Claude Code 2.1.228、显式 Change 绑定、上述 hook 观察边界与受管编辑前置条件；允许在测试通过后通过原生 adapter install/sync 对本机仓库进行**本 Change 的局部 opt-in 安装**。它会建立此前不存在的 `.claude/settings.local.json`，属于明确真实项目影响，不是本轮已做事实。
3. 确认将现有 `keepsail-cli-observer` 用于**严格核对的真实 Bash 返回的 Keepsail CLI context 内容**，保留其原有 actual CLI returned-content 边界，不扩到任意 Read、hook 输出或模型内心。真正新知识 v1/v2 和影响裁定仍分别呈现精确对象，等待所有者真实明确结论。

不修改或激活新 policy；当前 core 明确禁止工作树 candidate 替换 active trusted policy。不能为了接入 observer 顺带实现 policy migration。若上述 CLI observer 范围仍未被认可，保留 unavailable，不换 label 冒充；提交具体认可差异。

真实验收需新的有界知识对象，不能扩大 archived pilot 的 selector。拟新 ID `harness-context-evidence-boundary`，selector 限 `Dawinia/keepsail` AND 本 Change；v1/v2 文本及 digest 在 native propose 返回后单独提交所有者。可沿用四事实主题，但不得把旧 v2 认可复制成新 scope 的认可。知识演进用例如果事先设计，应标记为有边界演进验收，不冒称线上发现。

### 安装与撤回

- 安装时锁定 `.venv` 的 CLI/hook executable；不得依赖裸 PATH 解析到另一 checkout。使用现有 settings 规划/确认/原子事务，保留新旧 marker 与原始备份；不手写 `.harness/adapters.yaml`。
- 新入口只在选定、已绑定集成上启用；旧 `resume` 仍可纯读排障。撤回通过 adapter 的原生 uninstall/恢复受管配置，再由普通受审 revert 撤回代码；不删除 evidence、delivery 或 observation。
- 回退至旧入口意味着新上下文前置覆盖撤除，必须明确披露，不宣称同等保证；不创建 `gate-disabled`、不降级 trusted base、不改事件历史。
- 所有 raw callbacks/receipt 只保留完成此观察所需内容；最终可分享 evidence 导出前检查项目敏感信息，不把整份外部会话抄入仓库。
- 当前确认不包含 push、PR 发布、merge、release、外部仓库操作、通用共享权威或策略迁移；这些阶段在形成精确可审核结果后另按授权边界执行。

## 8. 实施顺序与治理检查点

1. **现在停在计划确认。** 本文件及调查 artifacts 可审核；不提前 `change start`、`plan ready`、install 或 source edit。
2. 获明确确认后，重新核实 SHA/import/工作树/政策，使用当前 checkout 的独立 `codex/` 分支（不清理其他分支/worktree，不创建用户 session）。仅在隔离必要且无合适现有 checkout 时采用 managed worktree；先确认 CLI/策略仍来自预期 checkout。
3. 建立本 Change，按合法 plan authoring 路径保存本计划和少数固定承诺；先处理准确空集供应或得到另行认可的确切 v1。freeze 完整 plan subject；由现有合同认可的独立外部过程产生精确结论并原生 import。Keepsail 本体不启动/选择 reviewer；审查 pending 时不编辑。
4. 完成基于当前宿主类型和 fixture 的入口合同验证，先覆盖能真实失败的关键回归，再实现共用 projection/CLI/观察/gate 和 transactional settings。若 2.1.228 的实际 hook 不提供可校验 stdout，不能填假 receipt；在具体失败证据上修订方案。
5. 自然检查点运行 `decision check --changed`；actual coverage/within_approval assessment 原生记录。新增 fixture/文档可在承诺内更新 coverage，不因 HEAD/文件数变化重复申请 plan。若变更承诺或放宽限制，则先新 plan candidate 和认可 review。
6. 针对 changed gate 的 `d-keepsail-single-gate-policy` 及相关 ratified anchors 做真实 read/reconcile；仍保持 state pure fold、events append-only、固定 transition matrix、core-is-base、Git 产品路径门禁、pure-Git merge、gh CLI 访问等。只用原生命令，不手编 reconciliation。必要改 decision 正文需新所有者决定，本计划不授权。
7. 跑受影响回归、项目正式 lint/mypy/pytest、full decision/doc checks、native `done`。完整 code subject 先 commit/freeze，再由认可外部过程给真实 code conclusion 并 import，attestation 绑定实际对象。code-only rejection 走 `implementation reopen --reason`；pending review 不修改。
8. 在授权的局部 opt-in 后进行下节真实开发任务。真实 session 行为若产生代码变动，重新完成 actual coverage、verify/exact code review/attestation；不拿之前的 review 声称覆盖新 HEAD。
9. 最终分别报告本地已实现、宿主已触发、真实获取、真实跨 session 验收、未验证边界和交付状态；保留操作成本、失败/重试。push/PR/merge/publication 未授权前不执行。

## 9. 验收矩阵与证据位置

正式 evidence 根：`docs/evidence/harness-knowledge-context/`。对应事件与原生 original_evidence 仍由 Keepsail 生成。临时缓存 receipt 在 `.harness/operation-logs/context/`；最终导出自包含原始证据与 SHA256 manifest，不能只保留本机路径。

| ID | 用例与必需观察 | 检查层/证据 |
|---|---|---|
| A1 | 显式新任务启动，拿到准确 Change/state、冻结 approval/commitments/限制、适用版本正文/依据、pending matters。wrong slug/root 与 residual default 不串任务。 | CLI+hook fixture；`entry-a/{identity,manifest,pages,raw-hook,raw-tool-return}.json`；真实宿主 A。 |
| A2 | 日常继续无变化时不重发近 1 MB 历史；授权/知识/coverage 变化时刷新；自身 observation 追加不造成无限失效。 | fingerprint/idempotency/CAS tests；`refresh/` 与 bytes/latency 表。 |
| A3 | 换**真实 Claude session B**，SessionStart 实际触发；保留 A 的原依据，B 重新核对当前版本/授权/未决事项并取得本 epoch receipt。即使 resume 同 session id、compact/clear 也重建 epoch。 | 用户手动开启 B；`entry-b/` 原 callback、实际 tool_use_id/返回、继续开发 diff/check；session 身份自报只是补充，不能替代 raw hook。 |
| A4 | 真实任务中认可 v1→认可 v2；旧 delivery/v1/当时 approval 不变；当前暴露 impact；精确 owner disposition 才改变等待状态，v2 acquisition/adoption 独立记录。 | `evolution/` 的 native proposal/recognition/impact/disposition/delivery/receipts/checks；两版精确认可原文独立保留。 |
| A5 | 未激活/缺 policy、ledger/manifest/receipt 损坏、unknown protocol/issuer、无认可/失败/空/skip、无匹配分别正确标记。负例不污染真实账本。 | 临时 Git fixture 的负路径；`negative-controls/`。 |
| A6 | 供应缺失或旧版本、页截断/缺页/错序/伪 hash、工具失败/interrupt、旧 session/entry receipt、另一任务 stdout 均不能伪装 acquired/ready。 | observer+gate tests；保留 actual stdout/hash/错误原因。部分片段重组未完成不能写整版本 acquisition。 |
| A7 | 有依赖争议挡相关 source 编辑；明确独立路径在当前完整供应/entry 获取和原批准内可继续；global/unknown/无证据独立性不能放行。 | 真实临时 Git+同一 pure gate；实际文件 diff 与 check；确认 `--paths` 没绕过供应。 |
| A8 | 知识纠正要求新承诺时只能进入新 plan approval；新增批准内 fixture 只更新 assessment/coverage，原 trigger/裁定不因 coverage 变化失真。 | 复用 #131 regression、plan authority/attestation tests；`authorization/`。 |
| A9 | 供应、可观察获取、adopt/reject/challenge 声明、实际检查四列独立；缺声明不自动 adopt；passed 只支持覆盖范围。empty set receipt 与知识 acquisition 不混同。 | `four-facts.json`；原生 delivery/observation/statement/check IDs 与 retained original receipts。 |
| A10 | 安装、旧 marker 升级、重复安装、卸载恢复、无关 hooks/用户配置、路径带空格/Windows shell、symlink/CAS 失配、未知事件不串 PreToolUse。 | settings/adapter regression；实际安装前后只列受管差异与 backup/restore 结果。 |
| A11 | 最终 exact HEAD、plan/code subject、verification、code review、attestation 一致；可纯 Git复核。外部 shell/MCP/语义遵从边界明确。 | `final/{subjects,verification,review,attestation,limitations}`；当前仓库正式 checks。 |
| A12 | 记录每次启动/恢复/刷新人工动作数、page tool calls、bytes/token estimate、冷/热 latency、CAS retry、人工认可次数。 | `operator-cost.md` 和原始计时/体积 JSON；不以设计目标冒称实测。 |

### 真实开发任务与人工操作成本

真实任务使用本 Change 内有意义的开发尾项：A 根据实际入口新增一个“旧 entry receipt 不能授权当前编辑”的回归用例并运行针对测试；B 恢复后继续完成与 v2/局部独立路径有关的回归或公开用法文档，记录真实 diff、执行命令和结果。这些文件必须在已批准承诺/assessment 内。不能用打印标记文件、只跑模拟进程或只填写自报清单代替开发活动。

两 session 均由用户手动打开/切换；本聊天提供精确 handoff。无自动新用户 session。若还未发生 B，最终必须标为真实跨 session 未验收，不能宣称完成。宿主认证、模型服务和用户项目信任是实际依赖，本轮未触发。

目标人工成本：首次显式选择 Change、一次 opt-in 安装/宿主项目信任、手动开 A/B；日常启动/恢复由 agent 自动检索必要页，用户无需手写 JSON/digest/CAS。真实知识认可、实质影响裁定、承诺变化批准仍由所有者明确作出，不能为了降成本自动批准。目标稳态每次继续人工操作 0 次；实测不达标则保留数值并继续改进或报告验收差异。记录新入口的 cold/warm 与编辑前检查延迟，保持现有 SessionStart/PreToolUse 的 10 秒外层预算，不顺带调大 timeout；若超时必须保留缺失并解决根因或修订计划，不以 timeout 当 acquisition 成功。

## 10. 架构覆盖文档拟更新内容（尚未写入仓库）

保留 `docs/product-architecture-coverage.md:12-18` 明确标注 `bfcdb007/2026-10-22` 的历史主表；已有 `94-125` 的 #129 slice 也保留历史语境。新增本轮 dated current audit：

1. #130 的 trusted-base 策略现已激活，纠正 `:124` 当前“not activated”的失效表述；明确 repository protocol 与单个 knowledge selector 两层范围。
2. #131：coverage 更新保留原不可变 trigger/approval/裁定，真实 relevance 变化仍产生义务。
3. #132：真实手动 CLI 跨 session 证据与四事实收口已交付；历史文档 frozen pending 文案不是当前 lifecycle 未归档证明。
4. #133：历史 merged Change 的认可恢复与归档兼容已交付；product-baseline 结束，不重复实现。
5. 旧表 `:47` 的 tier-3 never-gates 是历史冲突；当前 `docs/ARCHITECTURE.md:157-159` 已修复，应标出解决证据，不能继续当现行冲突。
6. 本项未完成前标记“单一 Claude 日常入口/恢复集成 planned”；实施并真实验收后再改为 observed coverage，逐条关联 A1–A12 与 exact commit。
7. 继续保留共享权威、跨仓库分发、完整语义召回、所有工具拦截、模型理解/合规保证等未覆盖义务。历史基线归档和本项完成均不能抹去它们。

## 11. 本轮隔离验证与未验证边界

本轮所有新增文件都在聊天 artifact 目录。`probe_existing_semantics.py` 只在其中建立临时 Git，使用已有 `tests.unit.core.test_knowledge.Workspace` fixture；owner/review/recognition 全为**明确测试 fixture**，不是本仓库认可。

已验证：完整 `knowledge check` 在缺当前供应时 exit 2；相同状态下 `--paths docs/help.md` 可 exit 0；当前供应后 acquisition_coverage 仍 `not_observed` 时完整检查 exit 0。见 `isolated-probes.json`。这证实新增入口前置条件有必要，未修改实际协议或 gate。

本轮定向基线回归：**160 passed、3 skipped，451.30 秒**。见 `baseline-tests.stdout.txt`、`baseline-tests.xml` 与 `baseline-test-command.json`；包括知识核心、知识 delivery/bootstrap lifecycle、change/status、Claude adapter/settings transaction。3 个 skipped 都因 Windows 无 symlink 创建权限（WinError 1314），涉及 Claude 配置目录/settings file/settings parent 的链接保护；不能宣称本机这三项已执行通过。后续实施需在有权限的隔离环境/既有 CI 中补验，不为此更改本机安全配置。

准备脚本曾因错误导入 `keepsail.cli.main`、误用 `merge_base_commit` 参数、将 `not_observed` 覆盖行误当空列表、外部脚本缺 tests import path 而失败；已在只读或临时目录修正，最终验证以留存结果为准，不将准备失败冒充产品缺陷。未有真实账本写入。

本轮没有运行新集成（尚未实现）、真实 Claude 模型调用/认证、实际 session hook、replacement B、真实 v1/v2 认可或正式 merge gate。既有回归通过只能支持当前基线；不能宣称 proposed integration 已通过。

最终保全对比见 `preservation.json`：对调查前后 1,445 个 tracked/untracked/治理载体文件 SHA256、HEAD/main/origin/main 和 git status 比较，确认范围内文件未变。现有 lock 文件不纳入内容哈希。

## 12. 请求确认的少数选择

请确认或逐项修改：

1. **按本计划选 Claude Code，使用 SessionStart→真实 CLI 检索→PostToolUse 观察→编辑前置检查；保持显式 Change 绑定与 bounded paging。**
2. **允许认可合同内的实际 CLI observer 自动保存工具返回证据，以及测试通过后本机本 Change 的 adapter opt-in。** 不扩 observer 到任意 Read，不修改 trusted policy。
3. **实施范围包括本计划代码/正式覆盖文档及本 Change 的真实开发验收；两真实 session 由你手动开启；知识精确认可/裁定届时分别确认。** push、PR 发布、merge、release、迁移和跨仓库仍不在此次确认内。

确认前停止实施；调查、计划或外部 review 均不能替代你的明确确认。

