#!/usr/bin/env python3
"""Run the conformance suite against a repo.

Usage:
  python3 run.py --repo /path/to/repo [--declaration .claude/harness.json]
                 [--tiers static,behavioral,destructive] [--json]

Exit codes: 0 = no failures, 1 = at least one FAIL, 2 = suite error.
Destructive checks corrupt-and-restore the declared probe file; they refuse to
run on a dirty tree and are excluded unless requested.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--declaration", default=".claude/harness.json")
    ap.add_argument("--tiers", default="static,behavioral")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    tiers = {x.strip() for x in args.tiers.split(",") if x.strip()}
    unknown = tiers - {"static", "behavioral", "destructive"}
    if unknown:
        print(f"unknown tiers: {sorted(unknown)}", file=sys.stderr)
        return 2
    if not args.repo.is_dir():
        print(f"not a directory: {args.repo}", file=sys.stderr)
        return 2

    try:
        results = checks.run_all(args.repo, args.declaration, tiers)
    except Exception as e:  # noqa: BLE001
        print(f"suite error: {e}", file=sys.stderr)
        return 2

    summary = {s: sum(1 for r in results if r.status == s) for s in ("PASS", "FAIL", "WARN", "SKIP")}

    if args.as_json:
        report = {
            "schema_version": "0.1.0",
            "target": str(args.repo.resolve()),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "tiers_run": sorted(tiers),
            "summary": {k.lower(): v for k, v in summary.items()},
            "checks": [
                {"id": r.check_id, "layer": r.layer, "tier": r.tier,
                 "contract_ref": r.contract_ref, "status": r.status.lower(),
                 "detail": r.detail[:500], "duration_ms": r.duration_ms}
                for r in results
            ],
        }
        print(json.dumps(report, indent=2))
    else:
        print(f"conformance: {args.repo.resolve().name}  tiers={','.join(sorted(tiers))}")
        for r in results:
            print(" ", r.line())
        print(f"  ── {summary['PASS']} pass, {summary['FAIL']} fail, "
              f"{summary['WARN']} warn, {summary['SKIP']} skip")
        if summary["FAIL"]:
            print("  VERDICT: NONCONFORMANT")
        elif summary["WARN"]:
            print("  VERDICT: CONFORMANT (with warnings)")
        else:
            print("  VERDICT: CONFORMANT")

    return 1 if summary["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
