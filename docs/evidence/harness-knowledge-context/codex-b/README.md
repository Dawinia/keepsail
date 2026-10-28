# Real Codex task B: acquisition and development checkpoint

Observed on 2026-10-29 (Asia/Shanghai), before final current-object verification
and code review. This dated checkpoint is not final acceptance or a compliance claim.

## Actual entry and recovery

- Session: `01a183ab-9dad-7290-b609-aa79a90d5a2b`.
- Entry: `ev_01M61TQKEXFK74WB77F618PYG4`.
- Manifest: `c9a953c7eecb283e49b22823d928d86cd89255414d658730989fb8148b249068`.
- Approval: `approval:2026-10-28-harness-context-codex-revision-plan-01-84705107`.
- Adoption: `2af4a6ea3de1dffeece3c1b8db2e2a7f92652958b5524e9cc8f7f1f3d414b18f`.

The owner explicitly requested creation of B by the desktop's native create_thread
tool, superseding the earlier instruction against agent-created user sessions.
This was a real separate local task in the same checkout, not a fixture, fork or
subagent. It was **not manually created**. The approved plan's manual A/B creation
wording remains preserved; this report discloses the later owner-directed operator
change rather than claiming manual creation was tested.

Initial binding exited zero and supplied page 1, but no native root-turn record
existed. One owner-authorized send_message_to_thread continuation also lacked it.
After the owner directly entered a normal continuation in B, the actual native
UserPromptSubmit record appeared. B then retrieved all nine pages; native finalize
recorded both exact versions, followed by a separate adoption declaration. The
failed receipt remains under rejected/. No sender/root attribution was borrowed.

Independent native validation in the original chat checked all nine returned
pages and the two native acquired versions. The 18 entries of byte-manifest.json
matched their working-copy hashes. Git blob validation is a separate final check.
The original native-events-excerpt.jsonl contains broader related history;
provenance/selected-native-events.jsonl is the smaller exact-line selection for B
and the v2 owner decisions. Native sources are unchanged. The manifests, startup,
root callback, receipts and statement are copied as original bytes, not re-encoded
tool_response strings. The v1/v2 owner inputs under provenance/ are copies of
existing inputs; their native imported records, not these copies, carry authority.

## Current and historical grounds

Current Codex v2 is `68d822477101506d5bd39b1597e5f5819f04f85f2bd24495139b3b710d3dd00a`;
its recognized exact impact `a2e2c8ab806c0eb3f88a77c0c70369c687a475331a3d5ae7e06194a02a8bebee`
is resolved with continue and authorization_effect=unchanged. The original conditional
Claude version `24276b8e081c3d297cb035d5cf868f974e6e8afbc349edf0312596b3acde52fe` is
supplied unchanged. A's historical Codex v1 remains
`e7b60342f6b0ca752382050abcdb0f0a7172e048d4a4b0f429cd9f835c3c7699` with A's own manifest
and approval; it is not B's current acquisition. Use ../codex-a-exact/ for A's exact
raw return evidence; the first A export remains retained with its correction notice.

## Actual development and checks

B added 28 lines to docs/knowledge-context.md covering missing root attribution,
normal retrieval retries, historical acquisition versus current action eligibility,
the unchanged-authorization continue disposition, and local independent work.
It inspected existing public hook/CLI coverage before choosing this documentation
task instead of adding a duplicate test. The retained actual host check command
reports decision check --changed and doc check both clean. See
checks-and-cost-host-records.json for actual command identities, timing and outputs.
These checks are separate from acquisition and the executor's adoption declaration.

## Measured cost and limits

- Initial bind CLI: 20.933 seconds, exit zero. CLI duration is not hook duration.
- Nine accepted page calls: 32.033 seconds total, range 3.472–3.623 seconds.
- Complete context: 168,078 UTF-8 bytes. Actual raw returns: 188,426 bytes total;
  largest return 22,341 bytes, within the unchanged 24 KiB per-return bound.
- Native finalize CLI: 19.489 seconds; adoption CLI: 14.161 seconds.
- Three completed B turn windows: 270.556 seconds total, excluding user wait time.
- One initial missing-root attempt, one unsuccessful programmatic continuation,
  then one direct human continuation that actually produced native attribution.
- Token estimates reported by the CLI use UTF-8 bytes / 3; they are not measured
  model tokens. These execution times are not an invoice or human-effort estimate.

Hook execution latency, skipped/timed-out hook reliability and all possible desktop
entry modes are not established by CLI timings. Automatic creation/message paths
alone did not establish root attribution in this observed host. Earlier diagnostic
overflow remains a retained failure; limits were not raised. Supply, observed
acquisition, adoption and actual checks remain four separate facts. Shared authority,
cross-repository distribution, all-tool interception, semantic understanding and
general compliance are outside this bounded integration. No publication or merge
is authorized or claimed here.
