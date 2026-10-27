# Recover an already merged Change

`keepsail change recover` restores retained lifecycle history and records a
verified historical merge. It does not authorize new implementation or reassess
the delivered product. Ordinary `on-merge` and current knowledge gates keep their
existing preconditions.

Start with a read-only preview against the actual merged Git object:

```sh
keepsail --workspace /path/to/repo --json change recover my-change \
  --source-commit <merged-sha> --pr 123
```

The command checks the GitHub repository identified by origin, the PR's exact
Change metadata and actual merge object, the attestation retained at the merged
object and PR head, historical recognition, effective approval, final verification
and complete reviewed code subject. It supports squash merges. Git and an
authenticated `gh` invocation must be available; unavailable proof is a failure.

The preview returns the physical ledger SHA256 in `expected_revision`, the number
of missing historical events and the retained approval/subject. Apply using that
exact revision:

```sh
keepsail --workspace /path/to/repo --json change recover my-change \
  --source-commit <merged-sha> --pr 123 --apply \
  --expected-revision <preview-revision>
```

The target Change must be an exact ordered prefix of the immutable source.
Divergent histories, reused IDs, malformed/unknown source events and conflicting
merge records are rejected. Other Changes and knowledge events are preserved.
This protocol version rejects knowledge-bearing historical streams and historical
active knowledge policies requiring dependency closure; it never manufactures
delivery or imports unrelated knowledge to make a gate pass.

One `historical_change_recovered` event retains the original UTF-8 source bytes,
historical recognition, missing-event boundary, merge evidence and recovery time.
The common lifecycle reader replays the missing original events in source order,
then the recorded merge through the existing transition matrix. State rebuilding,
context/resume, ordering, authority and review-disclosure readers use this same
offline view. Knowledge CAS revisions continue to hash physical log bytes.
The merge event's timestamp records the actual merge time; the envelope records
when recovery occurred. Older readers do not support this envelope and cannot be
used to verify recovery.

Repeated application of the same verified recovery emits nothing. A concurrent
writer can invalidate the preview revision; obtain another preview and retry.
Recovery of separate worktrees is sequential, not an atomic cross-worktree action.
Each worktree keeps its own audit envelope; their entire ledgers need not match.

## Interrupted appends

Before appending, the strict recovery writer durably retains the exact intended
bytes in `.harness/.events.recovery-pending.json` under the existing event lock.
Ordinary writers refuse further writes while it is pending. A partial envelope
does not expose a subset of its restored approvals. Repeat the **same apply
command with its original revision** to validate the unchanged prefix and finish
only the unwritten suffix. The log is never replaced or truncated. A completed
append with a leftover journal is also resumable.

Do not edit/delete the journal or patch a damaged log. A changed prefix, damaged
journal, conflicting request or unavailable original proof fails closed and
retains the evidence for investigation. The journal is transport recovery, not
state authority; complete recovery is represented entirely by the log envelope.
This is process-interruption recovery, not a claim about network filesystems or
every storage device's power-loss behavior.

Back up original ledgers, state caches, attestations and original review evidence
outside the repository before operational recovery. Keep source attestations
unchanged. A recovered ARCHIVED trace is historical evidence; it is not a new
READY_TO_MERGE attestation and cannot reopen the archived Change. New work needs
its own Change and current authorization.
