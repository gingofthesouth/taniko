# Tāniko

Tāniko is a Māori finger-weaving technique that produces intricate geometric borders through precise, rule-based thread paths. The name maps onto what this repository is: the threads are scoped parallel nodes, the pattern's rules are the contracts and grammar, and the woven border is the verification gate at the edge of the work.

This is the generic home of a three-layer agent architecture. The **Harness** layer makes the environment cheap to know and safe to act on: declared toolchain, doctor checks, sandbox boundary, observation and verdict caching. The **Loop** layer makes progress real: work advances only on deterministic verification evidence, never on model confidence. The **Graph** layer makes work parallel and bounded: worktree-isolated nodes with disjoint write scopes, retry budgets, and an adversarial verification gate before anything merges.

## What's in the repo

- [CONTRACTS.md](CONTRACTS.md) — the layer contracts: what any conforming implementation must provide, and why each mechanism exists.
- [schemas/](schemas/) — six JSON Schemas for the evidence documents the layers produce, with [examples](schemas/examples/) and [SCHEMAS.md](schemas/SCHEMAS.md) (the schema set's own documentation and changelog).
- [conformance/](conformance/) — the suite that behaviorally tests a project's harness against the contracts, with a minimal [reference adapter](conformance/reference-adapter/) that doubles as specification-by-example.
- [schemas/routing-log-grammar.md](schemas/routing-log-grammar.md) — sequence rules for the graph's routing log that JSON Schema cannot express, with an executable lint ([conformance/loglint.py](conformance/loglint.py)) validated against a real production log.

## Running the gates

Requires Python 3.10+ and the `jsonschema` package.

```bash
python3 schemas/validate.py
python3 conformance/selftest.py
python3 conformance/loglint.py conformance/fixtures/finds-bug-run/routing.jsonl --evidence-dir conformance/fixtures/finds-bug-run
```

Or run all three through the repo's own harness front door: `bin/harness verify` (cost-ordered, fail-fast; the repo conforms to its own contracts — see [.claude/harness.json](.claude/harness.json)).

## Provenance

Every schema version was cut from a real implementation's evidence, never from theory: an iOS app's agent harness and graph layer strained each draft, and only what the strain proved necessary was kept. The decision record and lessons are in [docs/HISTORY.md](docs/HISTORY.md); the original mapping exercise is [docs/STRAIN-REPORT.md](docs/STRAIN-REPORT.md).

## Version

Current: v0.4.0. The next revision is deliberately frozen until real-world runs produce more evidence — the v0.5 docket lives in [docs/HISTORY.md](docs/HISTORY.md) §8.
