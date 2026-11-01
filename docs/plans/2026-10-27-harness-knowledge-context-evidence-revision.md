---
change: 2026-10-27-harness-knowledge-context
stage: plan
---

# Keepsail 证据负担修订：正式计划候选

日期：2026-10-30。所有者已审阅完整调查和实施计划，明确授权在新 session 执行正式计划修订、现行认可流程及获准后的本地实现和验证。本文件是待精确 review 的正式 revision 候选，不声称已获 review 或实施完成。
原 Change：2026-10-27-harness-knowledge-context。
现场 HEAD：ba6f7ce207f0e3880c566545ad7c19026c80c2ed。
原有效批准：approval:2026-10-28-harness-context-codex-revision-plan-01-84705107。
调查结论：原候选中 114 份过程材料共新增 7,413 行；14 份 assessment 和中间 subject 合计 61.6%。本修订解决 CLI 输入、原生重复存储及 agent 默认用法共同造成的放大循环；调查原件保留原位置，不复制到候选。

## 1. 本次完成什么

让普通用户按正常 CLI/adapter 指引工作时，无需创建和提交大批输入、副本、会话档案；保留足以执行授权、知识恢复、影响处理和完成核验的正式事实。处理这次已有候选，使其能以规模合理、公开边界准确的新对象交付。

不新增私有证据服务、证书体系、数据库、常驻任务或用户整理证据的工作流。不把“任何人重演全部宿主回调”作为产品要求。产品规范架构不缩减，事件仍 append-only，状态仍纯 fold，gate policy 仍单一，合并核验仍只依赖 Git 中的必要记录。

### 拟冻结的修订承诺

| ID | 承诺 |
|---|---|
| E1 | review、assessment、knowledge 的正常输入无需创建/提交临时文件；必要内容校验后原生收录，重复传输不制造重复正式事实。 |
| E2 | 机械文件 coverage 由 CLI 从准确 Git/工作区对象生成；语义上的批准内判断、理由和承诺关联仍显式记录；最终完整 diff 不漏审。 |
| E3 | observer 当场严格校验真实完整返回，永久记录准确获取事实及必要来源关系；整份回调不是每次获取的永久默认记录。旧失败不晋级、旧 entry 不替代新 entry。 |
| E4 | 正式结论只保存一次，生命周期引用它；checkpoint 不重复保存全量派生视图/全部旧回调，重复导出幂等，跨 Change 不反复复制全部历史。 |
| E5 | 新旧记录明确区分：旧原文/批准/认可/验收保持原义；由原生代码生成新表示，不手改历史，不把新摘要冒充旧原始事件。 |
| E6 | 正常开始/继续/恢复获得全部当前有效承诺、限制、适用知识和未决事项；历史过程不反复全量注入；动作检查不使用已失效依据。 |
| E7 | 新候选不携带旧私有材料的提交祖先；公开内容通过字段与完整 diff 检查，不靠扩大目录豁免隐藏变化。 |
| E8 | 当前精确对象完成所需回归、现行必需验证和认可流程，报告实际增长和执行成本；不以旧结果冒充新结果。 |

这将替换原计划 H3/H6/H8 中关于回调原文、自包含证据包和正式目录的具体载体选择，并补充输入、存储和增长约束；保留 H1/H2/H4/H5 的目标与边界，H7 的历史 A/B 事实保持不变。原知识 v1/v2 认可及 continue 裁定不重新索要，不更改含义。


### 接续旧批准的完整工作约束与覆盖映射

本节与 E1–E8、下文实现和验收共同构成当前完整工作承诺。仅替代明确列出的载体选择；旧批准、失败及验收事实保留原义。

| 旧义务 | 本 revision 接续的完整要求及落点 |
|---|---|
| H1、Codex 入口修订 | 唯一真实目标仍为本机 Codex 桌面任务；显式 Change/session/entry，startup 只绑定一次，不猜最近 Change。开始、继续、resume/clear/compact 使用真实新 epoch；UserPromptSubmit 不自行建 epoch。E3/E6。 |
| H2、原计划 §2/§4 | 复用原生知识、批准、影响模型；当前承诺、限制、批准、ratified 正文、知识正文/认可/适用关系及未决事项完整可恢复，不建平行权威。E5/E6。 |
| H3、原计划 §4/§9、Codex 返回合同 | 供应、实际完整 CLI 获取、执行者声明、检查分列；获取不证明理解，声明不证明合规。保留准确版本/来源/entry 关系；以 E3/E4 的显式观测格式替换默认永久回调全文、自包含 raw 包及正式 evidence 根。失败、截断、缺页、错任务/root/版本、未完成轮询不晋级。 |
| H4、原计划失效/重复规则 | 当前 authority 变化重新核对，旧供应/版本/批准不覆写；新 epoch 不继承获取。自身 delivery/acquisition/statement 不使 packet 无限失效；幂等重试复用原 request/CAS，冲突有限重试且失败如实保留。E3/E5/E6。 |
| H5、原计划 §5 | 既有生命周期与原授权前置、单一 gate policy、所有 patch add/update/delete/move 路径均保持。相关 challenge/impact 等待，独立工作须有依据且原授权覆盖；unknown/global/坏路径保守拒绝。读、排障及既有合法 authoring carveout 不扩大或取消。hook/CLI 同判定。E2/E6。 |
| 空集、有限语义范围 | 准确空集供应与入口完成单独记录，不虚构知识版本。unknown/non_matching/未激活/错误分别展示；不声称完整语义召回、所有工具观测或跨仓库共享。E3/E6。 |
| observer 与 root 边界 | 仍只认可真实 CLI 返回观察，保持当前 issuer；不扩到 Read、提示输出、自报或模型内心。不借 root 身份给子代理；无法确认归属保持未获取。旧 Claude v1 条件范围不改成 Codex。E3/E5。 |
| H6、安装/撤回 | 维持显式 opt-in、固定本仓库 CLI、事务/CAS/备份、无关 hook 保留、路径/链接防护及原生 opt-out；本任务不重新安装、不修改 hook trust、全局配置或宿主版本。不提高 10 秒预算。E6/E8。 |
| H7、A1/A3/A4/A9 | 已发生的真实 A/B、准确知识 v1/v2 认可和 continue 裁定保留当时范围与纠正关系，不重索要、不追溯升级。旧 Claude 仅源码/fixture。变化后的 observer 只补本 session 真实获取和一次新 epoch 恢复；fixture 不能冒充真实宿主。E5/E8/§8。 |
| A2/A5/A6/A7/A8/A10 | 继续覆盖分页/刷新/CAS、未激活/坏账本/坏 manifest、缺认可/空/skip、错返回/entry、局部独立、多路径、承诺变化与 coverage 调整、安装兼容；旧通过结果不覆盖新对象。现有适当测试内扩展。§3–§8。 |
| H8、A11/A12 | 当前精确对象的 actual coverage、decision/doc/verify、外部认可 plan/code 结论与原生 attestation 自洽，成本按真实 bytes/调用/延迟/重试报告。源码、安装、实际触发、获取、声明、检查及未验证边界分开。E4/E7/E8。 |
| 治理/公开边界 | append-only、纯 fold、固定 transition matrix、core 分层、pure-Git merge、完整 diff 和窄 attestation 豁免不变；ratified 正文不改，仅在确需时原生 reconcile。保留旧分支/HEAD/原件及无关目录/临时文件。不 push/PR/merge/release，不清理 PR #134 残留、不联系 Support、不改可见性、不重写 main、不删除原件、不新建用户聊天。E5/E7。 |
| 认可权限 | 计划授权不认可新知识或 disposition。recognition policy 生效机制若必须改变，先提出具体迁移差异；格式版本支持不得隐含扩大认可权限。§4/§5/§9。 |

执行投影精简前，以此映射和旧冻结文本逐段核对；未能证明被当前字段/必要正文覆盖的约束继续交付。当前完整 revision 成为新的授权对象后，历史过程可按索引恢复，不能借摘要丢失义务。

## 2. 顺序一：先完成正式计划修订，再编辑产品

按已确认的授权，在同一原 Change 走原生 plan revision；不另开一个抽象“证据平台”Change。

1. 保留原分支/HEAD 和本机原始材料，记录其定位，不再复制一套 114 文件备份。
2. 将本实施计划整理为一个正式 revision 文档，以原有效批准为 prior_approval 冻结完整计划对象。
3. 按当前 .harness/review-recognition.yaml 取得认可流程的精确计划结论并 import。Keepsail 本体不组织 reviewer；失败、空返回和 skip 不当批准。审查 pending 不编辑。
4. 原 READY_TO_MERGE 不充当新实施许可；获准 revision 后按原生生命周期进入可实施状态。旧 review/verification/code subject 继续只覆盖旧对象。

所有者已授权上述现行认可流程及获准后的本地实现/验证，不授权改变认可者/实质政策、全局配置、hook trust、发布或合并。若实现发现必须改变这些边界，明确提出新增差异。

## 3. 顺序二：先切断输入自我入库循环

### 输入接口

在现有选项上统一支持标准输入：
- review import <change> --evidence -
- implementation record <change> --assessment -
- knowledge propose --record -
- knowledge import --evidence -
- knowledge record --record -
- change context <change> --entry <entry> --statement -

文件输入保留为同等入口；不是建立两套业务协议。共用严格 JSON 解析、重复 key 检查和现行对象/认可验证。stdin 读取一次，knowledge 的 _input_digest 对实际输入字节计算。既有文件输入的路径限制不因 stdin 而放松。

CLI/adapter 的正常例子使用直接结构化传输，不要求用户选择 staging 目录。复杂输入也可由调用方在内存生成；不能把原文再写成一套“待提交证据”。必要外部来源是否已包含，按字段和消费者判断，不能仅因输入已导入就删掉引用原件。

### 自动 coverage

implementation record 在省略 coverage 时自动取得本 Change 的当前实际路径集合：可信基线到当前 HEAD 的完整 diff，加 staged/unstaged 的 tracked 变化；新增未跟踪文件由 agent 正常 git add 或 --include-path 显式纳入，不能把其他任务的未跟踪文件自动卷入。复用已有 canonical/path/Git manifest 能力，沿用现行 attestation JSONL 的窄豁免；不改变 gate 允许路径，更不能根据 gitignore 状态放宽门禁。

- rename/move 同时保留两端；删除、路径空格、显式新增文件、其他任务未跟踪文件和 Git 查询失败有回归。Git 冻结后的最终 diff 仍是完整性底线，不把尚未纳入的文件冒称已覆盖。
- 保存 coverage 的生成依据（base/head/工作区路径摘要），不让 agent 手写累计清单。
- 写入时核对输入对象未变化；最终验证仍按精确 code subject 检查 coverage 完整。自动 coverage 不授予 within_approval 语义批准。
- 显式传 coverage 仍可用并继续校验；缺理由/承诺关联不能自动补成“批准内”。
- 不把 docs/evidence/ 整体从 code subject 或门禁中豁免。

本阶段先不改 coverage 为通用增量事件；删除输入副本和自动枚举后测量剩余负担，避免提前重写 reducer。

主要文件：cli/review.py、cli/implementation.py、cli/knowledge.py、cli/change.py、core/approval.py 的现有 JSON/manifest seam；必要时仅增加一个共享输入小函数，不引入新框架。

## 4. 顺序三：获取记录改为必要事实，raw 仅供当场校验和未完成重试

新条目明确标记 schema/解释版本，例如 acquisition-observation/v2；不把任意非空对象塞进旧 original_receipt 字段。

持久内容：
- product/repository、Change、session/entry、delivery/manifest、authority/context 身份；
- 认可 producer、observer/transport 解释版本、实际 tool_use/root 关联；
- 完整页面集合及逐页内容摘要、实际完成状态；
- 每个准确知识版本与其正文摘要；
- not-understanding/not-compliance 的明确边界。

不持久内嵌：完整页面返回、原始 shell 命令、本机 cwd/用户路径、整个 callback 及其重复副本。知识正文、批准与限制仍由各自的原生版本记录准确恢复；不是只剩 hash 而丢正文。

执行流程：
1. 收到真实 PostToolUse 后，仍按当前严格条件核对身份、准确调用、成功结束、未截断、完整正文和摘要。
2. 原始返回只在当前入口的 ignored 临时区保留，供缺页、native finalize 和幂等重试使用。
3. 全部页完整且 authority 仍当前时，生成一份入口级观测结果，版本只记录关联；空集单独记录外层完成，不虚构知识版本。
4. 原生写入全部成功后，readiness 读取准确紧凑记录和当前 authority，不再每次重新解析 raw；完成紧凑记录持久化后清除本次 v2 临时 raw。
5. finalize 中断/部分失败保留 raw 以重试；清除不得先于正式记录成功。新 epoch 不沿用旧记录。
6. 新 v2 已失效/明确原生 opt-out 时清理其可再生临时 raw，留下必要失败类型/入口定位；不清理旧 v1 原件，也不新增定期 GC 服务或固定 90 天政策。

旧 v1 acquisition 和旧入口保持原读法；所有新写使用显式 v2。保持现有认可 observer 身份，不新增任意 agent 可自报成功的途径；本地 observer 信任边界不升级成密码学身份或语义理解保证。

主要文件：core/knowledge.py、core/context.py、daemon/context_hook.py、daemon/codex_context_hook.py、daemon/hook_entry.py，以及现有 gate CLI 输入。

## 5. 顺序四：正式结论单份保存，紧凑导出可持续增长

### review 去重

review_evidence_imported 持有完整原始结论、来源和 digest；plan/code 生命周期事件以 evidence_id/digest 关联，不再第二次携带同一正文。

writer validation、reducer 和离线 attestation 均解析同一份已导入结论；缺引用、摘要错、对象不匹配或非认可来源仍阻塞。读取既有包含 evidence 的历史事件，不改写历史。不借此取消计划/代码 review 或改变认可合同。

### checkpoint / attestation 新格式

采用显式格式版本，区分“原生事件原件”和“由原生记录生成的紧凑导出”。新格式包含：
- 当前 Change 必要生命周期/批准/检查/审查记录及关联；
- 可恢复的知识正文版本、认可、适用关系、delivery、声明/挑战、影响/裁定和执行结果；
- 紧凑获取事实，不带 raw callback；
- 准确 code subject、knowledge basis、当前义务校验结果；
- 可信 Git 基线 checkpoint 的身份与摘要，以及其后的新增事实。

实现原则：
- 不同时存全量事件和完整 report view；派生检查结果重算，仅保存必要预期摘要用于比对。
- 可信基线历史从 Git 读取，新 Change 只携带增量；首次 v2 从可信 v1 基线建立明确转换。不能每次把所有 Change 的完整知识事件再复制一遍。
- v1→v2 转换逐类保留规范事实及其来源身份；旧回调只提取当时已接受的获取事实。导出项明确是新表示，不沿用原始字节完整性的声明。
- 可信基线中已有的权威与历史事实，先规范化再核对不遗漏；candidate 不能靠更换格式删除约束/未决事项。新格式不重新授予历史认可或把失败变成功。
- 当前原 Change 尚未进入 main 的本地记录，先用原生 reader 验证，再由该原生导出生成新表示。旧日志/attestation 原字节保留在原分支/本地，不被覆盖。
- 对旧冻结计划的公开接续，以新获准 revision 中完整承诺/限制和明确替代关系为当前权威；旧批准保留其身份、历史含义和原件定位，不要求把旧计划中的本机叙述全部复制到新公共对象。新表示不声称公开 clone 能恢复每份旧载体的原始字节。
- 公开导出使用明确的逻辑关联标识连接 observation/session/turn，避免输出真实宿主标识和机器路径；内部真实身份核对不变，也不把这种映射宣传为身份认证。
- 同一语义输入重复导出返回相同内容，不向原日志追加同义 checkpoint。发生真正新增事实才产生新版本。
- 所有引用在 Git 闭包内可解析；无本机事件日志、断网的隔离 clone 仍能核验。不能用私有绝对路径或一个无法解析的 hash 充当正文。
- 验证责任仍是认可来源、对象、关系和明确结论，不要求 CI 重演宿主 raw 或审查者思考过程。

该项需要同时更新原生 exporter、对应 validator 和历史兼容读法，不是事后手工编辑生成物。如果无法在保留这些保证的前提下做有限改动，应报告具体冲突；不自动扩成证据平台。

主要文件：core/knowledge.py、core/events.py（仅必要声明）、core/reducer.py、core/emit_validation.py、cli/review.py、cli/attest.py、engineering/attestation.py；历史恢复代码仅在确有消费者时同步最小修改。

## 6. 顺序五：执行投影与热路径

### 冻结的结构化义务接续声明

以下唯一的 `keepsail-obligation-continuation` fenced JSON 是本计划的规范接口，随本 artifact 的原文摘要和完整 plan subject 一起冻结并接受相同精确 review。它显式声明上文覆盖表与本计划完整正文已接续列明旧 artifact 的全部当前义务；载体替换严格限于上文已声明的 H3/H6/H8，旧 Claude→Codex 取代、A/B 历史结果及其他边界沿已批准历史解释。本声明不独立授予批准，不扩认可者权限。

```keepsail-obligation-continuation
{
  "schema_version": "obligation-continuation/v1",
  "current_artifact": "docs/plans/2026-10-27-harness-knowledge-context-evidence-revision.md",
  "scope": "all-current-obligations-with-explicit-historical-replacements",
  "prior_approval": "approval:2026-10-28-harness-context-codex-revision-plan-01-84705107",
  "fallback": "retain-full-uncovered-lineage",
  "prior_approvals": [
    {
      "approval_id": "approval:2026-10-28-harness-context-codex-revision-plan-01-84705107",
      "subject_id": "plan:84705107e7caa0b29003fd7899f6cdbfc1049f5bc241dcdd38c938dd4d1a95b6",
      "artifacts": [
        {
          "path": "docs/plans/2026-10-27-harness-knowledge-context-codex-revision.md",
          "digest": "42b81e2ba405ff2e13b588df9bea4f14c3e164717a8f9e2e3de9c314e4862f5d",
          "continued_in": "docs/plans/2026-10-27-harness-knowledge-context-evidence-revision.md",
          "coverage": "all-current-obligations",
          "commitments": [
            "H1",
            "H2",
            "H4",
            "H5",
            "H7",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "E8"
          ]
        },
        {
          "path": "docs/product-foundations.md",
          "digest": "5c37dfe9ccd2cb57e8a3d31d1af4204512299a05922e4c2d988a80926241cfa6",
          "continued_in": "docs/product-foundations.md",
          "coverage": "entire-artifact-unchanged"
        }
      ]
    },
    {
      "approval_id": "approval:2026-10-27-harness-context-plan-01-78d618de",
      "subject_id": "plan:78d618dea2384d8b93aabe57e448453f75d261b71590ba09d7a6874c7bae87f7",
      "artifacts": [
        {
          "path": "docs/plans/2026-10-27-harness-knowledge-context.md",
          "digest": "44144697e8e9d5a6f0c7d424d11ad0862fd8cea38b0bdb652ec3972970821a7f",
          "continued_in": "docs/plans/2026-10-27-harness-knowledge-context-evidence-revision.md",
          "coverage": "all-current-obligations",
          "commitments": [
            "H1",
            "H2",
            "H4",
            "H5",
            "H7",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "E8"
          ]
        },
        {
          "path": "docs/product-foundations.md",
          "digest": "5c37dfe9ccd2cb57e8a3d31d1af4204512299a05922e4c2d988a80926241cfa6",
          "continued_in": "docs/product-foundations.md",
          "coverage": "entire-artifact-unchanged"
        }
      ]
    }
  ]
}
```

通用 reader 的固定解释规则：
1. 仅从当前有效批准的冻结 artifacts 中解析该专用 fenced JSON；共用严格 JSON/重复 key 验证。不读取当前工作树计划，不识别 Change 名或中文标题。先验证当前 approval/subject/artifact 摘要和认可结论；声明的 current_artifact 必须是承载该声明的已冻结 plan artifact。当前 artifact 本身的摘要由外层 subject 保护，不在自身内容中递归声明自己的 hash。
2. scope、schema_version 与 fallback 只接受此处明确版本；prior_approval 必须等于当前 subject 的准确 prior_approval。每份 prior 通过准确 approval_id、subject_id 和逐 artifact 的 path/digest 绑定到实际 lineage；每个 continued_in 必须属于当前 subject 的 artifacts。all-current-obligations 的 commitments 必须是当前 subject 中存在且非空的稳定 ID；entire-artifact-unchanged 还要求目标与旧 artifact 的 digest 相同。
3. 只有逐项匹配且完整接续的旧 artifact 才能在日常执行投影中改为历史身份/摘要/取代关系索引。语义上的“完整接续”由现行认可 review 判断，机械 reader 只校验其准确冻结来源、明确声明及关系。缺失、重复/歧义、未知版本、部分覆盖或身份失配不能获准压缩对应旧正文；保留未覆盖的完整旧正文并明确诊断。若该必要旧正文已不可获得，则显示 context unavailable/离线核验失败，不能用只有 hash 的索引冒充完整恢复。
4. 当前完整承诺/限制、ratified 约束、知识正文与认可、未决事项继续交付。普通 partial revision 或只有 prior_approval 的 revision 保持旧全文行为，不默认推断所有 revision 都是完整替代；历史获取及批准不被此声明重授或改写。
5. 紧凑导出保留当前冻结 artifact 中的同一声明、其完整 subject/认可结论，以及逐项对应的历史 approval/subject/artifact 身份和来源关系。原生 exporter 在原账本可用时先验证原记录和该绑定，再生成显式派生表示；可信 Git 历史可获得时仍逐项核对。离线 reader 用同一解释规则核对 Git 闭包内的当前正文、认可来源、绑定和必要历史索引；缺当前正文/认可结论/必要基线、伪摘要、缺或错历史绑定、缺未覆盖正文均失败。它验证当前工作依据和历史接续关系，不声称能恢复已由本 revision 明确替代载体的全部原字节。
6. 既有 context/attestation 回归增加：无声明、未知版本、只覆盖部分旧 artifact、错 approval/subject/digest、未知当前 commitment/目标 artifact、修改工作树不能改变冻结声明；合法完整声明减少旧全文，部分声明保留剩余全文。纯 Git fixture 验证导出保持同一绑定且任何缺项失败，不引入新的认可政策生效机制。

- 当前 packet 完整交付当前承诺/限制、ratified 约束正文、适用知识正文、待处理事项和当前认可关系。
- 冻结计划/上一代批准中的历史叙述不默认全文重传；先制作“旧义务→当前字段/必要原文段”的覆盖表，无法证明覆盖的段落仍交付。不能简单删除 artifact.content。
- 已解决历史以身份/版本/处置索引恢复，详情按需取得；未决事项不能只留数量。
- 一次动作共享 ledger/state/policy 的只读输入，动作前核对有效 revision/authority；变化则刷新或失败。不先引入跨调用缓存。
- CLI 与 hook 仍用同一 gate 判定；所有 patch 路径都检查，独立工作规则不扩大，未知归属仍未就绪。

主要文件：core/context.py、core/knowledge.py 的 report/投影 seam、daemon/hook_entry.py；不重写完整 agent loop。

## 7. 本次已有文件与候选历史

- 原分支、ba6f7ce、全部原始 A/B/失败/撤回材料保持可定位；不复制一套新档案，不改旧证据。
- 新候选从现场核验的可信 main 建立干净本地分支，按实际文件清单复用既有源码/测试/必要正式文档；不整段 cherry-pick 带私有原件的旧提交，不切走或覆盖无关工作。
- 14 份已收录 assessment、9 份 knowledge 输入、两份已收录 plan-review 输入、重复原文及中间 subject/输出不作为新候选的独立文件。
- 五份候选 review、两份独立 reject、A/B 原件中未原生收录的独有事实保全在原位置；新交付只留一份简短 dated 结论和准确来源，不自动作为每次 Change 模板。
- 原有效批准和历史限制在新 revision 中逐项接续；含旧全文的历史载体与新的工作承诺分别标明，不通过打码修改冻结批准。
- 新候选只有一份正式修订计划、一份简短验收/边界说明及必要原生 attestation；其余帮助、adapter 和 coverage 尽量修改已有文档，不创建新 docs/evidence 批次。
- 公开边界检查覆盖候选全部文件及解码后的 attestation 字段，不只扫描 evidence 目录。字段白名单结合真实本机路径检查；修复 macOS /private/ 合法临时路径误报，不以全文禁止 private 代替边界判断。
- 不重开 PR #134 残留清理、不改仓库可见性、不重写 main、不推送旧分支历史。

## 8. 验收、成本和完成标准

优先修改现有测试，新增测试文件仅限没有适当归属的集成场景。测试产物在临时工作区，不提交每次输出。

| 验收 | 必须观察到的结果 |
|---|---|
| 无额外文件输入 | 正常 review/assessment/knowledge/statement 可直接传输；导入后除正式原生记录，不生成要求提交的输入文件；stdin/文件等价且坏输入失败。 |
| coverage | 自动枚举覆盖提交/未提交/未跟踪、move/删除；不自动批准语义；最终 subject 不漏真实 diff；不豁免整个 evidence 目录。 |
| 获取事实 | 缺页/截断/失败/错 entry/root/版本不成立；全部完成才持久记录；native 写入失败保留重试材料；完成后清 raw，readiness 仍正确。 |
| 单份结论 | review 原文只在导入记录中出现一次；生命周期错引用/缺引用拒绝；历史完整正文记录仍可读。 |
| 纯 Git | 无 live ledger/operation-log、断网情况下核验成功；缺基线、缺正文、伪摘要、删历史权威或未决事项均失败。 |
| 持续迭代 | 用小型 native fixture 连续三个 Change：新增数据随新增事实增长；后一个导出不复制前几个完整正文/回调/view；重复导出新增事实数为 0。 |
| 实际集成 | 复用历史 A/B 作为历史证据；新 observer 格式补当前真实 root 的获取＋一次新 epoch 恢复，确认 raw 清理后仍就绪、旧 entry 不继承。只补变化边界，不默认重新开展完整 A/B。 |
| 正式完成 | decision/doc/verify 按现行配置通过；精确当前对象的外部 plan/code 结论及原生 attestation 一致。旧 2458 passed 不能替代。 |

拟议成本预算，均不是已测结果：
- 普通继续不新增手工整理/认可动作；人工知识认可、真实承诺变化授权仍按现行规则。
- 新 entry/manifest 新增第二版本只增加关联，不复制完整页面原文；以结构断言和序列化字节增量验收。
- 在本次同等有效义务 fixture 上，默认 packet 目标 ≤4 页；若必要正文无法满足，明确报告剩余必要内容，不删约束凑数。
- 同主机同账本做至少 5 次只读 gate 诊断，目标中位数 ≤2 秒、最大值 <5 秒；宿主原 10 秒预算不提高。测量 CLI/hook 分开，报告对象和样本。
- 全套必需验证在最终对象稳定后执行；修复期间只跑受影响回归，自然检查点运行 decision check --changed。对象变化影响既有验证时按必要范围刷新，不能为省成本沿用不匹配结果。
- 不制定任意证据行数硬上限；强制消除已识别的输入副本、回调复制、全历史重导出和自我扩大。只提供一份简短测量汇总，避免再造过程文档。
- 无任务级账单就不报金额；记录可观察的调用数、页面 bytes、延迟、重试和人工动作。

若真实宿主缺 root attribution，则保留未获取，不借身份、不要求反复创建聊天；把该新增验收保持未完成并说明具体缺项。人工 hook 信任仍由用户操作，本计划不授权修改 trust。无需用户提供不存在的“证据整理工作流”。

## 9. 已授权工作的边界

已经授权：同一 Change 的正式计划 revision、按现行合同取得外部明确结论、在批准后完成上述本地源码/文档/测试/原生格式修订、准备干净候选和本地验证。

不自动认可新知识、不更改既有 v1/v2 或 continue 的历史含义；不授权 push/PR/merge/release、全局配置、仓库可见性、删除旧原件或绕过门禁。若新格式需要改变 recognition policy 的生效/兼容机制，而非仅增加显式记录版本支持，应先报告具体迁移差异，不把政策迁移隐含在格式优化中。

工程细节由 agent 在 E1–E8 内处理。新的承诺、风险或认可权限变更才提交明确差异。精确 review/import 获准前不修改产品代码；pending review 不编辑。
