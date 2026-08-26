# Tāniko

Tāniko is a specification and test suite for running AI coding agents on real work without trusting their word for anything. It defines a three-layer architecture — **harness**, **loop**, and **graph** — and ships the contracts, data schemas, and executable checks you need to build your own conforming system.

The name comes from te reo Māori: tāniko weaving produces intricate geometric borders through precise, rule-based thread paths. The mapping is exact. The threads are parallel work items, the rules are the contracts and grammar in this repository, and the woven border is verification at the edge of the work.

Unfamiliar term? The [glossary](docs/GLOSSARY.md) defines every specialised word used here.

## The three layers

Each layer answers one question:

- **Harness** — *is the environment known and safe?* It declares the required toolchain, checks the machine against that declaration (`doctor`), fences off what the agent may write, remembers state between turns, and caches observations so they are paid for once. See [CONTRACTS.md](CONTRACTS.md) §1.
- **Loop** — *is the progress real?* Work counts as done only when a deterministic verification command exits 0 — never because the model sounded confident. Retries are bounded, failure feedback is compact, and verdicts are cached against the code's content. See [CONTRACTS.md](CONTRACTS.md) §2.
- **Graph** — *is the work parallel and contained?* Independent tasks run as isolated nodes in separate git worktrees with disjoint write scopes, every cycle has an attempt limit, and an adversarial verifier tries to break each result before it merges. See [CONTRACTS.md](CONTRACTS.md) §3.

The whole design serves three goals: accuracy (never report success without deterministic evidence), efficiency (never re-observe what is already known), and latency (independent work runs concurrently, deterministic work never touches the model).

## Start here

- New to the ideas? Read [CONTRACTS.md](CONTRACTS.md) — its opening states the goals, and each layer explains why it exists before what it requires.
- Building a conforming harness? Read the [schema documentation](schemas/SCHEMAS.md), then the [reference adapter](conformance/reference-adapter/) — a minimal working harness you can copy from.
- Checking whether a project conforms? Run the [conformance suite](conformance/README.md).
- Curious why anything is the way it is? Every decision traces to evidence: see [docs/HISTORY.md](docs/HISTORY.md).

## What's in the repository

- [CONTRACTS.md](CONTRACTS.md) — the layer contracts: what any conforming implementation must provide, and why each mechanism exists.
- [schemas/](schemas/) — six JSON Schemas for the evidence documents the layers produce, with examples in [schemas/examples/](schemas/examples/) and documentation plus changelog in [SCHEMAS.md](schemas/SCHEMAS.md).
- [conformance/](conformance/) — the suite that behaviourally tests a project's harness against the contracts, including the [reference adapter](conformance/reference-adapter/), which doubles as specification-by-example.
- [schemas/routing-log-grammar.md](schemas/routing-log-grammar.md) — sequence rules for the graph's routing log that JSON Schema cannot express, with an executable lint ([conformance/loglint.py](conformance/loglint.py)) validated against a real production log.
- [docs/GLOSSARY.md](docs/GLOSSARY.md) — plain-language definitions of every term used above.

## Running the gates

Requires Python 3.10+ and the `jsonschema` package. Three commands, all of which should pass:

```bash
python3 schemas/validate.py
python3 conformance/selftest.py
python3 conformance/loglint.py conformance/fixtures/finds-bug-run/routing.jsonl --evidence-dir conformance/fixtures/finds-bug-run
```

Expected results, in order: every schema reports `OK`; the self-test reports `SELFTEST: PASS` after showing one conforming run and three caught violations; the lint reports `LOGLINT PASS`. CI runs the same three on every push.

## Where this came from

Every schema version was cut from a real implementation's evidence, never from theory. An iOS app's agent harness and graph layer strained each draft, and only what the strain proved necessary was kept. The decision record and lessons are in [docs/HISTORY.md](docs/HISTORY.md); the original mapping exercise is [docs/STRAIN-REPORT.md](docs/STRAIN-REPORT.md); the disposition of every finding from the graph build is in [docs/RESOLUTIONS-0.4.0.md](docs/RESOLUTIONS-0.4.0.md).

## Version

Current: v0.4.0. The next revision is deliberately frozen until real-world runs produce more evidence — the v0.5 docket lives in [docs/HISTORY.md](docs/HISTORY.md) §7.
