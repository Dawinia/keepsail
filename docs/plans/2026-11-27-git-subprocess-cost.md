---
change: 2026-11-27-git-subprocess-cost
stage: plan
---

# 策略信任在闸门处验证一次，消除每条命令的全链回放与重复 Git 读取

关联 issue：#143（Windows 上 git 子进程成本拖慢 verify/done）。

## 问题

按 #143 "Reproduce first" 先测量（2026-11-26，本机 Windows，测量脚本未入库）：

- 单个测试 `test_recovery_plan_review_uses_only_the_signed_process_and_digest[False]`
  耗时 769 s，产生 9568 次 git 子进程，git 墙钟 711 s。其中产品代码 9492 次（99%），
  测试夹具 76 次（1%）。每次 git 进程平均 73–79 ms，是 Windows 进程创建成本。
- 产品调用点集中在：`scope_match.resolve_commit`（2756 次）、
  `git_objects.optional_regular_blob_bytes`（每个 blob 一次 `ls-tree` 加一次
  `cat-file`，共约 4400 次）、`approval._tree_entries`（560）、
  `approval._contract_base_candidates`（412 次 `for-each-ref`）、
  `attestation_v3_verify._verify_v2_activation` 及其递归回放。
- 同一次 CLI 调用内约 75% 的 git 查询是重复的（相同参数、相同不可变对象）。
- 单条命令的 git 次数随此前策略切换次数超线性增长：`review import` 平均每次 82 次，
  `done rotate-key` 477 次，`report` 每次 433 次。
- 全量测试：`-n 2` 1917 s（全部通过）；串行 2737 s（另有 73 个本机编码环境失败，
  与本问题无关）。最慢的单个测试独占 774 s，也是 xdist 的关键路径。

## 根因

### 1. 信任模型：每条命令都从起点证明整条策略链

已批准计划 `2026-11-10-delivery-policy-transition.md` 规定：策略生效后，
从新可信基线读取激活 v3，"以该旧基线和旧策略重放整个激活 v3"。实现上，
`load_effective_v2`、`verify_v3_delivery(base)` 和 `recognition_contract_active`
在每条命令中都调用 `verify_v2_activation`，它递归回放到 `initial` 策略，
每层都重新验证计划批准、代码审查、旧必需检查和签名授权。
复杂度为每条命令 O(策略切换次数)，并随项目寿命增长。

从信任锚推导，这种回放换不来额外的保证：

- 链的起点 `initial` 是未认证的负责人声明（`initial_policy.py`：
  "not an authentication mechanism. The host must independently treat the selected
  target commit as trusted"，`confirmation_assurance: retained-owner-claim`）。
  所以链的最终信任锚是宿主提供的可信基线本身。
- 能改写历史的人可以伪造整条链，回放拦不住。
- 经过合并闸门的 PR，已由 `attest verify` 用基线上的旧策略验证过
  （`verify_v3_delivery` 要求策略、密钥或检查的任何变化都携带签名授权，
  且每个变更文件都要有 attestation 覆盖）。这一步是 O(1)。
- 全链回放唯一额外能发现的，是不经闸门直接追加到目标分支、
  且没有签名密钥的策略修改。这只需要在基线前进时检查增量一次。

### 2. 实现：同一调用内重复查询不可变事实

`resolve_commit` 对完整 OID 反复执行 `rev-parse`；
每个 blob 读取都分别起 `ls-tree` 和 `cat-file` 两个进程；
`_contract_base_candidates` 每次调用都执行 `for-each-ref`；
同一提交的树列表、祖先关系和 merge-base 被重复计算。

已有的 `activation_replay_scope` 只缓存激活结果，还存在两个缺口：
`report` 不在 `cli/__init__.py` 进入作用域的子命令集合里；
`sensors/dispatcher.py` 的线程池不继承 ContextVar。

## 修订后的信任模型

本计划取代 `2026-11-10-delivery-policy-transition.md` 中
"生效后……以该旧基线和旧策略重放整个激活 v3"一句。该计划的其余承诺不变，
包括签名授权、义务保留、恢复、轮换、初始信任和离线验证。

- **T1 信任锚。** 宿主提供的可信基线就是信任锚。基线上的策略文件经结构校验后，
  直接作为生效策略。本地命令使用本地基线 ref，其结果仍只是本地提示；
  权威判断在宿主的合并闸门。
- **T2 闸门处单步验证。** 每次信任变更（策略切换、恢复、密钥轮换）在进入目标分支的
  那个 PR 的合并闸门处，用基线上的旧策略验证一次。这一步不回放基线自身的来历。
- **T3 增量审计。** 目标分支前进时，对新增区间内的策略状态变化逐一做单步验证，
  以发现不经闸门写入的修改。审计在目标分支更新之后运行，只能检出，不能阻止。
  可以从根提交起做全量审计，但它不在任何命令的常规路径上。
- **T4 记忆只用于加速。** 以不可变对象 OID 为键的查询结果可以在进程内复用。
  未命中时重新计算，正确性不依赖缓存。

保证边界的变化（需负责人在计划审查时明确接受）：对"绕过闸门直接写入目标分支的
策略修改"，原先是每条本地命令同步拒绝，改为基线前进后由审计检出。
初次采用时，在第一次审计运行之前，本地命令信任本地基线上的 initial 策略。

## 承诺

### C1 每条命令读取生效策略不再回放激活链

`load_effective_v2`、`recognition_contract_active`、`no_review`、`review_basis`、
`transition_guard`、`engineering/delivery_policy`、`verification_runner`、
`cli/pr` 等路径改为直接读取可信基线上的策略快照，并保留以下校验：

- v2 解析与 `policy_digest` 校验；
- `policy-authority.yaml` 解析，以及仓库标识与目标 ref 的一致性；
- 用基线上的 `verification.yaml` 重新计算 `required_checks_digest` 并比较；
- 未知字段和格式错误一律关闭失败。

单条命令读取策略所需的 git 进程数为常数，不随此前的策略切换次数变化。

### C2 合并闸门只验证 base→head

`attest verify --base --head` 对 v3 交付和切换的验证保持不变：
授权、义务变化、恢复依据、审查证据、必需检查、代码对象和 attestation 的引入
都照旧检查。唯一变化是不再回放 base 自身的激活链。

`policy_basis` 输出改为报告可信基线依据：`trusted_base`、`policy_digest`、
`required_checks_digest`、`activation` 定位，以及 `basis: trusted-base`。
不再报告回放得到的 `activation_commit`、`predecessor_base` 和 `authority_rotation`，
这些移到审计输出中。

### C3 新增 `keepsail policy audit`

命令形式：`keepsail policy audit [--from <commit>] --to <commit> --repository-id <id> --target-ref <ref>`。

- 沿 `--to` 的第一父提交，遍历 `--from` 之后的提交。
- 对每个使 v2 策略状态（策略摘要、密钥摘要、必需检查摘要、初始信任确认）
  不同于其第一父提交的提交，做一次单步验证：
  - 切换和恢复：在其前任基线上，用旧策略验证引入它的 v3 attestation；
  - 轮换：验证唯一的轮换记录；
  - initial：执行现有的 `verify_initial_policy`。
  - 前任基线视为已审计，不递归。
- 省略 `--from` 时，从根提交起全量审计。
- `--from` 不是 `--to` 的祖先（例如历史被改写）时失败，并提示做全量审计。
- 输出列出每个已验证的变化点及其依据，以及检出的问题。
- 逐提交比较策略状态时批量读取。
- 实现模块位于 `core/policy_audit.py`，属于 `d-policy-replay-offline-v2`
  的检查路径：只用本地 Git，不访问网络。

### C4 目标分支前进时运行审计

本仓库的 CI 和 `templates/keepsail_workflow.yml` 生成的工作流，在推送到目标分支时
运行 `policy audit --from <before> --to <after>`，仓库标识和目标 ref 由宿主事件提供。
`before` 为全零（首次推送）时做全量审计。
审计失败会让该次工作流失败并报告，但不会回滚已经写入的提交。
项目若没有启用 v2 策略，审计会报告"无 v2 策略"并通过。

### C5 进程内复用不可变 Git 事实，批量读取

- 新增一个进程内、有容量上限的记忆层，按 `(仓库根, OID, …)` 缓存只取决于不可变
  对象的结果：完整 OID 的 `resolve_commit`、`(commit, path)` 的 blob 读取、
  提交的树列表、`is_ancestor`、`merge_base`。
  符号 ref（如 `HEAD`、分支名）不进入这个记忆层。
- 一次读取多个策略快照文件时，合并为一次 `ls-tree` 加一次 `cat-file --batch`，
  保留"必须是普通文件 blob"的检查。
- `_contract_base_candidates` 的 `for-each-ref` 结果只在一次 CLI 调用内复用：
  - 作用域在顶层 CLI 为所有子命令进入，包括 `report`；
  - 线程池任务通过 `contextvars.copy_context()` 继承作用域。

### C6 回归守卫

新增测试，统计代表性命令的 git 子进程数：在同一类夹具上，分别在 1 次和 3 次策略
切换之后，对普通交付执行 `done` 和 `attest verify`。
断言两种情况下的子进程数相同，并低于计划实施时记录的上限。
计数通过测试内包装 `subprocess` 完成，不依赖计时。

### C7 拆分策略切换场景测试

把 `test_delivery_policy_transition.py` 中约 650 行的单一场景，按阶段拆成相互独立的
测试，每个测试自建所需的前置状态：

- 恢复授权；
- 负例；
- 已安装基线验证器；
- 继续计划；
- 生效后的普通交付；
- 下一次切换；
- 密钥轮换；
- 报告与状态。

多切换场景测试标记为 `e2e`（见 C8），由 CI 的 `e2e` job 运行。
单步的闸门与审计测试不标记，保留在本地快速套件中。
原先依赖每条命令回放才能发现的历史篡改负例（激活 attestation 在引入后被修改、
前任不可达等），迁移为 `policy audit` 的测试。CI 的 `delivery-policy-offline`
job 继续在网络隔离环境中运行这些测试，以及新的审计测试。

### C8 本地验证命令

负责人于 2026-11-27 在本次交付讨论中授权（原话："e2e 移出"）：

- 本地 `.harness/verification.yaml` 的 pytest 必需检查加 `-m "not e2e"`，
  与 CI `test.yml` 的 pytest job 一致。
- e2e 测试只在 CI 运行，由合并必需检查 `e2e` 覆盖。
- C7 拆分后的多切换场景测试标记为 `e2e`。

这是对本地验证义务的明确放宽。整体覆盖范围不缩小，只是执行位置从本地移到 CI。

然后执行 `2026-11-24-verify-timeout` 已批准的退出条件：在本机测量串行
`-m "not e2e"` 全量时长。

- 低于 2000 s：恢复串行命令和 2700 s 超时，并删除相应注释；
- 不低于 2000 s：保持 `-n 2` 和 3300 s，并在注释中记录实测值。

### C9 文档与决策

- 更新 `docs/getting-started.md` 中初始策略段落，说明 initial 的检查由审计执行。
- 更新 `docs/implementation-architecture.md`，在 §9 attestation 中写明信任模型
  T1–T4 和保证边界。
- 更新 `docs/limitations.md`，加入"绕过闸门的写入只能事后检出"。
- `docs/cli-reference.md` 由 `doc check --fix` 重新生成。
- 用 `keepsail decision new` 提交一份 proposed 决策记录，内容为
  "生效策略从可信基线读取；回放仅限闸门单步验证与审计"。
  是否 ratify 由负责人决定。

## 不做

- 不重新评估 v2 交付策略本身的机制（签名、恢复、轮换、初始信任是否应交给宿主）。
  负责人已决定在本次之后单独讨论。
- 不做跨进程或跨机器的持久缓存。按修订后的模型，常规路径不再需要它。
- 不改变 attestation、授权记录或策略文件的格式。
- 不改变 v1 策略的行为。

## 测试

- C1：在有多次切换的仓库中，普通命令能正常读取生效策略；
  基线策略的摘要被篡改、检查摘要不一致、密钥标识不符时，命令关闭失败。
- C2：现有闸门正例和负例保持通过；`policy_basis` 的新字段有对应断言。
- C3：
  - 审计通过：每种合法变化点（initial、切换、恢复、轮换）。
  - 审计失败：直接追加的未授权策略修改；激活 attestation 在引入后被修改；
    前任不可达；`--from` 非祖先；`--from` 为全零或省略时做全量审计；
    无 v2 策略时通过。
  - 审计以网络隔离方式运行。
- C5：
  - 记忆层的单元测试：符号 ref 不被缓存；容量上限有效。
  - 批量读取遇到非普通文件、缺失路径或异常输出时失败。
  - `report` 和线程池任务在作用域内。
- C6、C7：见上文。
- 全量：`keepsail verify`、`decision check`、`doc check` 通过。

## 验收测量

实施后用同一测量方法（不入库）重新测量并写入 PR 说明：

- 拆分后各测试的 git 次数和耗时；
- 普通命令在 1 次与 3 次切换后的 git 次数；
- 全量 `-n 2` 和串行时长。

## 文件范围（估计）

`src/keepsail/core/attestation_v3_verify.py`、`effective_policy.py`、
`initial_policy.py`、`policy_snapshot.py`、`git_objects.py`、`scope_match.py`、
`approval.py`、新增 `policy_audit.py`；`src/keepsail/cli/__init__.py`、`policy.py`、
`attest.py`；`src/keepsail/engineering/attestation.py`；
`src/keepsail/sensors/dispatcher.py`；`src/keepsail/templates/keepsail_workflow.yml`；
`.github/workflows/`；`.harness/verification.yaml`；
`tests/integration/lifecycle/test_delivery_policy_transition.py` 及拆分出的新测试；
`tests/unit/core/test_activation_replay_scope.py`；新增审计、记忆层和回归守卫测试；
`docs/getting-started.md`、`docs/implementation-architecture.md`、`docs/limitations.md`、
`docs/cli-reference.md`、`docs/decisions/` 下新的 proposed 记录；以及本计划。

## 产品基础核对

- F1（不静默偏离承诺）：闸门仍对每个进入目标分支的信任变更验证旧义务。
  绕过闸门的写入由审计显式检出并报告，不是静默的。
- C3（2026-11-10 计划）"合并判定可用已提交的证据离线重放"保持：
  闸门与审计都离线使用已提交证据。
- 本计划变更两项承诺：
  - 取代"生效后每次重放整个激活链"，见"修订后的信任模型"；
  - 把 e2e 移出本地必需检查（C8），已经负责人授权。

  两项都需要在计划审查中获得批准。
