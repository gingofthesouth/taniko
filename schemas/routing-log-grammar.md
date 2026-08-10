# Routing-Log Grammar (version 0.1)

JSON Schema validates routing records individually; it cannot express the rules that exist *between* records. Real implementations proved this gap exploitable: logs with perfectly valid records told false histories (open brackets on failure, success narratives for failed runs) and cited fabricated evidence. This grammar is the sequence-level contract, and `conformance/loglint.py` is its executable form — a log is conformant only when every record passes the schema AND the whole log passes the lint.

**G1 — Total order.** `seq` is dense and monotonic from 0. One writer assigns it; parallel node events interleave but never collide.

**G2 — Time flows forward.** `at` is nondecreasing with `seq`.

**G3 — Brackets balance.** Every `enter` has a later `exit` for the same node id; no exit without enter; no re-enter while open. This holds for *terminal failures too*: a node that fails still closes its bracket (`fail`, then `exit` with the failure detail). An unclosed bracket is indistinguishable from a crashed, truncated log — which is exactly why the rule exists.

**G4 — Runs conclude.** The final record is the `exit` of the first-entered (root) node, success or failure. "The log just stops" is not an outcome.

**G5 — Spawn precedes entry.** A spawned node's `enter` follows its `spawn`.

**G6 — Restore points at entry.** Model-node and root enters carry a `checkpoint` (whose `git_ref` the record schema now constrains to a resolved SHA).

**G7 — Fan-out independence.** Sibling `spawn` records under one run declare pairwise-disjoint `scope.writes`. This makes the graph layer's core correctness property auditable from the log alone.

**G8 — Evidence resolves and is plausible** (requires the run's evidence directory). Every `verify_ref` resolves to a verify-result document that parses, validates, and whose `started_at` falls within the run's time window (±300s skew). This is the anti-fabrication rule: a document claiming a midnight-January-1st verify inside an August run is caught here, not by `format: date-time`.

**G9 — Conditional payloads.** `route` carries `decision`, `retry` carries `attempt`, `spawn` carries `parent_node_id` (re-checked so the lint stands alone).

Advisory (not yet linted): terminal failure output should print run id, routing-log path, and report paths — provenance that prevented becoming lore only after its absence caused an evidence mix-up in live review; `failure_kind` should be set on fail/escalate events; `merge` should be structured rather than smuggled through `detail`.

The reference fixture (`conformance/fixtures/finds-bug-run/`) is a real production log: a two-node fan-out whose adversarial verifier found a planted bug — the gate working, recorded honestly.
