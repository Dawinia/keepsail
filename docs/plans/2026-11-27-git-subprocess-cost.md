---
change: 2026-11-27-git-subprocess-cost
stage: plan
---

# 去掉激活链回放与签名转换，策略变更改为 owner 的记录行为；降低 Git 子进程与内存开销

关联 issue：#143（Windows 上 git 子进程成本拖慢 verify/done），#159（v1 守卫把 owner 锁在门外）。

## 为什么重写

- 第 1–14 版都被评审拒绝。第 9–14 版的方向是"跨命令记住激活回放的结果"，评审连续六轮在同一方向上提出新的
  阻断项（缓存的认证、验证器摘要、依赖、动态库、alternates、grafts……），无法收敛。原始输出保留在
  `.harness/scratch/2026-11-27-git-subprocess-cost/plan-review-*`。
- 负责人 2026-11-27/28 对照产品公理指出：问题不在缓存，而在被缓存的东西。
  - F1 防的是 agent 在工作中**静默偏离**人的承诺，不是防 owner 伪造自己的本地历史；本地仓库是 owner 自己的环境。
  - 产品架构写明 "Owner-controlled recognition is not cryptographic identity"；历史是否经过闸门进入目标分支，
    由宿主的分支保护与 CI 负责（"separate evidence layers"）。
  - 认可策略和必需检查由 owner 决定。keepsail 要做的是**应用它，并让它的变化可见、由 owner 授权**，
    而不是在每条命令里用签名和回放反复证明它的来历。
- 因此负责人决定（2026-11-28）在本 Change 内一并完成：
  1. 去掉激活链回放、Ed25519 签名授权、密钥轮换、受限恢复和初始信任建立流程；
  2. 改变认可策略或必需检查的 Change，由计划声明并由 owner 的一次记录行为授权（无签名）；
  3. 旧数据"读得懂、不再执行"；
  4. 维护者审批计划改为普通的 owner 结论；
  5. 保留 #143 中与策略无关的性能和内存改进。
- 前几版计划中"性能 Change 不改变信任模型"一条，不是负责人定的规则，而是之前某个 session 自己的总结，
  这里撤回。
- 第 15 版（`468fff4`）由同一 Codex 配置评审（负责人选定，不是当前认可契约中的流程，无法记录为认可证据，#159），
  拒绝，4 个阻断项；原始输出在 `plan-review-15/`。本版的处理：
  - **与 `d-policy-replay-offline-v2` 的身份输入要求冲突**：接受，新增取代它的决策，由负责人 ratify（C9）。
  - **合并闸门从旧 base 安装的验证器只认签名**：接受，写明读端先行的顺序（C10）。C8 的恢复因此改在
    紧接着的下一个 Change 中执行，由负责人 2026-11-28 决定（C8）。
  - **逐项记录漏掉新增与加强的义务**：接受，逐项变化改为完整列出（C2）。
  - **停用策略缺少测试**：接受，补上（C7）。
- 第 16 版（`8702557`）由同一 Codex 配置评审，拒绝，2 个阻断项；原始输出在 `plan-review-16/`。评审确认第 15 轮的四项已处理。
  两项都针对计划流程为 `signed-plan-decision` 的已部署项目：重新解释它会在不触发授权的情况下改变认可规则，
  且这类项目在旧验证器下无法完成升级。负责人 2026-11-28 决定：先用旧版本迁移，新版本拒绝并给出说明，
  不再重新解释（C3、C7）。
- 第 17 版（`6726c1f`）由同一 Codex 配置评审，拒绝，2 个阻断项；原始输出在 `plan-review-17/`。本版的处理：
  - **迁移路径缺少端到端测试**：接受，加入旧版本迁移加新版本普通交付的测试（C7）。
  - **`reducer.py` 的改动未按 `d-state-pure-fold` 复核和 reconcile**：接受（C5）。
- 第 18 版（`bfc1618`）由同一 Codex 配置评审，拒绝，2 个阻断项；原始输出在 `plan-review-18/`。本版的处理：
  - **`delivery-policy-offline` 为浅克隆，取不到固定的旧提交**：接受，改为 `fetch-depth: 0`，缺失时测试失败（C7）。
  - **`delivery-policy-wheel` 仍运行被删除的 `test_policy_authority.py`**：接受，改为运行新机制的已安装 wheel 测试，
    并加一个守卫测试，检查 workflow 引用的测试路径都存在（C6）。
- 第 19 版（`7c0aebe`）由同一 Codex 配置评审，拒绝，2 个阻断项；原始输出在 `plan-review-19/`。本版的处理：
  - **"计划声明"没有可检查的表示**：接受，改为范围包含相关文件，加上一条保留 ID 为 `RISK-BOUNDARY` 的承诺，
    在 `done` 和合并判定中检查（C2）。
  - **升级后，已由签名切换授权的继续计划失去批准**：第 19 版曾按已记录的数据保留它；第 20 轮因此又出现两项阻断，
    见下。
- 第 20 版（`05f4091`）由同一 Codex 配置评审，拒绝，3 个阻断项；原始输出在 `plan-review-20/`。本版的处理：
  - **`scope` 不在冻结的计划对象中**：接受，声明只检查计划对象中的 `RISK-BOUNDARY` 承诺（C2）。
  - **新授权中的继续计划无法定位**、**旧 `signed-plan-decision` 下的继续批准没有认可规则**：两项都来自保留"继续计划"。
    负责人 2026-11-28 决定去掉这个功能：策略改变后，不被新策略认可的旧批准，按新流程重新取得批准。
    这只会更严，并删掉一整块兼容逻辑（C2、C3、C7）。
- 第 21 版（`eb9609f`）由同一 Codex 配置评审，拒绝，1 个阻断项；原始输出在 `plan-review-21/`。本版的处理：
  - **缺少"升级交付经旧 v2 json base 上安装的验证器"的端到端测试**：接受，迁移测试拆出这一步（C7）。
  - 非阻断项：写明历史 v3 的结构解析继续识别 `recovery`/`continued_plan` 模式，但新交付的判定不接受它们（C7）。
- 第 22 版（`a77042e`）由同一 Codex 配置评审，拒绝，2 个阻断项，都在 C5；原始输出在 `plan-review-22/`。本版的处理：
  - **进程级记忆与 `d-state-pure-fold` 冲突**：接受，去掉记忆，改为把展开后的行作为显式参数传给下游（C5）。
  - **其他直接调用方绕过记忆，计数承诺无法成立**：接受，覆盖范围收窄到测得重复的路径（`change resume`、
    严格写入的前置校验），计数按字节快照、直接包装 `effective_event_lines`（C5、C7）。
- 第 23 版（`4424401`）由同一 Codex 配置评审，拒绝，1 个阻断项；原始输出在 `plan-review-23/`。本版的处理：
  - **授权者与时间没有进入已提交的 attestation**：接受，`authorization` 同时带上授权事件的 `event_id`、`actor` 和 `ts`，
    并补上端到端一致性测试（C2、C7）。
- 第 24 版（`5121bc9`）先由 Codex 评审批准（不是认可流程），再由本仓库认可的 DSH 评审流程评审，
  拒绝，2 个阻断项。该结论已导入为认可证据，原始记录在
  `review-artifacts/2026-11-27-git-subprocess-cost/plan-review-dsh-25/`。本版的处理：
  - **禁用的 v1 策略没有首次启用的路径**：接受。首次启用时，绑定冻结的计划对象，由 owner 授权，
    交付时按改动前的义务（C2、C7）。
  - **逐项变化漏掉必需检查的层开关**：接受，层开关与 `policy-metadata` 都列为逐项变化（C2、C7）。
  - 非阻断项也一并处理：
    - 严格写入的整条前置校验共用一次展开（C5）；
    - 补上 `d-events-append-only` 的 reconcile（C9）；
    - 计划修订后授权失效的测试（C7）；
    - 同一场景的前后对比（验收）；
    - 摘要中 v2 兼容性的表述（产品基础核对）。
- 第 25 版（`46987dd`）由 DSH 评审拒绝，2 个阻断项，已导入；原始记录在
  `review-artifacts/2026-11-27-git-subprocess-cost/plan-review-dsh-26/`。本版的处理：
  - **在禁用策略下，"首次启用"走 Change 不可行**：属实。没有认可流程，就不会有计划批准。
    负责人 2026-11-28 确认按冷启动处理：首次启用属于采用时的初始设置，由 `init` 或 `policy enable` 完成；
    风险边界变更只适用于已启用的策略（C2、C7）。
  - **逐项变化的字段清单仍不完整（漏了 `shell`、`capture`）**：接受。改为在参与摘要的规范化对象上做通用的
    逐字段差异，并加一个性质测试：摘要相同，当且仅当差异为空（C2、C7）。
  - 非阻断项：
    - 常驻 `cat-file --batch` 的请求在锁内串行完成（C4），补上并发测试（C7）；
    - `repository_id`/`target_ref` 的说法改为描述改动后的性质（C1）；
    - 列全受影响的测试文件，并用 `--collect-only` 检查（C6）；
    - 首次启用不再需要"没有前任"的授权载荷，因为它不走 `policy accept`。

## 产品核心（本计划保持）

- 闸门、计划批准、适用的代码审查和必需检查照常生效；认可流程仍由可信基线上的策略决定。
- **改变承诺或风险边界不能静默发生：** 一个 Change 若改变生效的认可策略或必需检查，必须在计划中声明，
  并由 owner 在这个 Change 上留下记录的授权；做出这次改动的 Change 本身仍按**改动前**的义务交付。
- 记录可追溯：授权、改动前后的摘要和逐项义务变化，都进入事件账本和 attestation，并在 `status`/`report`/PR 中显示。
- 合并判定仍可用已提交的证据离线重放这一次交付，不访问网络（`d-policy-replay-offline-v2`）。
- 事件只追加，状态由事件纯折叠得到，状态转换只来自固定矩阵（`d-events-append-only`、`d-state-pure-fold`、
  `d-fixed-transition-matrix`）。

## 测量（2026-11-26/27，本机 Windows；作者报告值，脚本不入库）

### Git 子进程

- 最慢的单个测试 `test_recovery_plan_review_uses_only_the_signed_process_and_digest[False]` 耗时 769 s，
  有 9568 次 git 子进程，其中产品代码 9492 次（99%）。每次约 74 ms，即 Windows 的进程创建成本。
- 产品调用点：`scope_match.resolve_commit` 2756 次；`git_objects.optional_regular_blob_bytes` 每个 blob 用一次
  `ls-tree` 加一次 `cat-file`，合计约 4400 次；`approval._tree_entries` 560 次；`_contract_base_candidates` 的
  `for-each-ref` 412 次；`attestation_v3_verify._verify_v2_activation` 的递归回放。
- 激活回放每一步都要读取策略快照，用 `git log --diff-filter=A` 遍历整段历史，再完整重验当年那次切换的交付，
  并递归到前一步。所以单条命令的成本约为"v2 切换次数 ×（一次完整交付验证 + 一次历史遍历）"，
  例如 `done` 477 次、`report` 每次 433 次，并随项目寿命增长。
- 同一次 CLI 调用内约 75% 的 git 查询参数相同，查询的对象不可变。

### 内存

方法：把被测命令放进 Windows Job Object，读取整个进程树的峰值提交内存。本仓库账本 46 MB、3149 行。

- `status` 127 MB / 1.5 s；`change resume` 207 MB / 6.6 s；PreToolUse hook 39 MB；Stop hook 80 MB。
- 完整验证（并发 4）2020 s，进程树峰值 407 MB，单个进程最大 229 MB；其中 keepsail 自身约 123 MB，
  其余来自用户配置的检查。
- keepsail 的内存与账本大小成正比。`change resume` 在一次调用内对整个账本做了 3 次完整展开，`status` 做 1 次。
- 之前的内存不足发生在评审进程同时运行时；单独运行 verify 时没有出现内存紧张。

### 全量测试

- 串行（`2026-11-24-verify-timeout` 要求的本机测量）：2026-11-27 在 `3ad26a4` 上，`PYTHONUTF8=1`、`CI=1`，
  结果为 2754 passed、33 skipped、0 failed，pytest 报告 2833 s。该提交的产品代码与 `main` 相同。
- `-n 2`：1917 s。最慢的那个单测（恢复授权场景）独占约 770 s，也是 `-n 2` 的关键路径。

## 承诺

### C1 生效策略直接从可信基线读取，不回放激活链

- 本地命令与合并判定都以可信基线提交（本地为 `resolve_contract_base`，CI 为 `--base`）上已提交的
  `.harness/review-recognition.yaml` 与 `.harness/verification.yaml` 作为生效策略与必需检查。
  读取时照常校验结构、`policy_digest` 和 `required_checks_digest` 与提交中的检查配置一致。
- 删除：`_verify_v2_activation`、`verify_v2_activation`、`_verified_v2_activation`、`_verified_v2_snapshot`、
  `_introduction_commit`、`_verify_current_rotation`、`activation_replay_scope` 及其在 `cli/__init__.py` 中的作用域、
  `effective_policy.load_effective_v2` 中的回放。
- `PolicySnapshot` 去掉 `authority` 字段。
- 现在，`repository_id` 与 `target_ref` 用于和 `policy-authority.yaml` 及签名比较（`policy_snapshot.py`、
  `effective_policy.py`）。C1 与 C3 删除 authority 和签名之后，它们不再被任何验证使用，因此不再是必需输入。
  这是改动后的性质，不是对现状的描述。`attest verify` 仍接受 `--repository-id`/`--target-ref`，现有 workflow
  （例如 `.github/workflows/merge-gate.yml` 与 `keepsail_workflow.yml` 模板）原样可用；参数若提供，原样写入输出。
- 历史是否经过闸门进入目标分支，由宿主的分支保护与 CI 负责，在 `docs/limitations.md` 中写明。
- 效果：每条命令的策略读取成本是常数，与 v2 切换次数和提交数无关。

### C2 风险边界变更：计划声明 + owner 的记录授权

**什么算风险边界变更。** 候选提交与可信基线相比，满足以下任一条：

- 可信基线上**已启用**的认可策略与候选的生效摘要不同。这包括 v1 与 v2，也包括停用和 v1→v2 升级。
  首次启用（可信基线上没有已启用的策略）不属于这一类，见下文"采用：首次启用"；
- 必需检查契约（`required_check_contract`）的摘要不同。

逐项变化**完整列出**，并且**不按字段清单枚举**：对参与摘要计算的两个规范化对象，逐字段做通用的结构差异。

- 两个对象分别是：
  - 策略：`digest_record` 计算 `policy_digest` 时使用的、去掉 `policy_digest` 自身后的整个对象；
  - 必需检查契约：`required_check_contract` 计算摘要时使用的整个对象，包括 `layers` 和每个检查的完整定义
    （`command`、`shell`、`workdir`、`env`、`timeout_seconds`、`capture`、`must_pass`，以及以后加入摘要的任何字段）。
- 差异按路径列出，每项包含 JSON 路径、方向（`added`/`removed`/`changed`）以及改动前后的值。必需检查的列表
  按 `(来源, ID)` 对齐，因此新增、删除和定义修改分别显示为对应检查下的路径。
- 在通用差异之上，再给出便于阅读的语义标签，例如流程替换、代码审查放宽或加强、必需检查删除、层开关切换、
  启用与停用。标签只是附加说明，完整性由通用差异保证。
- 因为差异与摘要使用同一个规范化对象，摘要不同而差异为空在构造上不会发生。若仍然发生，视为实现错误并拒绝。

现有的 `changed_obligations`/`changed_required_checks` 只列出被删除、替换或削弱的旧义务，由上述差异函数取代。

**计划声明。** 冻结的计划对象（`make_plan_subject` 冻结计划文档与承诺）中必须有一条保留 ID 为
`RISK-BOUNDARY` 的承诺（`plan ready --commitment RISK-BOUNDARY=<文字>`），文字非空。`policy accept`、`done`
和合并判定都从计划对象本身检查这一点；合并判定从 attestation 快照中的批准读取计划对象。
keepsail 不判断文字的语义：语义由计划审查负责，具体改了什么由 owner 授权时看到的逐项变化覆盖。
`scope` 不在计划对象里（`plan ready` 把它单独记在事件中），所以不作为声明的一部分。

授权绑定该 Change 生效批准的计划对象。有风险边界变更、但计划对象缺少这条承诺时，`policy accept` 拒绝记录，
`done` 和合并判定也都拒绝。没有风险边界变更的计划可以不写这条承诺；写了也无害，只在 `status` 中提示。
计划被修订、生效批准换成新的计划对象后，旧计划对象上的授权失效，必须重新授权。

**采用：首次启用（负责人 2026-11-28 确认的冷启动流程）。** 策略还没有启用时，不存在认可的评审流程，
也就不会有计划批准，因此首次启用不能、也不需要通过 Change 完成。它属于采用 keepsail 时的初始设置，与
`keepsail init` 是同一类动作。用户的使用流程是：

1. **采用（一次，由 owner 完成）。** `keepsail init` 增加一个问题："谁的评审结论算数？"。交互模式下提问，
   非交互模式通过参数给出：
   - 默认为 owner 本人：计划流程为 json 形式的 owner 结论，issuer 为 `owner`，经 `review import` 导入；
   - 或者一个外部评审流程：给出流程 ID、版本、issuer 和证据形式；
   - 代码审查选 `off`、`full` 或 `scope`；
   - 必需检查取 `verification.yaml` 的当前内容，并显示给用户确认。

   `init` 据此生成一份**已启用**的 `review-recognition/v2`，`required_checks_digest` 由当前检查配置计算，
   不写 `activation`。owner 把初始化结果作为采用提交，提交到目标分支，与文档中"先往 main 推一个初始提交"
   是同一步，然后再开启分支保护和 CI。这一步不经过 keepsail 的闸门：此时还没有生效的认可策略，
   没有什么可以绕过。信任从 owner 写下的第一份策略开始，这一点写入 `docs/limitations.md`。
   - 非交互模式下没有给出选择时，`init` 仍生成禁用的骨架，并提示用 `policy enable` 启用。
2. **已初始化、仍是禁用骨架的项目：** 新命令 `keepsail policy enable` 问同样的问题，并写入启用后的策略，
   由 owner 作为采用提交提交。只有当可信基线（`resolve_contract_base`）上**没有**已启用的策略时，它才执行；
   已启用时拒绝，并提示改用风险边界变更（计划声明 + `policy accept`）。它不追加事件，也不改变任何 Change 的状态。
3. **日常：** 每个 Change 走 `change start`、`plan ready`、`review import`、实现、`done`、PR。
4. **改规则：** 只适用于已启用的策略，走本节上面所述的风险边界变更。

`init` 与 `policy enable` 生成的策略和检查配置，同 `policy accept` 一样经过 `parse_delivery_policy` 和
`required_check_contract` 校验。

**owner 授权。** 新命令 `keepsail policy accept <change>`：

- 从 Git 重新计算：可信基线与候选的策略摘要、必需检查摘要和逐项义务变化。先把这些逐项打印给人看，
  再追加一个事件 `policy_change_accepted`（非状态转换事件，加入 `transitions.py` 的非转换集合，
  不改 `_TRANSITIONS`）。
- 载荷为 `{version: "policy-acceptance/v1", change_id, plan_subject_id, predecessor_policy_digest,
  target_policy_digest, predecessor_checks_digest, target_checks_digest, obligation_changes}`。
  actor 按 `d-keepsail-identity-resolution-order` 记录。
- 不绑定基线 SHA 或 HEAD，所以 rebase 和代码修复不会使授权失效。目标策略、检查定义或义务变化一旦改变，
  授权就失效，必须重新授权。
- **不再有"继续计划"（负责人 2026-11-28 的决定）。** 策略改变后，进行中 Change 的计划批准如果不被新策略认可，
  就要按新流程重新取得计划批准；`status` 写明原因（"批准所依据的流程已不在生效策略中"）。这只会更严，
  不会放宽任何承诺。删除 `continued_plan_basis` 和 v3 中的 `continued_plan` 依据模式。

**交付时如何检查。**

- `done` 中的 `validate_delivery_obligations` 改为：没有风险边界变更时按原逻辑处理（`mode: unchanged`）；
  有变更时，要求最新一条 `policy_change_accepted` 与重算结果完全一致（`mode: accepted`），否则拒绝，
  并提示运行 `keepsail policy accept`。
- 做出改动的 Change 自身按**改动前**的策略与必需检查交付：计划批准、适用的代码审查和旧必需检查都照常要求。
  不能用改动后的 `off` 免除这个 Change 自身的义务。这条保留 `2026-11-10` 的规定。
- 风险边界变更的交付使用 v3 attestation（与现在相同），授权记录放在 v3 的 `authorization` 字段。
  actor 和时间属于事件外层（`events.py` 的 `Event`），不在载荷中，现有导出只取载荷。因此 `authorization`
  写为 `{acceptance: <载荷>, event_id, actor, ts}`，其中 `event_id`、`actor`、`ts` 原样取自被使用的那条
  `policy_change_accepted` 事件。合并判定和 `report` 从这里读取授权者与时间。
- 合并判定（`verify_v3_transition`/`verify_v3_delivery`）重算改动前后的摘要与逐项变化，要求与记录一致，
  并按基线策略重放这次交付。不验证签名。
- `status`、`report` 和 PR 元数据显示：这是一次风险边界变更、逐项变化、授权者和授权时间。

**与 #158 的关系（如实披露）。** 记录者身份不是密码学身份。在单人环境中，agent 与 owner 共用 Git 身份，
本计划不能从记录上区分二者。授权因此不能**静默**发生：它出现在账本、attestation 和 PR 中，
供 owner 与宿主层的审查看到。如何区分 owner 与 agent 的行为由 #158 决定。这一点写入 `docs/limitations.md`。

**由此解决 #159。** v1 与 v2 都可以通过"计划声明 + `policy accept`"更换认可流程或修改必需检查，
不再需要预先部署密钥。

### C3 移除签名机制；旧数据读得懂、不再执行

**删除：**

- `policy_authority.py` 中的签名、授权、轮换和恢复校验。`parse_unique_yaml` 与仍需要的结构解析移到合适的模块，
  不改语义；
- `initial_policy.py`、`policy initial prepare|confirmation`、`policy authorization import`；
- `transition_guard.py` 中依赖授权与密钥的分支，其余检测逻辑由 C2 取代；
- `review_basis` 与 `cli/review.py` 中的恢复依据；
- `require_signed_obligation_changes`，由 C2 的一致性比较取代；
- `keepsail init` 与 `init_plan` 不再生成 `policy-authority.yaml`；
- 依赖 `cryptography`（`pyproject.toml`、`uv.lock`）。

**维护者审批计划。**

- 生成的默认策略中，计划流程的证据形式改为 `json`，issuer 为 owner，通过 `review import` 导入 owner 的结论。
- 已有策略若列出 `signed-plan-decision`，新版本**不重新解释**它，以免在 owner 不知情时改变认可规则。
  可信 base 上的策略只要仍列出这种形式，新版本在 `status`、`review import`、`done` 和 `attest verify` 中
  都明确拒绝，并给出迁移说明（负责人 2026-11-28 的决定）：
  1. 仍用当前（旧）版本，走一次已有的签名切换，把计划流程改为 json 形式的 owner 结论，按旧义务交付并合并；
  2. 再升级 keepsail（C10 的读端先行顺序）。
  这样，这次认可规则的变化在旧机制下由 owner 签名授权，并留下记录。迁移只能在旧版本上完成，
  `docs/getting-started.md` 的升级说明写明这一点。

**旧数据：**

- `policy-authority.yaml`、`policy-initial-trust.json` 被忽略。`status` 与 `verify` 各提示一行
  "已不再使用，可以删除"。删除它们不算风险边界变更。
- 策略中的 `activation` 字段：仍按原结构接受，只当说明，不再执行；新生成的策略不写这个字段。
- 账本中历史的 `policy_authorization_imported` 事件照常读取和折叠，不再产生作用。不重写历史。
- 旧签名切换中的 `continued_plans` 列表不再生效。升级后，依靠这份列表的进行中 Change 要按生效策略
  重新取得计划批准；`status` 写明原因。
- 历史 v3 attestation（含签名授权、恢复依据、继续计划依据）仍能解析，不再被重放。**新增的** attestation 若携带签名授权
  （`transition`/`recovery`/`rotate_key`），合并判定拒绝，并提示改用 `policy accept`。

### C4 一次操作内复用不可变 Git 事实，批量读取

- 记忆层放在 `core/git_objects.py`，挂在一次 CLI 操作的作用域（`contextvars`）上：操作结束即丢弃；
  没有作用域时不缓存。它是带锁的 LRU，上限为 4096 个条目和 32 MiB。
- 键由仓库根的规范路径和完整 OID 组成。缓存的内容：
  - 40 位 OID 的 `resolve_commit`（ref 与 `HEAD` 不缓存）；
  - `(commit, path)` 的树条目与 blob 字节，"不存在"也缓存；
  - 提交的 `.harness/` 子树；
  - OID 间的 `is_ancestor` 与 `merge_base`。
- 只缓存成功的 git 调用。结构校验（普通文件、UTF-8）每次重做。`_contract_base_candidates` 的 `for-each-ref`
  读取可变 ref，不缓存（#143 的约束 "cache only by object OID, never by ref"）。
- 读取方式：
  - 策略快照改为一次 `ls-tree -z` 加批量读取。实现参考未推送分支 `perf/git-batch-reads` 的 `b6dd11c`，
    在当前代码上重写；
  - 常驻进程的并发：协议是单一管道，所以每个请求（写入 OID 并读完对应输出）在一把锁内完成，
    多个线程的请求串行化，不会交错。
  - 每次操作最多保持一个常驻的 `git cat-file --batch` 进程，在作用域结束时关闭。该进程异常时按现有错误失败，
    不静默回退。
- 作用域修复：顶层 CLI 为所有子命令进入作用域（包括 `report`）；`SensorDispatcher` 与 `run_checks`
  向线程池提交任务时用 `contextvars.copy_context().run`。
- 假设：一次操作期间仓库不发生 fetch --unshallow、replace 或 graft。现有代码在一次操作内本来就会多次查询，
  同样受并发改写影响。这一点写入 `docs/limitations.md`。

### C5 命令内存：在测得重复的路径上，同一份字节只展开一次

- **不使用任何模块级或进程级的记忆。** 持有账本字节的调用方展开一次，把展开后的行（不可变元组）作为
  显式参数传给下游；下游已有接受行的入口（如 `derive_state_from_lines`），缺少的补一个可选参数，
  不传时行为与现在相同。折叠函数本身不读写任何全局状态，与 `d-state-pure-fold` 一致。
- 覆盖范围限于测得重复展开的路径，其余约 20 个直接调用 `effective_event_lines` 的位置不改：
  - `change resume`（实测在一次调用中对整个账本展开 3 次）：`resume` 读取一次字节并展开一次，
    `derive_state`、`knowledge.read_inputs` 的状态推导与 `_tail_events_for_change` 使用同一份行。
    `read_inputs` 的账本回放与状态推导仍来自同一份字节；
  - 严格写入的前置校验：一次校验从读取账本字节开始，展开一次。之后整条前置校验路径都使用这一份行，
    包括 `_current_state`、`_change_event_types`、`_validate_authority` 中的 `derive_state`，以及它调用的
    `review_verdict.read_change_events`。这些函数各加一个可选的行参数，不传时行为不变。
- 计数口径按**字节快照**：同一份字节（以 SHA-256 区分）在上述路径中至多展开一次；事件追加会产生新快照，
  新快照的展开另计。
- `knowledge.load_ledger` 的物理行校验与逐行前缀哈希不变。折叠逻辑和事件格式不变。
- `reducer.py` 只增加接受已展开行的可选参数，不引入状态。按 `d-state-pure-fold` 复核后执行
  `keepsail decision reconcile d-state-pure-fold` 并写明理由；复核不成立则停下交负责人。
- 不做：调整 verify 并发、把检查输出直接写文件、knowledge checkpoint 去重（测量不支持这些改动）。

### C6 重写策略切换场景测试，保留回归入口

- `2026-11-10` 规定的最小回归入口 `python -m pytest -q tests/integration/lifecycle/test_delivery_policy_transition.py`
  与 `.github/workflows/test.yml` 的 `delivery-policy-offline` job 保留。
- 文件内容按新机制重写。保留一个按顺序走完整条路径的测试：在可过闸的隔离 Git 仓库中，依次执行
  `review import`（改动前流程）、`policy accept`、`done`，以及从可信 base 安装的
  `attest verify --base BASE --head HEAD`。
- 其余阶段写成相互独立的测试，各自构建前置状态，以便 `-n 2` 并行：
  - 生效后的普通交付；
  - 下一次切换；
  - 切换后进行中 Change 按新流程重新取得批准；
  - 报告与状态。
- 签名、恢复、轮换和初始信任的测试随功能删除：`test_policy_authority.py`、`test_initial_policy.py`、
  `test_policy_authorization_import.py`、`test_v1_policy_rotation.py`、`test_activation_replay_scope.py`；
  以及 `test_scoped_policy_rename.py`、`test_committed_policy_snapshot.py`、`test_attestation_v3.py`、
  `test_delivery_policy.py`、`tests/integration/cli/test_init.py`、`tests/unit/cli/test_init_plan.py`、
  `tests/unit/engineering/test_attestation.py` 中依赖签名、authority 或激活回放的用例。
  PR 中附一张对照表，逐条说明每个被删断言保护的是已删除的功能，还是已由新测试覆盖。
  用全量测试收集（`pytest --collect-only`）确认没有因导入已删除符号而失败的测试文件。
- CI 中引用这些文件的地方同步修改：
  - `.github/workflows/test.yml` 的 `delivery-policy-wheel` job 原来在已安装的 wheel 上运行
    `test_policy_authority.py`，验证 Ed25519 路径。改为在同一 OS/Python 矩阵上，用已安装的 wheel 运行新机制的
    单元测试（风险边界检测与完整差异、`policy-acceptance/v1` 的结构与一致性校验，放在新文件
    `tests/unit/core/test_policy_acceptance.py`），并断言已安装的 keepsail 在没有 `cryptography` 时可以导入并运行这些路径。
    job 名称与注释随之更新；
  - 新增一个测试：解析 `.github/workflows/*.yml` 中 `pytest` 命令引用的每个测试路径，断言这些路径在仓库中存在，
    防止删除测试文件后留下失效的 CI 步骤。

### C7 测试与回归守卫

测试中包装 `subprocess` 计数 git 进程，判定不依赖计时。

- **C1：**
  - 在 1 次与 3 次 v2 切换的夹具上，`done`、`report`、`review import`、`status` 的 git 进程数相同；
  - `attest verify` 的 git 进程数不随切换次数增长；
  - 基线上的策略摘要与检查配置不符时，照常拒绝。
- **C2：**
  - v1→v1 更换流程、v1→v2、v2→v2、修改必需检查、停用（v1 与 v2 各一例），各自需要授权才能
    `done` 和通过合并判定。停用的例子中，做出改动的 Change 在 `done` 和合并判定两处都仍要满足旧义务；
    候选策略被停用，不妨碍按基线策略判定；
  - 逐项记录完整：新增必需检查、加强代码审查（`off`→`full`、`scope` 增加路径）、新增流程 kind、
    以下每个检查定义字段**单独**修改（`command`、`shell`、`workdir`、`env`、`timeout_seconds`、`capture`、`must_pass`）、
    三个层开关各自的启用与停用（包括所选检查集合不变的情形）、只改 `activation`，都出现在记录中，
    并带正确的路径和方向；
  - 性质测试：对随机生成的策略对与检查契约对，"摘要相同"当且仅当"差异为空"；
  - **采用（冷启动）：**
    - 在空仓库中用非交互参数执行 `keepsail init`（owner 计划流程），生成已启用的策略。owner 提交为采用提交后，
      第一个 Change 走完 `plan ready`、`review import`（owner 的 json 结论）、`done`，`attest verify` 也通过；
    - 外部评审流程的选项生成对应的流程记录；
    - 从禁用的骨架执行 `policy enable` 后，同样能走通上面的流程；
    - 可信基线上已有启用的策略时，`policy enable` 拒绝执行，并提示改用 `policy accept`；
    - 非交互、未给出选择时，`init` 生成禁用的骨架，并给出提示；
  - 授权计划 A 之后修订计划并批准计划 B，A 上的授权失效，需要重新授权；
  - 授权后改动目标策略，或改动检查定义，授权失效；
  - 授权后 rebase 或修改代码，授权仍然有效；
  - 计划对象没有 `RISK-BOUNDARY` 承诺（或文字为空）时，`policy accept`、`done` 和合并判定都拒绝；
    合并判定的检查从 attestation 快照中的计划对象读取；
  - 做出改动的 Change 仍要满足旧必需检查与旧代码审查（`off` 不能免除）；
  - 策略改变后，进行中 Change 的旧批准不被新策略认可时，`done` 拒绝，`status` 给出原因；
    按新流程重新取得批准后可以交付；
  - 不改策略的交付不需要授权，且没有多余授权；
  - 删除 `policy-authority.yaml` 不需要授权。
  - **授权的可见性端到端：** 一次风险边界变更交付后，账本事件、已提交 attestation 的 `authorization`、`status`、
    `report` 和 PR 元数据中的授权者、授权时间、事件 ID 与逐项变化逐字段一致；attestation 中的 `actor`/`ts`
    等于账本中那条事件的外层字段；手工改动 attestation 中的 `acceptance` 使其与重算结果不符时，合并判定拒绝。
- **C3：**
  - 带 `activation` 字段、计划流程为 json 的已有 v2 策略可以读取并照常工作；
  - 可信 base 上的策略列出 `signed-plan-decision` 时，`status`、`review import`、`done`、`attest verify`
    都拒绝，错误信息包含迁移说明，且不接受不带签名的 json 计划结论来代替它；
  - **迁移端到端**，放在 `test_delivery_policy_transition.py` 中，作为一个独立测试：
    1. 在隔离仓库中，用本 Change 的分支起点（测试中以常量固定该提交 OID）构建并安装旧版本，
       沿用该文件现有的 `verify_with_installed_base` 构建方式；
    2. 用旧版本建立计划流程为 `signed-plan-decision` 的 v2 策略，签名授权一次切换，把计划流程改为 json owner 结论；
       按旧义务交付，并由从该 base 安装的旧验证器 `attest verify` 通过；
    3. **升级交付（读端先行）：** 在迁移后的 v2 json base 上，候选为本 Change 的代码，不含风险边界变更。
       该交付由**从迁移后 base 安装的旧验证器**执行 `attest verify --base BASE --head HEAD` 并通过，然后合并；
    4. 在升级后的 base 上，用本 Change 的代码完成一次普通交付：json owner 计划结论经 `review import` 被接受，
       `done` 通过；由从升级后 base 安装的新验证器执行 `attest verify` 并通过。
    第 1、2 步需要旧版本的 `cryptography`，它只进入测试依赖组，不再是运行时依赖；
    运行时依赖中没有 `cryptography` 由 C3 的另一条测试保证；
    固定的旧提交须在运行环境中可用：`.github/workflows/test.yml` 中运行该文件的 `delivery-policy-offline` job
    的 checkout 改为 `fetch-depth: 0`（`pytest` job 已是如此），取历史发生在网络隔离之前。
    提交缺失时测试**失败**并说明原因（例如浅克隆），不跳过；
  - 带历史 `policy_authorization_imported` 事件的账本折叠结果不变；
  - 历史签名 v3 可以解析，包括带 `recovery` 与 `continued_plan` 依据模式的记录：结构解析器继续识别这些模式，
    但新交付的判定不再接受它们；新增的签名 v3 被拒绝；
  - **升级后的进行中 Change：** 在迁移场景中，用旧版本让签名切换的 `continued_plans` 列出一个进行中 Change 并合并；
    换成新代码后，该 Change 的旧批准不再被接受（`status` 给出原因）。按新流程（json owner 结论）重新取得批准后，
    `done` 和 `attest verify` 通过；
  - `cryptography` 未安装时所有命令可用。
- **C4：**
  - ref 不缓存，失败不缓存，没有作用域时不缓存；
  - 两次相继的操作不共享条目；
  - 条目数与字节两个上限；多线程并发读写；
  - 多个线程同时向常驻 `cat-file --batch` 请求不同的 OID，每个线程得到的都是自己请求的内容，不挂起；
  - 批量读取与常驻进程遇到非普通文件、缺失、重复、非 UTF-8、异常输出、提前退出时，按原错误失败；
  - 常驻进程在作用域结束时关闭；
  - `report` 与线程池任务在作用域内。
- **C5：**
  - 计数直接包装 `effective_event_lines` 本身（不是某个辅助函数），按输入字节的 SHA-256 分组：
    `change resume` 中每个字节快照至多展开 1 次；一次严格写入的前置校验中，每个字节快照至多展开 1 次；
  - 传入行与不传行两种调用方式，在现有账本夹具上（含 completion transaction、紧凑 attestation、恢复记录、
    畸形行）得到逐项相同的状态与事件；展开错误的行为不变；
  - 模块中没有新增的全局可变状态（测试断言相关模块的模块级名称集合不变）；
  - `load_ledger` 的前缀哈希与 revision 逐字节不变；
  - 账本在读取后被追加时，`read_inputs` 仍来自同一份快照。
- **全量：** `keepsail verify`、`keepsail decision check`、`keepsail doc check` 通过。

### C8 `2026-11-24` 的串行测量义务

- 本计划不预先修改 `.harness/verification.yaml`。负责人 2026-11-27 的决定是：保持不变，但执行并报告串行测量。
- `2026-11-24` 要求在本计划中包含一次本机完整串行测量；若低于 2000 s，就在本 Change 内恢复串行命令与 2700 s。
  本计划中的测量为 2833 s，所以恢复条件在计划阶段不触发。
- 实施后再用同一方法测量一次，写入 PR 和 `implementation record`：
  - 不低于 2000 s：恢复条件不触发，文件不变。
  - 低于 2000 s：恢复串行命令与 2700 s 是必需检查的变更。本 Change 合并之前，合并闸门用的仍是 base 上的旧验证器，
    它只接受签名授权（C10），因此这一步不能在本 Change 内通过闸门。负责人 2026-11-28 决定：恢复在本 Change
    合并后**紧接着的下一个 Change** 中执行，按 C2 由计划声明、由 owner 执行 `policy accept`，并接受代码审查。
    这是负责人对 `2026-11-24` 中"在本 Change 内"的调整；恢复义务本身不放弃，测量结果仍写入本 Change 的 PR。
    作者不代替 owner 授权。
- 2026-12-31 由负责人重新评估的兜底条款不变。

### C9 文档与决策

- `docs/getting-started.md`：删除"建立初始交付策略"一节的签名流程，按"采用（`init` 或 `policy enable`）、
  日常、改规则（计划声明 + `policy accept`）"三段重写，说明如何首次启用或修改策略
  （计划声明 + `policy accept`）。
- `docs/limitations.md`：
  - 策略的来历由宿主分支保护负责；
  - 授权不是密码学身份，在单人环境中与 agent 共用身份（#158）；
  - C4 的单次操作假设。
- `docs/implementation-architecture.md`：更新策略读取、风险边界变更和授权记录的说明。
- `docs/product-architecture-coverage.md`：增加一条带日期的更新。
- `docs/cli-reference.md`：由 `doc check --fix` 重新生成。
- `AGENTS.md` 及其生成模板（`engineering/agents_md_render.py`）：把"Policy transitions must … carry the exact signed
  authorization … Recovery and initial trust require their own pre-established owner-controlled paths"改为新的规则。
- `2026-11-10-delivery-policy-transition` 中被取代的承诺：
  - C3 的"策略变更须由旧可信依据验证授权"改由 C2 的 owner 授权取代；
  - C4（受限恢复）删除；
  - 授权记录一节（Ed25519）、激活定位与生效后回放、初始信任建立都被取代。
  - 其余（交付义务、`code_review_not_required`、完成事务、必需检查摘要、可见性）保持。
  - 在 `docs/product-architecture-coverage.md` 中写明取代关系。已批准的计划文件本身不改写。
- 决策：
  - `d-policy-replay-offline-v2` 要求验证路径使用"独立提供的仓库与 ref 身份"。这个身份只用于签名比较，
    本 Change 删除签名后它不再是输入，与该决策的正文冲突。处理方式：
    - 用 `keepsail decision new d-policy-replay-offline-v3` 新增一条决策，`supersedes: d-policy-replay-offline-v2`。
      正文只保留"策略、交付、no-review、v3 重放和 Git 对象路径使用已提交的 Git 证据，不访问网络"，
      不再要求身份输入；检查脚本沿用 v2 的网络客户端检测，路径列表去掉已删除的文件；
    - 先用 `decision ratify --dry-run` 确认检查能拦截违规；
    - ratify 并取代 v2 是负责人的行为。负责人 ratify 之前，本 Change 不执行 `done`；作者不代为 ratify。
    - v2 的正文不手工修改。
  - `transitions.py` 的改动只在非转换集合中加入新事件类型，按 `d-fixed-transition-matrix` 的要求执行
    `decision reconcile` 并写明理由。
  - 新事件类型同时加入 `events.py` 的已知事件类型。按 `d-events-append-only` 的要求复核：只新增类型，
    不改写或删除已有事件。复核成立后执行 `decision reconcile d-events-append-only` 并写明理由。
  - 用 `keepsail decision new` 提交一条 proposed 决策（不附锚点，是否 ratify 由负责人决定）：
    "改变认可策略或必需检查的 Change 须计划声明并由 owner 记录授权；keepsail 不以签名或回放证明策略来历。"

### C10 读端先行：升级顺序

- 合并闸门从目标分支的 base 安装验证器（`.github/workflows/merge-gate.yml`）。在新版本进入目标分支之前，
  base 上的旧验证器只接受签名授权，不认识 `policy-acceptance/v1`。
- 因此，升级顺序是：
  1. 升级 keepsail 的那次交付本身**不得**包含风险边界变更，按普通交付通过旧验证器；
  2. 新验证器进入目标分支后，之后的 Change 才能用 `policy accept` 改变策略或必需检查。
- 本 Change 就是第一步：它不修改 `.harness/review-recognition.yaml` 与 `.harness/verification.yaml`
  的生效内容（C8 的恢复放到下一个 Change），可由本仓库 base 上的旧验证器验证。
- 不做自动的版本探测：本 Change 不提升版本号，用户的 workflow 固定的验证器版本也各不相同，探测不可靠。
  顺序写入 `docs/getting-started.md` 的升级说明和 `docs/limitations.md`：在旧验证器仍在 base 上时
  提交风险边界变更，合并闸门会以"缺少签名授权"拒绝，此时先合入升级即可。
- 测试：在隔离仓库中，base 为当前 `main` 的提交并从它安装验证器，候选为本 Change 的代码、不改策略，
  `attest verify --base BASE --head HEAD` 通过。

## 不做

- 不引入新的签名、密钥或审计命令；不区分 owner 与 agent 身份（#158）。
- 不缓存跨命令的验证结果，不缓存 verify 的检查结果（B14），不调整评审顺序（B39）。
- 不改写历史账本或已提交的 attestation。
- 不修改 `.harness/verification.yaml` 和 `.harness/review-recognition.yaml`（C8 的恢复在下一个 Change 中进行），
  不改 pytest worker 数。
- 不发布新版本，也不提升模板固定的 CLI 版本。
- 不处理本仓库的认可策略本身。更换本仓库的评审流程（#159 的直接诉求）将来作为单独的 Change，使用 C2 的路径。

## 验收测量

实施后用同一方法测量（脚本不入库），写入 PR：

- **Git：**
  - `test_delivery_policy_transition.py` 全文件由产品代码发起的 git 调用合计，低于原单一场景 9492 次的 25%，
    文件总耗时低于 200 s（本机）。这不是同一场景的前后对比：原场景（恢复授权）已随功能删除。
    PR 中分别报告改动前该文件各测试的数值与改动后各测试的数值；
  - 同一场景的前后对比：在一个不涉及签名的普通 v2 交付场景（改动前后都存在）中，分别报告 `done` 与
    `attest verify` 的产品 git 调用次数；
  - 3 次切换夹具上，`done` 由产品代码发起的 git 进程不超过 60 次；
  - 另构造一个 10 步切换的夹具（不入库），报告 `status` 与 `done` 的 git 次数，应与 1 步夹具相同。
- **内存：** 用 Job Object 方法重测 `status`、`change resume`、两个 hook 和完整验证。
  `change resume` 的进程树峰值不高于 `status` 加 50 MB（实施前分别为 207 MB 和 127 MB）。
- **全量测试：** 报告串行（C8 的义务）与 `-n 2` 的时长。

未达到目标时如实报告实测值和原因，不放宽测试。

## 文件范围（估计）

- `src/keepsail/`：
  - `core/`：`attestation_v3*.py`、`policy_*.py`、`effective_policy.py`、`initial_policy.py`（删除）、
    `delivery_policy.py`、`transition_guard.py`、`review_basis.py`、`approval.py`、`emit_validation.py`、`events.py`、
    `transitions.py`、`no_review.py`、`verification_*.py`、`git_objects.py`、`scope_match.py`、`reducer.py`、`knowledge.py`；
  - `cli/`：`__init__.py`、`policy.py`、`review.py`、`done.py`、`verify.py`、`pr.py`、`init.py`、`init_plan.py`、`change.py`、`attest.py`；
  - `engineering/`：`attestation.py`、`attestation_v3.py`、`delivery_policy.py`、`agents_md_render.py`；
  - `sensors/dispatcher.py`、`sensors/verification_runner.py`。
- `pyproject.toml`、`uv.lock`、`AGENTS.md`、`scripts/gen_cli_reference.py`（如需）、`.github/workflows`（如需）。
- `tests/`：上述测试的删除、重写与新增。
- `docs/`：`getting-started.md`、`limitations.md`、`implementation-architecture.md`、`product-architecture-coverage.md`、
  `cli-reference.md`，以及 `docs/decisions/` 下新的 proposed 记录。
- 本计划。

## 产品基础核对

- **F1：** 改变承诺或风险边界必须经过计划声明和 owner 授权，并在账本、attestation 和 PR 中可见；
  做出改动的 Change 仍按旧义务交付。agent 不能**静默**改变它们。是否能从身份上区分 agent 由 #158 处理，
  这里如实披露。
- **owner 的权限：** 认可策略与风险边界由 owner 决定，keepsail 记录并执行，不再要求 owner 先部署密钥才能行使决定（#159）。
- **证据分层：** 策略来历交给宿主分支保护与 CI，keepsail 不在本地重复证明。
- **开源用户：** 设计不依赖本仓库的使用习惯。命令成本不随项目寿命里的策略变化次数增长；已部署 v2 的项目，
  若计划流程为 json，不需要迁移即可继续工作；若使用 `signed-plan-decision`，需先用旧版本迁移（C3）。
