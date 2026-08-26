# Reference adapter — agent instructions

1. A task is not done until `bin/harness verify` exits 0 with `VERDICT: PASS`. Cite that output when claiming completion.
2. Never edit `.claude/`, `bin/`, or `tests/` — these directories gate your work. They are declared `protected` in `.claude/harness.json`.
