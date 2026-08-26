---
name: taniko-red-green
description: Enforceable test-first for agent-produced changes — the evidence chain must contain a failing verify that cites the new test before the passing one, tests count only when executed, and the test surface is provisioned as producer work. Use when planning or judging any change that claims test coverage.
---

# Red→green: the enforceable form of "test first"

"Write the test first" as prompt prose gets skipped. The enforceable form is
evidential: **the run's evidence chain must contain a failing verify citing
the new test, followed by the passing one.** The fail proves the test bites;
without it, a passing test proves only that it passes — possibly vacuously.
*Earned: told plainly to do red→green, a producer skipped the failing-test
step entirely; the durable fix is an orchestrator that checks for the
fail-then-pass pair of verify documents itself.*

## The three rules

**1. Tests are evidence only when they run.**
Completion reports cite executed tests — present in the verify counts —
never merely created files. The proof of an added test is the denominator
delta (unit count 822 → 825), and the failing-then-passing pair around it.
A created-but-never-executed test file is dead code wearing a test's name.

**2. The evidence surface is provisioned by the producer, at plan time.**
A verification gate can only assert against seams that exist: test files,
their build-target membership, assertable structure in the code under test.
Creating those seams is producer work, declared in the producer's write
scope — a plan whose producer touches source without including (or creating)
its test surface is invalid before it runs. A gate forced to improvise its
evidence surface has exactly two outcomes, both failures: it violates its
write scope, or it produces evidence that exists but never executes.
*Earned: smoke-test targets were picked twice *because* they lacked tests —
and the verifier, write-scoped to the test directory, could not add files to
the build target; its only options were violating scope or a dead-code test.*

**3. Provide the shape; never describe it.**
Scaffolds (test files, progress skeletons) are created ahead of the run in
the right place — name AND folder, per whatever mirror convention maps code
to tests — or file creation is placed explicitly in the producer's scope.
Prompts say "update the provided file", not "create a file that looks like".
*Earned twice: a pre-flight halt caught a scaffold in the wrong folder (the
mirror convention covers name and folder); and a producer improvised its
progress file from the wrong one of two coexisting conventions — providing a
schema-conforming skeleton fixed what prose descriptions had failed to.*

## The verifier's side

The adversarial verifier is separately scoped (test directories only),
carries a bounded attempt budget, and must show its added tests in the
executed counts. Its independence is the point: it must not share context,
incentives, or authorship with the producer whose work it gates.

## Judging a claimed red→green

Look for, in order: (1) a verify document with verdict `fail` whose feedback
cites the new test by name; (2) a later verify document with verdict `pass`
whose counts include it; (3) both documents `mode: real` with plausible
timestamps inside the run window. If the fail is missing, the test never
bit — send it back.
