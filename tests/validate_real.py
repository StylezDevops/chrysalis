"""Differential validation of `chrysalis.py apply` against copies of real repositories (clauses C4 to
C7, C13). Writes docs/validation.md from what it measured.

  python tests/validate_real.py              run every target listed in the local roots file
  python tests/validate_real.py --control    arm the apply-overwrites defect on 1 target; the harness
                                             must report changed files and exit 1

Sources come from tests/evidence_roots.local.json (gitignored): keys CHRYSOS, SUBSTRATE, MIDAS,
CSAW_REPO, and CSAW_BRIEF_DIR (a folder holding CSAW_JUCE_brief.md and csaw_rt.py). Each existing repo
is copied with `git clone --depth 1` into a temp folder, so only tracked files are copied: ignored and
untracked files, including any secret files, never leave the source. The source is only read.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chrysalis.py"
ROOTS_FILE = pathlib.Path(os.environ.get("CHRYSALIS_ROOTS_FILE")
                          or ROOT / "tests" / "evidence_roots.local.json")
ROOTS = json.loads(ROOTS_FILE.read_text(encoding="utf-8")) if ROOTS_FILE.is_file() else None
SKIPPED = 3  # exit code when the local copies are absent: never 0, because a skip is not a pass (U2, R-7)
REPORT = ROOT / "docs" / "validation.md"

BASE_RISK = {"live_production": False, "handles_money": False, "handles_personal_data": False,
             "auth": False, "realtime": False, "client_engagement": False, "mutates_data": False}


def config(name, description, problem, users, stage, existing, languages, platforms, **risk):
    return {
        "project": {"name": name, "title": name, "description": description, "problem": problem,
                    "users": users},
        "stage": stage,
        "repo": {"existing": existing, "default_branch": "main"},
        "stack": {"languages": languages, "platforms": platforms},
        "risk": dict(BASE_RISK, **risk),
        "ci": {"remote": "on-request"},
        "agents": {"max_parallel_agents": 2},
    }


TARGETS = {
    "CHRYSOS": config("CHRYSOS", "A sampler and effects instrument plugin.", "Musicians need the instrument "
                      "to sound right and never glitch on the audio thread.", ["music producers"], "pre-release",
                      True, ["c++", "typescript"], ["desktop", "plugin"], realtime=True),
    "SUBSTRATE": config("Substrate", "A provenance registry for music releases.", "Labels need evidence-backed "
                        "provenance records that cannot be quietly rewritten.", ["record labels", "listeners"],
                        "pre-release", True, ["python", "typescript", "solidity"], ["web"], handles_money=True,
                        handles_personal_data=True, auth=True),
    "MIDAS": config("MIDAS", "A wavetable synthesiser plugin.", "Producers need a synth that stays stable and "
                    "matches its presets.", ["music producers"], "pre-release", True, ["c++"],
                    ["desktop", "plugin"], realtime=True),
    "CSAW_REPO": config("CSAW", "An audio effect plugin ported from a Python reference.", "The plugin must "
                        "match the Python reference output.", ["music producers"], "pre-release", True, ["c++"],
                        ["desktop", "plugin"], realtime=True),
}
NEW_PROJECT = config("CSAW", "An audio effect plugin ported from a Python reference.", "The plugin must match "
                     "the Python reference output.", ["music producers"], "new", False, ["c++", "python"],
                     ["desktop", "plugin"], realtime=True)


def sh(cmd, cwd=None, env=None):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode, r.stdout + r.stderr


def hashes(root):
    out = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] == ".git":
            continue
        if p.is_file():
            out[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def git_state(repo):
    return {k: sh(["git", "-C", str(repo), *args])[1].strip() for k, args in {
        "head": ["rev-parse", "HEAD"], "branches": ["branch", "--list"], "remotes": ["remote", "-v"],
        "staged": ["diff", "--cached", "--name-only"], "commits": ["rev-list", "--all", "--count"]}.items()}


def run_apply(repo, cfg, work, env):
    cfg_path = work / f"{repo.name}-config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return sh([sys.executable, str(SCRIPT), "apply", str(repo), "--config", str(cfg_path), "--home",
               str(work / "home")], env=env)


def validate_existing(key, work, env):
    src = pathlib.Path(ROOTS[key])
    dest = work / key.lower()
    code, out = sh(["git", "clone", "--quiet", "--depth", "1", "--no-hardlinks", src.as_uri(), str(dest)])
    if code:
        return {"target": key, "error": f"clone failed: {out[-300:]}"}
    before, state_before = hashes(dest), git_state(dest)
    code, out = run_apply(dest, TARGETS[key], work, env)
    after, state_after = hashes(dest), git_state(dest)
    changed = sorted(p for p in before if p in after and before[p] != after[p])
    deleted = sorted(p for p in before if p not in after)
    created = sorted(p for p in after if p not in before)
    verbs = {v: len(re.findall(rf"(?m)^{v} ", out)) for v in ("CREATE", "PROPOSE", "REUSE", "SKIP")}
    porcelain = sh(["git", "-C", str(dest), "status", "--porcelain"])[1].splitlines()
    return {
        "target": key, "apply_exit": code, "files_before": len(before), "changed": changed, "deleted": deleted,
        "created": len(created), "verbs": verbs,
        "git_unchanged": state_before == state_after,
        "status_only_untracked": all(l.startswith("??") for l in porcelain if l.strip()),
        "reuse": re.findall(r"(?m)^REUSE (.+)$", out),
        "propose": re.findall(r"(?m)^PROPOSE (\S+)", out),
    }


def validate_new(work, env):
    src = pathlib.Path(ROOTS["CSAW_BRIEF_DIR"])
    dest = work / "csaw-new"
    dest.mkdir()
    for name in ("CSAW_JUCE_brief.md", "csaw_rt.py"):
        shutil.copy2(src / name, dest / name)
    before = hashes(dest)
    code, out = run_apply(dest, NEW_PROJECT, work, env)
    after = hashes(dest)
    method = (ROOT / "METHOD.md").read_text(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "scripts"))
    import chrysalis  # noqa: E402
    claude = (dest / "CLAUDE.md").read_text(encoding="utf-8") if (dest / "CLAUDE.md").exists() else ""
    copied = sorted(chrysalis.long_sentences(method) & chrysalis.long_sentences(claude))
    g_code, g_out = sh([sys.executable, str(SCRIPT), "gates", "validate", "--file", str(dest / "gates.toml")])
    # Kept for the human acceptance check (gate A1): what init writes for a real new project.
    samples = ROOT / "docs" / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    for name in ("initial.md", "CLAUDE.md"):
        if (dest / name).exists():
            text = (dest / name).read_text(encoding="utf-8").replace(str(ROOT), "<chrysalis>")
            (samples / f"csaw-{name}").write_text(text, encoding="utf-8", newline="\n")
    return {
        "target": "CSAW new project", "apply_exit": code,
        "inputs_unchanged": all(after.get(p) == h for p, h in before.items()),
        "required_present": {f: (dest / f).is_file() for f in
                             ("initial.md", "docs/backlog.md", "gates.toml", "CLAUDE.md")},
        "claude_rule_ids": sorted(set(re.findall(r"\b([UK]\d+)\b", claude)), key=lambda s: (s[0], int(s[1:]))),
        "copied_sentences": copied,
        "gates_validate_exit": g_code,
        "created": len(after) - len(before),
    }


def ok_existing(r):
    return (not r.get("error") and r["apply_exit"] == 0 and not r["changed"] and not r["deleted"]
            and r["git_unchanged"] and r["status_only_untracked"])


def ok_new(r):
    return (r["apply_exit"] == 0 and r["inputs_unchanged"] and all(r["required_present"].values())
            and not r["copied_sentences"] and r["gates_validate_exit"] == 0 and r["claude_rule_ids"])


def write_report(results, new, when):
    lines = [
        "# Validation against real repositories",
        "",
        f"Measured {when} by `python tests/validate_real.py`. Regenerated on every run; do not edit by hand.",
        "",
        "Method: each repository was copied with `git clone --depth 1` into a temp folder (tracked files only,",
        "so ignored and secret files never left the source). Every file was hashed before and after",
        "`chrysalis.py apply`, and the git state (HEAD, branches, remotes, staged files, commit count) was",
        "compared. The sources were only read.",
        "",
        "## Existing repositories",
        "",
        "| Target | Files before | Changed | Deleted | Created | CREATE | PROPOSE | REUSE | Git state same | Only untracked additions | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r['target']} | - | - | - | - | - | - | - | - | - | ERROR: {r['error'][:80]} |")
            continue
        v = r["verbs"]
        lines.append(f"| {r['target']} | {r['files_before']} | {len(r['changed'])} | {len(r['deleted'])} | "
                     f"{r['created']} | {v['CREATE']} | {v['PROPOSE']} | {v['REUSE']} | {r['git_unchanged']} | "
                     f"{r['status_only_untracked']} | {'PASS' if ok_existing(r) else 'FAIL'} |")
    lines += ["", "What apply reused instead of duplicating, and what it only proposed:", ""]
    for r in results:
        if not r.get("error"):
            lines.append(f"- **{r['target']}**: reused {', '.join(r['reuse']) or 'nothing'}; "
                         f"proposed {', '.join(r['propose']) or 'nothing'}.")
    lines += ["", "## New project", "",
              "An empty folder holding only the CSAW brief and its Python reference.", "",
              "| Check | Result |", "|---|---|",
              f"| apply exit code | {new['apply_exit']} |",
              f"| brief and reference unchanged | {new['inputs_unchanged']} |"]
    for f, present in new["required_present"].items():
        lines.append(f"| {f} created | {present} |")
    lines += [f"| rule IDs cited in CLAUDE.md | {', '.join(new['claude_rule_ids'])} |",
              f"| METHOD sentences copied into CLAUDE.md | {len(new['copied_sentences'])} |",
              f"| generated gates.toml validates (exit) | {new['gates_validate_exit']} |",
              f"| files created | {new['created']} |",
              f"| verdict | {'PASS' if ok_new(new) else 'FAIL'} |", ""]
    lines += ["## Limits", "",
              "- A shallow clone copies tracked files only. Untracked or ignored files in the source (for example a",
              "  gitignored register) were not present, so equivalents that exist only as ignored files were not tested.",
              "- The configs used here were written by the harness, not by a human. They are in tests/validate_real.py.",
              ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the temp copies for inspection")
    args = ap.parse_args()
    if ROOTS is None:
        print(f"SKIPPED: {ROOTS_FILE.name} not found, so there are no local repository copies to "
              f"validate against. This is not a pass (exit {SKIPPED}).")
        return SKIPPED
    env = dict(os.environ)
    env.pop("CHRYSALIS_SABOTAGE", None)
    work = pathlib.Path(tempfile.mkdtemp(prefix="chrysalis-validate-")) / "w"
    work.mkdir()
    try:
        if args.control:
            env["CHRYSALIS_SABOTAGE"] = "apply-overwrites"
            r = validate_existing("CSAW_REPO", work, env)
            print(f"control: {r['target']} changed {len(r.get('changed', []))} file(s), "
                  f"verdict {'PASS' if ok_existing(r) else 'FAIL'} (must be FAIL)")
            return 1 if not ok_existing(r) else 0
        results = [validate_existing(k, work, env) for k in TARGETS if k in ROOTS]
        new = validate_new(work, env)
        when = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        write_report(results, new, when)
        for r in results:
            print(f"{r['target']:<10} {'PASS' if ok_existing(r) else 'FAIL'}"
                  + (f"  changed={len(r['changed'])} deleted={len(r['deleted'])} created={r['created']}"
                     if not r.get('error') else f"  {r['error'][:120]}"))
        print(f"{'CSAW new':<10} {'PASS' if ok_new(new) else 'FAIL'}")
        bad = sum(not ok_existing(r) for r in results) + (not ok_new(new))
        print("RESULT:", "OK" if not bad else f"FAIL ({bad})", f"report: {REPORT.relative_to(ROOT).as_posix()}")
        return 1 if bad else 0
    finally:
        if args.keep:
            print(f"kept: {work}")
        else:
            shutil.rmtree(work.parent, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
