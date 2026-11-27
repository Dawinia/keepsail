---
change: 2026-11-27-git-subprocess-cost
stage: plan
---

# 策略信任在闸门处验证一次，消除每条命令的激活链回放与重复 Git 读取

关联 issue：#143（Windows 上 git 子进程成本拖慢 verify/done）。

## 问题

按 #143 "Reproduce first" 先做了测量（2026-11-26，本机 Windows）。测量脚本按 issue 要求未入库，
以下数字均为作者报告值，与 `2026-11-24-verify-timeout` 计划采用同样的说明方式。

- 单个测试 `test_recovery_plan_review_uses_only_the_signed_process_and_digest[False]`
  - 耗时 769 s，产生 9568 次 git 子进程，git 墙钟 711 s。
  - 产品代码 9492 次（99%），测试夹具 76 次。
  - 每次 git 进程平均 73–79 ms，即 Windows 的进程创建成本。
- 产品调用点集中在：
  - `scope_match.resolve_commit`：2756 次；
  - `git_objects.optional_regular_blob_bytes`：每个 blob 一次 `ls-tree` 加一次 `cat-file`，合计约 4400 次；
  - `approval._tree_entries`：560 次；
  - `approval._contract_base_candidates` 的 `for-each-ref`：412 次；
  - `attestation_v3_verify._verify_v2_activation` 及其递归回放。
- 同一次 CLI 调用中，约 75% 的 git 查询重复：参数相同，查询对象不可变。
- 单条命令的 git 次数随此前 v2 切换次数线性增长，例如 `done rotate-key` 477 次、`report` 每次 433 次。
  整个场景中命令数和链长同时增加，所以场景总量增长更快。
- 全量测试：
  - `-n 2` 用时 1917 s，全部通过；
  - 串行 2737 s，另有 73 个本机编码环境失败，与本问题无关；
  - 最慢的单个测试独占 774 s，也是 xdist 的关键路径。

## 根因

### 1. 每条命令都回放策略激活链

已批准计划 `2026-11-10-delivery-policy-transition.md` 规定："生效后，从新可信基线读取同一路径，
……以该旧基线和旧策略重放整个激活 v3"（第 47 行），对应的验收表第 137 行要求
"激活后再以新基线重放整个激活 v3"。

实现上，下列路径都在命令中调用 `verify_v2_activation` 或 `_verified_v2_snapshot`：

- `load_effective_v2`；
- `verify_v3_delivery(base)`（`attestation_v3_verify.py:414`）；
- `engineering/attestation.py:467` 生成 `policy_basis`；
- `recognition_contract_active`。

这些调用沿 v2 激活链递归，每层都重新验证计划批准、代码审查、旧必需检查和签名授权，
直到链首。链首是 initial 策略，或前任为 v1 时止于该 v1 基线（`attestation_v3_verify.py:341-349`）。
因此用到这些路径的命令，其成本为 O(v2 切换次数)，并随项目寿命增长。

这种回放的实际作用如下：

- 链首不是认证：
  - initial 是负责人声明的留存（`initial_policy.py`："not an authentication mechanism.
    The host must independently treat the selected target commit as trusted"，
    `confirmation_assurance: retained-owner-claim`）；
  - v1 链首同样只是基线上的文件。
  - 因此链最终锚定在宿主提供的可信基线上。
- 经过合并闸门的 PR，已由 `attest verify` 用基线上的旧策略单步验证过：
  - `committed_transition_required` 让 v2 基线下对策略、密钥、`verification.yaml` 的任何修改都要求 v3 验证
    （`transition_guard.py:102-106`），v1 基线下也有相应检测；
  - `verify_v3_delivery` 要求策略或密钥的变化携带签名授权，并逐项核对义务变化（第 438-484 行）。
- 全链回放比这多出的保证有两项：
  - 对不经闸门直接写入目标分支的未授权策略修改，在每条命令上同步拒绝；
  - 用当前验证器重新检查历史切换。
  这是一项风险取舍，并不是等价替换。负责人已在下文接受了这项取舍。

### 2. 同一调用内重复查询不可变事实

- `resolve_commit` 对完整 OID 反复执行 `rev-parse`。
- 每个 blob 读取都分别起 `ls-tree` 和 `cat-file` 两个进程。
- `_contract_base_candidates` 每次调用都执行 `for-each-ref`。
- 同一提交的树列表、祖先关系和 merge-base 被重复计算。
- 现有的 `activation_replay_scope` 只缓存激活结果，而且有两个缺口：
  - `report` 不在 `cli/__init__.py:155` 进入作用域的子命令集合里；
  - `sensors/dispatcher.py:203` 的线程池任务不继承 ContextVar。

## 修订后的信任模型

### 模型

- **T1 信任锚。** 宿主提供的可信基线即信任锚。
  - 基线上的策略快照经结构校验后，直接作为生效策略（见 C1）。
  - 本地命令使用本地基线 ref，执行的是较低保证级别的本地约束（例如 `done`、编辑闸门仍会拒绝）。
    它不是宿主权威，权威判断在宿主的合并闸门。
  - 本地命令从基线的 authority 文件取仓库标识和目标 ref，这只是本地提示，不构成独立认证。
- **T2 闸门处单步验证。** 每次信任变更（切换、恢复、轮换）在进入目标分支的 PR 的合并闸门处，
  用宿主提供的基线上的旧策略验证一次，不回放基线自身的来历。
  基线新鲜度由宿主负责：宿主必须提供当前目标分支提交。若托管规则允许以过时 base 合并，
  由 T3 的审计检出（C3 情形 2 的祖先关系与状态一致性要求）。
- **T3 增量审计。** 目标分支前进后，`policy audit` 对新增区间内每个策略状态变化做单步验证（C3）。
  - 它只能检出，不能阻止。
  - 审计结果不被本地命令或合并闸门读取，它们独立信任基线。
  - 全量审计（从根提交起）不在任何命令的常规路径上，需要时手动运行，例如验证器修复之后。
- **T4 记忆只用于加速。** 以不可变对象 OID 为键的查询结果可以在进程内复用。
  未命中时重新计算，正确性不依赖缓存。

### 威胁模型与保证边界

- 新旧模型都运行来自仓库自身的验证器代码：闸门安装的是 `BASE_SHA` 的验证器，本仓库本地是可编辑安装。
  能直接写目标分支、同时修改验证器或 CI 工作流的人，旧的全链回放和新的审计都防不住。
  这类写入只能由宿主的分支保护（禁止直接推送和强制推送）阻止，它属于宿主证据层，不由本计划提供。
- 假设的宿主控制：
  - 目标分支受保护，只能经 PR 合并；`attest-verify` 是必需检查。
  - 审计工作流由 push 事件触发，属于事后运行的工作流，不能成为合并的必需检查；它的失败通过工作流状态和通知暴露。
  - 这些控制是否真实生效，仍须在托管平台单独验收。
- 本计划针对的是：不经闸门写入策略文件、但未改动验证器或 CI 的写入。
  对这类写入，保证从"每条本地命令同步拒绝"变为"目标分支前进后由审计检出"。
- 初次采用 v2 时，在首次审计运行之前，本地命令信任本地基线上的 initial 策略；
  之后依然独立信任基线（同 T3）。
- 验证器修复后，旧激活不再在每条命令上被自动复核，需要手动运行一次全量审计。

### 负责人接受

负责人于 2026-11-27 在本次交付讨论中接受了上述保证边界变化。经过是：
- 讨论中给出两个方案：方案 1 保留 v2 能力，只把验证移到合并闸门；方案 2 重审 v2 本身。
  负责人选择"先1"，方案 2 留待本次之后单独讨论。
- 计划审查拒绝后，再次逐项列出第 (1) 直接写入改为事后检出、第 (2) 首次审计前信任 initial、
  第 (3) 验证器修复需手动全量审计，以及上述威胁模型，负责人回答 "Accept"。

### 本计划取代的已批准承诺

- `2026-11-10-delivery-policy-transition.md` 第 47 行"生效后……以该旧基线和旧策略重放整个激活 v3"，
  以及验收表第 137 行对应的"激活后再以新基线重放整个激活 v3"。改为：闸门单步验证加审计单步验证。
  该计划的其余承诺本计划不改变，包括签名授权（含签名绑定完整基线 SHA）、义务保留、恢复、轮换、初始信任、离线验证，以及"删除或损坏已激活策略不能降级"。
- **已存在的阻断（不是本计划造成的）：** 2026-11-10 计划第 100 行规定的"已启用旧契约仓库 → v2"升级路径，需要先在 v1 下建立 authority。但自 #140 起，`transition_guard.py:91-100` 拒绝在 v1 下启用 authority（"initial enabled trust needs separate owner establishment"），而仓库没有受认可的负责人信任建立流程。
  - 本计划不改变这一点：闸门照旧，审计情形 1 与闸门的 v1 守卫一致。
  - 这一缺陷与 C8 的必需检查锁定同源，归入负责人已安排在本次之后的 v2 产品讨论（负责人 2026-11-27 的"先1"及"Drop C8 here"）。本计划不声称该路径可用。
- `2026-11-24-verify-timeout` 退出条件：
  - "低于 2000 s 则在后续 Change 内恢复串行和 2700 s"一项：推迟，见 C8。
  - 测量位置：从"计划中"改为 PR 与评估记录（解释性偏离，见 C8）。
  - 测量义务本身与 2026-12-31 兜底条款不变。

## 承诺

### C1 读取生效策略不再回放激活链

`load_effective_v2`、`recognition_contract_active` 及其全部调用者改为直接读取可信基线上的策略快照（经 `trusted_policy_snapshot`，见下文），不再调用激活回放。调用者包括 `no_review`、`review_basis`、`transition_guard`、`policy_authority`、`engineering/delivery_policy`（`report` 经由它）、`engineering/attestation` 的格式选择、`verification_runner`、`cli/pr`。

保留并关闭失败的校验：
- v2 解析与 `policy_digest`；
- `policy-authority.yaml` 解析，以及仓库标识、目标 ref 一致。本地命令的仓库标识与目标 ref 本就取自该 authority，所以这一项在本地是自我比较，只是提示，不构成 `d-policy-replay-offline-v2` 所说的独立提供的身份；闸门上的这两项由宿主独立提供。
- `plan-decision` 用途；
- 以基线 `verification.yaml` 重算 `required_checks_digest` 并比较。
- initial 策略：`.harness/policy-initial-trust.json` 须满足：
  - 存在，可严格解析，恰含规定字段，且 `version` 为 `policy-initial-trust/v1`；
  - `repository_id`、`target_ref` 与 authority 一致；
  - `policy_digest` 等于当前策略摘要；
  - `initial_commit` 是完整 OID，不等于基线，且是基线的祖先（一次 `merge-base --is-ancestor`）；
  - `owner_confirmation` 恰含 `owner`、`statement`、`evidence_reference`、`original_evidence` 四个非空字符串。

  这比原 `verify_initial_policy` 的检查少：
  - 不扫描先前启用策略的历史；
  - 不核对确认文件的唯一引入提交；
  - 不在 initial 提交处重算确认（因此不核对 `authority_digest`，密钥可能已轮换）。

  这些检查移到审计（C3 情形 4）。本地只保留上述 O(1) 检查，并有对应测试。

实现方式：
- 以上全部校验放在一个共享函数 `trusted_policy_snapshot(root, base, repository_id=None, target_ref=None)` 中，位于 `core/effective_policy.py`。
  - 它用一次 `ls-tree` 加一次 `cat-file --batch`，同时读取 authority、策略、`verification.yaml` 和确认文件四个 blob。
  - 未提供仓库标识时，用 authority 中的值作为本地提示。
  - 然后在内存中执行 `read_policy_snapshot` 的同一套校验：`read_policy_snapshot` 拆为"读取"与"校验"两部分，校验语义不变；再执行 initial 检查。
  - git 进程数：transition 基线为 3（`rev-parse` 校验 OID、`ls-tree`、`cat-file --batch`）；initial 基线另加一次 `merge-base --is-ancestor`，共 4。
- 凡是把某个提交当作可信基线读取策略的路径，都调用它，包括 `load_effective_v2`、`verify_v3_delivery` 的 base、`verify_attestations` 的 base。
- 候选 head 的快照仍只调用 `read_policy_snapshot`，它同样批量读取三个文件。
- `effective_policy` 与 `attestation_v3_verify` 之间改为函数内延迟导入，避免导入循环。删除 `_verified_v2_snapshot`、`_verified_v2_activation`、`_activation_results` 与 `activation_replay_scope`；相应地重写 `tests/unit/core/test_activation_replay_scope.py`，改为测试 C5 的调用作用域。

`continued_plan_basis` 对前任 v2 基线也只读快照。

更新 `policy_snapshot.py` 与 `load_effective_v2` 的文档字符串：快照的权威来自宿主可信基线，结构校验本身不授予权威。

### C2 合并闸门只验证 base→head

`verify_v3_delivery` 把第 414 行对 base 的激活回放替换为 `trusted_policy_snapshot(base)`，并使用它返回的快照，删去第 416 行对同一 base 的重复读取。因此闸门仍会对确认文件缺失、畸形或不符的 initial 基线关闭失败。`verify_v3_transition` 不变。授权、义务变化、恢复依据、审查证据、必需检查、代码对象与 attestation 新增检查全部保持。

`verify_attestations` 判断 `active_v2` 的方式不变：仍读取 base 的策略版本，据此要求 v3 证据并选择 `verify_v3_delivery`。区别只是用 `trusted_policy_snapshot` 代替回放。

`verify_attestations` 不再调用 `verify_v2_activation`。`attest verify` 输出的 `policy_basis` 改为可信基线依据，字段为 `basis: "trusted-base"`、`trusted_base`、`policy_digest`、`required_checks_digest`、`activation`（策略中的定位对象）。回放产出的 `activation_commit`、`predecessor_base`、`initial_confirmation`、`confirmation_assurance`、`authority_rotation` 移到审计输出，其中 `authority_rotation` 保持原对象 `{change, commit, predecessor_base, authority_digest}`。CLI 参考与断言这些字段的测试（`test_initial_policy.py`、`test_delivery_policy_transition.py`）相应更新。

`verify_v2_activation` 作为公共入口删除，单步验证逻辑移入审计模块。同时：
- 删除 `engineering/attestation_v3.py:17` 的再导出；
- 修改 `tests/unit/core/test_policy_obligations.py` 中对它的 monkeypatch；
- 更新 `transition_guard.validate_delivery_obligations` 文档字符串中"经激活链核验"的描述。

### C3 `keepsail policy audit`

命令：`keepsail [--json] policy audit [--from <commit>] --to <commit> [--v1-since <commit>|root] --repository-id <id> --target-ref <ref>`

**区间：**
- 遍历 `git rev-list --first-parent --reverse <to> ^<from>`。
- `--from` 必须是 `--to` 的祖先，否则失败并提示做全量审计。`--from` 可以不在第一父链上，此时以 rev-list 结果为准。
- `--from` 等于 `--to` 时，区间为空，通过。
- 省略 `--from` 或其值为全零 OID 时为全量审计：从根提交起；仓库是浅克隆时失败。
- 每个提交与其第一父提交比较；根提交与"空状态"比较。

**策略状态** S(C) 由 C 中以下内容组成：
- `review-recognition.yaml` 的解析结果（不存在、v1 及其摘要、v2 及其摘要）；
- `policy-authority.yaml` 的摘要（或不存在）；
- `verification.yaml` 的必需检查契约摘要，文件不存在时取"不存在"；
- `policy-initial-trust.json` 的字节（或不存在）；
- `.harness/attestations/v3/` 下每个文件的路径与 blob OID 映射。

前四项合称"策略四项"。attestation 映射只在一种情况下用作变化点：P 中已存在的某条 v3 attestation 在 C 中被修改或删除（情形 6）。新增 attestation 属于正常交付，不单独构成变化点。

读取时按普通文件 blob 校验。文件存在但畸形时，退出码为 2；文件被删除时，按"不存在"进入变化点判定，例如 v2 下删除 `verification.yaml` 属于情形 5 的发现。

**变化点判定**（S(C) ≠ S(P)，P 为第一父提交）：

1. **v1 区间。** 两侧都没有 v2 策略，也都没有初始信任确认文件；变化只落在 v1 或未启用的策略状态内，authority 变化也包括在内，由 v1 守卫判定。
   - **v1 基线：** `--v1-since <commit>`。
     - 提供了 `--from` 时，默认取 `--from`，即增量审计中的一切 v1 变化都按规则判定。
     - 全量审计必须显式给出这个参数，`root` 表示从根提交起全部判定。
     - 工作流：全零 `before` 的首次推送使用 `--v1-since root`；`workflow_dispatch` 的全量审计以必填输入 `v1_since` 提供。
   - **基线之后的变化：** 指从基线提交不可达的提交，与 rev-list 的区间语义一致。`--from` 不在第一父链上时，同样按可达性归类。这些变化 按今天闸门的 v1 规则判定，即对 (P, C) 调用 `committed_transition_required`。
     - 返回 true 或抛错（例如删除 v1 策略、替换或删除必需检查、在 v1 下启用 authority），记为发现。v1 仓库无法合法完成这些修改。
     - 返回 false（例如新增检查），列为信息项。
   - **基线及之前的变化（从基线可达）：** 列为信息项。它们当时由 PR 审查和当时生效的规则把关，不把今天的守卫追溯套用上去。
   - 与原回放相比：原回放不验证 v1 历史；新审计对基线之后的 v1 区间增加了检出。
2. **v2 切换或恢复（以交付为单位）。** 第一父链提交 C 使策略摘要变化，且新策略为 `{kind: transition, change: X}`。
   - **定位交付：**
     - I：X 的 attestation 在 `--to` 历史中的唯一引入提交（`_introduction_commit`）。
     - B：attestation 记录中的 `trusted_base`。
     - 交付范围 R：从 I 可达、从 B 不可达的提交。
   - **要求：**
     - B ≠ I，且 B 是 I 的祖先（沿用原回放检查）。
     - I 是 `--to` 的祖先或等于 `--to`。
     - C 与交付相关，满足以下之一：
       - C 属于 R（快进或 rebase 合并，C 可以早于 I）；
       - C 是合并提交，其第二父链包含 I。
     - 主线前驱 M：从 C 沿第一父方向（向历史方向）回溯，第一个不属于 R 的提交（合并提交即其第一父）。要求 B = M，与闸门的 `record["trusted_base"] == base_sha` 及 2026-11-10 计划"签名绑定完整基线 SHA，基线前进须重新签名"一致。B ≠ M 时（即便策略四项相同），授权针对的是过时基线，记为发现。
     - attestation 在 `--to` 中的字节与在 I 中相同。
     - S(I) 的策略、authority、检查三项等于这次交付落到主线后的状态。这一状态取 R 在第一父链上的最后一个提交，或合并提交 C。
   - **I 处的内容与闸门一致：** 闸门在 PR head 重算代码主题，要求非 attestation 内容与已记录的代码主题完全一致（`attestation_replay.py:157-184`）。因此在闸门接受的交付中，I 之后只能修改 attestation 路径，策略文件在 I 处已是最终状态。在 attestation 之后才修改策略的交付会被闸门拒绝，审计中则表现为 S(I) 与落地状态不符，记为发现。
   - **单步验证：** 按 B 的策略版本，调用 `verify_v3_transition(base=B, head=I, _historical_replay=True)` 或 `verify_v3_delivery(base=B, head=I, _historical_replay=True)`，都不递归验证 B 的来历。结果中的目标策略摘要须等于 S(I) 的策略摘要。
   - **可激活性：** `_historical_replay=True` 只用于义务变化的历史语义，它会跳过 `require_activatable_policy`。因此审计对目标策略另行调用 `require_activatable_policy`：
     - 属于新增区间的变化点（从 `--from` 不可达，即增量审计中的全部变化点）：不可激活记为发现，与闸门一致。
     - 全量审计中早于 `--from` 语义的历史变化点（全量审计没有 `--from`，以 `--v1-since` 为界）：不可激活记为警告。这样，验证器升级后收紧的规则不会把已合法激活的历史判为违规，但仍会显示出来。
   - **每个策略变化点独立判定，不合并。**
     - 一次交付的第一父链上只允许出现一个策略、authority 或检查的变化点，也就是这次切换本身；只改动 attestation 或非策略文件的提交不构成变化点。
     - 快进合并使第一父链上出现多个策略变化点时（例如同一 PR 内先改出中间策略 X，再改到 Y），中间点 X 没有自己的已验证依据，记为发现，提示"多步策略交付须使用合并提交或 squash"。审计在这一点上比闸门严格：闸门只验证 PR 的最终状态。
     - 同一交付内加入的初始信任确认是情形 4 的独立变化点，仍执行 `verify_initial_policy`，不归入切换验证。
3. **密钥轮换。** authority 摘要变化，策略与检查不变。
   - 在落地状态中枚举 v3 attestation，要求恰有一条 `rotate_key` 记录指向新的 authority 摘要，沿用 `_verify_current_rotation` 的匹配规则。
   - 按情形 2 的方式定位 I、B、R、M 并检查（包括 B = M，以及 S(I) 的策略、authority、检查三项等于落地状态），以 `verify_v3_delivery(..., _historical_replay=True)` 单步验证。
4. **initial 建立。** 
   - P 无启用策略而 C 出现 `{kind: initial}` 的 v2 策略时：执行 `require_no_prior_enabled_policy(C)`。
   - `policy-initial-trust.json` 首次出现的提交上：执行 `verify_initial_policy`。它自行核对 initial 提交是更早的可达提交、不存在先前启用的策略、确认文件唯一引入且未被修改，因此不依赖之前区间的状态。
   - 合法的建立顺序：
     1. 提交 initial 策略与 authority；
     2. 在之后的提交中加入确认；
     3. 之后才可以做切换。

     前两步可以分在不同的推送中。确认早于 initial 策略，或与它在同一提交中时，`verify_initial_policy` 会拒绝（它要求 initial 提交早于确认的引入提交），记为发现。初始信任文件的任何变化都不会落入情形 1。
     - 区间结束时已有 initial 策略但还没有确认，列为"initial 待确认"警告，不计为发现。
     - 在此期间，本地命令会因 C1 要求确认文件存在而关闭失败。
5. **其它变化，一律记为发现。** 包括：
   - v2 被删除、禁用或降级为 v1；
   - authority 被删除；
   - 检查摘要变化但未伴随授权切换；
   - 确认文件被修改或删除；
   - 不符合上述任何情形的组合。
6. **已有 v3 attestation 被修改或删除，记为发现。** 不论该 attestation 是否属于当前生效的策略，v3 记录都只能追加。这一条取代原回放中"生效 attestation 自引入后未被修改"的逐命令检查，并在增量审计中同样生效。

**输出与退出码：**
- `--json` 输出 `{"range": {"from", "to", "full", "v1_since"}, "points": [...], "findings": [...], "warnings": [...], "informational": [...]}`。
  - `findings`、`warnings`、`informational` 都是 `{commit, case, message}` 对象的数组，每一项对应 `points` 中 `result` 为 `finding`、`warning` 或 `informational` 的点。
  - `result` 取值为 `pass`、`finding`、`warning`、`informational`。
- 每个变化点包含：
  - `commit`、`case`（`v1-interval`、`transition`、`recovery`、`rotate_key`、`initial`、`initial-confirmation`、`other`）、`result`；
  - 依据字段 `activation_commit`（I）、`predecessor_base`（B）、`change`；
  - initial 确认点另含 `initial_commit`、`initial_confirmation`、`confirmation_assurance`；
  - 轮换点另含 `authority_rotation` 对象 `{change, commit, predecessor_base, authority_digest}`；
  - 归入某次交付的变化点另含 `delivery`（该交付的 I）。
- 文本输出与 JSON 内容一一对应。
- 0 表示无发现；1 表示有发现；2 表示参数错误、git 错误、浅克隆或畸形输入。任何错误都不会被当作通过。

**离线：** 模块为 `core/policy_audit.py`，在 `d-policy-replay-offline-v2` 的检查路径内，只用本地 Git。

### C4 目标分支前进时运行审计

- **本仓库：** 新增 `.github/workflows/policy-audit.yml`。
  - 触发：`push` 到 `main`，审计区间为 `before..after`；`workflow_dispatch` 做全量审计。
  - 使用 `fetch-depth: 0`。
  - 验证器在网络隔离命名空间中运行，方式同 `delivery-policy-offline`。
  - 仓库标识与目标 ref 取自 `github.repository` 与 `github.ref`。
- **生成工作流：** `templates/keepsail_workflow.yml` 的 `on-merge` 中加入同样的审计步骤。
  - 该模板固定安装已发布的 CLI 版本，因此审计步骤先探测 `policy audit` 是否存在（与模板现有的 `--repository-id` 探测方式相同）；不存在时输出"当前安装的版本不支持审计"并跳过，不伪装为通过。
  - 发布含该命令的版本后提升固定版本，不在本计划范围内。
- **采用说明：** 文档要求采用 v2 或升级到含审计的版本时，手动运行一次全量审计。
- **本次交付：** 在本仓库运行一次全量审计并记录结果，命令为 `keepsail --json policy audit --to main --v1-since 24d955b --repository-id Dawinia/keepsail --target-ref refs/heads/main`。
  - 选 `24d955b` 的原因：它是 #140 的合并提交，今天的 v1 守卫从这里起生效；也是本计划起草时主线上最后一个改动策略相关守卫的提交。
  - 本仓库只有 v1 历史。预期 `findings` 为空。
  - `informational` 应恰好列出当前第一父链上改动策略文件的提交：`443fbbd`、`d33eeea`、`86d2d84`、`2021717`、`a1512ca`、`5549b4a`。它们都在 `24d955b` 之前。
  - 本仓库的 CI 审计从此按增量运行：`--v1-since` 默认等于 `before`，之后任何非法的 v1 修改都记为发现。
- **既有 v2 采用者：** 本仓库所知范围内没有。在发布包含审计的版本之前，生成的工作流不会自动审计，文档要求采用者手动运行。
- **审计不是合并的必需检查**，原因见威胁模型。

### C5 进程内复用不可变 Git 事实，批量读取

- 记忆层放在 `core/git_objects.py` 中，该文件已在 `d-policy-replay-offline-v2` 的检查路径内。`git_objects.py` 对 `ApprovalError` 的导入改为在函数内延迟导入，以免出现 `scope_match → git_objects → approval → scope_match` 的导入循环。它是进程内、带锁、按条目数限容的 LRU，上限 4096 条；只存不可变值（bytes、str、bool、tuple）。
  - 键包含仓库根的规范路径和完整 OID。
  - 缓存对象：完整 OID 的 `resolve_commit`；`(commit, path)` 的原始 git 查询结果（树条目的模式、类型和 OID，以及 blob 字节），"不存在"也是一种成功查询结果，同样缓存；是否为普通文件、能否解析等结构校验每次重新执行，不缓存；提交的树列表；`is_ancestor`；`merge_base`。
  - 只缓存成功的 git 调用结果，git 失败不缓存。
  - 符号 ref（`HEAD`、分支名）不缓存。
  - 假设：单次进程运行期间，不在同一仓库执行 fetch、unshallow、replace 或 graft，keepsail 自身也不执行；文档字符串写明这一点。
    - 若在进程运行期间由外部并发改写这些历史，`is_ancestor` 与 `merge_base` 的缓存结果可能过时。这是已接受的限制，写入 `docs/limitations.md`。
- `read_policy_snapshot` 内部改为一次 `ls-tree` 加一次 `cat-file --batch`，读取它所需的三个文件。它的校验语义和错误行为不变（"原样保留"指语义）。`trusted_policy_snapshot` 的 initial 检查另外读取确认文件。
- `_contract_base_candidates` 的 `for-each-ref` 结果在一次 CLI 调用的作用域内复用，因为它对应可变 ref。
  - 作用域由顶层 CLI 为所有子命令进入，包括 `report`。
  - 作用域对象带锁；dispatcher 提交任务时用 `contextvars.copy_context().run`，让线程共享同一个带锁对象。
  - 假设：keepsail 命令在一次调用内不移动这些 ref。
- 不在范围内：`file_text_at_commit` 以外的 `git diff` 与 `git log` 调用不做缓存，不承诺消除所有重复。

### C6 回归守卫

测试中包装 `subprocess` 计数 git 进程，判断条件不依赖计时。

- **单元级上限。**
  - 在有 3 次 v2 切换的夹具上（基线为 transition 策略），以完整 OID 首次调用 `load_effective_v2`，git 进程数不超过 3。
  - 在 initial 基线夹具上，首次调用不超过 4（多一次祖先检查）。确认文件与另外三个文件在同一次批量读取中。
  - 同一进程内以同一 OID 再次调用，为 0。符号 ref 不缓存，所以这个目标只针对完整 OID。
- **命令级链长无关。** 同类夹具分别在 1 次和 3 次 v2 切换之后执行 `done`、`attest verify`、`report`、`review import`、`status`，每条命令的 git 进程数须相同。
- **作用域重置。** 两次独立的 CLI 调用之间，`for-each-ref` 结果不被复用。
- **测试隔离。**
  - 记忆层提供仅供测试使用的 `clear()`，计数测试开始前调用；每个测试使用独立的临时仓库根。
  - 1 次与 3 次切换的夹具由同一构造函数生成：3 次夹具在 1 次夹具之后追加两次切换，再追加相同的一次普通交付。被测命令都针对这次普通交付，参数相同。
  - 夹具的必需检查是不调用 git 的 `python -c` 命令。
  - 计数从夹具构建完成后开始，只统计被测命令调用期间启动的 git 进程。
- **未调用历史验证。** 计数之外，再用 monkeypatch 把只服务于历史验证的函数替换为抛错函数，执行上述五条命令（普通交付）。它们必须成功，证明命令路径不调用历史验证。这些函数是 `_introduction_commit`、`_verify_current_rotation`、`require_no_prior_enabled_policy`、`verify_initial_policy`，以及审计的单步入口。这项测试只是辅助，回归守卫的主要证据是上面的进程计数。

### C7 拆分策略切换场景测试

- 把 `test_delivery_policy_transition.py`（797 行，单个参数化测试）按阶段拆成相互独立、各自构建前置状态的测试，放在 `tests/integration/lifecycle/policy_transition/` 目录下：
  - 恢复授权；
  - 负例；
  - 已安装基线验证器；
  - 继续计划；
  - 生效后的普通交付；
  - 下一次切换；
  - 密钥轮换；
  - 报告与状态。
- 原先依赖每条命令回放才能发现的历史篡改负例（激活 attestation 在引入后被修改、前任不可达等），迁移为 `policy audit` 测试。
- `test.yml` 的 `delivery-policy-offline` job 改为运行该目录和审计测试文件。
- 不新增 `e2e` 标记，测试在本地和 CI 的覆盖范围不变。

### C8 本地验证命令不变，执行既有测量义务

本计划不修改 `.harness/verification.yaml`，原因如下：
- 自 #140 合并后，`transition_guard` 把删除或替换已有必需检查定义视为必须经签名 v2 切换授权的义务变化（`transition_guard.py:121-126,191,290`）。
- 本仓库为 v1，没有签名密钥，在 v1 下新增密钥也会被拒绝。
- 负责人于 2026-11-27 决定本次不处理这一点："Drop C8 here"。

**对 `2026-11-24-verify-timeout` 退出条件的处理（取代其中一项已批准承诺）**

该退出条件要求本 Change：
- 在计划中包含一次完整串行全量测量；
- 若低于 2000 s，在本 Change 内恢复串行命令和 2700 s 超时。

本计划：
- **测量：照常执行。**
  - 实施前的测量已写入"问题"一节：串行 2737 s，另有 73 个本机编码环境失败，因此不能作为合格测量。
  - 实施后的合格串行全量测量，写入 PR 说明和 `implementation record` 的评估记录。批准后的计划主题保持冻结，不回写本计划。
  - 这与 2026-11-24 原文"在其计划中包含测量"的位置不同：实施前无法得到优化后的测量值。本计划把这一点列为对该条款的解释性偏离，见"本计划取代的已批准承诺"。
- **恢复：推迟，不在本 Change 内执行。**
  - 修改必需检查定义会被上述守卫拒绝，本 Change 无法合法完成恢复。
  - 负责人在被告知"2026-11-24 的退出条件（恢复串行 / 2700 s）同样被阻断"之后，选择了 "Drop C8 here"。该选项写明 "Leave verification.yaml as it is. Still run the serial measurement the 2026-11-24 plan requires and report it."
  - 因此，"低于 2000 s 则在本 Change 内恢复"一项被推迟，留待后续 v2 产品讨论让必需检查变更成为可授权之后处理。
  - `2026-11-24-verify-timeout` 中 2026-12-31 由负责人重新评估的兜底条款不变。

负责人此前授权的"e2e 移出"也不在本计划中执行。"v1 下必需检查被锁定"这一发现，归入负责人已安排在本次之后的 v2 产品讨论。

### C9 文档与决策

- `docs/getting-started.md`：初始策略段落改为说明 initial 的历史检查由审计执行，并补充采用时的全量审计。
- `docs/implementation-architecture.md`：§9 写入 T1–T4、威胁模型与保证边界。
- `docs/limitations.md`：写明绕过闸门的写入只能事后检出，以及不防篡改验证器或 CI 的写入者。
- `docs/product-architecture-coverage.md`：增加一条带日期的更新。
- `docs/cli-reference.md`：由 `doc check --fix` 重新生成。
- 用 `keepsail decision new` 提交一份 proposed 决策："生效策略从宿主可信基线读取；策略历史只在闸门单步验证与审计中验证"。是否 ratify 由负责人决定。

## 不做

- 不重新评估 v2 交付策略的机制，留给负责人安排的后续产品讨论。该讨论同时处理 C8 记录的锁定问题。
- 不做跨进程或跨机器的持久缓存。
- 不改变 attestation、授权记录或策略文件格式。
- 不改变 v1 策略的行为。
- 不修改 `.harness/verification.yaml`。
- 不发布新版本，也不提升模板固定的 CLI 版本。

## 测试

- **C1**
  - 有多次切换的仓库中，读取生效策略不调用回放（可由 C6 证明）。
  - 以下情况关闭失败：基线策略摘要被篡改；检查摘要不一致；authority 的仓库或 ref 不符；initial 缺确认文件、确认的摘要或仓库标识不符、`initial_commit` 等于基线或不是祖先、`owner_confirmation` 字段不全。
  - 删除或损坏基线上已激活的策略不能降级为 legacy。
- **C2**
  - 现有闸门正例和负例保持通过。
  - 闸门层的 initial 检查：base 为 initial v2 策略，而确认文件缺失、畸形、仓库或 ref 不符、`policy_digest` 不符、`initial_commit` 不是祖先时，`attest verify` 退出 2。
  - `active_v2` 判断保持：base 为 v2 时，普通交付仍要求 v3 证据。
  - `policy_basis` 新字段有断言。
  - v1→v2 切换闸门路径不变。
- **C3**
  - 通过的情形：
    - initial（建立加确认，含分两次推送）、切换、恢复、轮换、空区间；
    - `--v1-since` 及之前的 v1 区间变化列为信息项，包括替换 v1 必需检查；
    - 基线之后在 v1 区间新增检查，列为信息项；
    - 合并提交交付，其中 I 位于第二父链上；
    - `--from` 不在第一父链上的区间。
  - 本仓库的全量审计（`--v1-since 24d955b`）：`findings` 为空，`informational` 恰为 C4 列出的六个提交。
  - 多提交交付（单个策略变化点）：先改策略后加 attestation 的快进合并；合并提交交付。
  - initial 确认与切换的时序：
    - 闸门负例：切换 PR 的 base 是还没有确认文件的 initial 策略，`attest verify` 退出 2（`trusted_policy_snapshot(base)` 失败）。
    - 审计正例：确认先单独落到主线；之后的切换交付以确认之后的提交为 B = M。两个变化点分别验证，都通过。
    - 审计负例：切换绑定的 B 缺少确认文件，记为发现。
  - 记为发现的情形：
    - 直接追加的未授权策略修改、检查删除、authority 替换；
    - 禁用、删除 v2 或将其降为 v1；
    - attestation 引入后被修改；
    - 前任不可达；
    - B 是 P 的祖先但不是 I 的祖先；
    - B ≠ M 的过时基线授权，分两种：策略四项不同；策略四项相同，但主线已经前进了非策略提交；
    - 目标策略不可激活（例如 `code_review: scope` 搭配 `keepsail-baseline/v1`）：增量审计中记为发现；对照组 `full`/v2 通过；全量审计的历史点上，记为警告；
    - v2 下删除 `verification.yaml`；
    - attestation 之后又修改策略的交付（S(I) 与落地状态不符）；
    - 快进合并的多步策略交付：中间点 X 无论有没有自己的 attestation，都记为发现；
    - 被篡改的初始确认（`version`、字段或摘要不符）；
    - 增量审计中，后续推送修改或删除已有的 v3 attestation，包括生效策略的激活记录；
    - v1 区间内启用 authority；
    - 基线之后的 v1 区间内：替换或删除必需检查、删除 v1 策略、启用 authority；
    - 全量审计缺少 `--v1-since`（退出码 2）；
    - initial 确认文件被修改或删除。
  - 警告而不计为发现的情形：区间结束时 initial 待确认。
  - 退出码 2 的情形：`--from` 非祖先、浅克隆全量审计、畸形策略文件、git 错误。
  - 以上测试纳入网络隔离 job。
- **C4**
  - 工作流结构测试：触发条件、`fetch-depth: 0`、`before`/`after` 映射、全零 `before` 转为全量审计、模板探测分支。
- **C5**
  - 符号 ref 不缓存；失败不缓存；容量上限。
  - 多线程并发读写同一键的结果正确。
  - 批量读取遇到非普通文件、缺失路径或异常输出时失败。
  - `report` 与线程池任务在作用域内。
- **C6、C7**：见上文。
- **全量**：`keepsail verify`、`decision check`、`doc check` 通过。

## 验收测量

实施后用同一方法（不入库）测量，并写入 PR 说明：

- **拆分后的场景测试。** 原单一场景测得的是产品代码 9492 次 git 调用。拆分后，所有测试中由产品代码发起的 git 调用合计（不含夹具构建）降到它的 25% 以下，所有拆分测试的总耗时降到 200 s 以下（本机）。
- **命令级。** 每条命令的 git 次数满足 C6；在 C6 的 3 次切换夹具上，`done` 由产品代码发起的 git 进程数不超过 60。
- **全量测试。** 分别报告串行和 `-n 2` 的时长（串行测量即 C8 的义务）。

若未达到以上目标，在 PR 中如实报告实测值和原因，不放宽测试。

## 文件范围（估计）

- `src/keepsail/core/`：
  - `attestation_v3_verify.py`、`effective_policy.py`、`initial_policy.py`、`policy_snapshot.py`；
  - `git_objects.py`、`scope_match.py`、`approval.py`、`transition_guard.py`；
  - `no_review.py`、`review_basis.py`、`policy_authority.py`；
  - 新增 `policy_audit.py`。
- `src/keepsail/cli/`：`__init__.py`、`policy.py`、`attest.py`、`pr.py`。
- `src/keepsail/engineering/`：`attestation.py`、`attestation_v3.py`、`delivery_policy.py`。
- `src/keepsail/sensors/`：`dispatcher.py`、`verification_runner.py`。
- `src/keepsail/templates/keepsail_workflow.yml`。
- `.github/workflows/test.yml`，新增 `.github/workflows/policy-audit.yml`。
- `tests/`：
  - 拆分出的测试；
  - `test_initial_policy.py`、`test_activation_replay_scope.py`、`tests/unit/core/test_policy_obligations.py`；
  - 新增审计、记忆层、回归守卫、工作流测试。
- `docs/`：
  - `getting-started.md`、`implementation-architecture.md`、`limitations.md`；
  - `product-architecture-coverage.md`、`cli-reference.md`；
  - `docs/decisions/` 下新的 proposed 记录。
- 本计划。

## 产品基础核对

- **F1（不静默偏离承诺）。**
  - 闸门仍对每个进入目标分支的信任变更验证旧义务。
  - 不经闸门、且未篡改验证器或 CI 的写入，由审计显式检出。v2 历史全部检出；v1 区间从 `--v1-since` 基线之后检出，基线之前的 v1 历史按当时规则接受，列为信息项。
  - 篡改验证器或 CI 的直接写入者，新旧模型都无法防范，已写入保证边界。
- **2026-11-10 计划的 C3**（"合并判定可用已提交的证据离线重放"）保持：闸门与审计都离线使用已提交证据。
- **风险边界变化。** 属于 `product-architecture.md` 中保留给负责人的决定，负责人已接受，见"负责人接受"。
- **被取代的已批准承诺。** 见"本计划取代的已批准承诺"。`2026-11-24-verify-timeout` 的范围限制不变（本计划不改动过滤或选择），其恢复义务推迟（C8）。

## 修订记录

- **第 1 版（`e945faa`）** 被独立 DSH 子代理拒绝，拒绝证据为 `dsh-plan-9d4fc4f17e5a-e945faa-20261127`。第 2 版的回应如下：
  - **C8 在 v1 义务守卫下不可实施。** 删除对 `verification.yaml` 的修改（负责人决定）。
  - **缺少负责人接受。** 记录负责人对逐项列出的边界变化的接受。
  - **审计不足以替代回放。** 补充威胁模型：新旧模型同样依赖仓库自身的验证器代码。完整定义审计的区间、变化点、前任基线、initial 时序、轮换匹配、禁用或降级、浅克隆、根提交、退出码，以及网络隔离 CI。
  - **Windows 覆盖下降。** 不再新增 e2e 标记，也不改本地检查。
  - **被取代承诺识别不全。** 补充 2026-11-10 验收表第 137 行；明确 2026-11-24 不受影响。
  - **非阻断问题：**
    - 修正"超线性"和"回放到 initial"两处表述；
    - 测量数字标为作者报告值；
    - 给出明确的性能目标；
    - C6 覆盖 `report`、`review import`、`status`；
    - 补充线程安全、失败不缓存等记忆层规则；
    - 说明 `policy_basis` 字段变化；
    - 更新文档字符串和 coverage 文档；
    - 说明模板版本探测；
    - 处理 initial 确认文件的加入。
- **第 2 版（`80925f0`）** 被独立 DSH 子代理拒绝，拒绝证据为 `dsh-plan-dc0cd9c6d09f-80925f0-20261127`。第 3 版的回应如下：
  - **审计未要求 B 是 I 的祖先。** 补充 B ≠ I 且 B 是 I 的祖先，沿用原回放的检查；增加对应测试。
  - **全量审计会把本仓库合法的 v1 历史计为发现。** v1 区间变化改为信息项，不追溯套用今天的 v1 守卫，与原回放止于 v1 基线的覆盖范围一致；写明本仓库全量审计的预期结果。
  - **2026-11-24 退出条件未被正确处理。** 明确测量照常执行，恢复义务推迟，引用负责人的原选项文字，并列入被取代的已批准承诺。
  - **非阻断问题：**
    - 定义审计输出结构；
    - 精确说明 C1 保留的 initial 本地检查，以及移到审计的部分；
    - 列出 `verify_v2_activation` 的再导出、测试和文档字符串；
    - S(B) 与 S(P) 比较全部四项；
    - initial 分两次推送是合法序列，记为警告；
    - 记忆层的测试隔离与夹具规范化；
    - 说明模板的审计在发布前不生效，以及审计不是必需检查；
    - 列出假设的宿主控制；
    - 补充合并提交和非第一父链 `--from` 的测试。
- **第 3 版（`0a31db5`）** 被独立 DSH 子代理拒绝，拒绝证据为 `dsh-plan-7e51c784bc74-0a31db5-20261127`。第 4 版的回应如下：
  - **审计锚定在单个策略变更提交上，会误拒闸门接受的多提交交付。** 改为以交付为单位：
    - 定位 attestation 引入提交 I、交付范围 R 和主线前驱 M，比较 S(B) 与 S(M)；
    - 在 I 处单步验证，并要求 S(I) 等于落地状态；
    - 引用闸门在 PR head 重算代码主题的规则，说明为何以 I 为验证点与闸门一致；
    - 同一交付内的变化点合并判定；
    - 增加相应测试。
  - **initial 检查没有进入闸门。** 新增共享函数 `trusted_policy_snapshot`，供本地读取、`verify_v3_delivery` 的 base 和 `verify_attestations` 使用；增加闸门层测试。
  - **v1 区间没有历史边界。** 新增 `--v1-since`：基线之后的 v1 区间变化按今天的 v1 规则判定，非法修改记为发现；基线之前的变化为信息项。增量审计默认以 `--from` 为基线。本仓库的全量审计以 `24d955b` 为基线，并给出确切的预期信息项。
  - **非阻断问题：**
    - `active_v2` 判断保持并有测试；
    - `authority_rotation` 输出保持原对象；
    - 两条验证路径都传入 `_historical_replay`；
    - 写明 initial 的建立顺序；
    - 记忆层的容量、不可变值和外部并发改写的限制；
    - 增加"未调用回放"的直接测试与计数口径；
    - `done` 夹具的检查不调用 git；
    - 串行测量写入 PR 和评估记录，不回写已批准的计划；
    - 记忆层放入已受离线决策检查的 `git_objects.py`；
    - 列出第一父链上带入 v1 变化的提交；
    - 补全文件范围。
- **第 4 版（`6626e28`）** 被独立 DSH 子代理拒绝，拒绝证据为 `dsh-plan-b627a35b4679-6626e28-20261127`。第 5 版的回应如下：
  - **交付合并处理隐藏了中间的策略变化点和初始确认变化点。** 取消合并判定：每个策略变化点独立判定。快进合并的多步策略交付中，中间点记为发现。同一交付内的初始确认作为独立变化点，仍执行 `verify_initial_policy`。增加相应测试。
  - **增量审计不能发现之后对生效 attestation 的修改。** 策略状态加入 v3 attestation 的路径与 blob 映射。新增情形 6：修改或删除任何已有的 v3 attestation 都记为发现，在增量审计中同样生效。增加相应测试。
  - **非阻断问题：**
    - "未调用历史验证"测试改为替换只服务于历史验证的函数；
    - 测量位置的解释性偏离列入被取代承诺；
    - 写明工作流全量审计的 `--v1-since` 来源；
    - `git_objects.py` 延迟导入，避免导入循环；
    - initial 本地检查要求 `initial_commit` 不等于基线，并校验 `owner_confirmation` 结构；
    - v1 区间不再要求没有 authority，交由 v1 守卫判定；
    - 基线前后按可达性归类；
    - 写明 `read_policy_snapshot` 批量读取但语义不变；
    - 第二次调用为 0 只针对完整 OID；
    - 删去 `verify_v3_delivery` 中的重复快照读取。
- **第 5 版（`8172e64`）** 被独立 DSH 子代理拒绝，拒绝证据为 `dsh-plan-4d8b8dbd3907-8172e64-20261127`。第 6 版的回应如下：
  - **B 是 M 的较早祖先、且策略相同时，过时基线授权会被放过。** 改为要求 B = M，与闸门及签名绑定完整基线 SHA 的承诺一致；增加"策略四项相同但主线已前进"的测试。
  - **`_historical_replay` 跳过了可激活性检查。** 审计另行调用 `require_activatable_policy`：增量审计中不可激活记为发现，全量审计的历史点上记为警告；增加测试。
  - **C6 的上限没有计入 authority 读取。** `trusted_policy_snapshot` 一次批量读取四个 blob；上限改为 transition 基线 3、initial 基线 4，并写明夹具类型。
  - **v1→v2 升级路径被阻断，却未说明。** 标明这是 #140 以来已有的阻断，不是本计划造成的，本计划不改变它，并归入负责人安排的后续讨论；同时修正"其余承诺不变"的表述。
  - **"同一交付内先确认再切换"的测试不可证伪。** 改为闸门负例、审计正例（确认先落主线）和审计负例三项。
  - **非阻断问题：**
    - 明确"策略四项"；
    - 本地 initial 检查加入 `version` 校验；
    - C8 改为"删除或替换"；
    - 写明进程计数是回归守卫的主要证据；
    - 删除旧回放缓存，并改为延迟导入；
    - 定义 `verification.yaml` 不存在与畸形两种情况；
    - "向前"改为"向历史方向"；
    - 写明性能目标的计数口径；
    - 给出完整的审计命令；
    - 定义 `findings`、`warnings`、`informational` 的结构；
    - 写明本地身份比较只是提示；
    - 轮换同样比较 S(I)；
    - 写明记忆层只缓存原始 git 结果、每次重新做结构校验。
  - **负责人接受的范围。** B = M 修复后，第 1 项不再带来新的后果；第 4 项是本计划之前就存在的阻断，由负责人已安排的后续讨论处理。
