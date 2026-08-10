# Prompt 1 — Implement the Harness and Loop layers

You are working in the adopting repository (yours, not Tāniko's). This prompt
implements the Harness and Loop layer contracts against the Tāniko
specification, judged by the Tāniko conformance suite. Orient by reading
`../taniko/CONTRACTS.md` §1–§2, `../taniko/conformance/README.md`, and the
reference adapter at `../taniko/conformance/reference-adapter/` — the
reference adapter is the specification by example: read it before writing a
line of your own harness.

## Ground rules

- **The artifact is the authority.** Every phase ends with gate output
  pasted, not described.
- **Halt and report on any failed precondition or ambiguity.** Never
  improvise around a gate.
- **The suite is the judge and is read-only.** It is consumed from
  `../taniko`, a clone pinned to the tag in this repo's `TANIKO_VERSION`
  file — outside this repository, never inside your sandbox, never vendored,
  never edited. An agent must not be able to edit the suite that judges it.
- **Skills.** The Tāniko skills are installed alongside this prompt
  (`install-skills.sh`). In this prompt, consult **taniko-protect-gates**
  when you reach the tamper-isolation phase, and **taniko-red-green** to
  understand how the verify evidence you build here will be judged by
  everything downstream — design your feedback so a failing test is citable
  by name.
- **Each phase ends with a commit and a FULL STOP** for human greenlight. Do
  not begin the next phase until told. Work on a feature branch.
- **Cost calibration** (measured baselines from the first adapter): a
  trivial headless agent node cost ~10 AI credits (9.73 credits, 9 seconds,
  ~47k tokens of always-on context); a real producer session ran ~8.5
  minutes. Budget a meaningful multiple for real work, and use your CLI's
  credit-cap flag (e.g. a `--max-ai-credits`-style option) wherever the tool
  has one.

## Phase 0 — Doctor (halt if any check fails)

1. `TANIKO_VERSION` exists at this repo's root and contains exactly the
   Tāniko tag being adopted (e.g. `v0.4.0`). Write it if this is first
   adoption; verify it otherwise.
2. `../taniko` exists, is clean, and is checked out at exactly that tag
   (`git -C ../taniko describe --tags --exact-match`). If missing:
   `git clone --depth 1 --branch "$(cat TANIKO_VERSION)" <taniko-remote-url> ../taniko`.
3. Your CI is (or will be, in this phase) instructed to do the same clone —
   by exactly that tag, outside the repository checkout, never inside the
   agent's sandbox.
4. The suite's own gates pass in the clone:
   `python3 ../taniko/schemas/validate.py` and
   `python3 ../taniko/conformance/selftest.py` (requires Python 3.10+ and
   `jsonschema`). A suite that can't pass its own self-test judges nothing.
5. This repo's tree is clean; you are on a feature branch.

Paste all five outputs. Commit (`TANIKO_VERSION`, CI clone step). STOP.

## Phase 1 — Harness declaration

Write your declaration (default `.claude/harness.json`; another path is fine
if your `--declaration` flag says so) conforming to
`../taniko/schemas/harness-declaration.schema.json`:

- `commands`: how to invoke doctor and verify (argv arrays, no shell);
  `json_flag` if you will support machine-readable output (you should).
- `toolchain`: every tool whose version the code depends on, with `detect`
  commands and requirements.
- `sandbox`: `writable` (least privilege), and `protected` covering — at
  minimum — your verifier scripts, test configuration, CI workflows, and
  **the declaration itself**.
- `state.dir`: session state location, gitignored in this phase.
- `verify.tiers` cheapest-first with commands and timeouts;
  `verify.budgets.max_attempts_total` small.
- `conformance.probe_file`: a writable source file whose corruption a tier
  will catch. Declare it honestly: if no tier can catch it, it is not a
  probe. (Most code repos have one; if yours truly doesn't, omit it and
  record why in the commit message.)

Gate: `python3 ../taniko/conformance/run.py --repo . --tiers static` — paste
the verdict. Commit. STOP.

## Phase 2 — Doctor

Implement `doctor` with both duties: **drift** (declared toolchain vs this
machine, checked from the declaration file — never from a hardcoded copy)
and **health** (required resources present, state dir writable). Exit codes:
0 ok/warn, 2 drift/fail, 1 doctor-itself-broke. With `json_flag`, output
conforms to `../taniko/schemas/doctor-report.schema.json` and includes the
declaration's sha256.

Gate: run doctor both ways; validate the JSON against the schema; paste
both. Commit. STOP.

## Phase 3 — Verify

Implement `verify`: tiers in declared order, fail-fast, deterministic
(flaky tests are contract violations — fix, quarantine, or declare bounded
reruns with mandatory disclosure). On failure, bounded feedback (the
distilled assertion, file, line — never the raw log) with raw logs retained
on disk and referenced by path. Budgets enforced; exhaustion is an explicit
failure with evidence. With `json_flag`, output conforms to
`../taniko/schemas/verify-result.schema.json`: `mode: "real"`, honest
`profile` and `profile_tiers`, `failed_stage` + `feedback` on fail.

A verdict cache is strongly recommended (it is the highest-value cache in
the architecture): keyed by working-tree content hash AND profile, replay
flagged via `cache.replayed`, bypassed by a declared `no_cache_flag`. If you
skip it, say so and accept the conformance WARN knowingly.

Gate: run verify twice on an unchanged tree (same verdict, and the second
should replay if you cached); run a subset profile if declared and show its
result never claims `full`; validate the JSON. Paste everything. Commit.
STOP.

## Phase 4 — Tamper isolation

Follow the **taniko-protect-gates** checklist end to end: deny rules (or
hooks) in your agent CLI's permission layer for every protected glob;
bypass/demo/stub seams gated at operator level and self-identifying in their
evidence; state dir gitignored; destructive-test fencing where applicable.

Gate: attempt a protected write through the agent tool path and paste the
denial. Re-run the static tier. Commit. STOP.

## Phase 5 — Conformance gate

```
python3 ../taniko/conformance/run.py --repo . --tiers static,behavioral
```

Add `,destructive` if you declared a probe_file and the tree is clean. Paste
the full verdict. WARNs are acceptable only where this repo genuinely cannot
satisfy a check — state each one and why. FAILs are not acceptable.

### Greenlight checklist (for the human)

- [ ] Declaration reviewed; sandbox is least-privilege; protected globs
      cover verifiers, tests config, CI, and the declaration itself
- [ ] Deny rules confirmed active (the Phase 4 denial is pasted)
- [ ] Doctor and verify JSON outputs validated against the schemas (pasted)
- [ ] Conformance verdict pasted; every WARN stated and justified
- [ ] Strain notes non-empty (see below) or "no friction" justified per phase

Commit. STOP — Prompt 2a (graph foundations) is issued separately.

## Strain notes (required, every phase)

Append to `docs/taniko/STRAIN.md` as you work. For each point of friction,
three lines: **Needed** (what the work actually required), **Offered** (what
the Tāniko contracts/schemas provided), **Implemented** (what you built, and
the delta). Mark entries whose delta implies a spec change with
`file-against-taniko`. An empty strain file is treated as "didn't look", not
"no friction" — if a phase was genuinely frictionless, write its header and
name the artifact that proves you looked.
