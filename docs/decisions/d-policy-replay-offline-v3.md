---
id: d-policy-replay-offline-v3
status: ratified
ratified_by: agent:claude-code (owner-authorized 2026-11-28)
ratified_at: '2026-11-28T03:04:07.393956Z'
supersedes: d-policy-replay-offline-v2
ratified_text_hash: sha256:c530109be8c477bcdc8555d3392ac089027a08f0b6dbaa09c1e8573e88e367c1
authoring_time: true
---
Delivery-policy, no-review, v3 replay and Git-object paths use committed Git evidence and do not access the network.

Delivery-policy, obligation, no-review, v3 replay and Git-object paths read the
effective policy and required checks from committed Git objects at the trusted
base and verify a delivery from committed evidence. They do not take repository
or ref identity as a trust input; whether history reached the target branch
through the gate is the host's branch protection and CI. An installed verifier
may use local Git subprocesses and temporary file I/O, but must not use a network
client to fetch policy, trust or review conclusions.

The check detects direct imports and simple member access for the listed
`urllib`, `requests`, `httpx`, `socket`, `http` and `aiohttp` clients, plus the
GitHub API hostname in the listed paths. It does not detect all clients, aliased
or dynamic imports, indirect imports, subprocess networking or an untrusted host.
The hosted verifier separately runs in a network-isolated namespace.

```check
for f in src/keepsail/cli/attest.py src/keepsail/engineering/attestation.py src/keepsail/engineering/attestation_v3.py src/keepsail/engineering/delivery_policy.py src/keepsail/core/policy_*.py src/keepsail/core/delivery_policy.py src/keepsail/core/effective_policy.py src/keepsail/core/no_review.py src/keepsail/core/completion_transaction.py src/keepsail/core/attestation_v3*.py src/keepsail/core/attestation_replay.py src/keepsail/core/git_objects.py src/keepsail/core/git_diff.py src/keepsail/core/review_basis.py src/keepsail/core/transition_guard.py src/keepsail/core/scope_match.py src/keepsail/core/approval.py src/keepsail/core/verification_config.py src/keepsail/core/verification_evidence.py; do
  [ -f "$f" ] || continue
  grep -nE '^[[:space:]]*(import[[:space:]]+(urllib|requests|httpx|socket|http|aiohttp)([. ,]|$)|from[[:space:]]+(urllib|requests|httpx|socket|http|aiohttp)([. ]|$))|(urllib|requests|httpx|socket|http|aiohttp)\.[a-zA-Z_]|api\.github\.com' "$f" >/dev/null
  case "$?" in
    0) exit 1 ;;
    1) ;;
    *) exit 1 ;;
  esac
done
```

```counterexample path=src/keepsail/core/policy__network_counterexample.py
import http.client
from http import client
import aiohttp
```
