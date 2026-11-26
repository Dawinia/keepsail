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
  基线新鲜度由宿主负责：宿主必须提供当前目标分支提交；若托管规则允许以过时 base 合并，
  由 T3 的审计检出。
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
  该计划的其余承诺不变，包括签名授权、义务保留、恢复、轮换、初始信任、离线验证，以及"删除或损坏已激活策略不能降级"。

## 承诺

### C1 读取生效策略不再回放激活链

`load_effective_v2`、`recognition_contract_active` 及其全部调用者改为直接读取可信基线上的策略快照（`read_policy_snapshot`），不再调用激活回放。调用者包括 `no_review`、`review_basis`、`transition_guard`、`policy_authority`、`engineering/delivery_policy`（`report` 经由它）、`engineering/attestation` 的格式选择、`verification_runner`、`cli/pr`。

保留并关闭失败的校验：
- v2 解析与 `policy_digest`；
- `policy-authority.yaml` 解析与仓库标识、目标 ref 一致；
- `plan-decision` 用途；
- 以基线 `verification.yaml` 重算 `required_checks_digest` 并比较。
- initial 策略：`.harness/policy-initial-trust.json` 必须存在且字段完整，其 `policy_digest` 等于当前策略摘要，`initial_commit` 为完整 OID。只做 O(1) 读取，不扫描历史。

`continued_plan_basis` 对前任 v2 基线也只读快照。

更新 `policy_snapshot.py` 与 `load_effective_v2` 的文档字符串：快照的权威来自宿主可信基线，结构校验本身不授予权威。

### C2 合并闸门只验证 base→head

`verify_v3_delivery` 删除第 414 行对 base 的激活回放；`verify_v3_transition` 不变。授权、义务变化、恢复依据、审查证据、必需检查、代码对象与 attestation 新增检查全部保持。

`verify_attestations` 不再调用 `verify_v2_activation`。`attest verify` 输出的 `policy_basis` 改为可信基线依据，字段为 `basis: "trusted-base"`、`trusted_base`、`policy_digest`、`required_checks_digest`、`activation`（策略中的定位对象）。回放产出的 `activation_commit`、`predecessor_base`、`initial_confirmation`、`confirmation_assurance`、`authority_rotation` 移到审计输出。CLI 参考与断言这些字段的测试（`test_initial_policy.py`、`test_delivery_policy_transition.py`）相应更新。

`verify_v2_activation` 作为公共入口删除，单步验证逻辑移入审计模块。

### C3 `keepsail policy audit`

命令：`keepsail [--json] policy audit [--from <commit>] --to <commit> --repository-id <id> --target-ref <ref>`

**区间：**
- 遍历 `git rev-list --first-parent --reverse <to> ^<from>`。
- `--from` 必须是 `--to` 的祖先，否则失败并提示做全量审计。`--from` 可以不在第一父链上，此时以 rev-list 结果为准。
- `--from` 等于 `--to` 时，区间为空，通过。
- 省略 `--from` 或其值为全零 OID 时为全量审计：从根提交起；仓库是浅克隆时失败。
- 每个提交与其第一父提交比较；根提交与"空状态"比较。

**策略状态** S(C) 由 C 中以下内容组成：
- `review-recognition.yaml` 的解析结果（不存在、v1 及其摘要、v2 及其摘要）；
- `policy-authority.yaml` 的摘要（或不存在）；
- `verification.yaml` 的必需检查契约摘要；
- `policy-initial-trust.json` 的字节（或不存在）。

读取时按普通文件 blob 校验，畸形内容关闭失败。

**变化点判定**（S(C) ≠ S(P)，P 为第一父提交）：

1. **v2 未启用，且两侧都不涉及 v2。** 两侧均无 v2 策略和 authority，变化落在 v1 或未启用状态。按闸门的 v1 规则判定，即复用 `committed_transition_required` 对 (P, C) 的判断：
   - 不需要转换授权的变化（例如新增检查）通过；
   - 需要授权的，记为发现。
2. **v2 切换或恢复。** C 的策略为 `{kind: transition, change: X}`，且策略摘要变化。
   - 读取 C 中 `.harness/attestations/v3/X.jsonl`，定位其唯一引入提交 I（`_introduction_commit`）。
   - 要求：
     - I 是 C 或 C 的祖先，且不是 P 的祖先；
     - 记录的 `trusted_base` B 是 P 的祖先或等于 P；
     - S(B) 与 S(P) 的策略、authority、检查三项相同，否则授权针对的是过时基线，记为发现；
     - attestation 自引入后未被修改。
   - 然后按 B 的策略版本，调用 `verify_v3_transition` 或 `verify_v3_delivery(base=B, head=I, _historical_replay=True)`；B 的来历不递归验证。
   - 结果中的目标策略摘要须等于 C 的策略摘要。
3. **密钥轮换。** authority 摘要变化，策略与检查不变。
   - 在 C 中枚举 v3 attestation，要求恰有一条 `rotate_key` 记录指向 C 的 authority 摘要，沿用 `_verify_current_rotation` 的匹配规则。
   - 按情形 2 的同样方式定位 I 与 B，并以 `verify_v3_delivery` 单步验证。
4. **initial 建立。** 
   - P 无启用策略而 C 出现 `{kind: initial}` 的 v2 策略时：执行 `require_no_prior_enabled_policy(C)`，并记录"待确认"。
   - `policy-initial-trust.json` 首次出现的提交上：执行 `verify_initial_policy`，它要求确认文件晚于 initial 提交。
   - 区间结束时仍处于"待确认"的，记为发现。
5. **其它变化，一律记为发现。** 包括：
   - v2 被删除、禁用或降级为 v1；
   - authority 被删除；
   - 检查摘要变化但未伴随授权切换；
   - 确认文件被修改或删除；
   - 不符合上述任何情形的组合。

**输出与退出码：**
- 逐个列出变化点：提交、情形、依据（引入提交、前任基线、记录 Change）、结果。
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
- **本次交付：** 在本仓库运行一次全量审计并记录结果。本仓库为 v1，预期无变化点发现。

### C5 进程内复用不可变 Git 事实，批量读取

- 新模块 `core/git_memo.py`：进程内、带锁、按条目数限容（LRU）的记忆层。
  - 键包含仓库根的规范路径和完整 OID。
  - 缓存对象：完整 OID 的 `resolve_commit`；`(commit, path)` 的 blob 读取，含"不存在"与"非普通文件"结果；提交的树列表；`is_ancestor`；`merge_base`。
  - 只缓存成功的 git 调用结果，git 失败不缓存。
  - 符号 ref（`HEAD`、分支名）不缓存。
  - 假设：单次进程内不执行 fetch、unshallow、replace 或 graft；文档字符串写明这一点。
- 策略快照的四个文件合并为一次 `ls-tree` 加一次 `cat-file --batch`，保留普通文件 blob 校验。
- `_contract_base_candidates` 的 `for-each-ref` 结果在一次 CLI 调用的作用域内复用，因为它对应可变 ref。
  - 作用域由顶层 CLI 为所有子命令进入，包括 `report`。
  - 作用域对象带锁；dispatcher 提交任务时用 `contextvars.copy_context().run`，让线程共享同一个带锁对象。
  - 假设：keepsail 命令在一次调用内不移动这些 ref。
- 不在范围内：`file_text_at_commit` 以外的 `git diff` 与 `git log` 调用不做缓存，不承诺消除所有重复。

### C6 回归守卫

测试中包装 `subprocess` 计数 git 进程，判断条件不依赖计时。

- **单元级上限。** 在有 3 次 v2 切换的夹具上：
  - 首次调用 `load_effective_v2`，git 进程数不超过 4（解析 ref、`ls-tree`、`cat-file --batch`，以及一次可能的 OID 校验）；
  - 同一进程内再次调用，为 0。
- **命令级链长无关。** 同类夹具分别在 1 次和 3 次 v2 切换之后执行 `done`、`attest verify`、`report`、`review import`、`status`，每条命令的 git 进程数须相同。
- **作用域重置。** 两次独立的 CLI 调用之间，`for-each-ref` 结果不被复用。

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
- 自 #140 合并后，`transition_guard` 把任何必需检查定义的变化视为必须经签名 v2 切换授权的义务变化（`transition_guard.py:121-126,191,290`）。
- 本仓库为 v1，没有签名密钥，在 v1 下新增密钥也会被拒绝。
- 负责人于 2026-11-27 决定本次不处理这一点："Drop C8 here"。

因此，负责人此前授权的"e2e 移出"以及 `2026-11-24-verify-timeout` 的恢复串行，在本计划中都不执行。"v1 下必需检查被锁定"这一发现，归入负责人已安排在本次之后的 v2 产品讨论。

`2026-11-24-verify-timeout` 要求本 Change 做一次完整串行全量测量，这项义务照常执行：实施后在本机测量串行全量 pytest，并把时长写入 PR 说明。

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
  - 以下情况关闭失败：基线策略摘要被篡改；检查摘要不一致；authority 的仓库或 ref 不符；initial 缺确认文件或确认的摘要不符。
  - 删除或损坏基线上已激活的策略不能降级为 legacy。
- **C2**
  - 现有闸门正例和负例保持通过。
  - `policy_basis` 新字段有断言。
  - v1→v2 切换闸门路径不变。
- **C3**
  - 通过的情形：initial（建立加确认）、切换、恢复、轮换、v1 允许的新增检查、空区间。
  - 记为发现的情形：
    - 直接追加的未授权策略修改、检查删除、authority 替换；
    - 禁用、删除 v2 或将其降为 v1；
    - attestation 引入后被修改；
    - 前任不可达，或 S(B) ≠ S(P) 的过时基线授权；
    - initial 无确认。
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

- **拆分后的场景测试。** 原单一场景的总 git 次数降至原来（9492 次）的 25% 以下，总耗时降至 200 s 以下（本机）。
- **命令级。** 每条命令的 git 次数满足 C6；`done` 在 3 次切换夹具上的 git 进程数不超过 60。
- **全量测试。** 分别报告串行和 `-n 2` 的时长（串行测量即 C8 的义务）。

若未达到以上目标，在 PR 中如实报告实测值和原因，不放宽测试。

## 文件范围（估计）

- `src/keepsail/core/`：
  - `attestation_v3_verify.py`、`effective_policy.py`、`initial_policy.py`、`policy_snapshot.py`；
  - `git_objects.py`、`scope_match.py`、`approval.py`、`transition_guard.py`；
  - `no_review.py`、`review_basis.py`、`policy_authority.py`；
  - 新增 `policy_audit.py`、`git_memo.py`。
- `src/keepsail/cli/`：`__init__.py`、`policy.py`、`attest.py`、`pr.py`。
- `src/keepsail/engineering/`：`attestation.py`、`attestation_v3.py`、`delivery_policy.py`。
- `src/keepsail/sensors/`：`dispatcher.py`、`verification_runner.py`。
- `src/keepsail/templates/keepsail_workflow.yml`。
- `.github/workflows/test.yml`，新增 `.github/workflows/policy-audit.yml`。
- `tests/`：
  - 拆分出的测试；
  - `test_initial_policy.py`、`test_activation_replay_scope.py`；
  - 新增审计、记忆层、回归守卫、工作流测试。
- `docs/`：
  - `getting-started.md`、`implementation-architecture.md`、`limitations.md`；
  - `product-architecture-coverage.md`、`cli-reference.md`；
  - `docs/decisions/` 下新的 proposed 记录。
- 本计划。

## 产品基础核对

- **F1（不静默偏离承诺）。**
  - 闸门仍对每个进入目标分支的信任变更验证旧义务。
  - 不经闸门、且未篡改验证器或 CI 的写入，由审计显式检出。
  - 篡改验证器或 CI 的直接写入者，新旧模型都无法防范，已写入保证边界。
- **2026-11-10 计划的 C3**（"合并判定可用已提交的证据离线重放"）保持：闸门与审计都离线使用已提交证据。
- **风险边界变化。** 属于 `product-architecture.md` 中保留给负责人的决定，负责人已接受，见"负责人接受"。
- **被取代的已批准承诺。** 见"本计划取代的已批准承诺"。`2026-11-24-verify-timeout` 的限制与退出条件不被改变（C8）。

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
