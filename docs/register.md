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

| R-6 | CLOSED | `tests/run_all.py` printed PASS for the evidence suite when 2 of its 3 tests were skipped (any machine without the local source copies), against U2's "a test that cannot run reports itself skipped" | suites reported as plain PASS while holding skipped tests, fresh clone | 1 | 0 | tests/test_chrysalis.py::test_C8_suite_with_skipped_tests_is_not_reported_as_plain_pass | rule: the runner reads the skip count from every unittest log; found by running the suites in a fresh clone before adding CI |
| R-7 | CLOSED | `tests/validate_real.py` crashed with FileNotFoundError on a machine without `tests/evidence_roots.local.json`, while the README said it skips | tracebacks from validate_real.py with no local roots file | 1 | 0 | tests/test_chrysalis.py::test_C13_validation_without_local_copies_skips_with_a_nonzero_exit | rule: a missing input is a named skip with exit 3, never 0 (U2, U17); CI leaves V1 out by name |

R-4 and R-5 were held at the 14-part budget until the budget was raised to 16 (2026-11-26), then fixed
with regression tests that failed before the fix.

## Unreproduced

- (none)
