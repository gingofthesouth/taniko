"""Conformance checks: does this repo's harness behave the way CONTRACTS.md says a harness must?

Three tiers, in increasing cost and risk:
  static      — inspect files; never execute the harness
  behavioral  — execute doctor/verify non-destructively
  destructive — deliberately corrupt the declared probe file, prove the loop
                catches it, restore (requires a clean git tree; opt-in)

Every check carries a contract_ref back to the clause it enforces. Statuses:
  PASS  the contract clause holds
  FAIL  the clause is violated
  WARN  advisory: legal but weaker than the contracts intend
  SKIP  not applicable / prerequisites absent (the reason says what's missing)
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
STDOUT_BUDGET = 8000          # chars: verify/doctor console output beyond this is context-hostile
REPLAY_FAST_SECONDS = 5.0     # a cached replay should come back within this
REPLAY_FAST_RATIO = 0.25      # ...or at least this fraction of the fresh run


@dataclass
class Result:
    check_id: str
    layer: str                # harness | loop | state | instruction
    tier: str                 # static | behavioral | destructive
    contract_ref: str
    status: str = "SKIP"      # PASS | FAIL | WARN | SKIP
    detail: str = ""
    duration_ms: int = 0

    def line(self) -> str:
        detail = (self.detail[:200] + "…") if len(self.detail) > 201 else self.detail
        return f"{self.status:<4} [{self.tier[:1].upper()}] {self.check_id:<28} {detail}"


@dataclass
class Target:
    """Everything the checks need to know about the repo under test."""
    root: Path
    declaration_path: Path
    declaration: dict | None = None
    decl_error: str = ""
    runs: dict = field(default_factory=dict)   # memoized command runs

    # -- invocation ---------------------------------------------------------
    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True, timeout=60)

    def run(self, argv: list[str], timeout: int = 900) -> tuple[subprocess.CompletedProcess, float]:
        start = time.monotonic()
        proc = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        return proc, time.monotonic() - start

    def command(self, name: str) -> list[str] | None:
        cmds = (self.declaration or {}).get("commands", {})
        return cmds.get(name)

    def verify_argv(self, profile: str | None = None, fresh: bool = False,
                    as_json: bool = False) -> list[str] | None:
        cmds = (self.declaration or {}).get("commands", {})
        argv = cmds.get("profiles", {}).get(profile) if profile else cmds.get("verify")
        if argv is None:
            return None
        argv = list(argv)
        if fresh and cmds.get("no_cache_flag"):
            argv.append(cmds["no_cache_flag"])
        if as_json and cmds.get("json_flag"):
            argv.append(cmds["json_flag"])
        return argv

    def json_supported(self) -> bool:
        return bool((self.declaration or {}).get("commands", {}).get("json_flag"))

    # -- helpers ------------------------------------------------------------
    def state_dir(self) -> str:
        return (self.declaration or {}).get("state", {}).get("dir", ".claude/memory")

    def sandbox(self, key: str) -> list[str]:
        return (self.declaration or {}).get("sandbox", {}).get(key, []) or []


def _match_any(path: str, globs: list[str]) -> bool:
    for g in globs:
        if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.rstrip("/") + "/*"):
            return True
        # '**' should also match the bare directory prefix
        if g.endswith("/**") and (path == g[:-3] or path.startswith(g[:-3] + "/")):
            return True
    return False


def _validate(instance: dict, schema_name: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed"]
    schema = json.loads((SCHEMA_DIR / f"{schema_name}.schema.json").read_text())
    return [f"/{'/'.join(map(str, e.path))}: {e.message}"
            for e in Draft202012Validator(schema).iter_errors(instance)][:5]


def _parse_json_tail(stdout: str) -> dict | None:
    """The verdict JSON is the last JSON object on stdout (harness may print a banner first)."""
    for chunk in reversed(stdout.strip().splitlines()):
        chunk = chunk.strip()
        if chunk.startswith("{"):
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


# ═══════════════════════════════════════ static ══════════════════════════════

def check_declaration(t: Target) -> Result:
    r = Result("decl-present-valid", "harness", "static",
               "CONTRACTS §1 Environment declaration / schemas: harness-declaration")
    if not t.declaration_path.exists():
        r.status, r.detail = "FAIL", f"no declaration at {t.declaration_path.name} — nothing downstream can attest drift, profiles, or protection"
        return r
    if t.declaration is None:
        r.status, r.detail = "FAIL", f"declaration unreadable: {t.decl_error}"
        return r
    errors = _validate(t.declaration, "harness-declaration")
    if errors:
        r.status, r.detail = "FAIL", "schema violations: " + "; ".join(errors)
    else:
        r.status, r.detail = "PASS", f"validates against harness-declaration {t.declaration.get('schema_version')}"
    return r


def check_profiles_consistent(t: Target) -> Result:
    r = Result("profiles-consistent", "loop", "static", "CONTRACTS §2 / declaration verify.profiles")
    if t.declaration is None:
        r.status, r.detail = "SKIP", "no declaration"
        return r
    tiers = [x["id"] for x in t.declaration["verify"]["tiers"]]
    problems = []
    for name, subset in t.declaration["verify"].get("profiles", {}).items():
        unknown = [s for s in subset if s not in tiers]
        if unknown:
            problems.append(f"profile '{name}' references unknown tiers {unknown}")
        elif [x for x in tiers if x in subset] != subset:
            problems.append(f"profile '{name}' is not a subsequence of the tier order")
        if name not in t.declaration.get("commands", {}).get("profiles", {}):
            problems.append(f"profile '{name}' has no invocation in commands.profiles")
    r.status = "FAIL" if problems else "PASS"
    r.detail = "; ".join(problems) or f"{len(t.declaration['verify'].get('profiles', {}))} profile(s) consistent with tier order and invocable"
    return r


def check_state_gitignored(t: Target) -> Result:
    r = Result("state-gitignored", "state", "static", "CONTRACTS §1 Placement: session state gitignored")
    state = t.state_dir()
    probe = t.git("check-ignore", "-q", f"{state}/probe.json")
    if probe.returncode == 0:
        r.status, r.detail = "PASS", f"{state}/ is ignored"
    else:
        r.status, r.detail = "FAIL", f"{state}/ is NOT gitignored — session state will be committed, causing merge conflicts and cross-branch state leakage"
    return r


def check_declaration_protected(t: Target) -> Result:
    r = Result("declaration-protected", "loop", "static", "CONTRACTS §2 Tamper isolation")
    if t.declaration is None:
        r.status, r.detail = "SKIP", "no declaration"
        return r
    protected = t.sandbox("protected")
    if not protected:
        r.status, r.detail = "FAIL", "sandbox.protected is empty — the verifiers, tests, and this declaration are all editable by the agent under verification"
        return r
    rel = str(t.declaration_path.relative_to(t.root))
    if _match_any(rel, protected):
        r.status, r.detail = "PASS", f"declaration itself is protected; {len(protected)} protected glob(s)"
    else:
        r.status, r.detail = "FAIL", f"declaration '{rel}' is not covered by any protected glob — an agent can edit its own budgets and tiers"
    return r


def check_forbidden_untracked(t: Target) -> Result:
    r = Result("forbidden-untracked", "harness", "static", "CONTRACTS §1 Sandbox boundary (forbidden paths)")
    if t.declaration is None or not t.sandbox("forbidden"):
        r.status, r.detail = "SKIP", "no forbidden paths declared"
        return r
    tracked = t.git("ls-files").stdout.splitlines()
    leaked = [p for p in tracked if _match_any(p, t.sandbox("forbidden"))][:5]
    if leaked:
        r.status, r.detail = "FAIL", f"forbidden paths are tracked in git: {leaked}"
    else:
        r.status, r.detail = "PASS", "no forbidden path is tracked"
    return r


def check_instructions_present(t: Target) -> Result:
    r = Result("instructions-present", "instruction", "static", "CONTRACTS §1 Instruction specification")
    names = [n for n in ("AGENTS.md", "CLAUDE.md") if (t.root / n).exists()]
    if names:
        r.status, r.detail = "PASS", f"canonical rules file: {', '.join(names)}"
    else:
        r.status, r.detail = "WARN", "no AGENTS.md/CLAUDE.md at repo root — rules are scattered or absent"
    return r


def check_tamper_rules(t: Target) -> Result:
    r = Result("tamper-rules-crosscheck", "loop", "static",
               "CONTRACTS §2 Tamper isolation (enforcement lives in the agent CLI's permission layer)")
    if t.declaration is None or not t.sandbox("protected"):
        r.status, r.detail = "SKIP", "no protected paths declared"
        return r
    settings = t.root / ".claude" / "settings.json"
    if not settings.exists():
        r.status, r.detail = "WARN", "no .claude/settings.json — cannot statically confirm protected paths are deny-listed in the agent CLI; verify enforcement manually"
        return r
    text = settings.read_text()
    uncovered = [g for g in t.sandbox("protected") if g.split("/")[0].strip("*") not in text][:5]
    if uncovered:
        r.status, r.detail = "WARN", f"protected globs with no apparent deny rule in settings.json: {uncovered}"
    else:
        r.status, r.detail = "PASS", "every protected glob appears in agent CLI settings (best-effort textual check)"
    return r


# ═════════════════════════════════════ behavioral ════════════════════════════

def check_doctor_runs(t: Target) -> Result:
    r = Result("doctor-runs", "harness", "behavioral", "CONTRACTS §1 doctor: drift + health duties")
    argv = t.command("doctor")
    if argv is None:
        r.status, r.detail = "SKIP", "no commands.doctor in declaration"
        return r
    try:
        proc, secs = t.run(argv, timeout=120)
    except Exception as e:  # noqa: BLE001
        r.status, r.detail = "FAIL", f"doctor did not run: {e}"
        return r
    r.duration_ms = int(secs * 1000)
    out = proc.stdout + proc.stderr
    if proc.returncode not in (0, 1, 2):
        r.status, r.detail = "FAIL", f"doctor exit {proc.returncode} outside contract set {{0,1,2}}"
    elif len(out) > STDOUT_BUDGET:
        r.status, r.detail = "WARN", f"doctor exit {proc.returncode} but output {len(out)} chars exceeds {STDOUT_BUDGET} budget"
    else:
        r.status, r.detail = "PASS", f"exit {proc.returncode}, {len(out)} chars, {secs:.1f}s"
    t.runs["doctor"] = proc
    return r


def check_doctor_report_valid(t: Target) -> Result:
    r = Result("doctor-report-valid", "harness", "behavioral", "schemas: doctor-report")
    argv = t.command("doctor")
    if argv is None or not t.json_supported():
        r.status, r.detail = "SKIP", "no json_flag declared — full conformance requires machine-readable doctor output"
        return r
    proc, secs = t.run(argv + [t.declaration["commands"]["json_flag"]], timeout=120)
    r.duration_ms = int(secs * 1000)
    doc = _parse_json_tail(proc.stdout)
    if doc is None:
        r.status, r.detail = "FAIL", "doctor json_flag produced no parseable JSON"
        return r
    errors = _validate(doc, "doctor-report")
    r.status = "FAIL" if errors else "PASS"
    r.detail = "; ".join(errors) or f"conforms; status={doc.get('status')}"
    return r


def _run_verify(t: Target, key: str, profile: str | None = None, fresh: bool = False):
    """Memoized verify run; returns (proc, seconds, parsed_json_or_None)."""
    if key in t.runs:
        return t.runs[key]
    argv = t.verify_argv(profile=profile, fresh=fresh, as_json=t.json_supported())
    proc, secs = t.run(argv)
    doc = _parse_json_tail(proc.stdout) if t.json_supported() else None
    t.runs[key] = (proc, secs, doc)
    return t.runs[key]


def check_verify_runs(t: Target) -> Result:
    r = Result("verify-runs", "loop", "behavioral",
               "CONTRACTS §2 Deterministic verdicts / schemas: verify-result")
    if t.command("verify") is None:
        r.status, r.detail = "SKIP", "no commands.verify in declaration"
        return r
    try:
        proc, secs, doc = _run_verify(t, "verify_full_1", fresh=True)
    except Exception as e:  # noqa: BLE001
        r.status, r.detail = "FAIL", f"verify did not run: {e}"
        return r
    r.duration_ms = int(secs * 1000)
    out = proc.stdout + proc.stderr
    if proc.returncode not in (0, 1, 2):
        r.status, r.detail = "FAIL", f"verify exit {proc.returncode} outside {{0,1,2}}"
        return r
    if t.json_supported():
        if doc is None:
            r.status, r.detail = "FAIL", "json_flag declared but verify emitted no parseable JSON"
            return r
        errors = _validate(doc, "verify-result")
        if errors:
            r.status, r.detail = "FAIL", "verify-result schema violations: " + "; ".join(errors)
            return r
        if doc.get("profile") != "full":
            r.status, r.detail = "FAIL", f"full verify reported profile '{doc.get('profile')}' — must be 'full'"
            return r
        r.status, r.detail = "PASS", f"verdict={doc['verdict']}, {len(doc.get('stages', []))} stages, {secs:.1f}s, conforms"
    else:
        status = "WARN" if len(out) > STDOUT_BUDGET else "PASS"
        r.status = status
        r.detail = f"exit {proc.returncode}, {len(out)} chars, {secs:.1f}s (no json_flag — envelope unvalidatable)"
    return r


def check_verify_deterministic(t: Target) -> Result:
    r = Result("verify-deterministic", "loop", "behavioral", "CONTRACTS §2 Deterministic verdicts")
    if t.command("verify") is None:
        r.status, r.detail = "SKIP", "no commands.verify"
        return r
    p1, s1, d1 = _run_verify(t, "verify_full_1", fresh=True)
    p2, s2, d2 = _run_verify(t, "verify_full_2")          # second run: cache allowed
    r.duration_ms = int(s2 * 1000)
    if p1.returncode != p2.returncode:
        r.status, r.detail = "FAIL", f"same tree, different exit codes ({p1.returncode} then {p2.returncode}) — nondeterministic gate teaches the loop nothing"
    elif d1 and d2 and d1.get("verdict") != d2.get("verdict"):
        r.status, r.detail = "FAIL", f"same tree, different verdicts ({d1['verdict']} then {d2['verdict']})"
    else:
        r.status, r.detail = "PASS", f"identical verdict on identical tree (exit {p1.returncode} twice)"
    return r


def check_verify_replay(t: Target) -> Result:
    r = Result("verify-replay-fast", "loop", "behavioral", "CONTRACTS §2 Verdict replay")
    if t.command("verify") is None:
        r.status, r.detail = "SKIP", "no commands.verify"
        return r
    _, s1, _ = _run_verify(t, "verify_full_1", fresh=True)
    _, s2, d2 = _run_verify(t, "verify_full_2")
    r.duration_ms = int(s2 * 1000)
    fast = s2 <= max(REPLAY_FAST_SECONDS, s1 * REPLAY_FAST_RATIO)
    replay_flagged = bool(d2 and d2.get("cache", {}).get("replayed"))
    if fast and (replay_flagged or d2 is None):
        r.status, r.detail = "PASS", f"unchanged tree replays in {s2:.1f}s (fresh {s1:.1f}s)" + (" and marks cache.replayed" if replay_flagged else "")
    elif fast and not replay_flagged:
        r.status, r.detail = "WARN", f"replay is fast ({s2:.1f}s) but result does not set cache.replayed — provenance unattested"
    else:
        r.status, r.detail = "WARN", f"no verdict cache detected ({s1:.1f}s then {s2:.1f}s) — replay is the highest-value caching mechanism; consider implementing"
    return r


def check_profile_separation(t: Target) -> Result:
    r = Result("profile-separation", "loop", "behavioral",
               "CONTRACTS §2 Verdict replay: profile-scoped keys / declaration profiles")
    profiles = (t.declaration or {}).get("verify", {}).get("profiles", {})
    if not profiles:
        r.status, r.detail = "SKIP", "no profiles declared"
        return r
    name = sorted(profiles)[0]
    if t.verify_argv(profile=name) is None:
        r.status, r.detail = "FAIL", f"profile '{name}' declared but not invocable via commands.profiles"
        return r
    _run_verify(t, "verify_full_1", fresh=True)            # ensure a full verdict is cached
    proc, secs, doc = _run_verify(t, f"verify_{name}", profile=name)
    r.duration_ms = int(secs * 1000)
    if doc is None:
        r.status, r.detail = "WARN", f"profile '{name}' ran (exit {proc.returncode}) but without json the profile field is unattestable"
    elif doc.get("profile") == "full":
        r.status, r.detail = "FAIL", f"'{name}' run reported profile 'full' — a subset verdict is masquerading as full (cache keys must include profile)"
    elif doc.get("profile") != name:
        r.status, r.detail = "FAIL", f"'{name}' run reported profile '{doc.get('profile')}'"
    else:
        r.status, r.detail = "PASS", f"'{name}' verdict carries profile='{name}', never 'full'"
    return r


# ════════════════════════════════════ destructive ════════════════════════════

def destructive_sequence(t: Target) -> list[Result]:
    """Corrupt the declared probe file → verify must FAIL with bounded feedback →
    restore → verify must replay the original verdict. Requires a clean tree."""
    base = dict(layer="loop", tier="destructive")
    fail_r = Result("fail-on-broken-code", contract_ref="CONTRACTS §2 Deterministic verdicts (evidence, not confidence)", **base)
    bound_r = Result("feedback-bounded", contract_ref="CONTRACTS §2 Compact, bounded feedback", **base)
    restore_r = Result("cache-restore-replay", contract_ref="CONTRACTS §1 Observation cache (content-hash invalidation) + §2 Verdict replay", **base)
    results = [fail_r, bound_r, restore_r]

    probe_rel = (t.declaration or {}).get("conformance", {}).get("probe_file")
    if not probe_rel:
        for x in results:
            x.status, x.detail = "SKIP", "no conformance.probe_file declared"
        return results
    if t.git("status", "--porcelain").stdout.strip():
        for x in results:
            x.status, x.detail = "SKIP", "working tree not clean — destructive checks refuse to run"
        return results
    probe = t.root / probe_rel
    if not probe.exists() or not _match_any(probe_rel, t.sandbox("writable")):
        for x in results:
            x.status, x.detail = "SKIP", f"probe '{probe_rel}' missing or not inside sandbox.writable"
        return results

    # Baseline (fresh, so we measure a real run and know the honest verdict).
    p0, s0, d0 = _run_verify(t, "verify_full_1", fresh=True)
    original = probe.read_bytes()
    try:
        probe.write_bytes(original + b"\nthis is deliberately not valid source code (\n")
        argv = t.verify_argv(as_json=t.json_supported())
        p1, s1 = t.run(argv)
        doc1 = _parse_json_tail(p1.stdout) if t.json_supported() else None
        out1 = p1.stdout + p1.stderr

        fail_r.duration_ms = int(s1 * 1000)
        if p1.returncode == 0:
            fail_r.status, fail_r.detail = "FAIL", "verify PASSED on deliberately broken code — the gate is not gating"
        elif doc1 is not None and doc1.get("verdict") not in ("fail", "error"):
            fail_r.status, fail_r.detail = "FAIL", f"nonzero exit but verdict '{doc1.get('verdict')}'"
        else:
            v = f", verdict={doc1['verdict']}, failed_stage={doc1.get('failed_stage')}" if doc1 else ""
            fail_r.status, fail_r.detail = "PASS", f"broken probe → exit {p1.returncode} in {s1:.1f}s{v}"

        if doc1 is not None:
            errors = _validate(doc1, "verify-result")
            bound_r.status = "FAIL" if errors else "PASS"
            bound_r.detail = "; ".join(errors) or "failure envelope conforms (summary ≤500, details ≤4000, ≤20 locations)"
        else:
            bound_r.status = "WARN" if len(out1) > STDOUT_BUDGET else "PASS"
            bound_r.detail = f"failure output {len(out1)} chars vs {STDOUT_BUDGET} budget (no json — bounds checked on console output only)"
    finally:
        probe.write_bytes(original)

    p2, s2 = t.run(t.verify_argv(as_json=t.json_supported()))
    doc2 = _parse_json_tail(p2.stdout) if t.json_supported() else None
    restore_r.duration_ms = int(s2 * 1000)
    if p2.returncode != p0.returncode:
        restore_r.status, restore_r.detail = "FAIL", f"restored tree exit {p2.returncode} != baseline {p0.returncode} — invalidation or determinism broken"
    elif doc0_v := (d0.get("verdict") if d0 else None):
        if doc2 and doc2.get("verdict") != doc0_v:
            restore_r.status, restore_r.detail = "FAIL", f"restored verdict {doc2.get('verdict')} != baseline {doc0_v}"
        else:
            fast = s2 <= max(REPLAY_FAST_SECONDS, s0 * REPLAY_FAST_RATIO)
            restore_r.status = "PASS" if fast else "WARN"
            restore_r.detail = f"restored tree → baseline verdict in {s2:.1f}s (fresh {s0:.1f}s)" + ("" if fast else " — slow: content-keyed cache should have replayed")
    else:
        restore_r.status, restore_r.detail = "PASS", f"restored tree → baseline exit {p0.returncode} in {s2:.1f}s"
    return results


STATIC = [check_declaration, check_profiles_consistent, check_state_gitignored,
          check_declaration_protected, check_forbidden_untracked,
          check_instructions_present, check_tamper_rules]
BEHAVIORAL = [check_doctor_runs, check_doctor_report_valid, check_verify_runs,
              check_verify_deterministic, check_verify_replay, check_profile_separation]


def run_all(root: Path, declaration_rel: str, tiers: set[str]) -> list[Result]:
    t = Target(root=root.resolve(), declaration_path=root.resolve() / declaration_rel)
    if t.declaration_path.exists():
        try:
            t.declaration = json.loads(t.declaration_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            t.decl_error = str(e)
    results: list[Result] = []
    if "static" in tiers:
        results += [c(t) for c in STATIC]
    if "behavioral" in tiers:
        results += [c(t) for c in BEHAVIORAL]
    if "destructive" in tiers:
        results += destructive_sequence(t)
    return results
