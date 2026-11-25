---
id: d-policy-replay-offline-v2
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-11-23T14:18:01.855506Z'
supersedes: d-policy-replay-offline
ratified_text_hash: sha256:3e235237c67668a729ec6230659532c95c7c794d66b2fa13379af18a21013ba9
authoring_time: true
---
Policy trust and attestation replay use committed Git evidence and do not access the network.

Initial trust, authority, obligation, delivery-policy, no-review, v3 replay and
Git-object paths use committed evidence and independently supplied repository and
ref identity. An installed verifier may use local Git subprocesses and temporary
file I/O, but must not use a network client to fetch trust or review conclusions.

The check detects direct imports and simple member access for the listed
`urllib`, `requests`, `httpx`, `socket`, `http` and `aiohttp` clients, plus the
GitHub API hostname in the listed paths. It does not detect all clients, aliased
or dynamic imports, indirect imports, subprocess networking or an untrusted host.
The hosted verifier separately runs in a network-isolated namespace.

```check
for f in src/keepsail/cli/attest.py src/keepsail/engineering/attestation.py src/keepsail/engineering/attestation_v3.py src/keepsail/engineering/delivery_policy.py src/keepsail/core/policy_*.py src/keepsail/core/initial_policy.py src/keepsail/core/delivery_policy.py src/keepsail/core/effective_policy.py src/keepsail/core/no_review.py src/keepsail/core/completion_transaction.py src/keepsail/core/attestation_v3*.py src/keepsail/core/attestation_replay.py src/keepsail/core/git_objects.py src/keepsail/core/git_diff.py src/keepsail/core/review_basis.py src/keepsail/core/transition_guard.py src/keepsail/core/scope_match.py src/keepsail/core/approval.py src/keepsail/core/verification_config.py src/keepsail/core/verification_evidence.py; do
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
