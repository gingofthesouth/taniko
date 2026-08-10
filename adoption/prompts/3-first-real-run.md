# Prompt 3 — The first real run

You are working in the adopting repository. Prompts 1, 2a, and 2b are
complete and human-reviewed: harness, loop, and graph all exist, all gates
passed, and the machinery has only ever run stubs. This prompt puts one real
bug through it. The goal is not the fix — it is evidence that the machinery
produces adversarially-tested fixes under its own rules.

Historical calibration: the first adapter attempted six launches. Three
halted in pre-flight. One ran and failed *legibly* — it died on a contract
violation, and three secondary bugs were diagnosed from the routing log
alone; that failure hardened the machinery for the run that followed. One
ran and shipped a real, adversarially-tested bug fix. And one correctly
never launched, because the bug was already fixed — the fourth pre-flight
catch, by prevention. **Three halts, one legible failure, one shipped fix,
one launch prevented; zero improvised workarounds** — that record is the
standard. A halt is a success of the fences, and a legible failure is a
success of the evidence; neither is a failure of the run.

## Fill in before issuing (the human does this)

- `TARGET_BUG`: one-paragraph description, plus the exact command or test
  that reproduces it today.
- `TEST_MIRROR`: the test file path that mirrors the code under change
  (name AND folder per your mirror convention).
- `PRODUCER_SCOPE` / `VERIFIER_SCOPE`: declared write scopes. The verifier's
  is test directories only. If the test mirror doesn't exist yet, its
  creation is explicitly inside `PRODUCER_SCOPE`.
- `RED_GREEN`: the red→green declaration on the producer node (the
  mechanism built in Prompt 2b Phase 1) naming the test in `TEST_MIRROR`
  whose failing-then-passing verify pair the orchestrator must find in the
  evidence chain.
- Budgets: producer attempts, verifier attempts (2 was the measured
  starting point), per-node timeouts (warm the build as orchestrator
  pre-work first — a cold build is deterministic work and must never spend
  an agent session's timeout budget), and the CLI credit cap where your
  tool has one.

## Ground rules

- The artifact is the authority; paste, never describe.
- Halt and report on any failed pre-flight item. **Do not improvise around
  a halt** — every historical halt was correct, and a helpful agent without
  these fences would have committed the mess and proceeded.
- **Skills:** the post-run ritual is **taniko-validate-run**, executed in
  full; use **taniko-review-agent-work** when reading the producer's and
  verifier's reports and when shaping any correction prompt (approval scope
  first, blocking items first, downstream consumer explained, echo-back
  required).
- The suite is read-only at `../taniko`, pinned to `TANIKO_VERSION`.

## Pre-flight (halt on any; run every check even after one fails, then report all)

1. **Clean tree** — `git status --porcelain` empty. (Launch 1 halted here:
   dirty tree, a scaffold in the wrong folder, and debris from an abandoned
   approach.)
2. **All infrastructure committed** — worktrees are created from the
   resolved commit, so uncommitted infrastructure does not exist inside a
   run. (Launch 3 halted here: the freshly wired runner was uncommitted.)
3. **Runner standalone-tested since its last change** — a short hello-world
   run passed. (A 60-second run once caught a path bug before a 15-minute
   graph run could bury it inside a confusing escalation. Launch 2 halted
   because the runner was still a stub.)
4. **The target bug exists right now** — run the `TARGET_BUG` repro and
   paste the failure. (Launch 6 correctly never fired: the fix had already
   landed through normal channels.)
5. **Test mirror pre-created or in producer scope** — name AND folder.
6. **Demo/stub modes unset** — inspect the operator config and environment;
   paste the check. Every seam self-identifies, so a `mode` other than
   `real` in any produced evidence is an automatic run failure.
7. **Deny rules active** — attempt one protected write through the agent
   tool path; paste the denial.
8. **`TANIKO_VERSION` matches** `../taniko`'s checked-out tag.

Paste all eight results. STOP for human confirmation before launching.

## The run

- **Producer**: red→green, enforced by the `RED_GREEN` declaration — the
  orchestrator (mechanism from Prompt 2b Phase 1) requires the evidence
  chain to contain a failing verify citing the declared test *before* the
  passing one, and rejects completion otherwise; prompt prose alone was
  proven insufficient (a producer once skipped the failing-test step
  entirely). The failing verify is recorded evidence, not a discarded
  intermediate.
- **Verifier**: adversarial, write scope limited to test directories,
  bounded attempts, and its contribution proven by executed-count evidence
  — the unit-test denominator moves (the first real run went 822 → 825),
  and the new tests appear in the verify counts, not merely on disk.
- Monitor cost against the cap. If the run escalates, apply
  **taniko-debug-verify-failure**: provenance first, fail vs error, is the
  timeout downstream of the real cause, search the retained logs narrowly.

## Post-run ritual (before believing any report)

Execute **taniko-validate-run** in full, all seven steps: true-base diff
with content assertion; routing log against schema AND lint (with
`--evidence-dir`); verify documents' mode/profile honesty; executed-test
counts; denominators everywhere ("N resolved", N > 0); strain-note tone;
one live command exercising the fix. Paste each step's output. The green
self-report is the beginning of review, not the end of it.

## Landing

**The human lands the result.** The agent never pushes or merges to the
main line — an agent environment without push credentials is a feature.
Present: the integration branch, the diff against true base, the routing
log, all verify documents, and the verifier's added tests. Preserve the
run's evidence directory and any failure worktrees per the retention
policy; they are diagnostic material, not debris.

## Strain notes (required)

Append to `docs/taniko/STRAIN.md`: **Needed** / **Offered** /
**Implemented** per friction point, spec-implicating entries marked
`file-against-taniko` — a first real run is exactly where the specification
meets reality, and Tāniko's next revision is deliberately frozen until
findings like yours exist. An empty strain file is treated as "didn't
look"; if the run was genuinely frictionless, say so per phase and name the
artifact that proves you looked.
