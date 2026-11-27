---
change: 2026-11-27-git-subprocess-cost
stage: plan
---

# 确定性验证只做一次：记住激活验证结果，复用不可变 Git 事实，控制命令内存

关联 issue：#143（Windows 上 git 子进程成本拖慢 verify/done）。

## 这一版与前 8 版的关系

前 8 版（最后一版 `3ad26a4`）都被独立评审拒绝，负责人与作者随后共同否定了它们的方向：

- 前几版删除了每条命令的激活链回放，改变了信任模型；为补回失去的保证，又新造了 `policy audit`，
  并背上了风险接受、取代 `2026-11-10` 承诺等产品级决策。一个性能 Change 不应改变信任模型。
- 负责人的问题是"历史链已经验证通过，为什么每次重跑"。对应的答案是**记住结果，不要重跑**，
  而不是"不再验证"。

本版不再包含前几版的审计、威胁模型变更、风险接受或对已批准承诺的取代。

## 不变量（本计划不改变）

- 信任模型与验证语义：每条命令仍按 `2026-11-10-delivery-policy-transition` 的规定使用已验证的生效策略；
  回放的检查内容、顺序与失败行为不变。本计划只让"同一组输入已经验证通过"的事实被复用。
- 闸门、attestation、授权记录、策略文件和事件格式。
- v1 策略的行为。
- `.harness/verification.yaml`（见 C6）。
- 已批准计划的承诺。`2026-11-24-verify-timeout` 的测量义务按其原文执行（见 C6）。
- 不新增安全组件；不新增网络依赖（`d-policy-replay-offline-v2`）。

## 测量（2026-11-26/27，本机 Windows；作者报告值）

测量脚本按 #143 的要求不入库，与 `2026-11-24-verify-timeout` 采用同样的说明方式。

### Git 子进程

- 单个测试 `test_recovery_plan_review_uses_only_the_signed_process_and_digest[False]`：
  - 耗时 769 s，9568 次 git 子进程；产品代码 9492 次（99%），测试夹具 76 次。
  - 每次 git 进程约 74 ms，即 Windows 的进程创建成本。
- 产品调用点：
  - `scope_match.resolve_commit` 2756 次；
  - `git_objects.optional_regular_blob_bytes` 每个 blob 一次 `ls-tree` 加一次 `cat-file`，合计约 4400 次；
  - `approval._tree_entries` 560 次；
  - `approval._contract_base_candidates` 的 `for-each-ref` 412 次；
  - `attestation_v3_verify._verify_v2_activation` 的递归回放。
- 同一次 CLI 调用内约 75% 的 git 查询参数相同、对象不可变。
- 单条命令的 git 次数随此前 v2 切换次数线性增长，例如 `done` 477 次、`report` 每次 433 次。
- 因此 #143 的停止条件落在第三项："成本主要在产品路径"。

### 内存

方法：把被测命令放进 Windows Job Object，读取整个进程树的峰值提交内存（`PeakJobMemoryUsed`，精确值，
不是采样）和单个进程的最大值。本仓库账本 `.harness/events.jsonl` 为 46 MB、3149 行。

- 单条命令（整个进程树峰值 / 墙钟）：
  - `status` 127 MB / 1.5 s；`change resume` 207 MB / 6.6 s；
  - `decision check` 57 MB；`decision check --changed` 38 MB；
  - PreToolUse hook 39 MB / 0.5 s；Stop hook 80 MB / 1.5 s。
- 完整验证（ruff、mypy、pytest `-n 2`，并发 4）：
  - 没有批准计划时 `keepsail verify` 拒绝运行，所以测量直接调用同一个 `VerificationRunner.check`，
    只跳过识别前置检查，不写事件。
  - 2020 s，进程树峰值 407 MB，单个进程最大 229 MB。
  - 逐项单独运行时，最大的进程都是 keepsail 自身（约 123 MB）；ruff 与（缓存已热的）mypy 增加很少。
    其余主要是 pytest 主进程、两个 worker 及测试启动的子进程。
- keepsail 自身的内存与账本大小成正比：`status` 的 Python 堆峰值为 112 MB，同时持有整个文件的 bytes、
  解码后的 str、行列表和解析后的对象。`change resume` 对整个账本做了 3 次完整处理，分别在
  `resume`、`knowledge._inputs_from_content` 和 `_tail_events_for_change`；`status` 1 次。
- 账本构成：22 条 `knowledge_checkpointed` 共 22.4 MB，其中一条 13 MB，写于 2026-10-29。
  2026-10-30 起 checkpoint 已改为增量表示，2026-11-04 以来账本只增长了 4.8 MB。
  体积问题属于历史数据，现有代码已不再产生，本计划不处理。
- 结论：
  - 单独运行 verify 时没有出现内存紧张。运行前空闲物理内存约 6 GB（共 16 GB）；之前的内存不足发生在
    DSH 评审进程同时运行时。
  - 对所有用户都成立的问题是：每条命令的内存和时间随账本线性增长，重复的完整处理又把它放大。

### 全量测试

- 串行（`2026-11-24-verify-timeout` 要求的本机完整串行测量）：2026-11-27 在 `3ad26a4` 上运行
  `python -m scripts.run_project_check pytest -q -p no:cacheprovider`，设置 `PYTHONUTF8=1`、`CI=1`。
  结果为 2754 passed、33 skipped、0 failed，pytest 报告 2833 s（墙钟 2868 s）。
  - 该提交与 `main` 的差异只有本计划文件，产品代码与 `main` 相同。
  - 之前一次串行 2737 s 的测量有 73 个本机 GBK 编码失败，不算合格测量，被这一次取代。
- `-n 2`：1917 s，全部通过；verify 中的同一检查（上文内存测量）为 2020 s。
- 最慢的单个测试独占约 770 s，也是 `-n 2` 的关键路径。

## 根因

### R1 已验证的激活链在每条命令重新回放

`_verify_v2_activation` 的结果只取决于已提交的 Git 对象：可信基线提交、它可达的历史、
以及验证器代码本身（见 C1 的纯函数前提）。现有 `activation_replay_scope` 已在一次 CLI 调用内记住结果，
但下一条命令从头再验证整条链，所以每条命令的成本是 O(v2 切换次数)，并随项目寿命增长。

此外，进程内的记忆在两处失效：

- `cli/__init__.py:155-159` 进入作用域的子命令集合不含 `report`；
- `SensorDispatcher` 在线程池中运行 `VerificationRunner`（`dispatcher.py:203-204`）时不复制 `contextvars`，
  所以 `verify`/`done` 的检查线程里每次调用都新建作用域。

### R2 同一调用内重复查询不可变 Git 事实

完整 OID 的 `rev-parse`、`(commit, path)` 的 blob、提交的树、祖先关系、merge-base 都不可变，
却被重复查询；每个 blob 读两个进程。

### R3 内存

每条命令都完整读取并处理账本；个别命令（例如 `change resume`）在同一次调用内处理 3 次，
各次的中间结果在峰值时同时存在。账本会随项目寿命增长，所以这部分开销对每个用户都会持续增长。
verify 进程树的其余内存来自用户自己配置的检查，不属于 keepsail 的开销。

## 承诺

### C1 按内容寻址持久记住激活验证结果

**记住什么。** `_verified_v2_activation` 的**成功**结果（结果字典）。失败从不持久化。

**键。** `(提交完整 OID, repository_id, target_ref, 验证器摘要)`：

- 提交 OID 是内容寻址的，键中不出现 ref 或分支名（#143 的约束）。
- 验证器摘要 = 已安装 `keepsail` 包内全部 `*.py` 文件（按相对路径排序）的内容 SHA-256，
  加上 `KEEPSAIL_ACTIVATION_CACHE_SCHEMA = 1`。验证器代码任何改动（包括可编辑安装下的未发布改动）都换键，
  不依赖人工递增版本号。摘要在一个进程内只计算一次。

**纯函数前提（实施的第一步，先于缓存代码）。**

- 逐一检查 `_verify_v2_activation` 调用树中的输入，确认只来自：键中的提交、该提交可达的 Git 对象、
  显式传入的 `repository_id`/`target_ref`，以及验证器代码。已知的临时文件（`tempfile` 中由已提交 attestation
  派生的 lifecycle）属于派生值，不是外部输入。
- 加一个测试：同一仓库中，删除工作区的 `.harness/events.jsonl`、改写工作区的策略文件、移动 `refs/heads/main`
  之后，以同一 OID 调用 `verify_v2_activation`，结果与之前逐字节相同。
- 如果检查发现某条路径读取了工作区、账本、时钟或环境变量，就把该输入加入键；无法加入键的，
  该路径不持久化，只用进程内记忆，并在 PR 中写明。

**存放。**

- `$(git rev-parse --git-common-dir)/keepsail/activation-v1/<sha256(规范化键)>.json`，
  不在工作区内，不进入提交，无需改 `.gitignore`。
- 文件内容为 `{schema, key, result, result_digest}`。读取时要求 `key` 与当前键完全相等、
  `result_digest` 与 `result` 一致，否则视为未命中，重算后覆盖。
- 写入：临时文件加 `os.replace`，原子替换；写失败（只读、权限、磁盘满）忽略，不影响命令结果。
- 上限：目录中最多 512 个文件，超出时按修改时间删除最旧的。单个结果约 1 KB。

**命中后仍要做的事。** 命中只省去回放；`PolicySnapshot` 仍从该提交读取（经 C2 批量读取），
并检查其 `policy_digest`、`required_checks_digest`、`activation_commit` 与记住的结果一致，不一致按未命中处理。

**复杂度。** 回放递归到前任基线时同样经过 `_verified_v2_activation`，命中即停止。主分支前进后，
第一条命令只验证新增的一步，O(Δ)。换机器、清空 `.git/keepsail/` 或升级验证器后，冷启动完整验证一次。

**不持久化（仅用进程内记忆）的条件。**

- 浅克隆（`git rev-parse --is-shallow-repository` 为 `true`）；
- 存在 `refs/replace/` 下的 ref，或 `.git/info/grafts`，或设置了 `GIT_REPLACE_REF_BASE`、
  `GIT_GRAFT_FILE`、`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`（这些会让同一 OID 的历史或对象来源变化）；
- 设置了 `KEEPSAIL_NO_ACTIVATION_CACHE=1`；
- 以上检测本身失败。

**为什么跨命令持久是安全的（#143："cache lifetime must not exceed a single operation unless shown to be safe"）。**

- 结果是键的纯函数：同一提交、同一身份、同一验证器代码，重算必得同一结果。持久化不改变任何判定，只省时间。
- 缓存只用于加速，不作为依据：缓存条目不产生任何闸门结论；闸门的权威在 CI。
  `keepsail_workflow.yml` 与本仓库 workflow 不恢复这个目录（不加 `actions/cache`），CI 每次冷启动完整验证。
- 本地信任等级不变：缓存与本地 refs、对象库同在 `.git/` 下。能写缓存的人同样能移动 `refs/heads/main`、
  `refs/remotes/origin/*`，或直接改写对象库；这些已是本地命令信任的输入。缓存没有引入新的可写信任来源。
- 失败不持久化，所以修复环境（例如补齐对象）后立即重新验证。

### C2 进程内复用不可变 Git 事实，批量读取

- 记忆层放在 `core/git_objects.py`（已在 `d-policy-replay-offline-v2` 的检查路径内），进程内、带锁的 LRU，
  上限为 4096 个条目和 32 MiB，超出任一上限即淘汰最久未用的条目。只存不可变值（bytes、str、bool、tuple）。
  为避免导入循环，`git_objects.py` 对 `ApprovalError` 改为函数内延迟导入。
- 键包含仓库根的规范路径和完整 OID。缓存：
  - 40 位十六进制 OID 的 `resolve_commit`（ref 和 `HEAD` 不缓存）；
  - `(commit, path)` 的树条目查询结果（模式、类型、OID）与 blob 字节；"不存在"也是成功的查询结果，同样缓存；
    普通文件、UTF-8 等结构校验每次重新执行；
  - 提交的 `.harness/` 子树列表（不缓存整棵仓库树）；
  - OID 之间的 `is_ancestor` 与 `merge_base`；
  - `_introduction_commit` 的 `(commit, path)` 结果。
- 只缓存成功的 git 调用；git 失败不缓存。
- `read_policy_snapshot` 及可信基线快照改为一次 `ls-tree -z` 加一次 `cat-file --batch` 读取所需文件，
  校验语义和错误行为不变。实现参考未推送分支 `perf/git-batch-reads` 的 `b6dd11c`（`regular_blob_texts`），
  在当前 `main` 上重新实现并评审。
- `_contract_base_candidates` 的 `for-each-ref` 结果对应可变 ref，只在一次 CLI 调用内复用。
- 作用域修复（R1）：
  - 顶层 CLI 为所有子命令进入作用域，包括 `report`；
  - `SensorDispatcher` 与 `run_checks` 提交线程池任务时用 `contextvars.copy_context().run`，
    线程共享同一个带锁的作用域对象。
- 假设：一次进程运行期间，同一仓库不发生 fetch --unshallow、replace 或 graft；keepsail 自身不做这些。
  外部并发改写历史时，`is_ancestor`/`merge_base` 的进程内结果可能过时，写入 `docs/limitations.md`。

### C3 命令内存

- **一次调用内账本只处理一次（按内容寻址）。**
  - 新增 `effective_ledger_lines(path)`：读取账本 bytes，以 SHA-256 为键，在进程内记住
    `effective_event_lines` 的结果（不可变的 `tuple[str, ...]`），只保留最近 1 个条目。
  - `derive_state`、`knowledge.read_inputs`/`_inputs_from_content`/`load_ledger`、
    `cli/change.py` 的 `_tail_events_for_change` 改为经由它取得行。
  - 账本在调用中被追加时内容摘要改变，自动重新处理，不会读到旧结果。
  - 记住的是同一份 bytes 的纯函数结果，折叠逻辑本身不变，因此与 `d-state-pure-fold`、
    `d-events-append-only` 一致；实施时运行 `keepsail decision check --changed` 确认。
- 不改变事件格式与折叠语义，不重写历史账本。

**不做的内存项（测量不支持）：**

- verify 默认并发（4）不改：本次测量中进程树峰值主要来自用户的检查，并发不是瓶颈；
  按内存调节并发需要另外的设计和跨平台测量。
- 检查输出直接写文件不做：本仓库检查的输出很小，没有测得收益。
- knowledge checkpoint 去重不做：增量表示已在 2026-10-30 落地。

### C4 回归守卫

测试中包装 `subprocess` 计数 git 进程，判定不依赖计时。夹具的必需检查是不调用 git 的 `python -c`。

- **链长无关。** 同一构造函数生成 1 次和 3 次 v2 切换的夹具（3 次夹具在 1 次夹具之后追加两次切换，
  再追加相同的一次普通交付）。在**持久缓存已预热**的状态下，`done`、`attest verify`、`report`、
  `review import`、`status` 的 git 进程数在两种夹具上相同。
- **冷启动只验证一次。** 清空缓存目录后：第一条命令可以随链长增长；紧接着的第二条命令与预热状态的次数相同。
- **O(Δ)。** 预热后在主分支追加一次 v2 切换，下一条命令的 git 次数只比预热状态多出验证这一步所需的次数，
  且与此前的链长无关（1 次与 3 次夹具上的增量相同）。
- **验证器换键。** 改变验证器摘要（测试中替换摘要函数）后不命中旧条目。
- **语义不变。** 对每一个现有的回放负例（激活 attestation 在引入后被修改、前任不可达、目标策略摘要不符等），
  分别在冷缓存与预热缓存下运行：两次的退出码和错误信息相同。预热缓存下，篡改发生在新提交上，
  所以新提交不命中，仍被拒绝。
- **不持久化条件。** 浅克隆、存在 `refs/replace/`、设置 `KEEPSAIL_NO_ACTIVATION_CACHE=1` 时，缓存目录不被写入。
- **缓存损坏。** 条目被截断、`key` 不符、`result_digest` 不符、目录只读时，命令结果与无缓存时相同。
- **账本处理次数。** 包装 `effective_event_lines` 计数：账本在调用期间未变时，`status`、`change resume`、
  `done`、`report`、`verify` 各自对完整账本的处理不超过 1 次；在 1 次和 3 次切换的夹具上次数相同。
- **测试隔离。** 每个测试用独立的临时仓库，因而有独立的 `.git/keepsail/`；进程内记忆层提供仅测试使用的
  `clear()`；计数只统计被测命令调用期间启动的 git 进程。

### C5 拆分策略切换场景测试

- 把 `tests/integration/lifecycle/test_delivery_policy_transition.py`（797 行，单个参数化测试）按阶段拆成
  相互独立、各自构建前置状态的测试，放在 `tests/integration/lifecycle/policy_transition/`：
  恢复授权、负例、已安装基线验证器、继续计划、生效后的普通交付、下一次切换、密钥轮换、报告与状态。
- 断言内容与原测试逐条对应，不删除断言；PR 说明附对照表。
- `.github/workflows/test.yml` 中 `delivery-policy-offline` job 改为运行该目录。
- 不新增 `e2e` 标记；本地与 CI 的覆盖范围不变。

### C6 `verification.yaml` 不变；执行 `2026-11-24` 的测量义务

- 本计划不修改 `.harness/verification.yaml`。负责人于 2026-11-27 选择 "Drop C8 here"
  （"Leave verification.yaml as it is. Still run the serial measurement the 2026-11-24 plan requires and report it."）。
- `2026-11-24-verify-timeout` 要求本 Change "在其计划中包含一次本机完整串行测量；若低于 2000 s，
  在本 Change 内恢复串行命令与 2700 s"。本计划"测量"一节已包含这次测量，结果为 2833 s，
  不低于 2000 s，所以恢复条件在本计划中不触发。
- 实施后再做一次同方法的串行测量，写入 PR 说明和 `implementation record`。若届时低于 2000 s：
  恢复需要修改必需检查定义，而自 #140 起 v1 守卫拒绝替换必需检查（`transition_guard.py:121-126,191,290`），
  本仓库无法在本 Change 内合法完成。按负责人的 "Drop C8 here"，本 Change 只报告该结果；
  `2026-11-24` 中 2026-12-31 由负责人重新评估的兜底条款不变。这一锁定问题归入负责人已安排的后续 v2 讨论。

### C7 文档与决策

- `docs/implementation-architecture.md`：§9 增加"激活验证结果的持久记忆"：键、存放、不持久化条件、
  与信任等级的关系。
- `docs/limitations.md`：C2 的进程内假设；持久记忆在浅克隆和 replace/graft 下不启用。
- `docs/product-architecture-coverage.md`：增加一条带日期的更新。
- `docs/cli-reference.md`：如有 CLI 文本变化，由 `doc check --fix` 重新生成。
- 用 `keepsail decision new` 提交 proposed 决策（不附 `@decision:` 锚点，是否 ratify 由负责人决定）：
  - 确定性验证按内容寻址只做一次：结果以不可变输入为键记住，验证器代码变化即换键；
  - Windows 进程创建成本要求批量读取 Git 对象并在进程内复用不可变事实；
  - 性能 Change 不改变信任模型或产品公理；需要改变时作为单独的产品决策处理。

## 不做

- 不评估 v2 交付策略机制本身是否过重（负责人安排在本 Change 之后单独讨论）。
- 不删除或削弱任何回放检查；不新增审计命令或 workflow。
- 不缓存 verify 检查结果（B14），不调整评审顺序（B39）。
- 不改变 attestation、授权记录、策略文件或事件格式；不改变 v1 行为。
- 不修改 `.harness/verification.yaml`，不改变 pytest worker 数。
- 不优化测试夹具（测量显示夹具占 1%）。
- 不发布新版本，也不提升模板固定的 CLI 版本。

## 测试

- **C1**：C4 中的链长、冷启动、O(Δ)、换键、语义不变、不持久化条件、缓存损坏各项；纯函数测试；
  缓存文件不出现在 `git status` 中；并发两个进程写同一键不产生损坏文件。
- **C2**：ref 不缓存；失败不缓存；条目数与字节两个上限；子树只含 `.harness/`；多线程并发读写同一键结果正确；
  批量读取遇到非普通文件、缺失路径、重复路径、非 UTF-8、异常输出时按原错误失败；`report` 与线程池任务在作用域内；
  两次独立 CLI 调用之间不复用 `for-each-ref` 结果。
- **C3**：bytes 相同则命中；追加一行后不命中且结果包含新行；返回值不可变；在现有账本夹具
  （含 completion transaction、紧凑 attestation、恢复记录、畸形行）上，经由新函数与直接调用
  `effective_event_lines` 的结果逐项相同；恢复记录引发的 `EventSchemaError` 行为不变，且错误不被记住。
- **C5**：拆分后的测试全部通过，断言对照表完整。
- **全量**：`keepsail verify`、`keepsail decision check`、`keepsail doc check` 通过。

## 验收测量

实施后用同一方法测量（脚本不入库），写入 PR 说明：

- **Git。** 拆分后场景测试中由产品代码发起的 git 调用合计，降到原单一场景 9492 次的 25% 以下；
  拆分测试总耗时低于 200 s（本机）。C4 的 3 次切换夹具上，预热后 `done` 由产品代码发起的 git 进程不超过 60 次。
- **内存。** 用同一 Job Object 方法在本仓库重测 `status`、`change resume`、两个 hook 和完整验证；
  `change resume` 的进程树峰值不高于 `status` 的峰值加 30 MB（实施前分别为 207 MB 和 127 MB）。
- **全量测试。** 串行和 `-n 2` 的时长都报告（串行即 C6 的义务）。

未达到目标时，在 PR 中如实报告实测值与原因，不放宽测试。

## 文件范围（估计）

- `src/keepsail/core/`：`attestation_v3_verify.py`、`effective_policy.py`、`policy_snapshot.py`、
  `git_objects.py`、`scope_match.py`、`approval.py`，新增 `activation_cache.py`；
  `events.py`、`reducer.py`、`knowledge.py`。
- `src/keepsail/cli/__init__.py`、`src/keepsail/cli/change.py`（`resume`、`_tail_events_for_change`）。
- `src/keepsail/sensors/dispatcher.py`、`src/keepsail/sensors/verification_runner.py`。
- `.github/workflows/test.yml`。
- `tests/`：拆分出的测试，新增记忆层、持久缓存、回归守卫测试。
- `docs/`：`implementation-architecture.md`、`limitations.md`、`product-architecture-coverage.md`、
  `cli-reference.md`（如需），`docs/decisions/` 下新的 proposed 记录。
- 本计划。

## 产品基础核对

- **F1（不静默偏离承诺）。** 每条命令仍使用经完整验证的生效策略；持久记忆只复用同一输入的已有结论，
  不产生新结论，也不越过任何检查。闸门判定在 CI 冷启动重新计算。
- **F2（记录的权威可恢复）。** 缓存不是记录：删除它不丢失任何权威，只需重新计算。
- **负责人的权限。** 本计划不改变风险边界、认可策略或已批准承诺，无需负责人另行接受风险。
- **开源用户。** 设计不依赖本仓库的使用习惯：不同的合并方式、浅克隆、只读 `.git`、无持久缓存的 CI 都能正确工作，
  只是可能得不到加速。
- **`2026-11-10` 的 C3**（"合并判定可用已提交的证据离线重放"）保持。
