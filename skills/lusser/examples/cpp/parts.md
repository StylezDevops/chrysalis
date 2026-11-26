# Parts ledger

| # | Part | Kind | Justification | Proven |
|---|------|------|---------------|--------|
| 1 | juce::AbstractFifo | dependency | already in the project; considered as the whole solution, rejected only because we need typed storage, so it is used as the *index* logic under our typed wrapper (C1–C3) | yes, in JUCE since v1.x, used in thousands of shipped plugins |
| 2 | include/ParamEventFifo.h | interface | typed wrapper over AbstractFifo, single header (C1–C5) | no |
| 3 | RapidCheck (vcpkg) | dependency | property tests for C3 in CI only, not shipped | yes, 2014+, widely used, stable API |
| 4 | Catch2 v3 | dependency | spec-tests; already in repo | yes |
| 5 | CMake option LUSSER_RT_CHECKS | config | enables the real-time-violation detector in debug builds (C4) | no |
| 6 | RealtimeSanitizer (-fsanitize=realtime, clang 20+) | dependency | CI job proving C4 mechanically; toolchain feature, not a library | yes, upstream clang (RealtimeSanitizer landed in LLVM 20; confirm your toolchain version) |

Notes: bespoke atomic index logic was considered and rejected, AbstractFifo's index arithmetic has fifteen years of field runs that a fresh implementation cannot match. Decision: buy the hard part, build only the typed shell.
