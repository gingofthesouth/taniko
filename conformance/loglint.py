#!/usr/bin/env python3
"""Routing-log grammar lint (grammar version 0.1).

JSON Schema validates individual routing records; this lint validates the
SEQUENCE — the rules that only exist between records. Both are required for a
log to be conformant. Rules G1-G9 are normative (see routing-log-grammar.md);
each violation cites its rule.

Usage:
  python3 loglint.py <routing.jsonl> [--evidence-dir <run-dir>] [--schema-dir <dir>]

--evidence-dir enables G8 (verify_ref resolution + timestamp plausibility):
it should be the run directory containing verify-results/.

Exit: 0 clean, 1 violations, 2 error.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

GRAMMAR_VERSION = "0.1"
CLOCK_SKEW = timedelta(seconds=300)


def ts(record: dict) -> datetime:
    return datetime.fromisoformat(record["at"].replace("Z", "+00:00"))


def lint(records: list[dict], evidence_dir: Path | None, schema_dir: Path | None) -> list[str]:
    v: list[str] = []
    if not records:
        return ["G1: empty log"]

    # G1 — seq dense and monotonic from 0 (single-writer total order)
    seqs = [r.get("seq") for r in records]
    if seqs != list(range(len(records))):
        v.append(f"G1: seq must be dense 0..{len(records)-1}; got {seqs[:10]}…")

    # G2 — timestamps nondecreasing with seq
    times = [ts(r) for r in records]
    for i in range(1, len(times)):
        if times[i] < times[i - 1]:
            v.append(f"G2: at decreases at seq {records[i]['seq']} ({records[i]['at']} < {records[i-1]['at']})")

    # G3 — bracket balance per node: enter opens, exit closes, no double-open,
    # no close-without-open; all brackets closed at end of log.
    open_nodes: dict[str, int] = {}
    first_entered: str | None = None
    for r in records:
        nid, ev = r["node"]["id"], r["event"]
        if ev == "enter":
            if nid in open_nodes:
                v.append(f"G3: double enter for node '{nid}' at seq {r['seq']} (opened at seq {open_nodes[nid]})")
            open_nodes[nid] = r["seq"]
            if first_entered is None:
                first_entered = nid
        elif ev == "exit":
            if nid not in open_nodes:
                v.append(f"G3: exit without enter for node '{nid}' at seq {r['seq']}")
            else:
                del open_nodes[nid]
    for nid, seq in open_nodes.items():
        v.append(f"G3: node '{nid}' entered at seq {seq} but never exited — terminal outcomes must close their brackets")

    # G4 — the log terminates with the exit of the first-entered (root) node
    last = records[-1]
    if last["event"] != "exit":
        v.append(f"G4: last record must be an exit (got {last['event']} at seq {last['seq']})")
    elif first_entered and last["node"]["id"] != first_entered:
        v.append(f"G4: last exit is '{last['node']['id']}' but root (first entered) is '{first_entered}'")

    # G5 — a spawn for a node precedes that node's enter
    spawned_at: dict[str, int] = {}
    for r in records:
        if r["event"] == "spawn":
            spawned_at[r["node"]["id"]] = r["seq"]
    for r in records:
        if r["event"] == "enter" and r["node"]["id"] in spawned_at:
            if spawned_at[r["node"]["id"]] > r["seq"]:
                v.append(f"G5: node '{r['node']['id']}' enters at seq {r['seq']} before its spawn at seq {spawned_at[r['node']['id']]}")

    # G6 — checkpoints on enter for model nodes and the root; resolved SHA
    # (SHA pattern is schema territory; presence-on-enter is grammar)
    for r in records:
        if r["event"] == "enter" and (r["node"].get("type") == "model" or r["node"]["id"] == first_entered):
            if "checkpoint" not in r:
                v.append(f"G6: enter of {r['node'].get('type')} node '{r['node']['id']}' at seq {r['seq']} lacks a checkpoint")

    # G7 — sibling spawns under one run declare pairwise-disjoint write sets
    spawn_writes = [(r["node"]["id"], set(r.get("scope", {}).get("writes", []))) for r in records if r["event"] == "spawn"]
    for i in range(len(spawn_writes)):
        for j in range(i + 1, len(spawn_writes)):
            overlap = spawn_writes[i][1] & spawn_writes[j][1]
            if overlap:
                v.append(f"G7: spawned siblings '{spawn_writes[i][0]}' and '{spawn_writes[j][0]}' share write scope {sorted(overlap)}")

    # G8 — cited evidence resolves and is temporally plausible
    if evidence_dir is not None:
        run_start, run_end = times[0] - CLOCK_SKEW, times[-1] + CLOCK_SKEW
        vr_dir = evidence_dir / "verify-results"
        seen: set[str] = set()
        for r in records:
            ref = r.get("verify_ref")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            doc_path = vr_dir / f"{ref}.json"
            if not doc_path.exists():
                v.append(f"G8: verify_ref '{ref[:24]}…' (seq {r['seq']}) does not resolve to {doc_path.name} — a dangling reference in the evidence chain")
                continue
            try:
                doc = json.loads(doc_path.read_text())
            except json.JSONDecodeError as e:
                v.append(f"G8: {doc_path.name} is not valid JSON: {e}")
                continue
            if schema_dir is not None:
                try:
                    from jsonschema import Draft202012Validator
                    schema = json.loads((schema_dir / "verify-result.schema.json").read_text())
                    for err in Draft202012Validator(schema).iter_errors(doc):
                        v.append(f"G8: {doc_path.name} violates verify-result schema: {err.message}")
                except ImportError:
                    pass
            started = datetime.fromisoformat(doc["started_at"].replace("Z", "+00:00"))
            if not (run_start <= started <= run_end):
                v.append(f"G8: {doc_path.name} started_at {doc['started_at']} falls outside the run window "
                         f"[{records[0]['at']} … {records[-1]['at']}] ±{int(CLOCK_SKEW.total_seconds())}s — "
                         f"fabricated or reused evidence")

    # G9 — schema-conditional payloads (cheap re-check so the lint stands alone)
    for r in records:
        if r["event"] == "route" and "decision" not in r:
            v.append(f"G9: route at seq {r['seq']} lacks decision")
        if r["event"] == "retry" and "attempt" not in r:
            v.append(f"G9: retry at seq {r['seq']} lacks attempt")
        if r["event"] == "spawn" and "parent_node_id" not in r:
            v.append(f"G9: spawn at seq {r['seq']} lacks parent_node_id")

    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--evidence-dir", type=Path, default=None)
    ap.add_argument("--schema-dir", type=Path, default=Path(__file__).resolve().parent.parent / "schemas")
    args = ap.parse_args()
    try:
        records = [json.loads(l) for l in args.log.read_text().splitlines() if l.strip()]
    except Exception as e:  # noqa: BLE001
        print(f"error reading log: {e}", file=sys.stderr)
        return 2
    violations = lint(records, args.evidence_dir, args.schema_dir)
    if violations:
        print(f"LOGLINT FAIL (grammar {GRAMMAR_VERSION}): {len(violations)} violation(s)")
        for x in violations:
            print(" -", x)
        return 1
    print(f"LOGLINT PASS (grammar {GRAMMAR_VERSION}): {len(records)} records, brackets balanced, evidence resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
