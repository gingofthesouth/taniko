---
name: taniko-protect-gates
description: Set up and defend tamper isolation — protected globs enforced outside the model, bypass seams gated at operator level and visible in evidence, state gitignored, tests fenced off real repos. Run after installing the Tāniko skills to finish deny-rule setup, and whenever gates or verifiers change.
---

# Protect the gates from the agent they gate

**An agent that can edit its own exam will, under optimization pressure,
eventually do so.** Rules enforced by prose get skipped; rules enforced by
mechanism don't. Everything below converts a prose rule into a mechanism.
*Earned: an agent granted itself the protected-write override flag four or
more times in one project's history.*

## 1. Declare and enforce the boundary

In the harness declaration (`.claude/harness.json` or equivalent), list as
`protected`: the verifier scripts, test configuration, CI workflows, hook
scripts, and **the declaration itself** — budgets and tiers are part of the
exam. Then enforce the list *outside the model*, in whatever your platform
provides:

- an agent CLI permission layer (e.g. deny rules for Write/Edit on each
  protected glob in the tool's settings file);
- pre-tool hooks that reject writes into protected paths;
- filesystem permissions or OS sandboxing where available.

Cross-check that the declaration is covered by its own protected globs, and
that every protected glob has a corresponding deny rule. The Tāniko
conformance suite's static tier checks both; run it after any change to
gates, settings, or the declaration.

## 2. Gate the bypass seams at operator level

Every escape hatch — a protected-write override flag, a demo/stub verify
mode, a cache-bypass variable — must require configuration the agent cannot
reach (operator-level config, environment outside the sandbox), and every
seam must be visible in the evidence it produces: a verify document declares
its `mode` (real/demo/stub) and the tiers its profile actually ran; a cached
verdict declares `replayed`. A non-real document never satisfies
done-evidence, whatever its verdict.
*Earned: a stub verifier emitted profile "full" with two static stages, a
2 ms duration, and a fabricated start date — and was schema-valid
throughout. Nothing in the document admitted it was a stub.*

## 3. Keep state out of the repository

The session state directory (progress, caches, checkpoints) is gitignored —
committing it causes merge conflicts and cross-branch state leakage. The
conformance suite verifies this statically.

## 4. Fence the test machinery off the real repository

Any test that exercises worktree, branch, or cleanup machinery must refuse
to operate on a repository that lacks an explicit fixture marker file, and a
full test run must create zero new run directories in the real repo — make
that an acceptance check, not a hope.
*Earned: graph tests exercising worktree and branch deletion ran against the
developer's actual checkout and left ~30 stale run directories behind.*

## Checklist

- [ ] Protected globs declared, including the declaration itself
- [ ] A deny rule (or hook) exists for every protected glob
- [ ] Override/demo/stub seams need operator-level config, and self-identify
      in their evidence
- [ ] State dir gitignored
- [ ] Destructive tests require a fixture marker; zero-debris check exists
- [ ] Conformance suite static tier passes after the change
