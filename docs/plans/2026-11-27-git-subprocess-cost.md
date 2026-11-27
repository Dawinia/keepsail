---
change: 2026-11-27-git-subprocess-cost
stage: plan
---

# 确定性验证按步只做一次：增量记住激活验证结果，复用不可变 Git 事实，控制命令内存

关联 issue：#143（Windows 上 git 子进程成本拖慢 verify/done）。

## 这一版与之前各版的关系

- 前 8 版（最后一版 `3ad26a4`）都被独立 DSH 评审拒绝。它们删除了每条命令的激活链回放，又新造了 `policy audit`
  来补回保证，改变了信任模型。负责人与作者随后否定了这个方向：答案是**记住结果，不要重跑**，而不是"不再验证"。
- 第 9 版（`3db9fb7`）按这个方向重写，由负责人选定的 Codex（codex-cli 0.172.0、gpt-6.1-terra、high）评审，
  结论为拒绝，4 个阻断项。原始输出保留在 `.harness/scratch/2026-11-27-git-subprocess-cost/plan-review-9/`。
  该结论不是当前 v1 认可契约中的流程，keepsail 无法把它记录为认可证据（#159），PR 中如实披露。
  本版对 4 项的处理：
  - **第 1 项（缓存条目未经认证）**：事实成立，论证改写。本版不再声称缓存"与本地 refs 同级"，
    而是写明缓存条目是 agent 可写的本地输入，伪造它可以让本地命令接受一个未经验证的激活；
    并说明这与本地现有的、已明确让出的信任边界属于同一类，同时规定合并验证路径永不读取它（C1）。
    这一取舍由负责人于 2026-11-27 决定，理由见 R1："链长随项目寿命增长，逐步全量回放不可接受"。
  - **第 2 项（验证器摘要遗漏依赖）**：接受，摘要纳入运行时依赖闭包与解释器版本（C1）。
  - **第 3 项（C3 破坏物理账本校验与单一快照）**：接受，C3 改为对已持有的字节做按内容寻址的记忆，
    不再按路径重读，`load_ledger` 的物理行校验不变。
  - **第 4 项（C5 改动已批准的回归入口）**：接受，C5 保留原文件、原入口命令与完整端到端路径。
  - 非阻断项（`PolicySnapshot` 没有 `activation_commit`）：命中后的复核改为比较快照中确实存在的字段（C1）。
- 第 10 版（`8be1a34`）由同一 Codex 配置评审，拒绝，2 个阻断项；原始输出保留在 `plan-review-10/`。
  评审确认第 9 轮的账本与回归入口问题已解决，也未因缓存未经认证本身拒绝。本版对 2 项的处理：
  - **依赖只按名称和版本标识**：接受。验证器摘要改为对依赖闭包中每个分发包实际安装的文件内容做哈希，
    可编辑安装或来源无法确定的依赖使持久记忆停用（C1）。
  - **冷启动边界只在 CLI 层规定**：接受。持久记忆改为默认关闭、由本地生命周期命令显式开启；
    核心合并判定入口 `engineering/attestation.py` 的 `verify_attestations` 在内部强制冷启动，
    即使外层已开启也不读写，并在该入口直接测试（C1、C4）。

## 不变量（本计划不改变）

- 验证语义：每一步回放的检查内容、顺序与失败行为不变；没有任何回放检查被删除或削弱。
- 合并验证（`attest verify`，CI 从可信 base 安装验证器运行）的输入与语义完全不变：它不读取持久记忆，
  每次从头完整回放。
- 闸门、attestation、授权记录、策略文件和事件格式；v1 策略的行为；`.harness/verification.yaml`（见 C6）。
- 已批准计划的承诺。`2026-11-10-delivery-policy-transition` 的最小回归入口与完整路径保留（见 C5）；
  `2026-11-24-verify-timeout` 的测量义务按其原文执行（见 C6）。
- 不新增网络依赖（`d-policy-replay-offline-v2`）；不新增审计命令或 workflow。

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
  解码后的 str、行列表和解析后的对象。`change resume` 对整个账本做了 3 次完整处理：`resume` 中的
  `derive_state`、`knowledge.read_inputs`（物理行校验一次、展开一次），以及 `_tail_events_for_change` 的再次展开；
  `status` 1 次。
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

### R1 已验证的激活链在每条命令逐步全量回放，成本随项目寿命增长

`_verify_v2_activation`（`attestation_v3_verify.py:302-359`）回放的"一步"不是几次查询，而是：

- 读取可信基线的策略快照与激活 attestation；
- `_introduction_commit` 用 `git log --diff-filter=A` 遍历可信提交的整段历史，找出引入该 attestation 的提交；
- 以前任基线和引入提交重新验证当年那次切换的完整交付（评审证据、检查证据、知识账本、覆盖范围），
  其中前任策略的有效性又递归回放前一步。

所以单条命令的成本约为"v2 切换次数 ×（一次完整交付验证 + 一次历史遍历）"。一个维护多年的项目，
每次更换认可的评审流程、修改必需检查、轮换密钥或恢复都会让链多一步，几年下来几十步是正常的；
历史遍历还随提交数增长。只降低每一步的常数（批量读取）改变不了这个增长趋势，必须**按步增量**：
已经验证过的一步，结论被记住，新增的一步只验证它自己。

现有 `activation_replay_scope` 已在一次 CLI 调用内按步记住结果，但下一条命令从头再验证整条链。
此外进程内的记忆在两处失效：

- `cli/__init__.py:155-159` 进入作用域的子命令集合不含 `report`；
- `SensorDispatcher` 在线程池中运行 `VerificationRunner`（`dispatcher.py:203-204`）时不复制 `contextvars`，
  所以 `verify`/`done` 的检查线程里每次调用都新建作用域。

### R2 同一调用内重复查询不可变 Git 事实

完整 OID 的 `rev-parse`、`(commit, path)` 的 blob、提交的树、祖先关系、merge-base 都不可变，
却被重复查询；每个 blob 读两个进程。这决定了冷启动（新克隆、CI、升级验证器之后）每一步的常数。

### R3 内存

每条命令都完整读取并处理账本；个别命令（例如 `change resume`）在同一次调用内对同一份内容重复展开，
各次的中间结果在峰值时同时存在。账本会随项目寿命增长，所以这部分开销对每个用户都会持续增长。
verify 进程树的其余内存来自用户自己配置的检查，不属于 keepsail 的开销。

## 承诺

### C1 按步增量记住激活验证结果（仅本地生命周期命令）

**记住什么。** `_verified_v2_activation` 对一个可信提交的**成功**结果（一步的结果字典）。失败从不持久化。
回放递归到前任基线时同样经过 `_verified_v2_activation`，命中即停止，所以新增一步只验证这一步。

**键。** `(可信提交完整 OID, repository_id, target_ref, 验证器摘要)`：

- 提交 OID 是内容寻址的，键中不出现 ref 或分支名（#143 的约束）。
- 验证器摘要标识实际执行的代码，而不只是版本号。它是以下内容的 SHA-256，在一个进程内只计算一次：
  - 已安装 `keepsail` 包内全部 `*.py` 文件（按相对路径排序）的内容，因而可编辑安装下的未发布改动也会换键；
  - keepsail 运行时依赖闭包：从 `importlib.metadata` 读取 keepsail 的 `Requires-Dist`（只取当前环境适用的项），
    递归解析，按规范化名称排序。对其中每个分发包，按相对路径排序，哈希它实际安装的每个文件的**内容**
    （`Distribution.files` 列出的文件，`.dist-info` 下的 `RECORD`、`INSTALLER` 等安装记录除外），
    包括编译扩展。这覆盖 PyYAML（含其 C 扩展）与 `cryptography` 的 Rust/OpenSSL 扩展；
    打补丁、换构建或换安装后，内容变化即换键；
  - Python 的 `sys.version`（含构建信息）、`sys.implementation.cache_tag`，以及 `sys.executable` 文件内容的哈希；
  - `KEEPSAIL_ACTIVATION_CACHE_SCHEMA = 1`。
- 以下情况不持久化，只用进程内记忆：任一依赖的元数据或文件清单缺失、列出的文件不存在或不可读；
  任一依赖是可编辑安装（`direct_url.json` 中 `dir_info.editable` 为真）或其导入位置不在列出的文件之内
  （此时安装记录不能代表实际执行的代码）。
- 未覆盖的部分如实写入 `docs/limitations.md`：解释器标准库或解释器动态库被原地改写（解释器版本与可执行文件不变）
  不会换键。这需要改写解释器安装本身，属于下文"信任边界"中已让出的本地写入，合并验证不受影响；
  需要时可用 `KEEPSAIL_NO_ACTIVATION_CACHE=1` 停用。
- 摘要的计算成本在实施后实测并写入 PR（本机，冷文件缓存与热文件缓存各一次）；
  若单次超过 200 ms，在 PR 中报告并说明对 hook 延迟的影响，不放宽覆盖范围。

**纯函数前提（实施的第一步，先于缓存代码）。**

- 逐一检查 `_verify_v2_activation` 调用树中的输入，确认只来自：键中的提交、该提交可达的 Git 对象、
  显式传入的 `repository_id`/`target_ref`，以及验证器代码与依赖。已知的临时文件（`tempfile` 中由已提交 attestation
  派生的 lifecycle）属于派生值，不是外部输入。
- 加一个测试：同一仓库中，删除工作区的 `.harness/events.jsonl`、改写工作区的策略文件、移动 `refs/heads/main`
  之后，以同一 OID 调用 `verify_v2_activation`，结果与之前逐字节相同。
- 如果检查发现某条路径读取了工作区、账本、时钟或环境变量，就把该输入加入键；无法加入键的，
  该路径不持久化，只用进程内记忆，并在 PR 中写明。

**存放。**

- `$(git rev-parse --git-common-dir)/keepsail/activation-v1/<sha256(规范化键)>.json`，
  不在工作区内，不进入提交，无需改 `.gitignore`。
- 文件内容为 `{schema, key, result}`。读取时要求 `schema` 与 `key` 与当前键完全相等、`result` 通过结构校验，
  否则视为未命中，重算后覆盖。
- 写入：临时文件加 `os.replace`，原子替换；写失败（只读、权限、磁盘满）忽略，不影响命令结果。
- 上限：目录中最多 512 个文件，超出时按修改时间删除最旧的。单个结果约 1 KB。

**命中后仍要做的事。** `PolicySnapshot` 仍从该提交读取（经 C2 批量读取），并核对它与记住的结果一致：
`snapshot.commit == result["trusted_base"]`、`snapshot.policy.policy_digest == result["policy_digest"]`、
`snapshot.checks["digest"] == result["required_checks_digest"]`，以及 `snapshot.policy.activation` 的 `kind` 与
`change` 与结果一致（`initial` 对应 `change` 为空）。不一致按未命中处理。这项核对只防止过期或错放的条目，
**不是**对条目的认证（见下文信任边界）。

**谁使用，以及如何强制。**

- 持久记忆**默认关闭**。`attestation_v3_verify` 的验证函数在没有显式开启时只用进程内记忆；任何新的或未列出的
  调用方因此默认冷启动。
- 只有本地生命周期命令通过一个显式的作用域 `persistent_activation_memo(root)` 开启它：`status`、`report`、
  `review import`、`done`、`verify`、`change resume`、hook。开启点在这些命令的 CLI 入口，逐个列出，不按子命令集合推断。
- 核心合并判定入口 `engineering/attestation.py` 的 `verify_attestations`（当前唯一调用方是 `cli/attest.py:235`
  的 `attest verify`）在函数内部进入一个强制冷启动的作用域：即使外层已经开启持久记忆，它和它调用的
  激活与交付验证也不读、不写持久记忆。`attest verify` 不开启持久记忆（CI 中从可信 base 安装运行；
  本地也可手动运行，得到冷启动的权威结论）。
- 即使在已开启的作用域内，以下情况也不读写持久记忆：
- 环境变量 `GITHUB_ACTIONS=true`，或 `KEEPSAIL_NO_ACTIVATION_CACHE=1`；
- 浅克隆（`git rev-parse --is-shallow-repository` 为 `true`）；
- 存在 `refs/replace/` 下的 ref，或 `.git/info/grafts`，或设置了 `GIT_REPLACE_REF_BASE`、`GIT_GRAFT_FILE`、
  `GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`（这些会让同一 OID 的历史或对象来源变化）；
- 以上检测本身失败。

`keepsail_workflow.yml` 与本仓库 workflow 不恢复该目录（不加 `actions/cache`）。

**信任边界（负责人 2026-11-27 的决定，如实写入 `docs/limitations.md`）。**

- 缓存条目没有签名，任何能写 `.git/` 的进程（包括 agent 的 shell）都能伪造一个条目，让本地生命周期命令
  把一个未经验证的激活当作已验证。本计划不声称它和本地 refs 处于同一信任等级。
- 这不是新的一类能力：
  - 本地本来就是"owner 控制的本地信任环境"（`docs/limitations.md:61`），通过 shell 直接写文件是已经让出的能力，
    由审批、评审、检查与 attestation 兜底（同文件"Hardlink residual"一段）；
  - 本地生命周期判定本来就以 agent 可写的本地历史为依据：`2026-11-10` 的 C5 写明"本地严格写入按本地历史强制相关义务；
    CI 只能核验保留的证据"，而本地历史 `.harness/events.jsonl` 同样可由 shell 追加。
- 权威层不变：合并验证不读取持久记忆，从头完整回放。伪造的条目最多改变本地命令的判定，过不了合并闸门。
- 纯函数前提成立、且验证器摘要覆盖的代码未变时，诚实产生的条目与重算结果逐字节相同，所以没有伪造时
  本地判定与现在完全一致；摘要未覆盖的情形（解释器安装被原地改写）见上文，同属已让出的本地写入。
- 失败不持久化，所以修复环境（例如补齐对象）后立即重新验证。

**复杂度。** 主分支前进一步后，第一条本地命令只验证新增的一步，与此前的链长无关。
换机器、清空 `.git/keepsail/` 或升级验证器、依赖、Python 后，冷启动完整验证一次；冷启动和合并验证的
每一步由 C2 降低常数。

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
- 读取方式：
  - `read_policy_snapshot` 及可信基线快照改为一次 `ls-tree -z` 加批量读取所需文件，校验语义和错误行为不变。
    实现参考未推送分支 `perf/git-batch-reads` 的 `b6dd11c`（`regular_blob_texts`），在当前 `main` 上重新实现并评审。
  - 一次调用的作用域内最多保持一个常驻的 `git cat-file --batch` 进程，按 OID 读取 blob，替代每个 blob 一个
    `cat-file` 进程；作用域结束时关闭。该进程异常退出或输出不符合协议时，按现有错误失败，不静默回退。
- `_contract_base_candidates` 的 `for-each-ref` 结果对应可变 ref，只在一次 CLI 调用内复用。
- 作用域修复（R1）：
  - 顶层 CLI 为所有子命令进入作用域，包括 `report`；
  - `SensorDispatcher` 与 `run_checks` 提交线程池任务时用 `contextvars.copy_context().run`，
    线程共享同一个带锁的作用域对象。
- 假设：一次进程运行期间，同一仓库不发生 fetch --unshallow、replace 或 graft；keepsail 自身不做这些。
  外部并发改写历史时，`is_ancestor`/`merge_base` 的进程内结果可能过时，写入 `docs/limitations.md`。

### C3 命令内存：同一份字节只展开一次

- 新增 `effective_lines_for(content: bytes) -> tuple[str, ...]`：以 `content` 的 SHA-256 为键，在进程内记住
  `effective_event_lines` 对这份字节的展开结果（不可变元组），只保留最近 1 个条目。它不读文件，
  调用方传入自己已经读到的字节。
- 改用它的位置，每处仍各自读取、各自持有自己的字节快照：
  - `reducer.derive_state`：读取一次字节，取展开行后调用 `derive_state_from_lines(..., _effective=True)`；
  - `knowledge._inputs_from_content`：对 `read_inputs` 传入的同一份 `content` 取展开行，
    账本回放与状态推导仍来自同一快照；
  - `cli/change.py` 的 `_tail_events_for_change`：读取一次字节后取展开行。
- 不改的部分：`knowledge.load_ledger` 的物理行校验与逐行前缀哈希保持原样，仍对原始字节逐行处理；
  它不是展开，不能用展开行替代。
- 账本在调用中被追加时字节摘要改变，自动重新展开，不会读到旧结果；同一快照内的一致性由调用方持有的字节保证。
- 记住的是同一份字节的纯函数结果，折叠逻辑不变，与 `d-state-pure-fold`、`d-events-append-only` 一致；
  实施时运行 `keepsail decision check --changed` 确认。
- 不改变事件格式与折叠语义，不重写历史账本。

**不做的内存项（测量不支持）：**

- verify 默认并发（4）不改：本次测量中进程树峰值主要来自用户的检查，并发不是瓶颈；
  按内存调节并发需要另外的设计和跨平台测量。
- 检查输出直接写文件不做：本仓库检查的输出很小，没有测得收益。
- knowledge checkpoint 去重不做：增量表示已在 2026-10-30 落地。

### C4 回归守卫

测试中包装 `subprocess` 计数 git 进程，判定不依赖计时。夹具的必需检查是不调用 git 的 `python -c`。

- **热状态与链长无关。** 同一构造函数生成 1 次和 3 次 v2 切换的夹具（3 次夹具在 1 次夹具之后追加两次切换，
  再追加相同的一次普通交付）。持久记忆已预热时，`done`、`report`、`review import`、`status` 的 git 进程数
  在两种夹具上相同。
- **增量。** 预热后在主分支追加一次 v2 切换，下一条命令的 git 次数只比预热状态多出验证这一步所需的次数，
  且在 1 次与 3 次夹具上相同。
- **冷启动按步线性。** 清空缓存目录后，第一条命令的 git 次数在 1 次与 3 次夹具上之差，等于两倍的单步增量
  （允许每步差异不超过 10%）；紧接着的第二条命令与预热状态的次数相同。
- **合并验证永远冷启动（在核心入口测试）。**
  - 预热后直接调用 `verify_attestations`：不读取、不写入缓存目录，git 次数与清空缓存时相同；
  - 在已进入 `persistent_activation_memo` 的作用域内调用 `verify_attestations`，结果相同（强制冷启动覆盖外层）；
  - 未进入该作用域时直接调用 `verify_v2_activation`，不读写缓存目录（默认关闭）；
  - CLI 层再测一次 `attest verify`；设置 `GITHUB_ACTIONS=true` 时，生命周期命令同样不读写缓存目录。
- **伪造条目的边界如实。** 为一个回放会失败的激活提交写入一个结构合法的伪造条目：`verify_attestations` 与
  `attest verify` 仍以原错误拒绝；该测试同时记录本地 `status` 接受该条目，与 `docs/limitations.md` 中写明的边界一致。
- **验证器换键。** 分别做以下改变后不命中旧条目：改动 keepsail 一个源文件；在版本号不变的情况下改动一个依赖
  安装文件的内容（测试中用临时的假分发包及其文件清单）；改变 Python 版本信息。依赖元数据或文件清单缺失、
  列出的文件不存在、依赖为可编辑安装时，不写入缓存目录。
- **语义不变。** 对每一个现有的回放负例（激活 attestation 在引入后被修改、前任不可达、目标策略摘要不符等），
  分别在冷缓存与预热缓存下运行：两次的退出码和错误信息相同。预热缓存下，篡改发生在新提交上，
  所以新提交不命中，仍被拒绝。
- **不持久化条件。** 浅克隆、存在 `refs/replace/`、设置 `KEEPSAIL_NO_ACTIVATION_CACHE=1` 时，缓存目录不被写入。
- **缓存损坏与过期。** 条目被截断、`schema` 或 `key` 不符、结构不合法、与快照核对不一致、目录只读时，
  命令结果与无缓存时相同。
- **账本处理次数。** 包装 `effective_event_lines` 计数：账本在调用期间未变时，`status`、`change resume`、
  `done`、`report`、`verify` 各自对完整账本的展开不超过 1 次；`load_ledger` 的物理行处理次数不增加。
  在 1 次和 3 次切换的夹具上次数相同。
- **测试隔离。** 每个测试用独立的临时仓库，因而有独立的 `.git/keepsail/`；进程内记忆层提供仅测试使用的
  `clear()`；计数只统计被测命令调用期间启动的 git 进程。

### C5 在原文件内拆分策略切换场景测试，保留已批准的回归入口

- `2026-11-10-delivery-policy-transition` 规定："最小回归执行入口为
  `python -m pytest -q tests/integration/lifecycle/test_delivery_policy_transition.py`"，并以一个可过闸的隔离 Git 仓库
  走完真实 `review import`、`done` 和从可信 base 安装的 `attest verify --base BASE --head HEAD` 的完整路径。
  本计划保留这两点：
  - 文件位置、文件名与该入口命令不变；`.github/workflows/test.yml` 的 `delivery-policy-offline` job 不变；
  - 保留一个测试按原顺序走完上述完整路径；
  - 其余阶段（恢复授权、负例、已安装基线验证器、继续计划、生效后的普通交付、下一次切换、密钥轮换、
    报告与状态）在**同一文件内**拆成相互独立、各自构建前置状态的测试，以便 `-n 2` 下并行。
- 断言内容与原测试逐条对应，不删除断言；PR 说明附对照表。
- 不新增 `e2e` 标记；本地与 CI 的覆盖范围不变。

### C6 `verification.yaml` 不变；执行 `2026-11-24` 的测量义务

- 本计划不修改 `.harness/verification.yaml`。负责人于 2026-11-27 选择 "Drop C8 here"
  （"Leave verification.yaml as it is. Still run the serial measurement the 2026-11-24 plan requires and report it."）。
- `2026-11-24-verify-timeout` 要求本 Change "在其计划中包含一次本机完整串行测量；若低于 2000 s，
  在本 Change 内恢复串行命令与 2700 s"。本计划"测量"一节已包含这次测量，结果为 2833 s，
  不低于 2000 s，所以恢复条件在本计划中不触发。
- 实施后再做一次同方法的串行测量，写入 PR 说明和 `implementation record`。若届时低于 2000 s：
  恢复需要修改必需检查定义，而自 #140 起 v1 守卫拒绝替换必需检查（`transition_guard.py:121-126,191,290`），
  本仓库无法在本 Change 内合法完成（#159）。按负责人的 "Drop C8 here"，本 Change 只报告该结果；
  `2026-11-24` 中 2026-12-31 由负责人重新评估的兜底条款不变。

### C7 文档与决策

- `docs/implementation-architecture.md`：§9 增加"激活验证结果的按步记忆"：键（含依赖闭包）、存放、
  使用者与不使用的路径、与合并验证的关系。
- `docs/limitations.md`：
  - 持久记忆未经认证：本地可写进程能伪造条目，改变本地生命周期命令的判定；合并验证不读取它；
    本地需要权威结论时运行 `attest verify`；
  - C2 的进程内假设；持久记忆在浅克隆、replace/graft 与 CI 中不启用。
- `docs/product-architecture-coverage.md`：增加一条带日期的更新。
- `docs/cli-reference.md`：如有 CLI 文本变化，由 `doc check --fix` 重新生成。
- 用 `keepsail decision new` 提交 proposed 决策（不附 `@decision:` 锚点，是否 ratify 由负责人决定）：
  - 确定性验证按内容寻址、按步只做一次：结果以不可变输入与验证器（含依赖）为键记住；合并验证永不读取本地记忆；
  - Windows 进程创建成本要求批量读取 Git 对象并在进程内复用不可变事实；
  - 性能 Change 不改变信任模型或产品公理；需要改变时作为单独的产品决策处理。

## 不做

- 不评估 v2 交付策略机制本身是否过重（负责人安排在本 Change 之后单独讨论）。
- 不删除或削弱任何回放检查；不新增审计命令或 workflow；不改变合并验证。
- 不给缓存条目签名或引入本地密钥（本地没有 agent 读不到的密钥；见 C1 信任边界）。
- 不缓存 verify 检查结果（B14），不调整评审顺序（B39）。
- 不改变 attestation、授权记录、策略文件或事件格式；不改变 v1 行为。
- 不修改 `.harness/verification.yaml`，不改变 pytest worker 数。
- 不优化测试夹具（测量显示夹具占 1%）。
- 不发布新版本，也不提升模板固定的 CLI 版本。

## 测试

- **C1**：C4 中的热状态、增量、冷启动线性、合并验证冷启动、伪造条目边界、换键、语义不变、不持久化条件、
  损坏与过期各项；纯函数测试；缓存文件不出现在 `git status` 中；并发两个进程写同一键不产生损坏文件。
- **C2**：ref 不缓存；失败不缓存；条目数与字节两个上限；子树只含 `.harness/`；多线程并发读写同一键结果正确；
  批量读取与常驻 `cat-file --batch` 遇到非普通文件、缺失路径、重复路径、非 UTF-8、异常输出、进程提前退出时
  按原错误失败；常驻进程在作用域结束时关闭；`report` 与线程池任务在作用域内；
  两次独立 CLI 调用之间不复用 `for-each-ref` 结果。
- **C3**：同一字节命中；追加一行后不命中且结果包含新行；返回值不可变；在现有账本夹具
  （含 completion transaction、紧凑 attestation、恢复记录、畸形行）上，新函数与直接调用 `effective_event_lines`
  的结果逐项相同；恢复记录引发的 `EventSchemaError` 行为不变，且错误不被记住；
  `load_ledger` 的物理前缀哈希与 revision 在改动前后逐字节相同；`read_inputs` 在账本于读取后被追加时，
  返回的账本回放、revision 与状态仍来自同一份字节。
- **C5**：原入口命令运行该文件全部测试并通过；完整路径测试存在且走完 `review import`、`done`、`attest verify`；
  断言对照表完整。
- **全量**：`keepsail verify`、`keepsail decision check`、`keepsail doc check` 通过。

## 验收测量

实施后用同一方法测量（脚本不入库），写入 PR 说明：

- **Git。**
  - 该场景文件中由产品代码发起的 git 调用合计，降到原单一场景 9492 次的 25% 以下；该文件总耗时低于 200 s（本机）。
  - C4 的 3 次切换夹具上，预热后 `done` 由产品代码发起的 git 进程不超过 60 次。
  - 另构造一次 10 步切换的夹具（只用于测量，不入库），报告冷启动的单步 git 次数与耗时，以及热状态下新增一步的
    git 次数与耗时；后者与 1 步、3 步夹具上的值相同。
- **内存。** 用同一 Job Object 方法在本仓库重测 `status`、`change resume`、两个 hook 和完整验证；
  `change resume` 的进程树峰值不高于 `status` 的峰值加 50 MB（实施前分别为 207 MB 和 127 MB；
  `load_ledger` 的物理处理保留，所以目标比上一版宽）。
- **全量测试。** 串行和 `-n 2` 的时长都报告（串行即 C6 的义务）。

未达到目标时，在 PR 中如实报告实测值与原因，不放宽测试。

## 文件范围（估计）

- `src/keepsail/core/`：`attestation_v3_verify.py`、`effective_policy.py`、`policy_snapshot.py`、
  `git_objects.py`、`scope_match.py`、`approval.py`，新增 `activation_cache.py`；
  `events.py`、`reducer.py`、`knowledge.py`。
- `src/keepsail/cli/__init__.py`、`src/keepsail/cli/change.py`（`resume`、`_tail_events_for_change`），
  以及开启持久记忆的各生命周期命令入口所在的 CLI 模块（hook 经 `cli/gate.py` 进入）。
- `src/keepsail/engineering/attestation.py`（`verify_attestations` 强制冷启动）。
- `src/keepsail/sensors/dispatcher.py`、`src/keepsail/sensors/verification_runner.py`。
- `tests/`：`test_delivery_policy_transition.py` 的文件内拆分，新增记忆层、持久缓存、回归守卫测试。
- `docs/`：`implementation-architecture.md`、`limitations.md`、`product-architecture-coverage.md`、
  `cli-reference.md`（如需），`docs/decisions/` 下新的 proposed 记录。
- 本计划。

## 产品基础核对

- **F1（不静默偏离承诺）。** 每一步回放的检查不变；没有伪造时，本地判定与现在逐字节相同；合并验证不读取记忆，
  人的承诺在合并闸门处按原方式兑现。伪造条目能影响的范围（本地生命周期命令）在 `limitations.md` 中如实写明。
- **F2（记录的权威可恢复）。** 缓存不是记录：删除它不丢失任何权威，只需重新计算。
- **负责人的权限。** 本地使用未认证的记忆，是负责人于 2026-11-27 在了解第 9 轮评审第 1 项之后作出的决定；
  它落在已让出的本地 shell 能力之内，不改变合并闸门的风险边界、认可策略或已批准承诺。
- **开源用户。** 设计不依赖本仓库的使用习惯与链长：长链项目热状态下每步成本不随链长增长；不同的合并方式、浅克隆、
  只读 `.git`、无持久缓存的 CI 都能正确工作，只是可能得不到加速。
- **`2026-11-10` 的 C3**（"合并判定可用已提交的证据离线重放"）与最小回归入口保持。
