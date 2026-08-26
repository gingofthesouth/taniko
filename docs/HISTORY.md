# Project History — Three-Layer Agent Architecture (Harness / Loop / Graph)

This document is the project's decision record: what was built, what was decided and why, what went wrong, what was learned, and what remains. It was written as orientation for anyone joining the project — human or AI agent — and covers the period up to 9 August 2026, when the first phase of the project closed.

> Historical record: sections below describe the project as it stood on the dates written. Current behaviour is defined by [CONTRACTS.md](../CONTRACTS.md), not by this document. Specialised terms are defined in the [glossary](GLOSSARY.md).

> Note: when this record was moved into the Tāniko repository, references identifying the origin project — its name, organisation, ticket numbers, and internal type names — were replaced with generic equivalents, and the text was rewritten for clarity. The facts, decisions, and lessons are unchanged from the original record.

A few terms used throughout:

- An **adapter** is a project-specific implementation of the generic layer contracts.
- A **strain finding** is a mismatch discovered by testing the generic schemas against real code. Recording and resolving these mismatches is how every schema version was produced.
- A **producer** is a graph node that writes code; a **verifier** is an adversarial node that gates the producer's work; the **runner** is the script that launches an agent session for a node.
- **Red→green** means writing a failing test first, then making it pass — proof that the test actually tests the change.
- A **verdict cache** stores the result of a verification run keyed by a hash of the source tree, so verifying an unchanged tree is instant.

## 1. The two codebases

**Tāniko, the generic repository** (v0.4.0, called "agent-layers" before the name was chosen). It contains: the layer contracts (CONTRACTS.md), including clauses added in response to real incidents; six JSON Schemas versioned together as a set (harness-declaration, doctor-report, progress, tool-cache, verify-result, routing-record) with examples and a validation script; a conformance suite (run.py and checks.py, with static, behavioral, and destructive tiers) that includes a ~250-line reference adapter serving as both test fixture and specification-by-example, plus a self-test; a routing-log grammar (rules G1–G9) with an executable lint (loglint.py), validated against a real production log kept as a fixture; a document describing the evidence directory layout; and the disposition of all eleven strain findings from the graph build (RESOLUTIONS-0.4.0.md) alongside the original strain report (STRAIN-REPORT.md).

**The origin app** — an iOS application of roughly 94,000 lines of code, the first real adapter and the source of every schema revision. It has two parts:

- A command-line harness (`bin/harness`, a Swift Package Manager CLI) providing doctor, lint, build, test, and verify commands. Verification runs in tiers ordered by cost and fails fast; feedback to the agent is trimmed to character budgets; verdicts are cached against a hash of the source tree; results are available as JSON; attempts are tracked; and a guard blocks writes to protected files.
- A graph layer, built 8–9 August 2026 on a pair of stacked feature branches (`feature/TICKET-314-Agent-Harness`, then `feature/TICKET-314-Graph-Layer`). It runs work as nodes in isolated git worktrees with enforced write scopes; gives each node a retry budget that ends in an escalation report; joins parallel branches with real merges; places an adversarial verifier gate, with no bypass, before anything lands; holds a lock per run; cleans up idempotently with a retention policy; supports replay and status inspection; and writes an append-only JSONL routing log that conforms to the schema and the grammar.

Agent instructions live in a single canonical AGENTS.md (CLAUDE.md is a symlink to it, and a pointer file exists for Copilot), with reusable skills and deep-dive documentation alongside.

**How the schema set reached 0.4.0.** Every version was cut from real code straining the generic artifacts, never from theory:

- **0.1.0** — a clean-room draft derived only from the contracts.
- **0.2.0** — from mapping the origin app's existing harness onto the schemas. The verify-result schema became pipeline-scoped (one record per verification run, not per tier), and the mapping added verdict-cache replay, disclosure of flaky test retries, named verification profiles, a generalised doctor report, and a place to record learned facts.
- **0.3.0** — from building the conformance suite, which revealed that the harness declaration never said how to *invoke* the harness. The declaration gained a `commands` block.
- **0.4.0** — from the graph build's strain findings: git references constrained to resolved SHAs, defined attempt semantics, node roles, structured merge outcomes, machine-readable failure kinds, verify-result honesty fields (mode, profile tiers, stage selection), and the routing-log grammar with its lint.

## 2. Principles established

These extend the article that inspired the project; each was earned in practice.

- **Progress on evidence, not confidence.** The article's core idea, which we extended: evidence must also attest to its own completeness and provenance (real vs demo vs stub mode, declared tiers, honest timestamps), because a document can be schema-valid and still lie.
- **A passing verification is not proof that work was done.** The verdict cache legitimately replays a pass for an unchanged tree — so a node is only complete when the runner succeeded *and* progress is valid *and* verification passed, in that order. Runs that are supposed to produce content must also prove the integration branch moved past its base.
- **Verification gates need their evidence surface provisioned.** A gate can only assert against test files and structures that exist. Creating them is producer work, declared at planning time; a gate forced to improvise its own evidence surface must either violate its write scope or pass vacuously. Only executed tests count — they must appear in the verification counts. Red→green is the enforceable form of "test first."
- **Rules enforced by prose get skipped; rules enforced by mechanism don't.** Proven repeatedly (see §4). This applies to agents — a to-do-driven agent is blind to "stop" instructions — and to policy generally.
- **Caching verdicts matters more than caching file reads.** In build-and-test work, the expensive redundant observation is the 80-second verification run, not the 2,000-token file read — and client-native file reads can't be intercepted anyway. This inverts the article's emphasis, on evidence.
- **Verification tiers invoke adapter commands, never raw tools.** Anything dynamic (such as mapping changed files to targeted tests) lives behind the adapter's CLI; the declared command stays static.
- **Every failure has one home layer.** "Improve the prompt" is the last resort. Escalating instructions while ignoring an environment problem is the article's failure mode #3, and we nearly committed it twice.
- **Rule of three before generalising.** No shared engine, no adapter generator, and no schema for a shape with only one (possibly stale) sample. Explicitly deferred on these grounds: escalation-report and verifier-failure schemas (v0.5, pending samples), and plan topology (deliberately engine-owned).

## 3. Lessons learned the hard way

Each entry: what happened, then what changed because of it.

1. **The pipeline that carried nothing.** Five phases of orchestration ran "verified" while the pipeline had never carried any content: node edits were never committed onto node branches, merges were empty, and the verifier examined an empty diff — every verdict was green, because each was a cached replay of the unchanged base tree. A single git command run by a human in a preserved worktree exposed it. *Changed:* the contracts gained content assertions (a content-producing run must prove its branch moved); preserved failure worktrees are now treated as essential diagnostic material; and "green" is never accepted as "true" without reading the evidence.
2. **The demo verification that lied.** A stub verifier emitted `profile: "full"` with two static stages, a 2-millisecond duration, and a start date of 1 January 2026 — and was schema-valid throughout. *Changed:* verify-results must declare their mode (real, demo, or stub) and the tiers their profile actually ran; the grammar lint checks timestamp plausibility (rule G8); and the general rule was set that every seam — cache, stub, bypass flag — must be visible in the evidence it produces.
3. **The unrestorable checkpoint.** A checkpoint recorded its git reference as `"HEAD"` — meaningless the moment HEAD moves. The schema's unconstrained string type had allowed it. *Changed:* git references must match a resolved-SHA pattern, and a broader point was recognised: a schema too loose to catch a real bug is itself a strain finding.
4. **Logs that never closed.** Failed runs ended with unbalanced enter/exit records in the routing log, so cleanup refused to run, debris accumulated, and replay was ambiguous. *Changed:* terminal outcomes must close their brackets. This class of rule — sequencing — is exactly what JSON Schema cannot express, and is why the grammar layer exists.
5. **The wrong run's log.** A failed run printed no run id or log path, the reviewer picked up a different run's log, and nearly diagnosed fabricated evidence. *Changed:* failure output must print its provenance (run id, log path, report paths). This was promoted from a usability nicety to a near-contract requirement the day it caused a real mix-up.
6. **Tests that ran against the real repository.** Graph tests exercising worktree and branch deletion ran against the developer's actual checkout, leaving ~30 stale run directories and a test fixture behind. *Changed:* a structural guard — test helpers refuse to operate on any repository that lacks a fixture marker file — and an acceptance check that a full test run creates zero new run directories in the real repository.
7. **The client's counter was wrong.** Copilot's UI reported "+9,283" changed lines; `git diff --numstat` showed 156 real insertions. *Changed:* when a narrative (any UI, any report) disagrees with evidence, interrogate the evidence first — the one command is cheap.
8. **Types drifted from the schema.** An agent planned a RoutingRecord type from memory of the schema rather than from the schema file, and got field names and structure wrong. *Changed:* derive types from the file, never from memory of prose; mirror the source faithfully and complain precisely where it seems wrong.
9. **The prediction the measurement overturned.** The first architecture decision record predicted per-worktree build caches would win under parallel verification. Measurement said otherwise: a shared build slot with a lock finished in 105 seconds against 156 for per-worktree, because cold starts never amortised for the nodes measured (they edited documentation, not source). *Changed:* measure per project; re-measure when nodes start diverging in source; treat predictions as hypotheses and decision records as numbers.
10. **The untestable target, chosen twice.** Smoke-test targets were picked *because* they lacked tests — first a SwiftUI view with logic in its `body`, then a service — but a verifier whose write scope is limited to the test directory cannot add files to an Xcode target (that requires editing the project file). Its only options were violating scope or writing a dead-code test. *Changed:* the evidence-provisioning clause (§2); test-file scaffolds are created ahead of runs, or file creation is placed explicitly in the producer's scope.
11. **Pre-flight halts pay for themselves.** One launch was halted by a dirty tree, a misnamed scaffold, and debris from an abandoned approach; another because the runner script was still a stub. Both were caught by evidence-based halt rules with explicit "do not improvise" instructions. A helpful agent without those fences would have committed the mess and proceeded.
12. **Test the runner by itself first.** A 60-second hello-world run caught a path-handling bug in the runner script before a 15-minute graph run could bury it inside a confusing escalation. An earlier relative of this bug: failing to drain a subprocess's output pipes turned instant exits into 900-second timeouts. Drain stdout and stderr concurrently while waiting.

(Lessons 13–18, from the smoke campaign, are in §7.)

## 4. Process rules for agent-driven builds

All of these were learned, none are theoretical.

- **One session per phase.** Give each phase a fresh context whose prompt contains only that phase. An agent driven by a persistent to-do queue blew through "stop here" instructions twice; the fix that worked in the moment was making it delete its future to-dos and confirm, but the durable fix is a context that physically does not contain the next phase. Every phase prompt now includes: "your to-do list contains only this phase's items."
- **A fixed review ritual at every phase boundary:** diff against the true base with `--stat` (remembering that plain `git diff` hides untracked files); validate the routing log against both schema and lint; read the new strain notes for tone (specific mechanical friction is a good sign — emptiness or vagueness means the agent didn't look, not that the schemas are perfect); run one live command that exercises the claimed fix; and check that promised tests exist by name. Agents' green self-reports caught none of the four integrity holes found during the project; evidence reads caught all of them.
- **Correction prompts have a shape:** open with the approval scope ("do not restructure") to prevent rewrite spirals; put blocking items first; explain each fix's downstream consumer (why, not just what); and require the agent to echo the fix list back before resuming work.
- **Commit and push discipline:** commit at every phase boundary on a feature branch — one agent built checkpoint machinery on a completely uncommitted tree. Push early; the agent environment has no git credentials, which is a feature: it cannot push unreviewed work. Branches follow `feature/TICKET-*`; stacked branches merge in order.
- **Plan mode only when there are open decisions.** A fully specified prompt should run interactively — planning over settled architecture just invites relitigating it. Judge a plan by whether it adds specifics beneath the prompt, never alternatives to it.
- **The human's role:** machines verify claims against evidence; humans verify that the evidence measures the right thing. All four integrity holes were human catches, each via a single evidence-reading command.

## 5. Measured baselines

First real numbers, for calibration:

- Verification (warm): lint ~1 s, build ~8 s, targeted tests ~5–15 s, quick profile ~25 s, full profile ~80 s, cached replay < 1 s. A cold build is ~80 s.
- Build-cache layout under two-node parallel quick verification: shared slot with lock, 105 s total; hybrid, 106 s; per-worktree, 156 s. Cold starts dominated, and the measured nodes edited documentation only — re-measure when nodes diverge in source.
- Headless Copilot baseline: a trivial one-file task cost 9.73 AI credits, 9 seconds, and ~47,100 tokens of always-on context. A real producer node will be a meaningful multiple of this. The CLI's `--max-ai-credits` flag exists and should become the runner's cost cap; it is currently unused.
- Runner flags, settled: `-p`, `--allow-all-tools`, and `--no-ask-user` (headless nodes must never wait for a human); `--deny-tool='shell(git push)'` (nodes exit only through the orchestrator's merge); `--add-dir <run-dir>` (the progress file lives outside the worktree, and Copilot verifies write paths); `--log-dir` and `--share` pointed into the node's evidence directory; keep `tee` with `PIPESTATUS`.

## 6. Open backlog

**Origin-app tickets** (letter labels kept stable — other sections cite them):

- **(a) Plan validation: no source changes without the test directory.** When a producer's write scope touches app sources, the plan must also include the matching test directory. *Why:* a verification gate whose producer never touches tests must either violate its write scope or produce tests that never run. The existing changed-file-to-test mapper can be reused.
- **(b) A prompt template for creating new source files,** covering project-file edits in scope, the add-source-file skill, and its known Xcode project hazard. *Why:* adding a file to an Xcode target means editing the project file — a protected path — so the safe pattern must be spelled out, not improvised.
- **(c) A static verification tier for test mirrors:** changed files must have a matching test file or sit on an explicit exemption list. *Why:* catches untested changes before anything expensive runs.
- **(d) Orchestrator-checked red→green:** instead of trusting prompt prose, the orchestrator itself checks the evidence for a fail-then-pass pair of verification results around the new test. *Why:* told plainly to do red→green, run 5's producer skipped the failing-test step entirely (lesson 13).
- **(e) Bypass hardening.** The protected-write override flag — which an agent granted itself four or more times — and the demo-verify environment variables must require operator-level configuration an agent cannot reach. Nothing currently gates protected *commits* at all. *Why:* rules enforced by prose get skipped; seams must be unreachable and visible (see [taniko-protect-gates] principles).
- **(f) A secret-scanning static tier.**
- **(g) Submit the merge request after human branch review,** harness branch first.

**Generic repo, v0.5 candidates** — each with what it is and why it waits:

- **Schemas for escalation reports and verifier-failure reports.** These are the two documents a graph emits when a node runs out of budget or a gate trips; they currently have no defined shape. Deferred from 0.4.0 because the only samples predated the report-format fixes; run 5 has since produced post-fix samples, so they can now be written from evidence.
- **Runner transcripts in the evidence layout.** Keep what the runner printed inside the run's evidence directory, so post-mortems read one folder instead of reconstructing console history.
- **Cross-check a verify-result's declared profile against the declaration.** A result claims a profile (e.g. `quick`); its self-declared tier list should be validated against the tiers the harness declaration actually defines, so a partial run can never present itself as more than it was.
- **Name new tests and their author in the evidence.** Today, proof that added tests ran is only arithmetic on counts (822 → 825). Attribution would name the tests and the node that wrote them, so reviewers check named things rather than number drift.
- **Promote provenance-in-failure-output from advisory to linted.** Failures should be required to print their run id and log paths, not merely encouraged to.
- **Wire the grammar lint into the conformance suite's run command,** so `run.py` checks log sequence rules too, not just single records.
- **Per-node cost fields fed by the runner's cost cap,** so each node's spend is recorded evidence instead of an estimate after the fact.
- **Rewrite the prose `description` fields inside the six schemas for newcomer readability.** Deferred from the August 2026 documentation pass so normative artifacts change in their own reviewed commit — if this item is still open, resurface it before v0.5.
- **Template or example adapters per product type** — iOS app, web service, CLI tool, and so on — so users can start from something shaped like their project instead of tailoring from scratch. Decision recorded August 2026: there are too many variations to ship Tāniko itself as plugins or a stock harness; it stays a framework whose users tailor their harness, loop, and graph layers while enforcing what the contracts determine must hold — deterministic verification above all. If this item is still open, resurface it before v0.5.

**Still wanted from the origin app:** one real, full-pipeline `verify --json --no-cache` document and one cached-replay document — the pipeline-shaped verify-result introduced in 0.2.0 has never been validated against anything but demo runs.

**Housekeeping:** move the smoke-test script under the graph support directory; create the actual generic repository, name it, and give it CI running the validation script, the conformance self-test, and the lint against the log fixture. *(Done — this repository.)*

## 7. The smoke campaign (9 August 2026) and project close-out

The name was decided: **Tāniko** — te reo Māori for a finger-weaving technique that produces intricate geometric borders through precise, rule-based thread paths, chosen because the mapping is exact: graph topology, routing decisions, and verification gates at the borders of work. (Earlier candidates: Trellis, a Loom variant, Gantry, Chassis.) The ASCII slug `taniko` is used in repository and URN identifiers; the macron is used in prose.

**The chosen smoke test** was a real bug: a location-lookup method resolved records by id alone, so a sub-location could collide with a top-level location carrying the same id. The fix was to delete the method from its protocol and class and call the model's own absolute-location property at the single call site. The producer's job was red→green with an id-collision test; the verifier — write scope limited to the test directory, two attempts — was to add edge-case tests and show them in the verification counts.

**Six launches were attempted:**

1. Halted in pre-flight: dirty tree, a scaffold in the wrong folder (the test-mirror convention covers name *and* folder), and debris from an abandoned approach.
2. Halted in pre-flight: the runner script was still a stub.
3. Halted in pre-flight: the freshly wired runner script was uncommitted — worktrees are created from the resolved commit, so uncommitted infrastructure does not exist inside a run.
4. Ran. The producer genuinely did red→green (the failing-then-passing verification documents are in the worktree cache) but died on the progress-file contract; three secondary bugs were diagnosed from the routing log alone.
5. Ran. The producer merged real content — the first run ever to pass the content assertion. The adversarial verifier met a real diff for the first time and wrote three genuine edge-case tests (executed: the unit-test count went from 822 to 825). It then escalated on a timeout that turned out to be downstream of the real root cause (see lesson 13).
6. Never launched: the fix had already been reviewed and landed through normal channels, and the prompt's own pre-flight check (confirm the bug still exists) would have halted it. This was the correct outcome.

Four pre-flight catches, zero improvised workarounds, and one shipped bug fix that was adversarially tested by the machinery under test.

**Lessons 13–18,** continuing §3:

13. **Describing a file format in prose failed twice more; providing the file worked.** Run 4's producer improvised its progress file from the *other* progress convention in the repository (two formats coexisted, and instruction inheritance delivered the wrong one). The fix: the orchestrator now writes a schema-conforming skeleton before the run, and the prompt says "update the provided file" — provide the shape, never describe it. Run 5 then exposed the fix's scope bug: the verifier hadn't been provisioned, failed the same contract, and it was the *retry's* fresh session that hit the 900-second timeout — the headline failure was downstream of the real gap. In the same run the producer skipped the failing-test step entirely, so red→green as prompt prose also failed; orchestrator-checked fail-then-pass pairs (backlog item d) rose in priority with this as the citation.
14. **The lint caught what every summary missed — then the raw log corrected the lint's reader.** The lint's first live catch was a grammar violation in run 5's log that both the agent's report and human report-based grading had missed. The first lint-based diagnosis then got the mechanism wrong (it guessed a missing enter record); reading the raw log showed balanced brackets per attempt plus a duplicate exit record emitted only on the verifier's escalation path. Four accounts of the same event, each one step closer to the log, each correcting the last. House rule, final form: **the artifact is the authority; every summary above it — the agent's, the reviewer's, the tool author's — is a place for errors to live.**
15. **Check the artifact, not the code paths.** Both gaps in run 5 (the unprovisioned verifier, the duplicate exit record) escaped because log-writing correctness was tested per code path, and nobody had written tests for those paths. The fixes landed as structural invariants instead: the routing-log appender rejects a double close, and the orchestrator lints the completed log (bracket balance, terminal closure) before declaring a run finished. Artifact-level checks are path-independent — they catch the paths nobody thought to test.
16. **Honest tools state their denominators.** The lint printed "evidence resolves" while having checked zero evidence references — vacuously true, the same disease as the lying demo verification, committed by our own validator. For v0.5: outputs must carry counts ("3 resolved", not just "resolves"), and gate activity with zero evidence citations should warn.
17. **Warming caches is the orchestrator's job.** A cold build in a fresh worktree (~80 seconds) is deterministic work; it must never spend an agent session's timeout budget. The build now runs as ordinary pre-node work before every runner invocation, and timeouts are settable per plan (the verifier's is 1,800 seconds).
18. **Culture propagates more slowly than code.** The agent fixing the log bug implemented the corrected diagnosis without re-verifying it against the log — it swapped narratives on command. Separately, an agent's claim that "provisioning was tightened" took a human grep to confirm it actually meant "provisioned" (it did). The maturity signal to watch for in agent reports is citation of artifacts, not confidence of prose.

**The v0.5 docket** — recorded at project close-out (9 August 2026); every item traces to a run or commit:

| Item | What it means in practice | Earned from |
| --- | --- | --- |
| Add `progress_invalid` to the failure-kind enum | Tell "the progress file was missing" apart from "the progress file was malformed" instead of lumping both into one failure kind | The distinction proved useful during diagnosis |
| Align failure-kind spellings | One canonical spelling per kind; fixed in the origin app — the schema description should note it | Fixed in the origin app |
| Lint denominators and the zero-citations warning | Lint output must say what it actually checked ("3 of 3 refs resolved"), never a bare "resolves"; a gate citing zero evidence warns instead of passing | Lesson 16 — our own lint once printed "evidence resolves" having checked zero references |
| Persist verifier and node evidence independently of the runner's lifetime | A crash or timeout must not take the evidence with it — link the worktree-cache verification documents on every failure path | Partially fixed in the origin app; the schema and layout docs should state it |
| Runner transcripts in the evidence layout | Record the runner's console output inside the run's evidence directory | Post-mortems currently reconstruct console history by hand |
| Repository-relative paths in routing details | Log entries reference files relative to the repo root, so logs stay readable across machines | Replay ergonomics |
| Schemas for escalation reports and verifier failures | Define the two report documents emitted on budget exhaustion and gate trips | Run 5 finally produced post-fix samples |
| Name new tests and their author-node in verify counts | Proof that added tests ran is currently only a rising count (822 → 825); attribution names the tests and who wrote them | The count-delta weakness observed in run 5 |
| Wire the runner's cost-cap flag to plan budgets | Each node's spending limit becomes enforced configuration rather than an unused flag | Measured baseline §5 |

**v0.5 is held until a few real-ticket runs land** — the same evidence standard 0.4.0 was built to.

**Where the project stands** (close of 9 August 2026): The location-lookup fix is landed and pushed — a graph-produced, adversarially tested bug fix, shipped to the product. Still to verify: whether the verifier branch's three tests landed with it or need cherry-picking from run 5's verifier branch before that run is cleaned up. Remaining work: update and submit the merge request (its "no real agent sessions" caveat is now false in the best way); merge in order, harness branch then graph branch; clean up run 5; create the Tāniko repository from the 0.4.0 bundle *(done — this repository)*; then put real tickets through the graph. The first genuine two-producer fan-out is both the next validation and the point of the whole machine.
