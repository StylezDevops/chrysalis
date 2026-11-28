# Chrysalis: defect register

One row per defect (METHOD U3). Rows are never renumbered or deleted. Checked by gate R1:
`python scripts/chrysalis.py register check --file docs/register.md --root .`

| ID | State | Defect | Measure | Before | After | Test | Follow-up |
|---|---|---|---|---|---|---|---|
| R-1 | CLOSED | Case-insensitive glob matching on Windows took `.claude/register-loop.md` (a config file) for a defect register | non-register files listed as registers in the CHRYSOS copy (tests/validate_real.py) | 1 | 0 | tests/test_chrysalis.py::test_C6_register_loop_config_is_not_a_register | rule: asset matching is case-sensitive; comment at the match site in scripts/chrysalis.py |
| R-2 | CLOSED | On a case-insensitive filesystem an existing `docs/BACKLOG.md` made `docs/backlog.md` "exist", so apply proposed a second backlog instead of reusing the first | PROPOSE actions for files that already had an equivalent, CHRYSOS copy | 1 | 0 | tests/test_chrysalis.py::test_C6_existing_file_under_another_case_is_reused | none: covered by the regression test; same root as R-1 (case folding) |
| R-3 | CLOSED | An existing `.lusser/` received template proposals for its live spec, parts and checks files | template proposals beside a live .lusser/, CHRYSOS and Substrate copies combined | 6 | 0 | tests/test_chrysalis.py::test_C6_existing_lusser_files_are_reused_not_proposed | none: covered by the regression test |

| R-4 | CLOSED | lusser.py rejected a `checks.toml` that starts with a UTF-8 byte-order mark (what PowerShell 5.1 `Set-Content -Encoding utf8` writes) with the unhelpful "Invalid statement (at line 1, column 1)" | parse failures on a BOM-prefixed but otherwise valid spec, parts and checks | 1 | 0 | tests/test_lusser.py::test_L_bom_prefixed_files_parse | rule: tools read user-edited files as utf-8-sig |
| R-5 | CLOSED | chrysalis.py rejected a BOM-prefixed `config_project.json`; the error did name the BOM | parse failures on a BOM-prefixed but otherwise valid config | 1 | 0 | tests/test_chrysalis.py::test_C3_bom_prefixed_config_is_read | rule: same as R-4; config, gates, register and templates all read as utf-8-sig |

| R-6 | CLOSED | `tests/run_all.py` printed PASS for the evidence suite when 2 of its 3 tests were skipped (any machine without the local source copies), against U2's "a test that cannot run reports itself skipped" | suites reported as plain PASS while holding skipped tests, fresh clone | 1 | 0 | tests/test_checks.py::test_C8_suite_with_skipped_tests_is_not_reported_as_plain_pass | rule: the runner reads the skip count from every unittest log; found by running the suites in a fresh clone before adding CI |
| R-7 | CLOSED | `tests/validate_real.py` crashed with FileNotFoundError on a machine without `tests/evidence_roots.local.json`, while the README said it skips | tracebacks from validate_real.py with no local roots file | 1 | 0 | tests/test_checks.py::test_C13_validation_without_local_copies_skips_with_a_nonzero_exit | rule: a missing input is a named skip with exit 3, never 0 (U2, U17); CI leaves V1 out by name |

| R-8 | CLOSED | `worktree` ignored `repo.default_branch` and always used `main`, so `new` and `sweep` failed on a repo whose default branch is `master`, `trunk` or `develop` unless `--base` was passed | worktree tests failing on a repo whose only branch is `trunk`, with the config naming it | 3 | 0 | tests/test_worktrees.py::test_C12_base_defaults_to_the_configured_default_branch | rule: base comes from --base, then the config, then main, and the output names the source; an unreadable config fails closed (U17, U19) |
| R-9 | CLOSED | `register check` split table rows on every pipe, so an escaped pipe or a pipe inside a code span shifted the columns and misread before, after and test | register rows misread in the regression fixture | 1 | 0 | tests/test_checks.py::test_C9_escaped_pipe_and_code_span_pipe_stay_inside_their_cell | rule: one Markdown row splitter, used by register check and the K-table check |
| R-10 | CLOSED | `inspect` stopped at 3 folder levels without saying so, so assets deeper in a monorepo were missed silently | folders cut off by the depth limit and not reported, test repo | 1 | 0 | tests/test_chrysalis.py::test_C6_folders_past_the_depth_limit_are_reported_and_reachable | rule: the inventory lists every folder it did not walk, plan prints a note, and --max-depth raises the limit (U13) |
| R-11 | CLOSED | `lusser parts` kept `main` as its fixed default base, so on a repo whose default branch is `trunk` it failed unless `--base` was passed; R-8 had fixed the same promise for `worktree` only | base-branch family members failing on a `trunk` repo with the config naming it (tests/test_worktrees.py::BaseBranchFamily) | 1 | 0 | tests/test_worktrees.py::test_C12_every_member_takes_its_base_from_the_config | rule: U21; the base-branch promise is tested once per member, so a tool added later fails until it reads the config the same way |
| R-12 | CLOSED | `scripts/chrysalis.py` had grown to 1,341 lines and `tests/test_chrysalis.py` to 768, against the about-500-line limit U9 sets for a source file, and no check enforced the limit | lines in the largest Python file under scripts/, hooks/, tests/ and skills/ | 1341 | 444 | tests/test_governance.py::test_C15_check_fails_on_a_source_file_over_the_line_limit | rule: U9; `chrysalis.py check` (gate F1) now fails on any source file over 500 lines; the tool is 14 modules by responsibility and the spec tests 3 files |

R-8 to R-10 came from an outside review of `chrysalis.py` on 2026-11-27. The same review raised 2
points that were not defects and were hardened anyway: a K-table flag that is not true or false now
raises instead of being read as truthy (config validation already rejected such values), and `plan`
names the guardrails file it would write to the home folder, with `--no-home` to skip it.

R-11 was found the same day by applying U21 to R-8: the base-branch promise had been fixed for
`worktree` and not for `lusser parts`. `BaseBranchFamily` now runs it once per tool that picks a base.

R-12 was found by the outside review of 2026-11-28 being acted on: the new commands pushed `chrysalis.py` further past U9's limit, and the check written for it found the test file over the limit too.

R-4 and R-5 were held at the 14-part budget until the budget was raised to 16 (2026-11-26), then fixed
with regression tests that failed before the fix.

## Unreproduced

- (none)
