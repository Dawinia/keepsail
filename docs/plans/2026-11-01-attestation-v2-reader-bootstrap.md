---
change: 2026-11-01-attestation-v2-reader-bootstrap
stage: plan
---

# Stage the v2 reader before enabling v2 evidence

This prerequisite closes the trusted-reader rollout gap in the approved context
evidence revision. It changes record-version support, not review recognition or
who selects the verifier. The existing trusted-base contract remains binding.

## Commitments

- B1: Add the existing explicit v2 lifecycle/checkpoint readers and their closed
  core dependencies, preserving v1 interpretation and all authority checks.
- B2: Accept only the existing flat JSONL location and the explicit v2 JSONL
  location in the actual workflow projection. Keep regular-blob, resolved-path,
  source/config isolation and successful-candidate prerequisites unchanged.
- B3: Keep bootstrap output readable by v1. The native compatibility exporter
  must preserve trusted original facts exactly, project only new normative facts
  with explicit derived/source identity, and inline exact review conclusions.
  Its old verifier must validate the complete diff and exact evidence.
- B4: Prove the next producer release with the bootstrap as its trusted base,
  isolated from live events/operation logs and with network transports disabled.
  Never install the candidate itself as its trusted verifier.

## Implementation and boundaries

Reuse the already implemented readers and their core dependencies from the
context evidence revision. This closed slice includes the context module used by
the exporter for approval lineage; it does not install or activate any context
adapter, change gate policy, choose reviewers or recognize knowledge. Keep the
existing native CLI producers for the bootstrap; the following release alone
enables v2 output. There is no runtime switch or extra user evidence workflow.

Native preparation uses an isolated checkout sharing the existing append-only
native ledger and lock, not a forked/rebased copy of governance history. Normal
native commands append all new records with ordinary validation. Export is
eligible only for an exact empty constraint set with no impacts or target
acquisition observations. Other Changes' acquisition telemetry stays native and
is retained by their own v2 export; it is not converted into old receipt claims.
Preserve every trusted v1 knowledge event byte-for-byte. New projected operations
bind original source identity and digest and cannot be submitted as native
operations. Their v2 reader restores the same retained facts, so the next Change
can resolve the trusted baseline from the same original native history.
No temporary inputs or native raw returns are public deliverables.

Only ordinary reviewed base promotion can make the new decoder trusted. No
push, PR, merge, release, main rewrite, policy activation, hook trust change or
human-only override is authorized here. Prepare both locally verifiable stages
first; actual publication remains a separate, concrete owner decision.

## Validation

Run the actual workflow projection for flat/v2 evidence and reject unknown/deep
locations, symlinks, missing objects and a wrong base. Validate the bootstrap
with the pinned old verifier. After its source is used as a new trusted base,
validate the producer candidate's exact full diff with that installed reader,
using Git-only evidence. Keep the prior private branch and native originals.

Current code review, configured verification, decision/doc checks and native
attestation must cover each exact delivery object. A fixture is evidence of the
local upgrade path, not a claim that GitHub CI ran or that promotion occurred.
