---
change: 2026-10-27-harness-knowledge-context
stage: plan
---

# Confirmed Codex entry revision

On 2026-10-28 the owner replied “确认” in chat `01a17d4a-2fff-7cc0-9558-39ce65fb006d` to the complete Codex revision proposal SHA256 `abb3416bd985193cb2ccbac7f56335c0783ac519adb4ec5cc4da64cd5de49576`. This authorizes the stated revision, current-contract reviews, implementation and local opt-in/withdrawal. It does not recognize new knowledge or dispositions, authorize additional agent-created user sessions, global settings changes, publication, merge or release. The investigation-stage wording below is preserved as the confirmed proposal. The prior approved plan and original evidence remain retained; this revision replaces its Claude-specific entry/acceptance target and preserves all other architectural and authorization obligations.

## Unchanged commitments copied from the effective prior approval

| ID | Commitment |
|---|---|
| H2 | 复用原生知识、批准和影响模型；完整交付当前有限约束及冻结承诺/限制，不创建平行权威或缩减架构。 |
| H3 | 供应、实际 CLI 获取、agent 声明和实际检查四事实分离；原始证据、完整正文、版本、session/entry 可追溯。 |
| H4 | 恢复与知识变化重新核实当前依据，保存旧依据；知识纠正、challenge 或刷新不绕过承诺变更批准。 |

# 单一入口修订候选：当前 Codex 桌面端

日期：2026-10-28。状态：只读调查后的具体提案，等待所有者确认；未实施本修订。

## 原因与当前事实

用户当前没有可用的 Claude 订阅。因此停止要求用户开启 Claude A/B；该验收未发生，不计为通过。建议将本 Change 唯一的真实集成/验收目标改为正在使用的本机 Codex 桌面端，继续复用知识与批准底座。

- 仓库 `E:/Work/keepsail`，分支 `codex/harness-knowledge-context`，HEAD `fc783c1dac4025f1ae99730c753608464f04a7af`。没有 tracked diff。原有未跟踪材料保持。
- 原冻结计划 H1/H7 明确指定 Claude；有效批准为 `approval:2026-10-27-harness-context-plan-01-78d618de`。当前 `IMPLEMENTATION_IN_PROGRESS`，无 pending revision。切换目标需要计划修订，不能只用 within_approval assessment 替代。
- Claude 候选完整 verify 为 2442 passed、22 skipped、9 warnings，候选 preflight 02 approve。它们继续只证明原对象；不证明 Codex 集成、真实宿主回调或 H7 完成。
- `.claude/settings.local.json` 已原生 opt-in，固定仓库 `.venv` 路径。当前没有 `.codex/hooks.json`。本次未安装/卸载任何 adapter，也未改 hooks/trust/用户配置。
- PATH 上 `codex` 为 npm `@openai/codex 0.46.0`。当前桌面进程实际二进制为 `C:/Users/DawiniaLo/AppData/Local/OpenAI/Codex/bin/2993767bd1dfb009/codex.exe`，只读 `--version` 返回 `0.164.0-alpha.11.1`；Windows app 目录为 `OpenAI.Codex_26.1021.3705.0_x64__2p2nqsd0c76g0`。不升级 npm CLI，不混用这两套宿主证据。
- 既有 `CodexAdapter` 仅安装旧 resume/生命周期/Stop 三 hooks；源码虽然声明支持 post-tool-use，但没有本次 session acquisition 流程。其旧 shim 给 gate 传 `file=None`，不能直接证明多路径局部独立性。
- 当前 core context 的返回校验依赖 Claude 的 stdout/stderr/interrupted 对象；不能把 Codex 的任意 tool_response 填成同一形状而抹掉原始来源。

## 已核对的官方合同与待实测项

[OpenAI 官方 Hooks 文档](https://learn.chatgpt.com/docs/hooks) 说明项目本地 hooks、SessionStart/恢复/compact、实际工具前后回调及显式 deny；普通 hooks 需要人工信任。shell 与 unified exec 的规范 hook 名为 Bash，结束轮询可能才交付完成回调。工具输出格式依工具而异，超时/坏响应不能当阻止成功，宿主覆盖并非所有路径。

这些是当前公开合同，**不是本机已触发的证据**。本机桌面端的实际原始 callback、代码模式嵌套 exec/apply_patch、Windows shell 和超时表现仍须实测。只读 `--help/--version` 没有启动 agent/session 或请求模型。

## 修订后的有限承诺

保留产品架构、四类事实、准确权威、历史依据、局部依赖控制、原生知识/批准生命周期及全部发布边界。替换原计划中的以下目标，其他义务不缩减：

| ID | 修订承诺 |
|---|---|
| H1 | 唯一目标为当前本机 Codex 桌面端的本地任务；显式 Change/session/entry 绑定，支持开始、继续、恢复及 compact。不得自动选最近历史 Change。 |
| H5 | 在 Codex 实际暴露的 apply_patch 编辑边界核对当前上下文、原授权和所有触及路径；多文件动作必须全部满足。读与排障可继续；已知独立工作可继续；未知路径保守拒绝选定编辑，不能默认为独立。 |
| H6 | 继续复用有界分页/幂等/刷新；不另建跨 harness 框架。提供 Codex 本地 opt-in、人工信任步骤和原生撤回。 |
| H7 | 用户手动开启两个真实 Codex 桌面任务 A/B，在真实开发中验证准确获取、恢复、知识演进和成本；不以 CLI exec、子 agent 或隔离进程代替。 |
| H8 | 更新文档/dated coverage，完成新精确对象的测试、外部认可审查和最终 attestation；分别披露源实现、安装、实际触发及未验证边界。 |

H2/H3/H4 原有义务保留；知识认可另行决定，计划确认不认可任何新版本。

## 最小真实路径与具体接口

1. 安装后 SessionStart 只保留必要的真实 callback 字段并生成不可变 startup 身份及小提示。**不依赖从 PowerShell 设置环境变量能传入已运行的桌面 app，也不解析自然语言来猜 Change。**
2. 在实际任务首条提示明确 Change。agent 执行拟新增 `keepsail --json change context <slug> --bind-startup <startup-id>`，将该真实启动绑定一次到 Change，返回原有 manifest/page 1 形状与后续准确命令。绑定重复应幂等；同 startup 不得改绑其他 Change，恢复/compact 使用新的 startup/entry。
3. 所有者授权的原生命令先记录 supply；agent 用宿主实际 shell 执行每页命令。Windows 命令按当前 PowerShell transport 引用固定 `.venv` CLI，保留实际调用原文；不要求 Git Bash 或 Claude。
4. Codex PostToolUse 仅识别本 entry 的准确 CLI 调用。保留原始 callback，并在已核实的完成/成功输出形状上解码完整 CLI envelope；轮询未完成、截断、未知形状、错误退出、缺页不生成 acquisition。完整重组并从实际返回正文重算 hash 后，才复用 `keepsail-cli-observer` 的原生每版本 acquisition。
5. agent 用原有声明接口明确采用/异议，绑定本 entry/manifest；项目声明与知识记录仍分类保留。UserPromptSubmit 给未获取/已失效入口短提示；有效批准、版本或相关 coverage 变化刷新，旧依据不改写。
6. PreToolUse 对真实 apply_patch 提取全部 add/update/delete/move 路径，复用仓库已有 patch 解析能力（先查找；不足才写最小严格解析）。坏 patch/无法界定路径返回明确 deny。对每个路径使用同一纯 gate/current context 查询；任何相关阻塞则整个 patch 等待，另一个可证明独立的动作可继续。不扩大成任意 shell/MCP 全面拦截。
7. root-only 范围保留：无法可靠区分的子 agent callback 不借用主 agent 的获取记录。现有 read/diagnostic 和合法 authoring carveouts 仍按原生命周期处理；不通过 shell 绕过被拒绝的产品编辑。

CLI 无需用户手写 startup/session/digest/CAS JSON；agent 从实际提示/响应取得这些值。首次绑定由任务明确身份，日常继续不重复人工选择。

## 文件与数据影响

| 文件 | 拟修改 |
|---|---|
| `src/keepsail/adapters/agent/codex.py` | 显式 context opt-in，固定路径；新增真实事件注册、保留 unrelated settings/Stop/默认旧模式，更新使用提示。 |
| `src/keepsail/adapters/agent/_settings_merge.py`、`src/keepsail/cli/adapter.py` | 复用当前事务/可选事件能力，对 Codex 开放该 opt-in；不静默开启、不自动信任。 |
| `src/keepsail/daemon/codex_context_hook.py`（新）、`src/keepsail/daemon/hook_entry.py` | Codex 事件/输出/完成轮询适配、明确 deny、实际 raw receipt、startup 捕获；不直接把 Claude 回调当 Codex 回调。 |
| `src/keepsail/core/context.py`、`src/keepsail/cli/change.py` | 一次 startup 绑定、宿主/命令 transport 标识、当前 entry 查询；继续复用投影、manifest、历史、分页、原生 supply 与声明语义。旧 immutable Claude entry 保持可读。 |
| `src/keepsail/gates/decisions.py`、`src/keepsail/gates/pre_tool_use.py`、`src/keepsail/cli/gate.py` | Codex 全路径纯 gate 输入/检查保持 SSOT，CLI 诊断与 hook 不能有不同准许规则；ratified anchors 用原生命令 reconcile。 |
| `tests/unit/core/test_context.py`、`tests/unit/daemon/test_codex_context_hook.py`（新）、`tests/unit/adapters/test_codex.py`、`tests/unit/adapters/test_settings_merge.py`、相关 gate/CLI tests、`tests/integration/adapter/test_codex_context.py`（新） | 有意义的负路径与宿主协议 fixture；明确都不是实际跨 session。 |
| 原计划、`docs/knowledge-context.md`、`docs/adapters/codex.md`、`docs/product-architecture-coverage.md`、`docs/limitations.md`、CLI reference、AGENTS native template | 更新真实入口及 dated 能力；保留旧审查和结果，不能重命名成 Codex 通过。 |
| `docs/evidence/harness-knowledge-context/` | 新 revision、assessment、精确 review/check、真实 A/B 最小自包含证据、成本及撤回记录。 |

已有 `core.knowledge` 权威/策略事件、批准模型和 reducer 不新增状态机。startup/raw transport/manifest 继续使用既有 ignored operation-log 区域；native records 继续仅由 Keepsail 写。若实际协议迫使引入新 observer、策略替换或产品承诺变化，先提交具体差异，不在本确认中隐含授权。

## 实施和认可顺序（仅确认后）

1. 原生提交同一 Change 的计划 revision：`plan redeclare <slug> --plan <修订计划> --commitment H1=...` 等，保留旧有效批准和 candidate 历史；不是裸 redeclare 清空后假装原批准覆盖。先冻结精确 plan subject，由当前合同认可的独立外部过程出结论并 import；pending review 不编辑。
2. 先失败回归，再实现上述有限路径；新增文件用 approval-bound assessment/actual coverage，完成 decision/doc/affected checks、精确候选 preflight 和完整 verify。旧 2442 测试结果不能代替新实现验证。
3. 经本次确认授权后，原生撤回 Claude **context opt-in**（保留旧证据与标准 adapter）；再在本仓库原生安装 Codex opt-in。配置只写本仓库，备份/CAS/无关 hooks 保留。用户仍需在宿主中人工信任准确的新 hooks；不使用 bypass trust，不修改全局配置或升级 app/CLI。
4. 给出当前桌面端的准确人工操作。用户手动开 A；第一步先实际读取上下文观察 callback。如果实际 tool_response 不满足已核实的解码合同，就保存诊断并保持 not_observed/选定编辑未就绪，修复适配后重试。不手工填 receipt，不以失败/缺失等同于 acquisition。若宿主没有可用回调能力，保留具体失败并重新评估方案，不假装满足 H5/H7。
5. A 在本 Change 内完成有意义的旧 entry/新 epoch 授权回归开发；B 由用户手动开启，继续版本影响/独立路径回归或公开用法开发。实际 diff、命令、结果、session/entry/manifest 与 raw callback 分别保留。agent 不主动创建更多用户任务。
6. 最终完成 actual coverage、完整 verify、done、精确外部 code conclusion/import/attestation；真实开发若改动对象必须重新覆盖。push/PR/merge/release 仍未授权。

## 知识决定保持独立

现有 `harness-context-evidence-boundary` v1 正文明示 Claude Code，digest `24276b8e081c3d297cb035d5cf868f974e6e8afbc349edf0312596b3acde52fe`。保留其原认可/正文/供应；不改 body、selector 或声称它已认可 Codex。

建议为有边界的 Codex 实机演进验收使用独立 ID `codex-context-evidence-boundary`，仍限定 `Dawinia/keepsail` AND 当前 Change。先 native propose 得到准确 v1 正文/digest，再单独向所有者请求认可；A→B 使用该对象的 v1→v2 演进，v2 认可和精确影响裁定分别请求。两次计划确认都不替代这些决定。现有 Claude v1 若仍被原生 selector 选中，完整交付其原文及边界，不私自过滤或把适用性未知当无匹配。

## 验收、成本和撤回

| 领域 | 必须保留的证据 |
|---|---|
| 真实入口 | 当前桌面二进制/安装/trust 区分，实际 SessionStart/startup 绑定、全页返回；wrong root/slug、跨 entry、compact/恢复、未绑定均有负例。 |
| 观测合同 | 实际 exec_command/write_stdin 与代码模式嵌套回调，原始输出及重算摘要；缺/坏/截断/未知/未完成记录不晋级。 |
| 当前授权 | 冻结批准与限制全文、版本/适用依据、未决事项、历史和当前声明；新知识不能改工作承诺。 |
| 局部工作 | 多文件/move patch 全路径、相关 challenge/impact、独立 patch 可继续、坏路径保守处理；hook/CLI 同结果。 |
| 真跨会话 | 用户手动 A/B 的不同宿主 session 原始 callback、准确当时依据、实际开发 diff/check；fixture 或自报不可替代。 |
| 知识演进 | Codex 对象 v1/v2 的真实独立认可、保留旧依据、影响可见、单独认可裁定。 |
| 成本 | startup/绑定/页调用数、实际 UTF-8 bytes 与标注的 token estimate、冷/热/编辑前延迟、10 秒 hook budget、人工信任/认可/重试次数；不调大预算掩盖失败。 |
| 最终对象 | 新 HEAD/code subject/verification/review/attestation 自洽，未验证、skip 与 all-tool/语义/跨仓库边界明确。 |

正式验收根继续 `docs/evidence/harness-knowledge-context/`，Codex 子目录保留新证据；原 Claude 外部/仓库证据不删除。回退用原生 Codex context opt-out 撤回新增入口前置条件，原生恢复受管配置，必要时另行受审 revert；不删除历史或关闭 gate 逃避问题。若 Codex 不可用，不要求购买 Claude 订阅来完成本项。

## 唯一需要本轮确认的选择

确认采用本修订：**将本项唯一真实验收目标改为当前 Codex 桌面端，按上述原生计划 revision/审查流程实施，并在检查通过后撤回本机 Claude context opt-in、安装本仓库 Codex opt-in。** 人工 hook 信任与真实 A/B 仍由用户操作；新知识的精确认可/裁定另行决定。确认前不修改仓库代码、受治理计划、账本或本机配置。
