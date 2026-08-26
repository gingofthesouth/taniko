# Layer Schemas

These six JSON Schemas are the concrete interface between the generic engine and every project-specific adapter. They make the layer contracts in [CONTRACTS.md](../CONTRACTS.md) mechanical: an adapter conforms not by agreeing with prose but by emitting documents these schemas accept.

The set is versioned together. The current version lives in each schema's `$id` and at the top of the [changelog](#changelog) — this document deliberately does not repeat the number, so it cannot drift from the truth. Terms are defined in the [glossary](../docs/GLOSSARY.md).

## The six schemas and how they relate

**harness-declaration** is the one committed document: the repository's statement of what must be true — toolchain, sandbox boundary, verify tiers, budgets. Everything else is runtime output derived from or governed by it.

**doctor-report** is produced when the declaration is checked against the actual machine at session start. It carries the declaration's hash, so every report traces to the exact declaration it verified. A status of `drift` halts the session and routes to a harness-update task.

**progress** and **tool-cache** are session state. Both live in the declaration's `state.dir`, are gitignored, and are never committed. Progress is scoped per graph node, so parallel branches never share mutable state; the cache is keyed by tool + arguments digest and invalidated only by content hash, never by time.

**verify-result** is the evidence envelope — the single record type by which the system knows work is done. Two directions point at it: progress items cite it (`evidence_ref`) to justify `status: done`, and routing records cite it (`verify_ref`) to justify retries, gate openings, and escalations. Its verdict enum has exactly three members — `pass`, `fail`, `error` — and model confidence is deliberately not one of them.

**routing-record** is one line of the append-only JSONL graph log. It exists for replay — same `inputs_digest` in, different route out means nondeterminism to investigate — and it is the raw input to the eval layer: latency, retry counts, fan-out width, and escalation frequency all derive from it. Sibling `spawn` records under one fan-out must declare disjoint `scope.writes`, so fan-out independence is checkable from this log alone.

The reference chain, end to end: a routing `retry` cites a verify-result; the verify-result's tier and budget trace to the harness-declaration; the declaration's hash appears in the doctor-report that opened the session. Every claim in the system is one or two hops from a deterministic record.

## Design decisions worth knowing

Bounded strings are load-bearing, not stylistic. Every field whose content can be re-injected into model context (`feedback.summary`, `feedback.details`, `decision.reason`, `summary`) carries a `maxLength`, because unbounded feedback is how retry loops pay tokens to degrade their own attention. Producers must truncate before emitting, and truncation should keep the tail of tracebacks — where the assertion is — rather than the head.

`additionalProperties: false` everywhere is intentional strictness for v0. Unknown fields are typos or version skew, and both should fail loudly while the schemas are young. Expect this to relax to a namespaced extension convention (an `x_` prefix or a per-adapter `ext` object) once real adapters need project-specific fields; that relaxation will be a minor version bump.

Doctor reports include which machine facts resolved but never their values, so reports are safe to attach to CI logs and issues even when the facts are personal paths.

## Versioning policy

Schemas are versioned together as a set; the current set version lives in each schema's `$id` and the changelog. Every instance document carries `schema_version`.

Semver applies from 1.0.0 onward:

- **minor**: adding an optional field or enum member.
- **major**: renaming or removing a field, tightening a bound, changing exit-code semantics.

While the set is 0.x, any release may break, and adapters should pin exactly. Adapters declare the schema-set version they target; the conformance suite for version N validates against version N's schemas, nothing looser.

## Validating

1. Run `python3 validate.py`.
2. Confirm it reports `OK` for each of the six schemas and every example.

It checks every schema against JSON Schema draft 2020-12 and every example against its schema. The examples are normative in spirit: they show an iOS project (xcodebuild tiers, user-space sandbox via a `sandbox_root` machine fact) precisely because that is the first real adapter this set will be tested against.

## What these schemas deliberately do not cover

Graph *topology* — which nodes exist, which edges connect them — is not schematised here; only graph *execution* (the routing log) is. Topology definition is engine-version-specific and belongs with the engine. The log format is the stable contract because replay and eval consume it.

Likewise, hook invocation protocol — how the engine calls pre/post tool scripts, what they receive on stdin — is an engine API, versioned with the engine, not a data schema.

## Changelog

> agent-layers was renamed Tāniko at v0.4.0; urns rehomed (`urn:agent-layers:…` → `urn:taniko:…`). Entries below are records of what happened under the old name and are not rewritten.

### 0.4.0 — cut from the first graph-layer implementation's evidence

Every change traces to a strain finding or review catch from the origin app's graph build (see RESOLUTIONS-0.4.0.md for the full disposition of all eleven findings). routing-record: git_ref pattern-constrained to resolved SHAs, attempt.number semantics defined, optional node.role (producer|gate), structured merge outcome, machine-readable failure_kind. verify-result: mode (real|demo|stub — non-real never satisfies done-evidence), profile_tiers self-declaration, stage selection (all|targeted), started_at honesty requirements. New artifact kind: the routing-log grammar (schemas/routing-log-grammar.md) with executable lint (conformance/loglint.py) — sequence rules JSON Schema cannot express, validated against a real production log (conformance/fixtures/finds-bug-run/) and negative-tested against truncation, write-set overlap, fabricated timestamps, and dangling evidence refs. Evidence-directory convention documented (schemas/EVIDENCE-LAYOUT.md). Escalation/verifier-failure report schemas deferred to v0.5 pending post-fix samples.

### 0.3.0 — the conformance suite, and the gap it found

Building the enforcement tool strained the declaration schema again, in the by-now-familiar way: the declaration described tiers but never said how to *invoke* the harness, so no external tool could drive it. 0.3.0 adds a required `commands` block (doctor/verify argv, per-profile invocations, `json_flag`, `no_cache_flag`) and an optional `conformance.probe_file` hint. The bundle now contains `conformance/`: the three-tier suite (static / behavioral / destructive), its report schema, the minimal reference adapter (a fully conforming ~250-line Python harness that doubles as specification-by-example), and a self-test proving the suite passes a conforming harness and catches sabotaged ones.

### 0.2.0 — revised against the first real adapter (the origin iOS harness)

See STRAIN-REPORT.md for the full mapping exercise. Breaking: **verify-result is now pipeline-scoped** — one record per verify run with a `stages` array, not one per tier; this matches how evidence is actually consumed (progress cites "the verify that passed"). Added: `cache` block on verify-result (verdict replay on unchanged trees is legitimate evidence, keyed by tree content and profile); `profiles` and `preconditions` in the declaration; `skippable`, `flaky_reruns` (with mandatory `flaky_passed` disclosure), and `expected_seconds` on tiers; `learned` facts in progress (the ratchet's raw material); doctor checks generalized to kinds (tool/resource/path/capacity/file) with a non-halting `warn` status, and doctor's two duties (drift vs health) named. Unchanged and still clean-room: routing-record and tool-cache — routing-record is untested by any real adapter until the graph layer lands, and should be trusted least. The state dir may contain adapter-private files (e.g. a simulator pick cache) that are not schematized; only the files named by these schemas are contract surface.

### 0.1.0 — clean-room draft from CONTRACTS.md
