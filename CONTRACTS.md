# Layer Contracts: Harness, Loop, Graph

This document defines the contracts each layer must satisfy, the goal each contract serves, and why the mechanism exists. The implementation of each contract is project-specific; the contract itself is not.

The three goals of the whole system, stated once so every contract below can be traced to them:

1. **Accuracy** — the system never reports success without deterministic evidence, and never acts on stale or hallucinated state.
2. **Efficiency** — no token is spent observing something already known; no context is polluted with information the current task doesn't need.
3. **Latency and cost** — independent work runs concurrently; retries are bounded; deterministic work never runs through the model.

Every mechanism in this architecture (hashing, caching, evidence gates, fan-out) exists to serve one or more of these. If a proposed feature can't be traced to one, it doesn't belong.

---

## 1. Harness Layer Contract

### Why this layer exists

The model is stateless, unprivileged, and expensive to inform. It cannot execute commands, remember anything between turns, or know what machine it's on. Everything the model appears to "know" about the environment was paid for in tokens — and paid for again every time it re-observes it. The harness exists to make the environment *cheap to know and safe to act on*: it provides state so the model doesn't reconstruct it, caching so observation costs are paid once, and boundaries so mistakes are contained rather than prevented by hope.

The economic argument for caching specifically: file reads dominate token spend in real agent sessions, and most reads are re-reads of unchanged files. Content hashing converts "did this change?" from a token-priced model observation into a free local computation. The accuracy argument is just as strong: long contexts full of redundant file dumps measurably degrade model attention. A harness that de-duplicates observation isn't only cheaper — it produces a sharper agent.

### The contract

A conforming harness MUST provide:

**Environment declaration and verification.** A machine-readable declaration of the required toolchain (runtime versions, build tool versions, SDKs) and a `doctor` command with two distinct duties: *drift detection* — checking the actual machine against the declaration — and *health checking* — confirming the environment is usable right now (required runtime resources discoverable, working paths writable, disk sufficient, auxiliary tools responding). Doctor exits 0 on healthy match (advisory warnings permitted) and non-zero with a specific diff on drift or failed health. Both are halting conditions, not warnings: the correct response is a harness-update or environment-repair task, never "proceed and hope." A doctor without a committed declaration can attest health but cannot attest drift; conformance requires both. This is the mechanism that keeps the harness current as the environment evolves.

**Sandbox boundary.** A declaration of writable paths, read-only paths, and forbidden paths, enforced outside the model (hooks, filesystem permissions, or OS sandboxing — whatever the platform supports). The form of the sandbox is project-specific (a Docker container, a user dev directory, an Xcode derived-data space); the contract is only that the boundary is declared, enforced, and least-privilege. Critically, the boundary MUST protect the Loop layer's verifiers and configuration from modification by the agent (see §2 — evidence the agent can edit is not evidence).

**State persistence.** A defined location and schema for cross-turn memory: a progress record (what has been done, what remains, decisions made) and checkpointing sufficient to roll back a failed branch (in practice: git commits or stashes at defined points, with a log of checkpoint identity). The persistence contract is what allows a session to be interrupted, resumed, or handed to a parallel branch without re-deriving state through the model.

**Observation cache.** A cache of tool outputs keyed by (tool, arguments, content hash of inputs). A cache hit MUST be served without model involvement and without re-executing the tool. Invalidation is by content hash, never by time. The cache MUST record what it saved (token estimate) so the system's efficiency is measurable rather than assumed.

**Instruction specification.** A single canonical rules file (`CLAUDE.md`, `AGENTS.md`, or equivalent) that states the project's execution rules, constraints, and conventions, with per-tool entry points (symlinks or pointer files) that carry the one or two most load-bearing rules inline so they survive even a tool that reads nothing else. Rules live here, not scattered across prompts, so they version with the code and apply to every session identically. Alongside it, *skills*: task-shaped instruction files read on demand, which are where learned facts graduate once stable — the committed end state of the ratchet. Skills also carry a defensive duty: any convention a harness mechanism depends on (e.g. a naming convention that powers changed-file test mapping) must be actively stated and defended in the relevant skill, because the mechanism silently degrades when the convention drifts.

**Hook interface.** Defined pre-tool and post-tool interception points where policy runs deterministically: hash checks before reads, audit logging after writes, output-length truncation. Hooks are where "the agent keeps doing X wrong" becomes "the environment makes X impossible" — the ratchet by which the harness improves.

### Placement and lifecycle

The harness *declarations* (toolchain, boundaries, rules, verify adapters) live in the project repository and change in the same commit as the code that requires them. This preserves branch consistency and bisectability: every commit is a coherent world.

The harness *engine* (cache implementation, hook runner, hashing) is a pinned versioned dependency, not vendored code, so fixes propagate across projects.

*Machine facts* (personal paths, installed simulators, local sandbox locations) live in a per-machine config layer referenced by, but never committed to, the repo.

*Session state* (`progress.json`, `tool_cache.json`, checkpoint logs) is runtime data: gitignored, never committed. Committing it causes merge conflicts and cross-branch state leakage.

### Invariants

Harness operations are idempotent and exit with deterministic codes. No harness function requires model judgment to execute. If the fix for a failure is "the model should have known the environment better," the fix belongs here.

---

## 2. Loop Layer Contract

### Why this layer exists

A language model's native stopping condition is plausibility: it stops when the output *reads* finished. Left alone, an agent will loop until it asserts success, and its assertion correlates only weakly with reality. The loop layer replaces the model's self-report with external, deterministic evidence. This is the single highest-leverage accuracy mechanism in the architecture: it converts "the agent says the code works" into "the test suite exited 0."

The loop also carries the cost-control burden on the retry axis: unbounded retry against a hard problem is the failure mode that burns budgets. Evidence gating plus attempt caps turns runaway loops into bounded, observable ones.

### The contract

A conforming project MUST expose a verification interface with these properties:

**Deterministic verdicts.** Verification is invoked as a command (`verify`) whose exit code is the verdict. The same code state always produces the same verdict — flaky tests are a contract violation to be fixed or quarantined, because a nondeterministic gate teaches the loop nothing. Where a suite has known flakiness that cannot be fixed immediately, a *declared* retry policy (bounded reruns of failed tests) is a permitted bridge, with one absolute condition: a pass rescued by a rerun is disclosed in the evidence, never hidden. Undeclared retries and undisclosed flaky passes remain violations.

**Verdict replay.** Because verdicts are deterministic functions of code state, a verdict may be cached keyed by working-tree *content* (never timestamps) and replayed on an unchanged tree — and that replay is legitimate evidence, typically turning a minute-scale verify into a sub-second one. Replay legitimacy rests entirely on the determinism requirement above (every flaky test poisons cache validity), pass and fail are both cacheable, and cache keys MUST include the verification profile so a partial-tier pass can never replay as a full one. In practice this is the highest-value caching mechanism in the architecture: the expensive redundant observation in a build-and-test workflow is the verify run itself.

**Tiered cost.** Verification is offered in ordered tiers from cheapest to most expensive — typically static checks (lint, typecheck, build) before unit tests before integration/UI tests. The loop runs tiers in order and fails fast: there is no reason to spend a 9-minute UI test run on code that doesn't compile. Tier names and commands are project-specific (an iOS project's tiers might be `xcodebuild build`, `xcodebuild test` on a unit scheme, then a UI test scheme); the ordering property is not.

**Compact, bounded feedback.** On failure, the verifier emits feedback designed for re-injection into the model: size-bounded (e.g., the distilled traceback, not the full log), specific (the failing assertion, the file and line), and stripped of noise. Feedback quality directly determines retry efficiency — a loop fed a 40k-token raw log is paying tokens to degrade its own attention. Full logs and result bundles are retained on disk and *referenced* from the feedback, never inlined, and the bound is completed by its escalation path: a debug skill documenting how to query the retained raw evidence narrowly (search, don't read) when the summary is insufficient. A bounded envelope without a documented escalation path produces agents that either flail or dump whole logs; the pair is the contract.

**Budget caps.** The loop enforces a maximum attempt count and, where measurable, a cost ceiling. Exhausting the budget produces an explicit failure *with the accumulated evidence attached* — never a silent stop, and never a downgraded claim of partial success.

**Evidence self-identification.** Every verification document declares its own mode (real, demo, or stub) and the tier set its profile comprises. A non-real document never satisfies completion evidence regardless of verdict, and a document claiming a full profile while running a subset is a violation the tooling must be able to detect. Evidence that cannot attest to its own completeness will eventually be mistaken — or passed off — for more than it is.

**Tamper isolation.** The agent under verification MUST NOT be able to modify the verifier, its configuration, or the tests that gate it (except through an explicitly separate, reviewed path). This is enforced by the Harness sandbox boundary. An agent that can edit its own exam will, under optimization pressure, eventually do so.

### Invariants

The loop's output is one of exactly two things: a pass with evidence (what ran, what passed, at which tier) or a fail with evidence (attempts made, final feedback). "The agent is confident" is not a member of this set. If the failure mode is "it claimed success but the code is broken," the fix belongs here.

---

## 3. Graph Layer Contract

### Why this layer exists

Sequential execution is the latency ceiling: three independent 2-minute investigations run in 6 minutes sequentially and 2 minutes fanned out. But the graph layer's contribution to *accuracy* is just as important and less obvious: fan-out is context isolation. A sub-agent scoped to "inspect test coverage for module X" operates in a small, clean context and outperforms a monolithic agent dragging the entire session history. The graph is how the system keeps every model call's context minimal — which is the same efficiency goal the harness cache serves, applied at the topology level.

The graph also owns containment: a failed branch is rolled back (via harness checkpoints) without poisoning sibling branches or the main line.

### The contract

A conforming graph MUST define:

**Node interfaces.** Each node declares its inputs and outputs as typed artifacts (files, structured results, evidence records) — not as shared conversational context. A node receives the minimum context its scope requires and nothing else. Handing a sub-agent the full parent transcript is a contract violation with a measurable cost.

**Fan-out and join semantics.** Where work splits, the split is across *independent* scopes. Independence is defined by write sets, not by task labels: two nodes that write to the same files are not parallel work regardless of how differently their tasks are described — they are a race condition. Partition by file ownership first, and only then by task type within each ownership region; scopes whose write sets cannot be made disjoint must be serialized. (Read overlap is fine and expected — shared reads are what the harness cache is for.) Every fan-out declares its join: all-of, any-of, or quorum, and what happens to stragglers.

**Bounded cycles.** Any retry or revision edge in the graph carries an explicit attempt limit and an escalation edge (to a human gate or a failure report). Unconstrained cycles are the graph-level version of looping on confidence.

**Error branches.** Routing defines what happens on failure, not only on success. A node failure routes somewhere deliberate: retry, alternative strategy, rollback-and-escalate. "The graph didn't anticipate this" should terminate in a failure report, never in undefined behavior.

**Evidence provisioning.** A verification gate can only assert against seams that exist: test files, their build-target membership, and assertable structure in the code under test. Provisioning those seams is *producer* work, declared in the producer's write scope and validated at plan time — a plan whose producer touches source without including (or creating) its test surface is invalid before it runs. A gate forced to improvise its evidence surface has exactly two outcomes, both failures: it violates its write scope, or it produces evidence that exists but never executes. Corollary: tests are evidence only when they run — completion reports cite executed tests (present in the verify counts), never merely created files. Where a shift-left policy applies, the enforceable form is red→green: the evidence chain contains a failing verify citing the new test before the passing one, proving the test bites.

**Content assertions.** A verified tree is not evidence that work was performed: an unchanged tree legitimately replays a passing verdict, so a node whose runner failed can still present a valid PASS for its untouched worktree. Node completion therefore requires, in order: runner success, valid node progress, and verify evidence — and a content-producing run must assert that content actually flowed (integration tip differs from base; the verifier's input digest reflects a non-empty diff). This clause exists because a real implementation ran five phases of verified orchestration around a pipeline that had never carried cargo, and every verdict was green.

**Verification gates.** Completed work routes through an adversarial verifier node — a separately-scoped agent whose job is to break the patch (edge-case tests, boundary probing) before it is committed. The verifier's independence matters: it must not share context, incentives, or authorship with the node that produced the work.

**Replayable routing.** Every routing decision is logged with its inputs, so a run can be replayed and a misroute diagnosed as a graph bug rather than a mystery.

### Invariants

Deterministic work (string parsing, deduplication, file filtering, format conversion) is implemented as code nodes, never model nodes — model tokens are for judgment, not computation. If the failure mode is "work ran in the wrong order, sequentially, or in the wrong place," the fix belongs here.

---

## 4. Cross-Layer Dependencies

The layers are not independent modules; three couplings are load-bearing:

- **Loop integrity depends on Harness enforcement.** Evidence gating is only as strong as the sandbox that stops the agent editing the verifier.
- **Graph containment depends on Harness checkpoints.** Branch rollback is a graph decision executed by harness mechanisms (git checkpoints, state restore).
- **Every graph node contains a loop.** The graph routes between nodes; each node internally iterates against its own evidence gate. A node without a loop is a node that can route hallucinated results downstream.

## 5. Diagnosis Rule

Every failure has exactly one home layer. When triaging:

- Lost state, stale environment, redundant reads, permission surprises → **Harness**.
- Claimed success contradicted by reality, runaway retries, noisy feedback → **Loop**.
- Wrong order, needless serialization, misrouting, unbounded cycles, cross-branch contamination → **Graph**.
- "Improve the prompt" is the correct fix only when all three layers already hold and the residual failure is genuinely one of instruction clarity. It is the last resort, not the first.

## 6. Conformance Checklist

A project implements this architecture when: `doctor` exists and halts on drift; the sandbox boundary is declared, enforced, and protects the verifiers; session state is persisted, gitignored, and checkpointed; the observation cache is active and measured; `verify` exists with ordered tiers, deterministic exits, bounded feedback, and budget caps; fan-out scopes are independent with declared joins; every cycle is bounded with an escalation edge; an independent adversarial gate precedes commit; and routing decisions are logged for replay.
