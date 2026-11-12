---
id: d-policy-replay-offline
status: proposed
---
Policy trust and attestation replay read committed Git objects and do not access the network.

The initial-trust, policy-authority, policy-obligation, v3 replay, Git-object,
and effective-policy paths use committed evidence and the independently supplied
repository/ref identity. An installed verifier may use local subprocesses for
Git; it must not import a network client to fetch trust or review conclusions.

This check catches direct network-client imports in these paths. It does not
detect indirect imports, dynamic loading, subprocess networking, or a dishonest
hosting environment; offline replay and host-source acceptance have their own
evidence boundaries.

```check
for f in src/keepsail/core/policy_*.py src/keepsail/core/initial_policy.py src/keepsail/core/delivery_policy.py src/keepsail/core/effective_policy.py src/keepsail/core/attestation_v3*.py src/keepsail/core/attestation_replay.py src/keepsail/core/git_objects.py; do
  [ -f "$f" ] || continue
  grep -nE '^(import (urllib|requests|httpx|socket)([. ,]|$)|from (urllib|requests|httpx|socket)([. ]|$))' "$f" >/dev/null
  case "$?" in
    0) exit 1 ;;
    1) ;;
    *) exit 1 ;;
  esac
done
```

```counterexample path=src/keepsail/core/policy__network_counterexample.py
import requests
```
