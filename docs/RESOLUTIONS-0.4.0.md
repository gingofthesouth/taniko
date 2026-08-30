# v0.4.0 Resolutions

> Historical record: this document disposes of findings against schema set v0.3.0; it is preserved as evidence of how v0.4.0 was formed, not maintained as current guidance. Specialised terms are defined in the [glossary](GLOSSARY.md).

This document is the disposition of every strain finding from the first graph-layer implementation (the origin app's, built August 2026). A strain finding is a mismatch discovered when real code is mapped onto the generic schemas; each finding recorded here is resolved in one of four ways — a schema change, a new companion artifact, an advisory note, or an explicit deferral with reasons. Nothing is silently dropped.

> Note: when this document was moved into the Tāniko repository, references identifying the origin project were replaced with generic equivalents, and the text was rewritten for clarity. The findings and their dispositions are unchanged.

## Resolved as schema changes

- **Checkpoint git references were unconstrained.** A checkpoint had recorded its reference as `"HEAD"` — unrestorable the moment HEAD moves — and the schema's plain string type accepted it. `git_ref` is now pattern-constrained to a resolved SHA, making the motivating bug unrepresentable.
- **Attempt numbering was ambiguous.** The semantics are now defined in the field description exactly as the implementation chose them: retry records carry attempt numbers 1 through max−1, and the total recorded at exhaustion equals the maximum.
- **"Model node" and "gate node" were conflated.** A verifier is a model-driven node *acting as* a gate, which one field could not express. An optional `node.role` (`producer` | `gate`) was added, orthogonal to `type`: a verifier is `type: model`, `role: gate`.
- **A tripped gate looked identical to an infrastructure failure.** Telling "the verifier found a real problem" apart from "the runner timed out" required parsing free-text reasons. An optional `failure_kind` enum was added to the fail, escalate, and rollback events (`gate_finding`, `runner_timeout`, and so on), replacing reason-text parsing.
- **Merge outcomes were unstructured.** Join and exit events gained an optional structured `merge` object (`target`, `result_ref`) instead of describing the merge in prose.
- **Stage cost and stage role were entangled.** In verify-results, `cost_class` now stays a pure cost label; a new optional stage field `selection` (`all` | `targeted`) carries the role distinction separately.
- **Profile linkage could be weaponised.** A stub verification had claimed a full profile it never ran (see the "lying demo verify" lesson in HISTORY.md). Verify-results gained `mode` (`real` | `demo` | `stub` — anything non-real can never satisfy the evidence requirement for completed work) and `profile_tiers` (the result self-declares which tiers its profile contains, cross-checkable against a harness declaration). Together they implement the principle that evidence must attest to its own completeness and provenance.

## Resolved as a new companion artifact: the grammar layer

Two findings — the routing log needs sequence rules, and timestamps need plausibility checks — could not be resolved in JSON Schema at all, because JSON Schema validates single documents and cannot express rules *across* records ("every enter has a matching exit," "terminal events close their brackets," "timestamps move forward"). The resolution is a new kind of artifact for the set: an executable companion instead of a schema field. `schemas/routing-log-grammar.md` defines rules G1–G9, and `conformance/loglint.py` enforces them. The lint is validated against the real production log kept in the fixtures, and negative-tested against truncated logs, overlapping write scopes, fabricated timestamps, and evidence references that resolve to nothing.

## Resolved as advisory (documented, not yet enforced)

- **Failure output must print its provenance** (run id, log path, report paths — the lesson from the wrong-log mix-up in HISTORY.md). Stated in the grammar's advisory section; a candidate for lint enforcement once run-summary output is itself schematised.
- **A quick profile's exclusions should be visible.** Partially resolved by `profile_tiers`; full resolution requires the target repository to adopt a harness declaration — notably the third independent finding pointing at the same missing piece.

## Deferred, with reasons

- **Schemas for escalation reports and verifier-failure reports.** The only samples in hand predate the report-format improvements made late in the build (failure kinds, exit codes, reasons for empty evidence), and writing a schema for a shape known to have just changed would encode staleness. Deferred to v0.5, pending samples produced after the fix.
- **Plan-file topology** stays unschematised by original design — its format is versioned with the engine, not with the schema set. The observed format is documented in EVIDENCE-LAYOUT.md as reference.

## Calibration note (on the first architecture decision record)

The generic guidance had predicted that per-worktree build caches would win under parallel verification. The origin app's measurement said otherwise for its case: a shared build slot with a lock won, 105 seconds to 156, because per-worktree cold starts never amortised. The prediction had assumed nodes that diverge in source code; the nodes actually measured edited documentation, so the invalidation penalty the prediction rested on barely existed. The guidance is updated to: measure per project; expect the shared-lock layout to win for build-dominated quick tiers with low source divergence; and re-measure when nodes begin diverging in source. The prediction was wrong on the measured case; the numbers stand.

## Still wanted

One real, full-pipeline `verify --json` document from the origin app — lint, build, targeted, and unit stages with genuine counts and attempt-tracker values. The v0.2.0 pipeline-envelope rewrite of verify-result has still never been validated against a non-demo full run.
