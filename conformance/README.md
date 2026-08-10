# Conformance Suite

Tests the checker: does this repo's harness actually behave the way CONTRACTS.md says a harness must? Your test suite judges the app; this suite judges the harness. With it, "conforming adapter" stops being a README claim and becomes a command with an exit code.

## Running

```
python3 conformance/run.py --repo /path/to/repo                         # static + behavioral
python3 conformance/run.py --repo /path/to/repo --tiers static,behavioral,destructive
python3 conformance/run.py --repo /path/to/repo --json                  # machine-readable report
```

Exit 0 = no failures, 1 = nonconformant, 2 = suite error. The `--json` report conforms to `conformance-report.schema.json` (suite-versioned, separate from the layer schema set). Requires the target repo to carry a harness declaration (default `.claude/harness.json`, override with `--declaration`) whose `commands` block tells the suite how to invoke doctor and verify — the suite has no adapter-specific knowledge.

## The three tiers

**Static** inspects files without executing anything: the declaration exists and validates; profiles are consistent subsequences of the tier order with invocations; the state dir is gitignored; the declaration is covered by its own protected globs; forbidden paths aren't tracked; a canonical rules file exists; protected globs are cross-checked (best-effort, textually) against agent-CLI deny rules.

**Behavioral** executes the harness non-destructively: doctor runs with contract exit codes and, with a `json_flag`, emits a conforming doctor-report; verify runs, emits a conforming verify-result whose profile is `full`; two runs on an identical tree yield the identical verdict (determinism); the second run replays fast with `cache.replayed` set (verdict cache); a subset profile's verdict carries its own profile name and never masquerades as `full`.

**Destructive** (opt-in, refuses to run on a dirty tree) proves the loop is a loop: it corrupts the declared `conformance.probe_file`, requires verify to fail with a bounded, schema-conformant feedback envelope, restores the file byte-for-byte, and requires the restored tree to replay the baseline verdict — one sequence that exercises evidence-gating, feedback bounds, content-hash invalidation, and verdict replay together.

Every check carries a `contract_ref` to the clause it enforces. Statuses: PASS, FAIL (clause violated), WARN (legal but weaker than intended — e.g. no verdict cache, no machine-readable output), SKIP (prerequisite absent, with the reason).

## The reference adapter

`reference-adapter/` is the smallest fully conforming harness: a toy Python project whose ~250-line `bin/harness` implements cost-ordered fail-fast tiers, tree-content verdict caching with profile-scoped keys and replay provenance, bounded feedback, error-vs-fail discrimination, and schema-conformant `--json` envelopes for doctor and verify. It exists to be read: when writing a new adapter, this is the specification by example. It is also the suite's own test fixture.

## Self-test

```
python3 conformance/selftest.py
```

Builds the reference adapter into a temp git repo and requires the suite to find it conformant; then builds three sabotaged variants — state dir not gitignored, a gate that always passes, a quick verdict claiming to be full — and requires each to be caught by its specific check with a nonzero suite exit. The suite is only trusted because it passes its own evidence gate; run the self-test after any change to `checks.py`.

## Honest limits

Tamper isolation is *declared* in the harness declaration but *enforced* by the agent CLI's permission layer, which the suite cannot exercise from outside — the cross-check against `.claude/settings.json` is textual best-effort, and actual enforcement should be verified in the CLI itself. Doctor drift detection (report a mismatch against a modified declaration) has no portable invocation yet and is exercised only indirectly. Determinism is sampled with two runs, which catches gross nondeterminism, not rare flakes — the flaky-disclosure contract covers the rest. And a conformant harness is a *correctly built* harness, not a well-tuned one: feedback quality, tier cost balance, and cache hit rates are the evaluation layer's territory, not this suite's.
