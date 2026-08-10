# Adopting Tāniko

This directory is the adoption kit: everything a project needs to implement
the three-layer agent architecture — Harness, Loop, Graph — against the
Tāniko contracts, using its own coding agent to do the building.

## The model

**Your agent builds. The suite judges. You greenlight.** You issue the
prompts below to your own agent, in your own repository; the Tāniko
conformance suite and routing-log lint judge what it built, behaviorally,
with exit codes; and every phase ends in a commit plus a full stop for a
human read of the pasted evidence. No phase proceeds on an agent's say-so.

Tāniko ships a **specification and a judge, not an engine**: the contracts
([CONTRACTS.md](../CONTRACTS.md)) state what any conforming implementation
must do, the schemas ([schemas/](../schemas/)) define the evidence documents
it must produce, and the conformance suite
([conformance/](../conformance/README.md)) tests that it actually behaves
that way. Adopters build their own orchestrator against the contracts. A
reference orchestrator is deliberately deferred until multiple adopter
implementations exist — the same rule of three the contracts apply to every
other generalisation, applied to ourselves.

## Consuming the suite: the pinned outside clone

Adopting repositories carry a `TANIKO_VERSION` file at their root containing
exactly the Tāniko tag they build against. The suite is cloned **outside**
the repository, at exactly that tag:

```sh
git clone --depth 1 --branch "$(cat TANIKO_VERSION)" <taniko-remote-url> ../taniko
```

CI performs the same clone. The suite is never vendored into the repo and
never placed inside the agent's sandbox: an agent must not be able to edit
the suite that judges it. Upgrading Tāniko is a deliberate act — change
`TANIKO_VERSION`, re-run conformance, commit the pair together.

## The sequence

Four prompts in [prompts/](prompts/), issued in order. Every phase of every
prompt ends with gate output pasted, not described, and a full stop for
human greenlight.

| Prompt | Builds | Exit gate |
|---|---|---|
| [1-implement-harness-and-loop](prompts/1-implement-harness-and-loop.md) | harness declaration, doctor, verify, tamper isolation | conformance suite, static + behavioral (+ destructive where a probe is declared) |
| [2a-graph-foundations](prompts/2a-graph-foundations.md) | routing log, worktree-isolated nodes, checkpoints, provisioned skeletons, retry budgets, escalation reports | unit tests + a stub-runner single-node run whose log passes the lint |
| [2b-graph-gates](prompts/2b-graph-gates.md) | all-of joins with content assertions, adversarial verifier, red→green enforcement, clean-with-retention, run self-lint | stub two-node fan-out; lint with evidence resolution; layout check; zero leaked run dirs |
| [3-first-real-run](prompts/3-first-real-run.md) | one real bug through the machinery | eight-item pre-flight, the full validate-run ritual, human lands the result |

Prompts 2a and 2b are **phase-gated for re-issue across sessions**: one
session per phase, each session told only which phase it is executing. This
is a hard-won rule, not a style preference — see the re-issue header at the
top of each.

## The skills

Five review rituals distilled from the first implementation's incident
history; every rule in them carries the incident that earned it. They are
tool-agnostic Markdown with YAML frontmatter.

| Skill | Use it when |
|---|---|
| [taniko-validate-run](skills/taniko-validate-run/SKILL.md) | a run, node, or phase claims completion — the seven-step evidence ritual |
| [taniko-review-agent-work](skills/taniko-review-agent-work/SKILL.md) | reading any agent's report or shaping a correction prompt |
| [taniko-red-green](skills/taniko-red-green/SKILL.md) | planning or judging any change that claims test coverage |
| [taniko-protect-gates](skills/taniko-protect-gates/SKILL.md) | after installing; and whenever gates, verifiers, or settings change |
| [taniko-debug-verify-failure](skills/taniko-debug-verify-failure/SKILL.md) | a verify, node, or run fails or times out |

Install them with [install-skills.sh](install-skills.sh):

```sh
adoption/install-skills.sh --tool claude --target /path/to/your/repo
adoption/install-skills.sh --tool all              # every tool, current dir
adoption/install-skills.sh --tool claude --user    # your ~/.claude/skills
```

| Tool | Files land in |
|---|---|
| claude | `.claude/skills/<name>/SKILL.md` (repo) or `~/.claude/skills/` (`--user`) |
| copilot | `.github/instructions/<name>.instructions.md` |
| codex / opencode | `.agents/skills/<name>.md`, indexed in `AGENTS.md` between marker comments |
| cursor | `.cursor/rules/<name>.mdc` |

The installer is idempotent — re-run it to refresh; the `AGENTS.md` index is
rewritten between its markers and everything else is left untouched. After
installing, run the **taniko-protect-gates** checklist to finish deny-rule
setup — installation puts the skills in place, but tamper isolation is only
real once your agent CLI's permission layer enforces it.

## Cost expectations

Measured on the first adapter, for calibration, not as benchmarks: a trivial
headless agent node cost ~10 AI credits (9.73 credits, 9 seconds, ~47k
tokens of always-on context); a real producer session ran ~8.5 minutes —
budget a meaningful multiple per real node. Warm full verification was ~80
seconds and a cached verdict replay under 1 second, which is why the verify
cache is called the highest-value cache in the architecture. Use your CLI's
credit-cap flag (e.g. a `--max-ai-credits`-style option) wherever the tool
has one, and wire it to your plan budgets.

## What to send back

Every prompt requires strain notes (`docs/taniko/STRAIN.md` in your repo):
**Needed / Offered / Implemented** per friction point, with
`file-against-taniko` markers where the delta implies a spec change. These
findings are the fuel for the next revision — Tāniko's docket is
deliberately frozen until real adopter runs produce evidence
([docs/HISTORY.md](../docs/HISTORY.md) §8). An empty strain file is treated
as "didn't look".
