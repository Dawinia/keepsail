---
id: d-policy-replay-offline
status: superseded
ratified_by: codex-implementation-session
ratified_at: '2026-11-14T19:10:34.912383Z'
supersedes: d-keepsail-merge-gate-pure-git
superseded_by: d-policy-replay-offline-v2
ratified_text_hash: sha256:92979f6bf833034cd14023665e4d6463e300e0de1ce321132aee8b1fa8e55b72
authoring_time: true
---
Policy trust and attestation replay read committed Git objects and do not access the network.

The initial-trust, policy-authority, policy-obligation, v3 replay, Git-object,
and effective-policy paths use committed evidence and the independently supplied
repository/ref identity. An installed verifier may use local subprocesses for
Git; it must not import a network client to fetch trust or review conclusions.
This replaces the earlier two-file merge-gate check: the verifier now delegates
to additional modules and may perform local Git and temporary-file I/O.

This check catches direct network-client imports (including indented imports),
simple client member access, and the GitHub API hostname in the listed paths.
It does not detect every compound or aliased import, indirect imports, dynamic
loading, subprocess networking, or a dishonest hosting environment; offline
replay and host-source acceptance have their own evidence boundaries.

```check
for f in src/keepsail/cli/attest.py src/keepsail/engineering/attestation.py src/keepsail/engineering/attestation_v3.py src/keepsail/core/policy_*.py src/keepsail/core/initial_policy.py src/keepsail/core/delivery_policy.py src/keepsail/core/effective_policy.py src/keepsail/core/attestation_v3*.py src/keepsail/core/attestation_replay.py src/keepsail/core/git_objects.py src/keepsail/core/git_diff.py src/keepsail/core/review_basis.py src/keepsail/core/transition_guard.py src/keepsail/core/scope_match.py src/keepsail/core/approval.py src/keepsail/core/verification_config.py src/keepsail/core/verification_evidence.py; do
  [ -f "$f" ] || continue
  grep -nE '^[[:space:]]*(import[[:space:]]+(urllib|requests|httpx|socket)([. ,]|$)|from[[:space:]]+(urllib|requests|httpx|socket)([. ]|$))|(urllib|requests|httpx|socket)\.[a-zA-Z_]|api\.github\.com' "$f" >/dev/null
  case "$?" in
    0) exit 1 ;;
    1) ;;
    *) exit 1 ;;
  esac
done
```

```counterexample path=src/keepsail/core/policy__network_counterexample.py
def fetch():
    import requests
```
