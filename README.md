# Tāniko

Tāniko is a Māori finger-weaving technique that produces intricate geometric patterns through precise, rule-based thread paths. This repository uses that name to describe what it does: the threads are independent parallel processes, the pattern's rules are the contracts, and the final border is the verification gate that checks completed work.

This is the home of a three-layer agent architecture. The **Harness** layer makes the environment safe and easy to understand: you declare your tools, run health checks, set sandbox boundaries, and cache observations and results. The **Loop** layer makes real progress: work only moves forward when verification proves it's done, never based on what the model thinks it did. The **Graph** layer enables safe parallel work: each node runs in its own isolated workspace with separate write areas, retry limits are enforced, and nothing gets merged without passing verification.

## The problem

Coding agents fail in predictable ways. Better prompts alone don't fix them:

1. **Success by assumption.** An agent's natural stopping point is when its output looks finished. Whether it actually succeeded has no real connection to how confident it sounds.
2. **The agent rewrites its own rules.** An agent that can change its own verification, tests, or retry budgets will eventually do so if it helps the agent "succeed."
3. **Evidence that hides what it is.** A quick-pass result, a reused cached result, or a test environment result that doesn't say what it is looks the same as real proof. A pipeline once ran five verification stages that all looked good, but carried nothing real.
4. **Work nobody can see or stop.** Unlimited retries waste resources on impossible problems. Parallel work that shares write areas becomes race conditions, not real parallelism. Unlogged decisions mean every failure is a mystery, not a bug you can trace.

Each of these is a real failure we've seen, not theory. The incident record is in [docs/HISTORY.md](docs/HISTORY.md).

## How Tāniko solves it

Four mechanisms, one for each failure:

1. **Verification that must prove itself** (the Loop contract). Verification runs as a command that returns success or failure: costs are ordered from cheapest to most expensive so failures stop fast, feedback stays limited so you can re-use it, attempts are capped and escalate if needed. Work only moves forward on real proof, never confidence.
2. **A hard boundary nobody can cross** (the Harness contract). Your tools are declared and a `doctor` command stops if they change. The sandbox is declared and enforced outside the model itself, protecting the verifier and tests from the agent they control.
3. **Every result says what it is** (the schemas). Every result document says where it came from: whether it's real, a test run, or a shortcut result. It says which verification tiers actually ran. The routing log has a grammar that rejects anything that doesn't make sense: impossible sequences, unclosed blocks, bad timestamps.
4. **Parallel work that you can replay** (the Graph contract). Each process runs in its own workspace with separate write areas that can't conflict. Every cycle has a retry limit and a path for escalation. Verification gates every merge. Every routing decision is logged so you can replay the whole thing if something goes wrong.

Together these close the loop: a routing log where every entry points to a verification result where the counts show which tests ran, you can trace "done" through the evidence back to the actual exit code.

## Why use this

- Every rule came from a real system straining under real work, not from theory. Each hard rule is there because something failed without it.
- It checks itself with commands that have exit codes, not just claims in a readme: the test suite verifies that it actually works, that replays stay honest, that the gates really stop broken code, and it tests itself by breaking harnesses on purpose and catching them.
- The repo follows its own rules: it has its own harness declaration and test, and runs verification in CI.
- Costs are measured and reported, not promised: the adoption kit shows real baselines.

## Get started with your agent

The [adoption kit](adoption/) is built for your coding agent to run while you watch: four phased implementation guides (harness and loop, graph basics, graph verification, first real run), five review guides with a multi-tool installer, and a system that keeps the test suite out of the agent's reach. Start at [adoption/README.md](adoption/README.md).

## What's in this repo

- [CONTRACTS.md](CONTRACTS.md) — what each layer must provide and why each mechanism is needed.
- [schemas/](schemas/) — six JSON Schemas for the result documents the layers create, with [examples](schemas/examples/) and [SCHEMAS.md](schemas/SCHEMAS.md) (the full schema guide and changelog).
- [conformance/](conformance/) — the test suite that checks a harness against the requirements, with a basic [reference adapter](conformance/reference-adapter/) that shows how to build one.
- [schemas/routing-log-grammar.md](schemas/routing-log-grammar.md) — the rules for the routing log that JSON Schema can't express, with a working tool ([conformance/loglint.py](conformance/loglint.py)) that was tested against real production logs.

## Running the checks

Requires Python 3.10+ and the `jsonschema` package.

```bash
python3 schemas/validate.py
python3 conformance/selftest.py
python3 conformance/loglint.py conformance/fixtures/finds-bug-run/routing.jsonl --evidence-dir conformance/fixtures/finds-bug-run
```

Or run all three through the repo's own harness: `bin/harness verify` (checks cheapest first, stops on failure; the repo follows its own rules, see [.claude/harness.json](.claude/harness.json)).

## Origins

Every schema version came from a real system's results, not theory: an iOS app's agent and graph layer tested each draft, and only what actually proved necessary stayed in. The decision log and what we learned is in [docs/HISTORY.md](docs/HISTORY.md); the full mapping work is in [docs/STRAIN-REPORT.md](docs/STRAIN-REPORT.md).

## Version

Current: v0.4.0. The next version is held back on purpose until real-world runs give us more evidence. The v0.5 plan is in [docs/HISTORY.md](docs/HISTORY.md) §8.
