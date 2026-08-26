# Evidence Directory Layout (informative)

This document records where a graph run keeps its evidence files on disk. It is *informative*, not contractual: a recommended convention rather than an enforced schema.

The first graph-layer implementation converged on this layout; any adapter would otherwise reinvent it differently. A conformance check may follow once a second implementation exists.

## The layout

```
<state-dir>/graph/<run-id>/
├── routing.jsonl            # append-only routing log (schema + grammar conformant)
├── state.json               # orchestrator run state (engine-owned, unschematized)
├── verify-results/          # every verify-result cited by any verify_ref, as <ref>.json
├── <node-id>/
│   ├── prompt.txt           # the rendered prompt the node ran with
│   ├── progress.json        # node-scoped progress (schema-conformant, node_id set)
│   └── verify/              # node-local copies of its verify evidence
├── escalation-<node>.json   # on budget exhaustion (shape unschematized until v0.5)
├── verifier-failure.json    # on adversarial-gate trip (ditto)
└── worktrees/               # live only while the run exists; reaped by clean
```

## The principles behind it

- `verify-results/` is the resolution root for grammar rule G8: every cited evidence reference must exist there.
- Logs and reports are **evidence** and survive `clean`; worktrees and branches are **state** and are reaped.
- Preserving a failed verifier's worktree (pointed to by its report) is what made this layout's biggest catch possible: a reviewer ran one git command in a preserved worktree and found that no content had ever flowed through the pipeline.
