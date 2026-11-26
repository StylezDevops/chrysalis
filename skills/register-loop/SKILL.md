---
name: register-loop
description: Evidence-driven, one-row-at-a-time defect remediation loop for any codebase (audio/DSP, web, backend, mobile, data, infra). Works an audit/issue register row by row, measure the defect as a number through the shipping path, positive-control the detector, fix with a regression test, go green on the project's CI, then run a fresh-context adversarial subagent audit (domain checklist sweep plus free-form brief) and re-audit the fixes until a round comes back clean, and writes a handover doc that carries the loop itself forward at ~85% context. Use this whenever the user says "next row", "work the register", "run the loop", "carry on from the handover", "pick up where we left off", mentions AUDIT_REGISTER / a findings register / a remediation backlog, asks to fix audit findings one at a time, or starts a session by pasting a handover doc, even if they never say "register-loop".
---

# Register Loop

A disciplined remediation loop. Its value comes from three things that are easy to lose:

1. **Numbers, not opinions.** Every defect is a measurement that moves, and every detector is proven to move before it is trusted.
2. **Adversarial re-audit of the fixes.** Fixes are where new bugs live. The loop repeats the audit on its own fixes until a round is clean.
3. **The loop travels with the work.** The handover doc contains the loop verbatim, so the next session runs the same process instead of a paraphrase of it.

Nothing in the loop is domain-specific. Everything domain-specific lives in the project config (`.claude/register-loop.md`).

## 0. Load the project config

Read `.claude/register-loop.md` at the repo root. If it doesn't exist, build it from `assets/config-template.md` by inspecting the repo (CI scripts, test runners, build dirs, existing registers, installed checklist skills) and ask the user only for what can't be discovered. Show the filled config and get a yes before the first row.

The config defines: register path and row format, CI gate commands, the shipping path and how to measure through it, the fault-injection mechanism, isolation for the subagent, forbidden commands, commands that need a warning, the domain sweep, and the context threshold.

If the session opened with a handover doc, read it first, its **Loop** section is authoritative for this session, and its **State** section tells you where to resume.

## The loop

Restate the loop to the user (filled in from config) before the first row, and get confirmation. Then run it.

### 1. Take the next row
The next OPEN row in register order. One row. No batching, no "while I'm here". Other defects you spot get a new register row, not a drive-by fix. Mark the row IN PROGRESS.

### 2. Measure, then positive-control the detector
Express the defect as a number observed through the **shipping path**: the path real users/hosts/callers exercise (the built artefact, the running server, the release binary, the deployed config), not a unit-level shortcut that bypasses it. Record the baseline value.

Then **arm the defect** (config's injection mechanism: revert, fault flag, env var, fixture, mutation) and confirm the measurement moves. A measurement that still passes with the defect armed is measuring something else, fix the detector before touching the code. Record armed vs disarmed values.

See `references/measurement.md` for what "a number through the shipping path" looks like per domain.

### 3. Fix, plus a regression test
Make the smallest fix that moves the number. Add a test that fails if the behaviour regresses, ideally the step-2 measurement promoted into the suite. Confirm the test is red with the fix reverted.

### 4. Green gate
All of: every CI gate command in config, the unit/integration suites, and the row's own injection **red-then-green** (armed → fails, fixed → passes). Record results. Don't proceed on partial green.

### 5. Adversarial audit (subagent)
Spawn a subagent with **fresh context** (no conversation history, give it only the brief). Use the most capable model available (config `audit_model`). It gets:

- its **own isolation** (config: build dir / worktree / port / DB / env var) so it cannot collide with your builds;
- the **forbidden list** (config), commands it must never run, typically the heavyweight or machine-wide CI gates you own;
- the diff for this row and the files it touches.

The brief is in `references/adversarial-brief.md`. It has three parts, in order:
1. **Systematic sweep**: the config's domain checklist (an installed skill such as `audio-plugin-audit all`, or the class list from `references/sweeps.md`) over the touched code.
2. **Free-form adversarial pass** on top, because a checklist does not contain the unknown bug classes.
3. **The docs against the code**: what the change made wrong, what it added that no doc describes, and any doc promise the touched code does not keep. These are findings, fixed like any other; a row is not done while its docs lag.

**Exactly two messages to the subagent, both earned:**
- **Warning** before you run any config `warn_before` command (e.g. a CI script that kills processes machine-wide, resets a DB, clears caches), so it doesn't misread the fallout as a finding.
- **"Audit the fixes"** after you've applied fixes from its findings. This is where the findings are. Don't skip it.

No other chatter. Don't lead it toward conclusions.

### 6. Verify, act, re-audit until clean
For each finding: reproduce it as a **failing number** (step-2 rules, including positive control) before acting. Unreproducible → record as rejected with the attempt. Reproduced → fix now (with test) if within this row's scope, otherwise **queue as a new register row** and cite the row number.

Then send the "audit the fixes" message and repeat. A round is **clean** when the subagent returns no reproducible findings. Only then continue.

### 7. Close the row
Green gate again (step 4 in full). Update the register row (DONE, evidence: baseline/armed/fixed numbers, test names, commit). Commit, push, next row.

### 8. Context budget
At the config threshold (default ~85% context), stop taking rows. Finish or cleanly park the current one, then write the handover (`assets/handover-template.md`) to the config's handover path. The handover **must** include the loop verbatim as confirmed at the start of this session, with any amendments the user made. Tell the user the path.

## Rules that hold throughout

- Register order is the order. If the user reorders, update the register, don't freelance.
- Never mark anything done on reasoning alone. Every claim in the register has a number beside it.
- Never weaken a test or a detector to get green. If a gate is wrong, that's a register row.
- If a CI gate is flaky, record it as a row; don't retry until it passes and call it green.
- Keep the user's loop wording. If the user's handover loop differs from this file, theirs wins.
