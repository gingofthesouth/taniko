# Conformance Suite

This suite tests the checker — specifically, whether a project's harness actually behaves the way [CONTRACTS.md](../CONTRACTS.md) says a harness must. Your test suite judges your app; this suite judges your harness. With it, "conforming adapter" stops being a README claim and becomes a command with an exit code. Terms are defined in the [glossary](../docs/GLOSSARY.md).

## Running the suite

Prerequisites: Python 3.10+, and a target repository that carries a harness declaration (default `.claude/harness.json`, override with `--declaration`). The declaration's `commands` block tells the suite how to invoke `doctor` and `verify` — the suite has no adapter-specific knowledge.

```bash
python3 conformance/run.py --repo /path/to/repo                         # static + behavioral
python3 conformance/run.py --repo /path/to/repo --tiers static,behavioral,destructive
python3 conformance/run.py --repo /path/to/repo --json                  # machine-readable report
```

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | No failures — the harness conforms |
| 1 | Nonconformant |
| 2 | Suite error |

With `--json`, the report conforms to `conformance-report.schema.json` (versioned separately from the layer schema set).

## The three tiers

**Static** inspects files without executing anything:

- the declaration exists and validates;
- profiles are consistent subsequences of the tier order, with invocations;
- the state dir is gitignored;
- the declaration is covered by its own protected globs;
- forbidden paths aren't tracked;
- a canonical rules file exists;
- protected globs are cross-checked (best-effort, textually) against agent-CLI deny rules.

**Behavioral** executes the harness non-destructively:

- doctor runs with contract exit codes and, with a `json_flag`, emits a conforming doctor-report;
- verify runs and emits a conforming verify-result whose profile is `full`;
- two runs on an identical tree yield the identical verdict (determinism);
- the second run replays fast with `cache.replayed` set (verdict cache);
- a subset profile's verdict carries its own profile name and never masquerades as `full`.

**Destructive** (opt-in; refuses to run on a dirty tree) proves the loop is a loop. It corrupts the declared `conformance.probe_file`, requires verify to fail with a bounded, schema-conformant feedback envelope, restores the file byte-for-byte, then requires the restored tree to replay the baseline verdict. One sequence exercises evidence gating, feedback bounds, content-hash invalidation, and verdict replay together.

## Reading the results

Every check carries a `contract_ref` to the clause it enforces.

| Status | Meaning |
| --- | --- |
| PASS | Clause satisfied |
| FAIL | Clause violated |
| WARN | Legal but weaker than intended (e.g. no verdict cache, no machine-readable output) |
| SKIP | Prerequisite absent — the reason is given |

## The reference adapter

`reference-adapter/` is the smallest fully conforming harness: a toy Python project whose ~250-line `bin/harness` implements cost-ordered fail-fast tiers, tree-content verdict caching with profile-scoped keys and replay provenance, bounded feedback, error-vs-fail discrimination, and schema-conformant `--json` envelopes for doctor and verify. It exists to be read: when writing a new adapter, treat it as the specification by example. It is also the suite's own test fixture.

## Self-test

Run it after any change to `checks.py`:

```bash
python3 conformance/selftest.py
```

The self-test builds the reference adapter into a temp git repo and requires the suite to find it conformant. It then builds three sabotaged variants — state dir not gitignored, a gate that always passes, a quick verdict claiming to be full — and requires each to be caught by its specific check with a nonzero suite exit. The suite is only trusted because it passes its own evidence gate.

## Honest limits

- **Tamper isolation is declared here but enforced elsewhere.** The harness declaration states the boundary; actual enforcement belongs to the agent CLI's permission layer, which this suite cannot exercise from outside. The cross-check against `.claude/settings.json` is textual best-effort.
- **Doctor drift detection has no portable invocation yet** and is exercised only indirectly.
- **Determinism is sampled**, not proven: two runs catch gross nondeterminism, not rare flakes — the flaky-disclosure contract covers the rest.
- **Conformant means correctly built, not well-tuned.** Feedback quality, tier cost balance, and cache hit rates are the evaluation layer's territory, not this suite's.
