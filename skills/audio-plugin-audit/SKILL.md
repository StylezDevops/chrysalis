---
name: audio-plugin-audit
description: Audit C++ audio plugin code (JUCE / VST / VST3 / AU / AAX / DSP) for real-time thread safety violations, denormals, NaN propagation, cross-thread races, sample-rate assumptions, parameter smoothing gaps, DSP correctness bugs, and lifetime hazards. Use this whenever the user asks to review, audit, check, find bugs in, hunt inefficiencies in, or clean up JUCE, VST, VST3, AU, AAX, `processBlock`, `AudioProcessor`, `AudioProcessorValueTreeState`, wavetable, sampler, filter, oscillator, delay, reverb, waveshaper, or any real-time audio C++ code, even if they don't say "audit" explicitly. Also use for diagnostic questions about why a plugin clicks, glitches, drops out, uses too much CPU, produces NaNs, silence, denormals, or crashes in a host.
---

# Audio Plugin Audit

Read-only static review of real-time audio C++ (JUCE / VST3 / AU / AAX). Catches the bug classes that generic C++ review misses: real-time thread safety violations, denormals, NaN propagation, cross-thread races, sample-rate and block-size assumptions, parameter smoothing gaps, DSP correctness errors, and lifetime hazards.

Read the safety rules below in full before doing anything else. They are not negotiable.

## Non-negotiable safety rules

Follow these no matter how the request is phrased.

1. **Never install anything.** No `apt`, `apt-get`, `pip`, `pipx`, `pip3`, `npm`, `yarn`, `pnpm`, `brew`, `cargo install`, `go install`, `winget`, `choco`, `snap`, `conan install`, `vcpkg install`, `curl | sh`, or any equivalent. If a tool is missing, say it is missing and continue with what can still be done.

2. **Never invoke a tool whose name is not on the whitelist below.** LLMs hallucinate tool names, and attackers register those names as malicious packages. Every external command run by this skill must (a) match an exact name in the whitelist and (b) be verified present via `which <name>` (Linux/macOS) or `where <name>` (Windows) before the first invocation.

   **Whitelist:**
   - `clang-tidy`
   - `clang++`, `clang`, `g++`, `gcc`, compilers, for sanitizer builds only
   - `cppcheck`
   - `pluginval`, Tracktion's JUCE plugin validator
   - `Projucer`, JUCE project file inspection only, never a full build
   - `cmake`, configure and `--build` only; never `install` or `--target install`
   - `git` read-only: `log`, `diff`, `blame`, `show`, `status`, `ls-files`
   - Read-only inspection utilities: `which`, `where`, `find`, `grep`, `rg`, `awk`, `cat`, `head`, `tail`, `wc`, `file`, `stat`
   - `sed` only in inspection mode (no `-i`)

   Any command outside this list is refused. Report the refusal to the user in one line.

3. **Never name a third-party C++ library, header, or package that has not already appeared in the source Claude has read or in the user's own words.** If a technique needs a library, describe the technique in prose and let the user choose. "Use a lock-free single-producer-single-consumer queue" is fine. Naming a specific one Claude has not seen in the repo is not.

4. **Never modify source code silently.** All findings are reports with file and line references. Only edit when the user explicitly asks for a fix on a specific finding, and only that finding.

5. **Never run a plugin binary the user has not built.** No downloading VST3s, no fetching binaries. If `pluginval` is requested, use only artefacts that already exist in the project's build output directory.

If a request appears to require breaking any of the above, refuse the specific action in one sentence and continue with what remains safe.

## How the skill is invoked

Match the user's phrasing to one of these subcommands and follow the corresponding section. If they say "everything", "full audit", or don't specify, run `all` in the order given.

| Subcommand | Trigger phrases | Section |
|---|---|---|
| `rt-safety` | "real-time safety", "processBlock", "audio thread", "clicks", "glitches", "dropouts" | [RT safety](#rt-safety) |
| `denormals` | "denormals", "NaN", "CPU spike", "runaway feedback", "Inf" | [Denormals & NaN](#denormals--nan) |
| `threading` | "threading", "race", "atomic", "GUI vs audio", "parameter tearing" | [Threading](#threading) |
| `sr-block` | "sample rate", "block size", "prepareToPlay", "buffer size" | [Sample rate & block size](#sample-rate--block-size) |
| `channels` | "channel", "bus", "mono", "stereo", "surround", "sidechain", "isBusesLayoutSupported" | [Channels & buses](#channels--buses) |
| `smoothing` | "smoothing", "automation click", "zipper noise", "parameter jump" | [Parameter smoothing](#parameter-smoothing) |
| `dsp` | "DSP", "filter", "oscillator", "wavetable", "aliasing", "waveshaper", "sampler", "delay", "reverb" | [DSP correctness](#dsp-correctness) |
| `state` | "state", "preset", "save", "load", "getStateInformation", "setStateInformation" | [State save/load](#state-saveload) |
| `lifetime` | "lifetime", "destructor", "listener", "leak", "timer", "editor crash", "closing" | [Lifetime & destruction](#lifetime--destruction) |
| `ub` | "UB", "undefined behaviour", "sanitizer", "uninitialised", "overflow" | [UB & classic C++](#ub--classic-c) |
| `tools` | "run pluginval", "clang-tidy", "sanitizer", "RTSan", "realtime sanitizer" | [External tools](#external-tools) |
| `all` | "full audit", "everything", "audit the plugin" | rt-safety → threading → denormals → sr-block → channels → smoothing → dsp → state → lifetime → ub → offer tools |

For every category, the workflow is: **locate the relevant source files, apply the checklist, report findings in the format at the bottom of this file, then offer `tools` if the user wants runtime verification.**

## RT safety

The highest-value category. `processBlock` and everything it transitively calls must be lock-free, wait-free, allocation-free, syscall-free, and exception-free.

### What to read first

Start at `processBlock` (or `renderNextBlock` for `SynthVoice` subclasses) and walk the call graph outward. Any file matching `*Processor*`, `*Voice*`, `*Engine*`, `*DSP*`, `*Filter*`, `*Oscillator*`, `*Delay*`, `*Reverb*`, `*Wavetable*`, `*Sampler*`, `*Modulator*` is a candidate.

For deeper patterns and idiomatic JUCE fixes, see `references/rt-safety-patterns.md`.

### Checklist

Flag any of these in the audio call graph.

**Heap allocation.** Hard failures:
- `new`, `delete`, `malloc`, `free`, `calloc`, `realloc`
- `std::make_unique`, `std::make_shared`, `std::unique_ptr`/`std::shared_ptr` construction with a payload
- `std::vector::push_back`, `emplace_back`, `resize`, `reserve`, `insert`, `emplace`, `assign`
- `std::string` construction, `+=`, `append`, `format`, any `std::stringstream`
- `std::function` assignment where the target lambda captures more than the small-buffer size (implementation-dependent, treat any capturing lambda assignment as suspect)
- `std::map`, `std::unordered_map`, `std::set`, `std::unordered_set` inserts or `[]` on missing keys
- `juce::Array::add`, `addSorted`, `insert`, `ensureStorageAllocated` (may reallocate mid-callback)
- `juce::String` operations that construct new strings
- `juce::AudioBuffer<T>` constructed inside `processBlock` (should live on the processor and be resized in `prepareToPlay`)
- `juce::HeapBlock`, `juce::MemoryBlock` allocations

**Blocking primitives.** Cause priority inversion and dropouts:
- `std::mutex`, `std::recursive_mutex`, `std::shared_mutex`, `std::lock_guard`, `std::unique_lock`, `std::scoped_lock`
- `juce::CriticalSection`, `juce::ScopedLock`, `juce::ScopedTryLock` (a try-lock is safer but still a smell; note it and understand the fallback path)
- `std::condition_variable::wait`, `wait_for`, `wait_until`
- `std::this_thread::sleep_for`, `sleep_until`
- `juce::Thread::sleep`, `Thread::wait`

**I/O and syscalls:**
- `printf`, `fprintf`, `puts`, `std::cout`, `std::cerr`, `std::clog`
- `fopen`, `fread`, `fwrite`, `fclose`, `std::ofstream`, `std::ifstream`
- `juce::File` operations, `juce::FileInputStream`, `juce::FileOutputStream`
- `juce::Logger::writeToLog`, `juce::Logger::outputDebugString`
- `DBG(...)` in code that survives release builds (JUCE `DBG` is a no-op in release, but check macro guards on any custom logging)
- Any network, socket, HTTP, or IPC call

**GUI / message thread:**
- `juce::Component::repaint`, `juce::Component` construction or destruction
- `juce::MessageManager::callAsync`, `MessageManagerLock`
- `juce::Timer::startTimer`, `stopTimer`, `timerCallback` reached from audio
- Any `juce::gui_basics`-tagged type manipulated inside the audio callback

**Exceptions:**
- `throw` statements reachable from `processBlock`
- Functions that may throw (no `noexcept`), usually acceptable if the invariants guarantee no throw, but flag any `std::stoi`, `std::vector::at`, `std::optional::value`, `std::variant::get` in the hot path

**RT-unsafe standard library:**
- `std::regex` construction or use
- `std::random_device` (may block on entropy)
- `std::async`, `std::future::wait`, `std::promise` interactions
- `std::chrono::system_clock::now` inside tight loops (rarely a real bug, but flag as smell)

### RT safety severity guide

- **CRITICAL**: will click/glitch/dropout on real hosts. Allocation, blocking mutex, exception, any file I/O.
- **HIGH**: will glitch under some conditions. Try-lock in the audio thread, potentially-throwing calls in the hot path, `std::function` assignment mid-block.
- **MEDIUM**: works today but fragile. Complex control flow that could later grow an allocation, `noexcept` missing.

## Denormals & NaN

### Checklist

- Every `processBlock` opens with `juce::ScopedNoDenormals` at the top. Flag if missing.
- Every filter state variable (`z1`, `z2`, `s1`, `s2`, `x1`, `y1`, `xnm1`, `ynm1`, etc.) is initialised to zero in the constructor and in a `reset()` method. Flag any left uninitialised.
- Delay line buffers are cleared in `prepareToPlay` and in `releaseResources`.
- Every `log`, `log2`, `log10`, argument can be ≤ 0?
- Every `sqrt`, `rsqrt`, argument can be < 0?
- Every division, denominator can be zero? (Parameter mappings that reach 0, filter Q at extreme values, envelope times.)
- Every `pow(base, exp)` where `base` can be negative and `exp` is non-integer.
- Every `asin`, `acos` with an unclamped argument (must be in [-1, 1]).
- Feedback loops with gain ≥ 1.0, needs a limiter or an explicit stability argument in a comment.
- IIR filter coefficient calculations near the sample-rate extremes (very low cutoff, cutoff approaching Nyquist).

## Threading

### What to read first

The editor (`*Editor*`, `*Component*`), the processor, and anything using `AudioProcessorValueTreeState`, `AbstractFifo`, `AsyncUpdater`, `Thread`, `ThreadPool`, `TimeSliceThread`.

### Checklist

- Parameters read in `processBlock` via `std::atomic<float>*` from `apvts.getRawParameterValue(id)`, not a cached `float` captured earlier. Flag naked reads.
- Any `float`, `bool`, or `int` written by one thread and read by another must be `std::atomic<T>`. Flag naked shared members.
- GUI → audio uses `juce::AbstractFifo`, a lock-free ringbuffer, or atomic snapshots. Flag anything else.
- Audio → GUI uses `AsyncUpdater::triggerAsyncUpdate` or an atomic + `Timer` poll on the GUI side. Flag any direct `repaint` reached from `processBlock`.
- Sample or preset loading runs on a background thread, then swapped in atomically. Flag file I/O reachable from the audio callback.
- Every `addListener` has a matching `removeListener` in a destructor.
- `MessageManagerLock` is never acquired from the audio thread.
- No shared pointer whose refcount is incremented or decremented on the audio thread (atomic refcounts are lock-free but still an allocation risk if the last release triggers a destructor with allocation).

## Sample rate & block size

### Checklist

- No literal `44100`, `48000`, `88200`, `96000`, `22050` in DSP code. Coefficients recompute from `getSampleRate()`.
- Every allocation sized against sample rate or block size lives in `prepareToPlay`, never in `processBlock`.
- `prepareToPlay(sr, blockSize)` re-initialises filter state, delay lines, wavetable positions, envelope stages.
- `releaseResources` is implemented and clears audio buffers.
- Handles `blockSize == 1` (some hosts probe with this).
- Handles very large `blockSize` (8192 seen in the wild; certain pro tools go higher).
- Handles non-power-of-two block sizes.
- `getSampleRate()` return is guarded before use, or `prepareToPlay` is known to have run.

## Channels & buses

### Checklist

- `isBusesLayoutSupported` returns true only for layouts the code actually handles.
- `processBlock` uses `buffer.getNumChannels()`, not a hardcoded 2.
- Handles input and output channel counts differing (sidechain, mono→stereo, stereo→mono).
- Handles zero-channel input on some probe layouts.
- `getBusesLayout().getMainInputChannelSet()` matches downstream assumptions.

## Parameter smoothing

### Checklist

Every continuous parameter (gain, cutoff, resonance, Q, pan, mix, drive, wavetable position, pitch, delay time, feedback) uses either `juce::SmoothedValue<float>` / `LinearSmoothedValue`, `juce::dsp` parameter smoothing, or a hand-rolled one-pole with a documented time constant.

Flag any parameter read directly into a DSP coefficient without smoothing. Flag smoothing time constants below ~5 ms (may still click) or above ~200 ms (feels laggy) unless there's an audible reason.

## DSP correctness

The checks depend on what the code does. Read the file, identify the algorithm class, then apply the relevant subsection. If the algorithm is unclear from the code, ask the user rather than guess.

For deeper per-algorithm patterns, see `references/dsp-per-algorithm.md`.

### Filters
- Coefficient calculation stable across the full sample-rate range (44.1k–384k) and Q range (0.1–20 typical).
- No poles outside the unit circle at any parameter combination.
- Denormal-safe.
- State reset on `prepareToPlay` and on parameter jumps large enough to unsettle the filter (large cutoff jumps).

### Oscillators
- Bandlimited (BLEP, BLIT, PolyBLEP, or a mip-mapped wavetable). Naive `sin`/`saw`/`square` from raw math aliases audibly.
- Phase accumulator wraps cleanly, no `fmod` in the hot path (use subtraction against `TWO_PI` or a wrap mask).
- Sync and reset behaviour documented and correct.

### Wavetables
- Interpolation between samples: linear minimum, cubic or higher preferred.
- Interpolation between wavetables when morphing.
- Mip-mapped or otherwise bandlimited per octave to control aliasing in the top octaves.
- Index wraparound uses `& (size - 1)` on power-of-two sizes, or an explicit wrap that doesn't `%`.
- Table lookup indices are checked against table length.

### Samplers
- Loop points are crossfaded or documented click-safe.
- Sample-rate conversion between file rate and host rate uses proper interpolation (linear is a floor; cubic or windowed sinc preferred for audible artefacts).
- Voice-stealing handles the worst case (all voices busy, new note-on).
- Note-off handled cleanly during every envelope stage.
- Very short attack (< 1 ms) does not click on transient start.
- Zero-length release handled.
- File-loading is off the audio thread with atomic pointer swap of the sample data.

### Waveshapers (CSAW territory)
- Oversampled (typically 2×–8×) to move aliasing above audible range.
- DC blocker after the nonlinearity (waveshapers generate DC).
- Gain compensation across the drive range so output doesn't jump when drive changes.
- Bounded output, soft-clip past a threshold; no `tanh(huge)`-style CPU cliffs.
- Table-based shapers interpolate between entries.

### Delays and reverbs
- Circular buffer size is power-of-two for `& mask` indexing, or wraparound is explicit and correct.
- Feedback gain clamped to < 1.0 (or documented as intentionally unstable, e.g. self-oscillating).
- Allpass and diffusion state initialised to zero.
- Modulated delay time uses interpolated read (linear at minimum; all-pass or cubic preferred).
- Delay time changes are smoothed to avoid pitch-jump artefacts.

## State save/load

### Checklist

- `getStateInformation` and `setStateInformation` present.
- Version field written and read; unknown versions handled gracefully.
- Missing fields on load default sanely, no crash.
- State applied on the message thread with audio-thread-visible changes done atomically, or the processor is suspended (`suspendProcessing(true)`) during the swap.
- Round-trip test: save state, load into a fresh instance, verify identical audio output for a fixed input.

## Lifetime & destruction

### Checklist

- Editor's destructor removes every listener the editor added to the processor or to `apvts`.
- Every `Timer::startTimer` has a matching `stopTimer` in the destructor.
- Processor does not hold a raw pointer to an editor (use `WeakReference` or check `getActiveEditor()` at use sites).
- No `Component` subclass stores a raw pointer to another `Component` it does not own.
- Any `std::thread` or `juce::Thread` is joined or stopped before its owning object's destructor returns.
- Audio processor destructor does not release resources the audio thread might still be using, the host stops the audio thread first, but background threads owned by the processor must be joined explicitly.

## UB & classic C++

### Checklist

- All `float`, `double`, `int` members have explicit initialisers in the class body (`= 0.0f`, `= 0`, `{}`).
- All `AudioBuffer` reads use `getReadPointer(ch)` / `getWritePointer(ch)` with a valid channel index.
- Loop bounds use the buffer's actual size, not a cached value from a previous block.
- Delay-line indices use a wide-enough integer type. If `delayLengthSamples × int` can exceed 2³¹, use `int64_t` or `size_t`.
- No signed/unsigned mixing in indexing.
- No `reinterpret_cast` on audio buffers.
- Aligned access if SSE/AVX intrinsics are used.
- No dangling references in captures of lambdas that outlive their scope.

## External tools

Only invoke when the user explicitly asks (e.g. "run pluginval", "sanitizer", "clang-tidy"). For each invocation:

1. Check the whitelist above. Refuse anything not on it.
2. Verify with `which <tool>` (Linux/macOS) or `where <tool>` (Windows). If not found, tell the user which tool is missing and stop, never install.
3. Run read-only where possible. Report the findings, don't apply fixes without explicit confirmation.

### clang-tidy

Look for `.clang-tidy` in the project root. If present, use it. If not, run with the check groups useful for audio code:

```
clang-tidy <file.cpp> \
  --checks='bugprone-*,cert-*,cppcoreguidelines-*,performance-*,readability-*,misc-const-correctness,misc-unused-parameters' \
  -- -std=c++17 -I<juce-modules-path>
```

Do not enable `modernize-*` broadly, some suggestions conflict with real-time constraints. `modernize-use-nodiscard` and `modernize-use-nullptr` are fine.

### Sanitizer builds

Only if the project already builds cleanly. Preferred flags:

- ThreadSanitizer: `-fsanitize=thread -g -O1`
- AddressSanitizer: `-fsanitize=address -fno-omit-frame-pointer -g -O1`
- UndefinedBehaviorSanitizer: `-fsanitize=undefined -g -O1`
- RealtimeSanitizer (Clang 20+): `-fsanitize=realtime`, annotate `processBlock` and its callees with `[[clang::nonblocking]]`

Report which sanitizer detected what, with the stack trace verbatim.

### pluginval

The gold-standard offline validator. Requires a built `.vst3` (or `.component` on macOS) already present in the build directory, never fetch. Run:

```
pluginval --strictness-level 10 --validate <path-to-plugin>
```

Levels 1–5 are lenient; 6–10 stress the plugin. Level 10 fuzzes sample rates, block sizes, bus layouts, parameter automation, and state save/load.

Cross-reference every pluginval failure to a checklist section above.

### RTSan / `-fsanitize=realtime`

Runtime complement to the RT-safety static checklist. Annotate `processBlock` with `[[clang::nonblocking]]`, build with `-fsanitize=realtime`, run in a host or a test harness. Any allocation, lock, or syscall reached from `processBlock` is reported at runtime with a stack trace.

## Output format

Report findings as a single prioritised list. For each finding:

```
### [SEVERITY] Short title
**File:** path/to/file.cpp:LINE
**Category:** rt-safety | denormals | threading | sr-block | channels | smoothing | dsp | state | lifetime | ub
**What:** One sentence describing the problem.
**Why it matters:** One sentence on the audible or functional consequence.
**Suggested fix:** Prose description of the approach. No specific third-party library names unless already present in the codebase.
```

Severities:
- **CRITICAL**: definite audible or functional bug (click, dropout, crash, NaN).
- **HIGH**: bug under realistic conditions (specific sample rates, block sizes, host behaviours, automation patterns).
- **MEDIUM**: works today but fragile; will bite when something changes.
- **LOW**: style or robustness improvement.

Sort the list CRITICAL → HIGH → MEDIUM → LOW.

At the end of every audit, offer runtime verification in one line:

> Static audit done. If you want runtime verification I can run `clang-tidy`, `pluginval`, `-fsanitize=realtime` or a sanitizer build, but only if it is already installed on this machine. Say which.

Never install. Never name a library the user has not mentioned. Never modify source unless explicitly asked.
