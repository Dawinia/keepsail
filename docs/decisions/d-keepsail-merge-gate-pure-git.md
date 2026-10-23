---
id: d-keepsail-merge-gate-pure-git
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-10-23T14:02:35.654411Z'
supersedes: d-merge-gate-pure-git
ratified_text_hash: sha256:004673096ea486ad401cee69469337b8be2973f4539cb55ac6ede9dc13371e99
authoring_time: true
---
The merge gate verifies committed evidence with pure git — no network, no runtime trust.

The merge gate is `cli/attest.py` (subprocess only for `git diff`) + `engineering/attestation.py`
(pure). Both must stay free of network clients. The check scans exactly those two files —
`gates/` is the PreToolUse policy, not the merge gate, and stays out of scope.

```check
! grep -rnE 'import +(urllib|requests|httpx|socket)|(urllib|requests|httpx|socket)\.[a-zA-Z_]|api\.github\.com' src/keepsail/cli/attest.py src/keepsail/engineering/attestation.py
```

```counterexample path=src/keepsail/cli/attest.py
import urllib.request  # raw network smuggled into the merge gate
```
