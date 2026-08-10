# Prompt 2a — Graph foundations

> **Re-issue rule.** This prompt is designed to be issued once per phase
> across separate sessions — one session per phase is a hard-won rule,
> learned at exactly this layer, where an agent driven by a persistent
> to-do queue blew through "stop here" twice. On receipt: read
> `docs/taniko/PROGRESS.md`; if phases 1..N are complete per the progress
> notes, execute phase N+1 only, then stop. Your to-do list contains only
> that phase's items.

You are working in the adopting repository. Prompt 1 is complete: this repo
has a conformant harness and loop (doctor, verify, tamper isolation). This
prompt builds the graph layer's foundations — everything up to, but not
including, joins and gates (those are Prompt 2b). Orient with
`../taniko/CONTRACTS.md` §3, `../taniko/schemas/routing-record.schema.json`,
`../taniko/schemas/routing-log-grammar.md` (rules G1–G9), and
`../taniko/schemas/EVIDENCE-LAYOUT.md`.

## Ground rules

- The artifact is the authority; every phase ends with gate output pasted.
- Halt on any failed precondition or ambiguity; never improvise around a gate.
- The suite is read-only at `../taniko`, pinned to `TANIKO_VERSION`.
- **Skills:** run the **taniko-validate-run** ritual before declaring any
  phase complete, and reach for **taniko-debug-verify-failure** the moment a
  gate fails — provenance first, then narrow searches, never whole logs.
- **Stub runner only in this prompt.** No real agent sessions: the runner is
  a deterministic stand-in (e.g. a script that writes a known file and
  exits). Every stub seam must self-identify — verify documents it produces
  say `mode: "stub"`, and stub mode must be unreachable without
  operator-level configuration.
- Each phase: commit, then FULL STOP for human greenlight.

## Phase 0 — every session, before anything

1. `TANIKO_VERSION` matches `../taniko`'s checked-out tag exactly.
2. This repo's conformance still holds:
   `python3 ../taniko/conformance/run.py --repo . --tiers static` passes.
3. Tree clean, on the graph feature branch.
4. `docs/taniko/PROGRESS.md` read; announce which phase you are executing.

## Phase 1 — Routing log appender

An append-only JSONL log with a single writer assigning `seq`. Structural
invariants, enforced by the appender (not by convention): `seq` dense from
0 (G1); `at` nondecreasing (G2); brackets balance — no exit without enter,
no re-enter while open, and **a double close is rejected at append time**
(G3). Records conform to the routing-record schema. Terminal failures still
close their brackets — an unclosed bracket is indistinguishable from a
crashed, truncated log, which is why failed runs once left debris that
cleanup refused to touch.

Gate: unit tests including the rejection cases (double close, re-enter,
seq gap), and a generated toy log passing
`python3 ../taniko/conformance/loglint.py <log>`. Paste both. Commit. STOP.

## Phase 2 — Worktree-isolated nodes with disjoint write scopes

Nodes execute in git worktrees created from resolved SHAs. Each node
declares its write scope; plan validation rejects sibling scopes whose
write sets overlap (G7 — independence is defined by write sets, not task
labels; overlapping siblings are a race condition, not parallel work), and
runtime treats a write outside the declared scope as node failure, never a
silent allowance.

Test fencing is part of this phase, not an afterthought: worktree/branch
test helpers refuse to operate on any repository lacking a fixture marker
file, and the acceptance check is that a full test run creates zero new run
directories in the real repository — graph tests once left ~30 stale run
dirs in a developer's actual checkout.

Gate: unit tests (scope-overlap rejection, out-of-scope write failure,
fixture-marker refusal) + the zero-debris check. Paste. Commit. STOP.

## Phase 3 — Resolved-SHA checkpoints

Every checkpoint records a resolved SHA — never `HEAD`, never a branch
name. A checkpoint once recorded `"HEAD"` and was meaningless the moment
HEAD moved; the schema now rejects it, and so must you. A test proves the
round-trip: checkpoint, mutate, restore, verify tree identity.

Gate: unit tests incl. the round-trip. Paste. Commit. STOP.

## Phase 4 — Provisioned progress skeletons

Before each node runs, the orchestrator writes a schema-conforming
`progress.json` skeleton into the node's evidence directory
(`<state-dir>/graph/<run-id>/<node-id>/`, per EVIDENCE-LAYOUT), and the
node's prompt says "update the provided file". **Provision shapes; never
describe them.** Describing the format in prose failed twice — a node
improvised its progress file from the wrong one of two coexisting
conventions — and providing the file worked.

Gate: unit test that a freshly provisioned skeleton validates against
`../taniko/schemas/progress.schema.json`. Paste. Commit. STOP.

## Phase 5 — Retry budgets with feedback injection

Every retry edge carries an explicit attempt limit. On retry, the failed
verify's bounded feedback (summary, locations — never the raw log) is
injected into the next attempt's prompt. Budget exhaustion routes to
escalation — never a silent stop, never a downgraded success claim.

Gate: unit tests — attempt cap honored, feedback text present in attempt
N+1's rendered prompt, exhaustion escalates. Paste. Commit. STOP.

## Phase 6 — Escalation reports

Exhaustion and unanticipated failures terminate in an explicit report
artifact carrying the accumulated evidence (attempts, final feedback,
checkpoint to roll back to). Failure output prints its provenance — run id,
log path, report paths — because a failed run that printed none once sent a
reviewer to a different run's log and nearly produced a fabricated-evidence
diagnosis.

Gate — end-to-end for this prompt: unit tests green, then a stub-runner
single-node run whose `routing.jsonl` passes
`python3 ../taniko/conformance/loglint.py <log>`, with the evidence
directory laid out per EVIDENCE-LAYOUT. Paste the lint output (with its
denominators — "N records", not "passes") and the tree of the run
directory. Commit. STOP — Prompt 2b adds joins, gates, and cleanup.

## Strain notes (required, every phase)

Append to `docs/taniko/STRAIN.md`: for each friction point, **Needed** /
**Offered** / **Implemented** and the delta, marking spec-implicating
entries `file-against-taniko`. An empty strain file is treated as "didn't
look"; a frictionless phase gets its header plus the artifact that proves
you looked.
