# Python, where to dig

**Input validation**: Anything from a request, file, env var, CLI arg, or queue message. Look for `dict.get` chains with no schema, `int()`/`float()` on user strings without bounds, path joins from user input (`os.path.join` swallows a leading `/`), regexes with catastrophic backtracking on untrusted text.

**Serialization**: `pickle`, `yaml.load` without `SafeLoader`, `marshal`, `shelve`, `jsonpickle`, `eval`/`exec` on anything not a literal. Check what deserialises data from caches, queues, and sessions, that's where this hides.

**Dependency risks**: Unpinned or range-pinned requirements, packages with known CVEs (`pip-audit`), dependencies that shell out or download at import time, typosquat-adjacent names. Check `setup.py`/`pyproject.toml` for build-time code execution.

**Async behaviour**: Blocking calls inside `async def` (sync HTTP, `time.sleep`, file I/O, CPU-heavy work) that stall the event loop. Shared mutable state across coroutines without locks. `asyncio.gather` with `return_exceptions=False` dropping partial results. Tasks created and never awaited or cancelled. Mixing thread pools and event loops.

**Resource exhaustion**: Unbounded reads (`request.data`, `file.read()` with no limit), unbounded collections built from external input, no timeouts on outbound HTTP/DB calls, connection pools without limits, recursion on user-shaped structures, ZIP/decompression bombs, regex DoS.

**Privilege boundaries**: Subprocess calls with `shell=True` or user-shaped args, file operations running as a service account on user-chosen paths, `sudo`/setuid helpers, Django/Flask views missing auth decorators, ORM queries that filter by user only in the view and not the model manager, mass-assignment via `**request.json`.

**Also common**: Mutable default arguments holding state across calls; `except Exception: pass`; logging secrets; `assert` used for validation (stripped under `-O`); timezone-naive datetimes at boundaries; float arithmetic on money.

**Tools E should reach for**: `bandit`, `semgrep --config p/python`, `pip-audit`, `mypy --strict`, `pytest --cov`, `hypothesis` for property tests.
