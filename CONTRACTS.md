# Layer Contracts: Harness, Loop, Graph

This document defines what each layer must provide, the goal each requirement serves, and why the mechanism exists. The implementation of each contract is project-specific; the contract itself is not.

How to read it: each contract clause states **what it requires** first, then **why** — the failure or evidence that earned the rule. Normative keywords (MUST) are binding. Terms are defined in the [glossary](docs/GLOSSARY.md).

The three goals of the whole system, stated once so every contract below can be traced to them:

1. **Accuracy** — the system never reports success without deterministic evidence, and never acts on stale or hallucinated state.
2. **Efficiency** — no token is spent observing something already known; no context carries information the current task does not need.
3. **Latency and cost** — independent work runs concurrently; retries are bounded; deterministic work never runs through the model.

Every mechanism in this architecture (hashing, caching, evidence gates, fan-out) serves one or more of these goals. If a proposed feature cannot be traced to one, it does not belong.

---

## 1. Harness Layer Contract

### Why this layer exists

The model is stateless, unprivileged, and expensive to inform. It cannot execute commands, remember anything between turns, or know what machine it is on. Everything the model appears to "know" about the environment was paid for in tokens — and paid for again every time it re-observes the same thing. The harness exists to make the environment cheap to know and safe to act on: it provides state so the model does not reconstruct it, caching so observation costs are paid once, and boundaries so mistakes are contained rather than prevented by hope.

Caching deserves its own economic argument, because file reads dominate token spend in real agent sessions and most reads are re-reads of unchanged files. Content hashing turns "did this change?" from a token-priced model observation into a free local computation. The accuracy argument is just as strong: long contexts full of redundant file dumps measurably degrade model attention. A harness that de-duplicates observation is not only cheaper — it produces a sharper agent.

### The contract

A conforming harness MUST provide each of the following.

#### Environment declaration and verification

**What it requires.**

- A machine-readable declaration of the required toolchain: runtime versions, build tool versions, SDKs.
- A `doctor` command with two distinct duties:
  - *drift detection* — checking the actual machine against the declaration; and
  - *health checking* — confirming the environment is usable right now: required resources discoverable, working paths writable, disk sufficient, auxiliary tools responding.
- Exit codes with meaning: `0` on healthy match (advisory warnings permitted); non-zero with a specific diff on drift or failed health.
- Both duties backed by the committed declaration. A doctor without one can attest health but cannot attest drift; conformance requires both.

Drift and failed health are halting conditions, not warnings. The correct response is a harness-update or environment-repair task — never "proceed and hope". This mechanism is what keeps the harness current as the environment evolves.

#### Sandbox boundary

**What it requires.**

- A declaration of writable paths, read-only paths, and forbidden paths.
- Enforcement outside the model — hooks, filesystem permissions, or OS sandboxing, whatever the platform supports.
- Least privilege: the boundary permits exactly what the work needs.

The form of the sandbox is project-specific (a Docker container, a user dev directory, an Xcode derived-data space). The contract is only that the boundary is declared, enforced, and least-privilege. Critically, it MUST protect the Loop layer's verifiers and configuration from modification by the agent (see §2 — evidence the agent can edit is not evidence).

#### State persistence

**What it requires.**

- A defined location and schema for cross-turn memory: a progress record of what has been done, what remains, and decisions made.
- Checkpointing sufficient to roll back a failed branch — in practice, git commits or stashes at defined points, with a log of checkpoint identity.

Persistence is what allows a session to be interrupted, resumed, or handed to a parallel branch without re-deriving state through the model.

#### Observation cache

**What it requires.**

- A cache of tool outputs keyed by tool, arguments, and content hash of inputs.
- A cache hit MUST be served without model involvement and without re-executing the tool.
- Invalidation by content hash, never by time.
- The cache MUST record what it saved (a token estimate), so the efficiency gain is measurable rather than assumed.

#### Instruction specification

**What it requires.**

- One canonical rules file (`CLAUDE.md`, `AGENTS.md`, or equivalent) stating the project's execution rules, constraints, and conventions. Rules live here — not scattered across prompts — so they version with the code and apply to every session identically.
- Per-tool entry points (symlinks or pointer files) carrying the one or two most load-bearing rules inline, so they survive even a tool that reads nothing else.
- Alongside it, skills: task-shaped instruction files read on demand, where learned facts graduate once stable. This is the committed end state of the ratchet.

Skills also carry a defensive duty. Any convention a harness mechanism depends on — for example, a naming convention that powers changed-file test mapping — must be actively stated and defended in the relevant skill, because the mechanism silently degrades when the convention drifts.

#### Hook interface

**What it requires.**

- Defined pre-tool and post-tool interception points where policy runs deterministically: hash checks before reads, audit logging after writes, output-length truncation.

Hooks are where "the agent keeps doing X wrong" becomes "the environment makes X impossible". This is the ratchet by which the harness improves.

### Placement and lifecycle

- **Declarations** (toolchain, boundaries, rules, verify adapters) live in the project repository and change in the same commit as the code that requires them. This preserves branch consistency and bisectability: every commit is a coherent world.
- **The engine** (cache implementation, hook runner, hashing) is a pinned versioned dependency, not vendored code, so fixes propagate across projects.
- **Machine facts** (personal paths, installed simulators, local sandbox locations) live in a per-machine config layer referenced by — but never committed to — the repository.
- **Session state** (`progress.json`, `tool_cache.json`, checkpoint logs) is runtime data: gitignored, never committed. Committing it causes merge conflicts and cross-branch state leakage.

### Invariants

Harness operations are idempotent and exit with deterministic codes. No harness function requires model judgment to execute. If the fix for a failure is "the model should have known the environment better", the fix belongs in this layer.

---

## 2. Loop Layer Contract

### Why this layer exists

A language model's native stopping condition is plausibility: it stops when the output *reads* finished. Left alone, an agent loops until it asserts success, and its assertion correlates only weakly with reality. The loop layer replaces the model's self-report with external, deterministic evidence. This is the single highest-leverage accuracy mechanism in the architecture: it converts "the agent says the code works" into "the test suite exited 0".

The loop also carries the cost-control burden on the retry axis. Unbounded retry against a hard problem is the failure mode that burns budgets. Evidence gating plus attempt caps turns runaway loops into bounded, observable ones.

### The contract

A conforming project MUST expose a verification interface with these properties.

#### Deterministic verdicts

**What it requires.**

- Verification invoked as a command (`verify`) whose exit code is the verdict.
- The same code state always produces the same verdict.

Flaky tests are a contract violation, to be fixed or quarantined — a nondeterministic gate teaches the loop nothing. Where a suite has known flakiness that cannot be fixed immediately, a *declared* retry policy (bounded reruns of failed tests) is a permitted bridge, with one absolute condition: a pass rescued by a rerun is disclosed in the evidence, never hidden. Undeclared retries and undisclosed flaky passes remain violations.

#### Verdict replay

**What it requires.**

- Verdicts cached and replayed, keyed by working-tree *content*, never timestamps.
- Replay permitted on an unchanged tree as legitimate evidence — typically turning a minute-scale verify into a sub-second one.
- Cache keys MUST include the verification profile, so a partial-tier pass can never replay as a full one.
- Both pass and fail verdicts are cacheable.

Replay legitimacy rests entirely on determinism (every flaky test poisons cache validity). In practice this is the highest-value caching mechanism in the architecture: the expensive redundant observation in a build-and-test workflow is the verify run itself.

#### Tiered cost

**What it requires.**

- Verification offered in ordered tiers from cheapest to most expensive — typically static checks (lint, typecheck, build), then unit tests, then integration/UI tests.
- Tiers run in order, failing fast: there is no reason to spend a nine-minute UI test run on code that does not compile.

Tier names and commands are project-specific — an iOS project's tiers might be `xcodebuild build`, `xcodebuild test` on a unit scheme, then a UI test scheme. The ordering property is contractual.

#### Compact, bounded feedback

**What it requires.**

On failure, the verifier emits feedback designed for re-injection into the model:

- size-bounded — the distilled traceback, not the full log;
- specific — the failing assertion, the file, the line;
- stripped of noise;
- referencing retained full logs and result bundles on disk rather than inlining them;
- paired with an escalation path — a debug skill documenting how to query the retained raw evidence narrowly (search, don't read) when the summary is insufficient.

Feedback quality directly determines retry efficiency: a loop fed a 40k-token raw log is paying tokens to degrade its own attention. And the bounded envelope alone is incomplete — without a documented escalation path, agents either flail or dump whole logs. The pair is the contract.

#### Budget caps

**What it requires.**

- A maximum attempt count, and a cost ceiling where measurable.
- Exhausting the budget produces an explicit failure *with the accumulated evidence attached* — never a silent stop, and never a downgraded claim of partial success.

#### Evidence self-identification

**What it requires.**

- Every verification document declares its own mode: real, demo, or stub.
- It declares the tier set its profile comprises.
- A non-real document never satisfies completion evidence, regardless of verdict.
- Tooling can detect a document claiming a full profile while running a subset — this is a violation.

Evidence that cannot attest to its own completeness will eventually be mistaken — or passed off — for more than it is.

#### Tamper isolation

**What it requires.**

- The agent under verification MUST NOT be able to modify the verifier, its configuration, or the tests that gate it, except through an explicitly separate, reviewed path.

Enforcement comes from the Harness sandbox boundary (§1). The reason is adversarial: an agent that can edit its own exam will, under optimization pressure, eventually do so.

### Invariants

The loop's output is one of exactly two things:

- a **pass** with evidence — what ran, what passed, at which tier; or
- a **fail** with evidence — attempts made, final feedback.

"The agent is confident" is not a member of this set. If the failure mode is "it claimed success but the code is broken", the fix belongs in this layer.

---

## 3. Graph Layer Contract

### Why this layer exists

Sequential execution is the latency ceiling: three independent two-minute investigations take six minutes sequentially and two minutes fanned out. But the graph layer's contribution to accuracy matters just as much and is less obvious: fan-out is context isolation. A sub-agent scoped to "inspect test coverage for module X" operates in a small, clean context and outperforms a monolithic agent dragging the entire session history. The graph keeps every model call's context minimal — the same efficiency goal the harness cache serves, applied at the topology level.

The graph also owns containment: a failed branch is rolled back (via harness checkpoints) without poisoning sibling branches or the main line.

### The contract

A conforming graph MUST define each of the following.

#### Node interfaces

**What it requires.**

- Each node declares its inputs and outputs as typed artifacts — files, structured results, evidence records — not shared conversational context.
- A node receives the minimum context its scope requires, and nothing else.

Handing a sub-agent the full parent transcript is a contract violation with a measurable cost.

#### Fan-out and join semantics

**What it requires.**

- Where work splits, the split is across *independent* scopes.
- Independence is defined by write sets, not task labels. Two nodes writing the same files are not parallel work however different their tasks sound — they are a race condition.
- Partition by file ownership first, then by task type within each ownership region. Scopes whose write sets cannot be made disjoint must be serialized.
- Read overlap is fine and expected — shared reads are what the harness cache is for.
- Every fan-out declares its join: all-of, any-of, or quorum, and what happens to stragglers.

#### Bounded cycles

**What it requires.**

- Any retry or revision edge carries an explicit attempt limit.
- Every such edge has an escalation edge — to a human gate or a failure report.

Unconstrained cycles are the graph-level version of looping on confidence.

#### Error branches

**What it requires.**

- Routing defines what happens on failure, not only on success.
- A node failure routes somewhere deliberate: retry, alternative strategy, or rollback-and-escalate.
- "The graph didn't anticipate this" terminates in a failure report — never undefined behavior.

#### Evidence provisioning

**What it requires.**

- A verification gate asserts only against seams that exist: test files, their build-target membership, and assertable structure in the code under test.
- Provisioning those seams is producer work, declared in the producer's write scope and validated at plan time. A plan whose producer touches source without including (or creating) its test surface is invalid before it runs.
- Tests count as evidence only when they run: completion reports cite executed tests (present in the verify counts), never merely created files.
- Where shift-left policy applies, the enforceable form is red→green: the evidence chain contains a failing verify citing the new test before the passing one, proving the test bites.

A gate forced to improvise its evidence surface has exactly two outcomes, both failures: it violates its write scope, or it produces evidence that exists but never executes.

#### Content assertions

**What it requires.** Node completion, in order:

1. runner success;
2. valid node progress;
3. verify evidence; and
4. for a content-producing run, proof that content actually flowed — the integration tip differs from base, and the verifier's input digest reflects a non-empty diff.

A verified tree is not evidence that work was performed: an unchanged tree legitimately replays a passing verdict, so a node whose runner failed can still present a valid PASS for its untouched worktree. This clause exists because a real implementation ran five phases of verified orchestration around a pipeline that had never carried cargo, and every verdict was green.

#### Verification gates

**What it requires.**

- Completed work routes through an adversarial verifier node — a separately scoped agent whose job is to break the patch (edge-case tests, boundary probing) before it is committed.
- The verifier is independent: it shares no context, incentives, or authorship with the node that produced the work.

#### Replayable routing

**What it requires.**

- Every routing decision logged with its inputs, so any run can be replayed and any misroute diagnosed as a graph bug rather than a mystery.

### Invariants

Deterministic work — string parsing, deduplication, file filtering, format conversion — is implemented as code nodes, never model nodes. Model tokens are for judgment, not computation. If the failure mode is "work ran in the wrong order, sequentially, or in the wrong place", the fix belongs in this layer.

---

## 4. Cross-Layer Dependencies

The layers are not independent modules; three couplings are load-bearing:

- **Loop integrity depends on Harness enforcement.** Evidence gating is only as strong as the sandbox that stops the agent editing the verifier.
- **Graph containment depends on Harness checkpoints.** Branch rollback is a graph decision executed by harness mechanisms (git checkpoints, state restore).
- **Every graph node contains a loop.** The graph routes between nodes; each node internally iterates against its own evidence gate. A node without a loop is a node that can route hallucinated results downstream.

## 5. Diagnosis Rule

Every failure has exactly one home layer. When triaging:

| Symptom | Home layer |
| --- | --- |
| Lost state, stale environment, redundant reads, permission surprises | **Harness** |
| Claimed success contradicted by reality, runaway retries, noisy feedback | **Loop** |
| Wrong order, needless serialization, misrouting, unbounded cycles, cross-branch contamination | **Graph** |

"Improve the prompt" is the correct fix only when all three layers already hold and the residual failure is genuinely one of instruction clarity. It is the last resort, not the first.

## 6. Conformance Checklist

A project implements this architecture when all of the following hold:

- `doctor` exists and halts on drift.
- The sandbox boundary is declared, enforced, and protects the verifiers.
- Session state is persisted, gitignored, and checkpointed.
- The observation cache is active and measured.
- `verify` exists with ordered tiers, deterministic exits, bounded feedback, and budget caps.
- Fan-out scopes are independent, with declared joins.
- Every cycle is bounded, with an escalation edge.
- An independent adversarial gate precedes commit.
- Routing decisions are logged for replay.
