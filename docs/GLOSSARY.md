# Tāniko Glossary

Every specialised term used in this repository is defined here in plain language. Other documents link to this glossary instead of re-explaining terms; if you hit an unfamiliar word anywhere, look it up here first.

## The name

**Tāniko** is te reo Māori for a finger-weaving technique that produces intricate geometric borders through precise, rule-based thread paths. The mapping is exact: the threads are parallel work items, the rules are the contracts and grammar in this repo, and the woven border is verification at the edge of the work. In prose we always write **Tāniko**, with the macron (tohutō). In machine identifiers — repository slugs, URNs (`urn:taniko:…`), file names — we use the ASCII form `taniko`, because not every system handles macrons.

## The three layers, in one breath

A Tāniko system runs AI coding agents inside three nested safety structures:

- The **harness** makes the working environment cheap to know and safe to act in.
- The **loop** makes progress real: work only counts as done when deterministic evidence says so.
- The **graph** splits work across parallel, isolated workers and checks every result adversarially before it merges.

The rest of this glossary defines each term those sentences rely on.

## Terms

### Adapter
A project-specific implementation of the generic contracts in [CONTRACTS.md](../CONTRACTS.md). Tāniko is a framework, not a drop-in harness: whatever your product — an iOS app, a web service, a command-line tool, a Python library — you build its harness, loop, and graph layers to fit, tailoring everything the contracts leave open while enforcing what they determine must hold (deterministic verification above all). The toy project in `conformance/reference-adapter/` is one adapter; yours will be another. The contract is generic; the adapter is yours.

### Adversarial verifier (also *gate*)
An agent whose only job is to break the work a producer just did — edge cases, boundary conditions — before that work is allowed to merge. It is deliberately separate from the producer: different context, different instructions, no shared authorship. See CONTRACTS.md §3, *Verification gates*.

### Bounded feedback
Failure output trimmed to what a retrying agent actually needs — the failing assertion, file, and line — never the full log. Full logs stay on disk and are referenced, not pasted. A feedback envelope without a documented way to dig into the retained raw evidence is incomplete; the pair is the contract. See CONTRACTS.md §2, *Compact, bounded feedback*.

### Budget cap
A maximum number of attempts (and, where measurable, cost) the loop will spend on one problem. Hitting the cap produces an explicit failure with all evidence attached — never a silent stop, never "mostly done". See CONTRACTS.md §2, *Budget caps*.

### Checkpoint
A saved, restorable state of the work — in practice, git commits or stashes taken at defined points. Checkpoints let a failed branch be rolled back without poisoning its siblings. Provided by the harness; used by the graph.

### Content assertion
Proof that content actually flowed through a run. Because an unchanged tree can legitimately replay a passing verdict, a node claiming to produce content must show that its branch moved past its base. This clause exists because a real implementation once ran five phases of green-verifying orchestration around a pipeline that had carried nothing. See CONTRACTS.md §3, *Content assertions*.

### Conformance suite
The test suite in `conformance/` that judges a harness against CONTRACTS.md — the way your unit tests judge your app, this suite judges your harness. Runs in three tiers: static, behavioural, destructive. See [conformance/README.md](../conformance/README.md).

### Doctor
A command that answers two questions at session start: does the machine match the declared toolchain (**drift detection**), and is the environment usable right now (**health checking**)? Either problem halts the session; the fix is repairing the environment or updating the declaration, never pressing on regardless. See CONTRACTS.md §1.

### Canonical instructions file
The single committed file (`AGENTS.md`, `CLAUDE.md`, or equivalent) that states a project's execution rules for every agent session. One file, versioned with the code, so rules apply identically every session instead of living scattered in prompts. See CONTRACTS.md §1, *Instruction specification*.

### Escalation
What happens when a node exhausts its budget or a gate trips: work stops and a structured report routes to a human gate or failure handler with all evidence attached. An escalation is a deliberate outcome, never a crash.

### Evidence
A deterministic record produced by running something: a verify-result, a doctor-report, a routing log. "The agent is confident" is not evidence. Every claim in a Tāniko system traces back to evidence within one or two hops.

### Evidence surface / evidence provisioning
A verification gate can only test against test files and assertable structure that already exist. Creating that surface is planned, declared producer work — not something a gate improvises mid-run. Tests also count as evidence only once executed. See CONTRACTS.md §3, *Evidence provisioning*.

### Fan-out / join
Splitting one piece of work into parallel branches (**fan-out**) and combining their results (**join**: all-of, any-of, or quorum). Splits must be by disjoint write scopes — see *write scope*.

### Harness declaration
The committed file (`.claude/harness.json` by convention) stating what a project requires: toolchain versions, sandbox boundaries, verify tiers and budgets, and how to invoke doctor and verify. It is the one document the whole system is anchored to; everything else is runtime output derived from it. Schema: `schemas/harness-declaration.schema.json`.

### Hook
A defined interception point where the harness runs deterministic code before or after every tool use — hash checks before reads, audit logs after writes, output truncation. Hooks are where "the agent keeps doing X wrong" becomes "the environment makes X impossible". See CONTRACTS.md §1, *Hook interface*.

### Learned facts
Small, hard-won repository facts worth keeping across sessions ("this test is flaky", "this module is surprisingly coupled"). They live in gitignored session state until they stabilise, then graduate into committed instructions or skills.

### Loop
See *verification loop*.

### Mode (real / demo / stub)
Every verify-result declares how it was produced. `real` ran actual verification; `demo` and `stub` did not, and can never satisfy completion evidence no matter what verdict they carry. Added after a stub verifier once claimed a full profile with a 2-millisecond duration and a 1 January timestamp — and was schema-valid throughout.

### Node
One unit of graph work: an isolated worker (usually an agent session) with declared inputs, outputs, and write scope. Each node contains its own verification loop. Roles: a **producer** writes code; a **gate** verifies it (a gate is a node with `role: gate`).

### Producer
A node whose job is to do the work — write the code, add the test. Contrasts with the *adversarial verifier* that checks it.

### Profile
A named subset of verification tiers with its own cache key — typically `quick` (static checks) versus `full` (everything). A quick pass can never masquerade as a full pass; the profile name travels with every result.

### Progress record
Per-node session state listing what has been done, what remains, and decisions made. Gitignored, never committed, scoped to one node so parallel branches never share mutable state. Schema: `schemas/progress.schema.json`.

### Ratchet
The practice of turning a repeated agent mistake into a mechanism that makes the mistake impossible — a hook, a sandbox rule, a lint. Rules enforced by prose get skipped; rules enforced by mechanism don't. The metaphor: like a ratchet wrench, each improvement locks in and doesn't slip back.

### Red→green
Writing a failing test first, then making it pass. The failing run proves the test bites; the passing run proves the code changed. It is the enforceable form of "test first".

### Reference adapter
`conformance/reference-adapter/` — the smallest fully conforming harness (~250 lines of Python). Read it as specification-by-example when building your own adapter; the conformance suite also uses it as its test fixture.

### Routing log
The append-only JSONL record of every routing decision a graph run made: enters, exits, spawns, retries, escalations, with inputs and evidence references. It exists so any run can be replayed and any misroute diagnosed as a graph bug rather than a mystery. Schema: `schemas/routing-record.schema.json`; sequence rules: `schemas/routing-log-grammar.md` (rules G1–G9); executable check: `conformance/loglint.py`.

### Sandbox boundary
The declared split between writable, read-only, and forbidden paths, enforced outside the model by the harness. Critically, it must protect the verifiers and their configuration from the agent being verified — an agent that can edit its own exam eventually will.

### Session state
Runtime files a harness keeps between turns — progress records, tool caches, checkpoint logs. Always gitignored; committing it causes merge conflicts and cross-branch leakage. Lives in the directory named by the declaration's `state.dir`.

### Skill
A task-shaped instruction file an agent reads on demand, kept alongside the canonical instructions file. When a learned fact stabilises, this is where it graduates — committed, versioned, and applied identically every session.

### Strain finding
A mismatch discovered by pressing real code against the generic schemas ("straining" them). Recording and resolving strain findings is how every schema version was produced; nothing was ever designed purely from theory. The records live in [docs/STRAIN-REPORT.md](STRAIN-REPORT.md) and [docs/RESOLUTIONS-0.4.0.md](RESOLUTIONS-0.4.0.md).

### Tier
One ordered step of verification, cheapest first — typically static checks, then unit tests, then integration/UI tests. The loop runs tiers in order and stops at the first failure: no point spending a nine-minute UI run on code that doesn't compile. Tier names and commands are per-project; the ordering is contractual.

### Tool cache
A cache of tool outputs keyed by tool, arguments, and a content hash of inputs. A hit is served without re-running the tool or asking the model. Invalidated by content hash, never by time. Schema: `schemas/tool-cache.schema.json`.

### Verdict
A verification outcome, one of exactly three: `pass`, `fail`, or `error` (the tooling itself broke — distinct from "the tests found a bug"). Model confidence is deliberately not a fourth option.

### Verdict cache / replay
Because verification is deterministic, a verdict can be cached against the tree's content hash and replayed instantly on an unchanged tree — turning an 80-second verify into a sub-second one. Replay is legitimate precisely because determinism is contractual; every flaky test poisons it.

### Verification loop
The inner engine of progress: attempt work, verify with a deterministic command, read the bounded feedback, retry — with budget caps and evidence gating at every turn. "Work counts as done only when evidence says so" is the loop's whole philosophy. See CONTRACTS.md §2.

### Verify-result
The evidence envelope for one verification run: overall verdict, per-stage results, feedback from the failed stage, cache/replay information, mode, and the profile's tier list. It is the single record type by which the system knows work is done. Schema: `schemas/verify-result.schema.json`.

### Worktree
A git feature the graph leans on: a second checked-out copy of the repository sharing its history but with its own files. Each node works in its own worktree, which is how parallel branches avoid stepping on each other.

### Write scope
The exact set of paths a node may modify, declared before the run and enforced by the harness. Two nodes whose write scopes overlap are not parallel work — they are a race condition waiting to happen, whatever their task descriptions claim.

## Where to go next

- New to the whole idea? Start with the [README](../README.md), then [CONTRACTS.md](../CONTRACTS.md).
- Implementing an adapter? [CONTRACTS.md](../CONTRACTS.md), then [schemas/SCHEMAS.md](../schemas/SCHEMAS.md), then the [reference adapter](../conformance/reference-adapter/).
- Curious why anything is the way it is? [docs/HISTORY.md](HISTORY.md).
