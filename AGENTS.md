# Tāniko — agent instructions

Run `bin/harness doctor` before any work; halt on drift. A change is done
when `bin/harness verify` prints VERDICT: PASS — paste the output, never
describe it. The artifact is the authority: cite files, seq numbers, and
gate output, not summaries.

Never edit `.claude/**`, `schemas/*.schema.json`, `conformance/**`, or
`.github/**` — the gates may not be edited by the agent they gate.
`conformance/fixtures/finds-bug-run/` is immutable anonymized production
evidence. Schema and check changes are frozen pending real-world strain
evidence (docs/HISTORY.md §8); record friction as strain notes instead.
Never introduce origin-project identifiers, in any form.
