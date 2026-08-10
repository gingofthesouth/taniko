---
name: taniko-review-agent-work
description: Review work an agent claims to have done and correct it so the fix sticks — interrogate artifacts over narratives, watch for citation instead of confidence, and shape correction prompts with scope, ordering, and echo-back. Use when reading any agent's completion report or preparing a correction.
---

# Review agent work: artifacts over narratives

**The house rule, final form: the artifact is the authority; every summary
above it — the agent's, the reviewer's, the tool author's — is a place for
errors to live.**
*Earned: four successive accounts of one routing-log event, each one step
closer to the raw log, each correcting the last — the final truth (a
duplicate exit record on an escalation path) appeared in none of the
summaries, only in the log itself.*

## Reading a report

- **When any narrative disagrees with evidence, run the one cheap command
  before believing either.**
  *Earned: a client UI reported "+9,283" changed lines; `git diff --numstat`
  showed 156 real insertions.*
- **The maturity signal in an agent report is citation of artifacts, not
  confidence of prose.** A report that names files, seq numbers, and counts
  can be checked; a confident paragraph cannot.
  *Earned: an agent's claim that "provisioning was tightened" took a human
  grep to confirm it actually meant "provisioned" (it did — but the report
  couldn't say so).*
- **A corrected diagnosis is still a narrative.** Require the agent to
  re-verify any diagnosis against the artifact before implementing it.
  *Earned: an agent fixing a log bug implemented the corrected diagnosis
  without re-reading the log — it swapped narratives on command.*
- **Structures must be derived from source files, never from memory of
  them.** Mirror the source faithfully; complain precisely where it seems
  wrong.
  *Earned: an agent planned a type from memory of a schema and got field
  names and structure wrong.*

## Correcting the work

Correction prompts have a shape; each element was earned:

1. **Open with the approval scope** ("the structure is approved — do not
   restructure") to prevent rewrite spirals.
2. **Blocking items first**, cosmetics last.
3. **Explain each fix's downstream consumer** — why it matters, not just
   what to change. Agents apply "what" mechanically; "why" survives contact
   with the codebase.
4. **Require the agent to echo the fix list back** before resuming work.

## Process fences

- **One session per phase.** A fresh context whose prompt contains only that
  phase; the durable stop is a context that physically does not contain the
  next phase. Tell the agent: "your to-do list contains only this phase's
  items."
  *Earned: a to-do-driven agent blew through explicit "stop here"
  instructions twice.*
- **Commit at every phase boundary on a feature branch; push early.** An
  agent environment without push credentials is a feature — it cannot ship
  unreviewed work.
  *Earned: an agent built checkpoint machinery on a completely uncommitted
  tree.*
- **Plan mode only when there are open decisions.** Judge a plan by whether
  it adds specifics beneath the prompt, never alternatives to it — planning
  over settled architecture just invites relitigating it.
