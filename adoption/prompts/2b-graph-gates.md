# Prompt 2b — Graph gates, joins, and cleanup

> **Re-issue rule.** This prompt is designed to be issued once per phase
> across separate sessions — one session per phase, learned at exactly this
> layer. On receipt: read `docs/taniko/PROGRESS.md`; if phases 1..N are
> complete per the progress notes, execute phase N+1 only, then stop. Your
> to-do list contains only that phase's items.

You are working in the adopting repository. Prompt 2a is complete: routing
log, isolated nodes, checkpoints, provisioned skeletons, retry budgets, and
escalation reports all exist and their gates passed. This prompt adds what
makes the graph safe to trust: joins that prove content flowed, an
adversarial gate that cannot be bypassed, cleanup that keeps evidence, and
a run that lints itself. Orient with `../taniko/CONTRACTS.md` §3
(fan-out/join, content assertions, verification gates),
`../taniko/schemas/routing-log-grammar.md` G4/G7/G8, and
`../taniko/schemas/EVIDENCE-LAYOUT.md`.

## Ground rules

- The artifact is the authority; every phase ends with gate output pasted.
- Halt on any failed precondition or ambiguity; never improvise around a gate.
- The suite is read-only at `../taniko`, pinned to `TANIKO_VERSION`.
- **Skills:** run **taniko-validate-run** before declaring any phase
  complete — its content-assertion step exists because of this layer — and
  use **taniko-debug-verify-failure** on any gate failure.
- Stub runner only, self-identifying, operator-gated — as in 2a.
- Each phase: commit, then FULL STOP for human greenlight.

## Phase 0 — every session, before anything

Identical to 2a's: `TANIKO_VERSION` matches the clone's tag; static
conformance passes; tree clean on the graph branch; `PROGRESS.md` read and
the phase announced.

## Phase 1 — All-of join with real merges and content assertions

The join merges each completed node's branch into the integration branch
with real merge commits, in a deterministic order. Node completion requires,
in this order: runner success, valid node progress, verify evidence. Then
the content assertion: **a content-producing run must prove content flowed**
— integration tip differs from base, and the verifier's input digest
reflects a non-empty diff. A verified tree is not evidence work was
performed: an unchanged tree legitimately replays a passing verdict, which
is exactly how five phases of orchestration once ran fully "verified"
around a pipeline that had never carried cargo.

Also in this phase: **plan-declarable red→green enforcement.** A plan may
declare on any producer node a red→green requirement naming its test; the
orchestrator then requires that node's evidence chain to contain a failing
verify citing the named test *before* the passing one, and rejects
completion otherwise. Prompt prose alone was proven insufficient — a
producer once skipped the failing-test step entirely — so this is the
mechanism form, checked by the orchestrator, not requested of the agent.
Prompt 3 declares it on its producer.

Gate: unit tests — join produces real merge commits; an empty-cargo run is
*rejected* by the content assertion (build this test first; it is the whole
point); a red→green-declared node whose evidence lacks the
fail-citing-the-named-test-then-pass pair is rejected. Paste. Commit. STOP.

## Phase 2 — Adversarial verifier with no agent-reachable bypass

Completed work routes through a separately-scoped verifier node (write
scope: test directories only) whose job is to break the patch before it
lands. Independence is structural: no shared context, incentives, or
authorship with the producer. **No bypass is reachable by any agent**: no
flag, environment variable, or config inside the sandbox disables the gate
— only operator-level configuration outside it, and any such seam
self-identifies in the evidence it produces (per **taniko-protect-gates**).
A verifier failure produces its report artifact on every path, including
timeouts — evidence must survive whether or not the runner stays alive.

Gate: unit tests — merge blocked without verifier pass; bypass attempt from
inside the sandbox fails; verifier report exists on the failure path.
Paste. Commit. STOP.

## Phase 3 — Clean with retention

Cleanup is idempotent and reaps state — worktrees, node branches, locks —
while evidence survives: routing logs, verify-results, progress files,
escalation and verifier reports. Failed runs' worktrees are preserved per a
declared retention policy; a preserved worktree is what let one git command
expose the empty pipeline. Cleanup refuses nothing it should reap and
touches nothing it should keep.

Gate: unit tests — after clean, worktrees/branches gone, every evidence
file still present; clean twice is a no-op. Paste. Commit. STOP.

## Phase 4 — Run self-lint before terminal

Before declaring any run finished, the orchestrator lints its own completed
log: bracket balance (G3) and terminal closure (G4 — the final record is
the root node's exit, success or failure; "the log just stops" is not an
outcome). Artifact-level checks are path-independent: the two gaps that
escaped a real run's per-code-path tests — an unprovisioned verifier and a
duplicate exit record on the escalation path — were exactly the paths
nobody thought to test.

Gate: unit tests — a run with an unbalanced log refuses to conclude; the
double-close case from 2a Phase 1 is caught here too if the appender is
somehow bypassed. Paste. Commit. STOP.

## Final gate — the fan-out

A stub-runner **two-node hello-world fan-out** with disjoint declared write
scopes, run end to end, then:

1. `python3 ../taniko/conformance/loglint.py <run>/routing.jsonl
   --evidence-dir <run>` passes, including G8 evidence resolution. The
   pinned lint does not yet print G8's denominator, so supply it yourself:
   count the distinct `verify_ref`s in the log that resolve in
   `<run>/verify-results/` and paste the count — it must be greater than
   zero. A lint pass resting on zero citations is vacuously green and does
   not count. (A future lint will print "N resolved" itself; until then
   the adopter states the denominator.)
2. The evidence directory matches EVIDENCE-LAYOUT (paste the tree).
3. The real repository contains **zero** run directories leaked by the test
   suite (paste the check).

Paste all three. Commit. STOP — Prompt 3 (the first real run) is issued
separately, after human review of the whole graph layer.

## Strain notes (required, every phase)

Append to `docs/taniko/STRAIN.md`: **Needed** / **Offered** /
**Implemented** per friction point, spec-implicating entries marked
`file-against-taniko`. Empty file = "didn't look"; frictionless phase =
header + the artifact that proves you looked.
