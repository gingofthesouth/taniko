#!/usr/bin/env python3
"""Self-test: prove the suite passes a conforming harness and catches broken ones.

Fixtures (built in a temp dir from reference-adapter/):
  clean            — expect CONFORMANT, zero FAILs
  broken-state     — state dir not gitignored          → state-gitignored FAIL
  broken-gate      — verify exits 0 on broken code     → fail-on-broken-code FAIL
  broken-profile   — quick verdict claims profile=full → profile-separation FAIL

Also validates the suite's own --json output against conformance-report.schema.json.
Exit 0 only if every expectation holds — the suite eats its own evidence rule.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE / "reference-adapter"


def build_fixture(dest: Path, variant: str) -> None:
    shutil.copytree(REF, dest)
    if variant == "broken-state":
        (dest / ".gitignore").write_text("__pycache__/\n")   # .agent/ no longer ignored
    if variant == "broken-gate":
        harness = dest / "bin" / "harness"
        text = harness.read_text().replace(
            'if outcome["verdict"] != "pass":',
            'if False and outcome["verdict"] != "pass":')     # the gate stops gating
        harness.write_text(text)
    if variant == "broken-profile":
        harness = dest / "bin" / "harness"
        text = harness.read_text().replace(
            '"verdict": verdict, "profile": profile,',
            '"verdict": verdict, "profile": "full",')          # quick masquerades as full
        harness.write_text(text)
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
        subprocess.run(cmd, cwd=dest, check=True, capture_output=True)


def run_suite(repo: Path, as_json: bool = False) -> tuple[int, str]:
    argv = [sys.executable, str(HERE / "run.py"), "--repo", str(repo),
            "--tiers", "static,behavioral,destructive"]
    if as_json:
        argv.append("--json")
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def statuses(report_json: str) -> dict[str, str]:
    return {c["id"]: c["status"] for c in json.loads(report_json)["checks"]}


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 1. Clean fixture: fully conformant, and its JSON report conforms too.
        clean = tmp / "clean"
        build_fixture(clean, "clean")
        code, out = run_suite(clean, as_json=True)
        report = json.loads(out)
        if code != 0:
            failures.append(f"clean fixture: expected exit 0, got {code}")
        bad = [c for c in report["checks"] if c["status"] == "fail"]
        if bad:
            failures.append(f"clean fixture FAILs: {[c['id'] for c in bad]}")
        try:
            from jsonschema import Draft202012Validator
            schema = json.loads((HERE / "conformance-report.schema.json").read_text())
            errs = list(Draft202012Validator(schema).iter_errors(report))
            if errs:
                failures.append(f"suite --json violates its own schema: {errs[0].message}")
        except ImportError:
            pass
        print(f"clean:          exit {code}, "
              f"{report['summary']['pass']}p/{report['summary']['fail']}f/"
              f"{report['summary']['warn']}w/{report['summary']['skip']}s")

        # 2. Broken variants: each must be caught by its specific check.
        expectations = {
            "broken-state": "state-gitignored",
            "broken-gate": "fail-on-broken-code",
            "broken-profile": "profile-separation",
        }
        for variant, check_id in expectations.items():
            repo = tmp / variant
            build_fixture(repo, variant)
            code, out = run_suite(repo, as_json=True)
            st = statuses(out)
            caught = st.get(check_id) == "fail"
            print(f"{variant + ':':<15} exit {code}, {check_id} → {st.get(check_id)}")
            if code == 0:
                failures.append(f"{variant}: suite exited 0 — violation not reflected in exit code")
            if not caught:
                failures.append(f"{variant}: expected {check_id}=fail, got {st.get(check_id)}")

    if failures:
        print("\nSELFTEST: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("\nSELFTEST: PASS — conforming harness passes, each violation is caught by its specific check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
