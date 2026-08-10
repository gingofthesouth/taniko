# Tāniko

Tāniko is a Māori finger-weaving technique that produces intricate geometric borders through precise, rule-based thread paths. The name maps onto what this repository is: the threads are scoped parallel nodes, the pattern's rules are the contracts and grammar, and the woven border is the verification gate at the edge of the work.

This is the generic home of a three-layer agent architecture. The **Harness** layer makes the environment cheap to know and safe to act on: declared toolchain, doctor checks, sandbox boundary, observation and verdict caching. The **Loop** layer makes progress real: work advances only on deterministic verification evidence, never on model confidence. The **Graph** layer makes work parallel and bounded: worktree-isolated nodes with disjoint write scopes, retry budgets, and an adversarial verification gate before anything merges.

## The problem

Coding agents fail in predictable ways, and better prompting fixes none of them:

1. **Success by assertion.** A model's native stopping condition is plausibility: left alone, an agent stops when its output *reads* finished, and its claim of success correlates only weakly with reality.
2. **The editable exam.** An agent that can modify its own verifier, tests, or budgets will, under enough optimization pressure, eventually do so.
3. **Evidence that lies about itself.** A stub verdict, a cached replay, or a demo-mode document that doesn't declare itself is indistinguishable from proof of work — an entire pipeline once ran five phases "verified" while carrying nothing.
4. **Unbounded, unobservable work.** Uncapped retries burn budgets against hard problems; parallel branches that share write paths are race conditions, not parallelism; and unlogged routing makes every misroute a mystery instead of a bug.

Each of these is an observed failure, not a hypothetical — the incident record is [docs/HISTORY.md](docs/HISTORY.md).

## How Tāniko solves it

Four mechanisms, one per failure:

1. **Deterministic verification gates** (the Loop contract). Verification is a command whose exit code is the verdict: cost-ordered tiers that fail fast, feedback bounded for re-injection, attempts capped with escalation. Progress advances on evidence, never on confidence.
2. **An enforced boundary** (the Harness contract). The toolchain is declared and a `doctor` command halts on drift; the sandbox is declared and enforced *outside the model*, protecting the verifiers, tests, and the declaration itself from the agent they gate.
3. **Self-identifying evidence** (the schemas). Every evidence document declares its own provenance — real vs demo vs stub mode, the tiers its profile actually ran, whether it is a cached replay — and a routing-log grammar lint rejects what schemas can't: illegal sequences, unclosed brackets, implausible timestamps.
4. **Bounded, replayable parallelism** (the Graph contract). Nodes run in isolated worktrees with disjoint declared write scopes; every cycle carries an attempt limit and an escalation edge; an adversarial verifier gates every merge; every routing decision is logged for replay.

Together they close the chain: a routing log whose every citation resolves to a verify document whose counts name executed tests — "done" is traceable, artifact by artifact, from the claim down to the exit code.

## Why adopt

- Every contract clause was cut from a real implementation's strain, never from theory, and each hard rule carries the incident that earned it.
- Conformance is a command with an exit code, not a README claim: the suite behaviorally tests determinism, replay honesty, and that the gate actually fails on broken code — and it self-tests by catching deliberately sabotaged harnesses.
- The repo eats its own contracts: it carries its own harness declaration and shim, and its gates run in CI.
- Costs are measured, not promised — the adoption kit states the observed baselines.

## Adopt it with your agent

The [adoption kit](adoption/) is designed to be executed by your own coding agent under your review: four phased implementation prompts (harness+loop, graph foundations, graph gates, first real run), five review-ritual skills with a multi-tool installer, and a pinned-clone convention that keeps the judging suite outside the agent's reach. Start at [adoption/README.md](adoption/README.md).

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
