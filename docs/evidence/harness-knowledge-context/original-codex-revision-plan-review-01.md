# Independent Codex revision plan review 01

Decision: **approve**.

Reviewer: independent Codex subagent `/root/context_plan_review`, invoked by the implementation agent outside Keepsail core under `codex-subagent-review/v1`.

Change: `2026-10-27-harness-knowledge-context`.

Exact object: `plan:84705107e7caa0b29003fd7899f6cdbfc1049f5bc241dcdd38c938dd4d1a95b6`.

Commit: `c8717c1f6917f55f591f96022e356e2a76835c97`, branch `codex/harness-knowledge-context`.

Prior approval retained: `approval:2026-10-27-harness-context-plan-01-78d618de`, prior subject `plan:78d618dea2384d8b93aabe57e448453f75d261b71590ba09d7a6874c7bae87f7`.

## Review performed

I validated the complete native pending revision and its plan subject using the repository validator, compared it with the current native reducer result, and verified every adopted artifact digest against both its working file and the same artifact committed at the target HEAD. The two adopted artifacts are the Codex revision plan (digest `42b81e2ba405ff2e13b588df9bea4f14c3e164717a8f9e2e3de9c314e4862f5d`) and `docs/product-foundations.md` (digest `5c37dfe9ccd2cb57e8a3d31d1af4204512299a05922e4c2d988a80926241cfa6`). All match. I read the complete adopted artifacts, the prior approval and original plan, the normative product architecture, the current recognition contract, and supporting context, knowledge, Codex adapter and settings paths.

I also checked the [official Hooks contract](https://learn.chatgpt.com/docs/hooks): callbacks expose tool-specific outputs, a completion poll may deliver the original command's post-hook, and subagent hooks share the parent's session identity. This supports designing the adaptation but is not evidence of callbacks in this installed desktop build. I did not run a Codex model/session, change source or governed plans, import conclusions, alter the ledger, or count prior Claude checks as Codex verification.

## Findings and decision

No blocking plan finding. Approve this exact revision as an implementation plan.

1. **The target change is properly treated as an authorization revision.** H1/H5/H6/H7/H8 explicitly replace the Claude-specific target; H2/H3/H4 remain. The native candidate names the original approval rather than claiming that the original exclusive Claude target already authorized Codex. The product architecture and the existing release, policy, reviewer and human-decision boundaries remain authoritative. The revision does not silently retire the original evidence or manufacture new knowledge recognition.

2. **Startup binding is concrete and avoids the desktop environment trap.** The design captures a real startup without guessing a Change from recency or natural language. The subsequent explicit CLI `--bind-startup` uses the exact observed startup identity and binds it once; conflicting rebinds fail, repeats are idempotent, and resume/compact create a new epoch. The plan correctly avoids assuming that a PowerShell environment change reaches an already-running desktop app. Workspace/session/startup integrity and wrong-root/cross-entry cases are explicit acceptance obligations.

3. **The observer boundary preserves the four categories of fact.** Codex callbacks remain raw Codex evidence. Decoding must establish a supported completed response containing the exact native CLI envelope and returned pages; unknown, unfinished, truncated, failed or mismatched returns stay unobserved. Full observed text is reconstructed and hashed before native per-version acquisition is recorded. SessionStart text, old Claude observations, known expected hashes and generated manifests are not substituted for actual acquisition. Agent declarations and checks remain separately retained. The selected observer remains within the already-recognized actual CLI returned-content scope; an actual need for a new observer/policy must return as a concrete authority change.

4. **The proposed patch boundary can preserve local independence.** Extracting every add/update/delete/move path and evaluating the entire action through the same pure gate avoids the old `file=None` shortcut. A mixed patch cannot be admitted because only its independent path passed; an independently submitted action may still proceed when the current context and original authorization cover it. Unknown paths or malformed patches conservatively deny the selected editing action. The plan preserves canonical path checks, lifecycle authoring allowances, explicit explanations and read/diagnostic work, while disclosing that arbitrary shell/MCP writes are not all intercepted.

5. **Root-versus-subagent identity is an explicit limit rather than an implied guarantee.** Session identity alone is insufficient. The proposed implementation note of retaining the observed root UserPromptSubmit turn ID and requiring matching Pre/Post turn identity is a reasonable way to attempt the already-planned root-only boundary. It must be verified against actual callbacks; absence of `agent_id` cannot establish root identity. If the implementation cannot establish that relationship, it must retain the planned not-observed/deny behavior and report the limitation rather than borrow the root's receipt for a child. This is a refinement within the frozen boundary, not an expansion of scope.

6. **Real acceptance remains genuinely outstanding.** The plan requires user-operated desktop tasks A/B, actual raw callbacks, real development changes, separate v1/v2 recognition and exact impact disposition, current-object verification and final exact code review/attestation. The desktop bundled binary is clearly distinguished from the old PATH CLI. Official documentation, version/help output, fixtures, independent processes and previous Claude test counts cannot satisfy those acceptance steps. Human hook trust is retained, not bypassed. There is a defined failure path if this desktop build cannot supply the required callback coverage.

7. **Local installation and rollback remain bounded.** Claude context opt-out preserves ordinary adapter behavior and old evidence; Codex opt-in uses the existing transactional settings mechanism, fixed local executables, backups/CAS and explicit human trust. The plan does not authorize global settings changes, host upgrades, new agent-created user sessions, shared authority, publication, merge or release. It continues to use native knowledge/approval models without adding lifecycle states.

## Implementation reminders, not additional approval conditions

- The revision explicitly retains the original plan's other obligations, although its own subject adopts only the revision and foundations artifacts and links the prior approval by identity. Context recovery must preserve or provide exact retrieval of the retained original approved restrictions, together with the revision's explicit precedence; the shorter current revision must not make those unmodified restrictions disappear. The original frozen subject remains available through its retained approval/evidence chain.
- Keep the existing Claude-specific `harness-context-evidence-boundary` v1 intact. Its selector still mechanically matches this Change, while its body expressly describes the Claude boundary. Deliver that original body and its limit as planned; do not silently filter it, rewrite it to Codex, or treat a new independent knowledge ID as recognition of the old object. Any substantive applicability dispute follows the recognized judgment process.
- Parse complete patch grammar rather than searching arbitrary source lines for file-header-looking text, and check both source and destination of moves after canonicalization. These are implementation details needed to satisfy the frozen all-touched-paths requirement, not new product commitments.

This approval covers only the exact frozen revised plan. It is not a code review, successful host callback observation, successful real cross-session acceptance, knowledge recognition or impact disposition, or permission to publish/merge/release.
