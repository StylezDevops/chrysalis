# Adversarial audit brief (send to the subagent verbatim, filled in)

You are auditing a change in <project>. You have no prior context and should not assume the change is correct.

**Isolation.** Use <isolation> for every build/run. Never run: <forbidden>. You may run: <allowed test/build commands>.

**Scope.** Register row <id>: <one-line defect>. Diff: <diff or commit range>. Touched files: <list>. Also examine direct callers and callees of changed code.

**Part 1, systematic sweep.** <Run skill X with args Y | Walk these classes in order: ...> over the touched code. For each class, state checked/not-applicable and any findings.

**Part 2, free-form adversarial pass.** Now ignore the checklist. Your job is to break this change. Consider: inputs the author didn't imagine; boundaries (empty, one, max, negative, NaN, unicode, huge, concurrent); ordering and timing; state left behind by the previous call; the fix being right for the reported case but wrong for its siblings; the test passing for the wrong reason; the measurement not actually going through the shipping path. Think about bug classes that aren't on any list.

**Siblings.** For every finding, name the family it belongs to (the other backends, providers, databases, actors, routes or tools that make the same promise) and say, member by member, whether the finding holds there. A finding checked against one member only is incomplete, and a fix that reaches one member only is NOT CLEAN.

**Part 3, the docs against the code.** Read every doc the project keeps for what this change touches (user manual or help pages, API reference, specs, README, in-app help text, comments that state behaviour). Report as findings: anything the change made wrong or out of date, anything it added that no doc describes, and any doc claim about the touched area that the code does not do (a promise the software does not keep). Quote the doc line and the code that contradicts it. An undocumented or wrongly documented behaviour is a finding like any other, never a note.

**Evidence standard.** Every finding must include: location, the failure mechanism, and a concrete reproduction that produces a number or a failing assertion, a command or test the parent can run. Findings without a reproduction path are hypotheses; label them as such and rank them below reproducible ones.

**Output.** A list of findings, most severe first: id, severity, location, mechanism, reproduction, suggested fix. Then a one-line verdict: CLEAN or NOT CLEAN.

---

**Warning message template (send before a warn-before command):**
> Heads-up: I'm about to run <command>. It <side effect>. Any <symptom> in the next <duration> is from that, not a finding. Don't run anything until I say it's done.

**Audit-the-fixes message template:**
> I've applied fixes for findings <ids> in <commit/diff>. Audit these fixes with the same rigour, all three parts, treating the fixes themselves as the new change. Report CLEAN or NOT CLEAN.
