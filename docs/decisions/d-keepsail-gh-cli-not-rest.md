---
id: d-keepsail-gh-cli-not-rest
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-10-23T14:02:33.540862Z'
supersedes: d-gh-cli-not-rest
ratified_text_hash: sha256:81a1099345427bec038644c8c91efda883790c1b421ea30e88f00b545ee710f3
authoring_time: true
---
GitHub access goes through the gh CLI, never raw REST.

`gh api /repos/...` (REST *through* gh, relative paths, never the host) is allowed.
"Raw REST" = bypassing gh to hit the API host directly. The faithful mechanical
signature of that bypass is naming the host `api.github.com` in source.

```check
! grep -rn 'api\.github\.com' src/
```

```counterexample path=src/keepsail/_ce_raw_rest.py
import requests
requests.get("https://api.github.com/repos/owner/repo")
```
