# RT-safety patterns, concrete anti-patterns and fixes

Load this when the SKILL.md checklist has flagged a real-time thread safety concern and you need the pattern-level detail to explain the fix or spot subtler variants. Concrete before/after in prose; no third-party library names.

## 1. Allocation via std::vector inside processBlock

**Anti-pattern:**
The code declares a `std::vector<float>` inside `processBlock`, or resizes a member vector because the block size changed.

**Why it's a bug:**
`std::vector` construction and any capacity-changing operation calls `new` under the hood. `new` can take unbounded time (thread contention on the global heap, page faults, memory pressure). One late block = one audible click.

**Fix in prose:**
Move the vector to a member of the processor. Reserve or resize it in `prepareToPlay` to the maximum block size the host advertised, plus a safety margin. In `processBlock`, only ever write into the existing storage, never resize.

## 2. std::string in a log line

**Anti-pattern:**
Someone left a `DBG("cutoff = " + juce::String(cutoff))` inside `processBlock` during development.

**Why it's a bug:**
`juce::String` construction allocates. Concatenation allocates. Even if `DBG` compiles out in release, it fires in debug, and any developer running your plugin in a debug host will hear glitches or, worse, hit an assertion inside JUCE's allocator that fires on the audio thread.

**Fix in prose:**
Remove the log entirely, or replace with a lock-free ringbuffer of `float` values pushed from the audio thread and drained by a `Timer`-driven callback on the GUI thread that does the formatting there.

## 3. std::mutex protecting a parameter update

**Anti-pattern:**
GUI thread writes `params.cutoff` under a `std::lock_guard`, audio thread reads it under the same lock.

**Why it's a bug:**
If the GUI thread holds the lock when the audio thread arrives, the audio thread blocks. The OS's audio scheduler does not care that a low-priority GUI thread is holding a lock, it will simply miss its deadline. Priority inversion in its textbook form.

**Fix in prose:**
Use `std::atomic<float>` for the parameter. Writes from the GUI are atomic and non-blocking; reads on the audio thread are atomic and non-blocking. If the value needs to be several fields updated together, use a lock-free single-producer-single-consumer queue of "parameter change" structs, or a double-buffered snapshot pointer swapped atomically.

## 4. Sample loading on the audio thread

**Anti-pattern:**
A sampler that reads a `.wav` from disk when a new sample is selected, called from a parameter change handler that runs during `processBlock`.

**Why it's a bug:**
File I/O is unbounded latency. A network-mounted sample library could hang for seconds.

**Fix in prose:**
Push a "load sample X" message onto a lock-free queue drained by a background thread. The background thread reads the file, prepares the sample buffer, and posts a pointer to the loaded data back to the audio thread via an atomic pointer or a lock-free queue. The audio thread swaps in the new pointer at a safe moment (typically start of the next block, gated by an atomic flag).

## 5. std::function assigned during processBlock

**Anti-pattern:**
Code assigns a lambda to a `std::function` member inside the audio callback because the "effect chain" was reconfigured.

**Why it's a bug:**
`std::function` assignment with a capturing lambda may allocate on the heap to store the capture (implementation-defined small-buffer optimisation size). Assumption of no-alloc is not portable.

**Fix in prose:**
Reconfigure effect chains via an index, an enum, or a small POD state struct swapped atomically. Keep all callable objects preallocated as members; never build them mid-block.

## 6. juce::Array::add inside processBlock

**Anti-pattern:**
Voice pool represented as a `juce::Array<Voice*>` with `add` called on note-on inside the MIDI processing loop.

**Why it's a bug:**
`juce::Array::add` may reallocate its backing storage. Same class of failure as `std::vector::push_back`.

**Fix in prose:**
Pre-size the voice pool in `prepareToPlay` to the maximum polyphony. Use a fixed-size array or a preallocated `juce::Array` with `ensureStorageAllocated` called once from `prepareToPlay`. Track voice usage with an atomic flag per voice rather than growing the container.

## 7. throw reachable from processBlock

**Anti-pattern:**
`std::vector::at()`, `std::optional::value()`, or `std::variant::get<T>()` used in the hot path, all throw on unexpected state.

**Why it's a bug:**
Exceptions in `processBlock` unwind through hosts that were not built to catch them. Even where the host tolerates it, the throw itself may allocate (`std::exception::what()` implementations, exception dispatch tables, thread-local exception state).

**Fix in prose:**
Use `operator[]` on containers where the invariants make it safe, and check pointer / optional presence with `if` rather than accessor methods that throw. Mark the whole audio call graph `noexcept` so any accidental throw becomes a compile-time or clean-terminate failure rather than an unwind.

## 8. Direct repaint from processBlock

**Anti-pattern:**
The audio thread computes an RMS level and calls `meterComponent.repaint()` to update the UI.

**Why it's a bug:**
`repaint` interacts with the message manager. On some platforms this needs a lock. Even where it doesn't, it queues work onto the message thread, which may allocate, and definitely violates the layering.

**Fix in prose:**
Have the audio thread write the RMS value into an atomic float. On the GUI side, run a `Timer` at 30 Hz that reads the atomic and calls `repaint` if the value changed. Cheap, correct, and drops updates rather than backing up if the GUI is slow.

## 9. Uninitialised filter state → NaN on first block

**Anti-pattern:**
`float z1, z2;` declared but never assigned before the first `processBlock` runs.

**Why it's a bug:**
Uninitialised floats are undefined bit patterns. Some patterns are NaN. NaN into a filter's feedback path yields NaN forever. Users hear silence, then a click when they finally reset the plugin.

**Fix in prose:**
Initialise every audio-buffer, delay-line, and filter-state member in the class body (`float z1 = 0.0f;`). Provide a `reset()` method that zeroes them all, and call it from `prepareToPlay`.

## 10. try_lock in the audio thread

**Anti-pattern:**
`if (mutex.try_lock()) { … apply update … mutex.unlock(); }` in `processBlock`.

**Why it's a bug:**
Not as bad as a blocking lock, but the "silent skip" path means parameter updates get dropped under contention. Users report "the plugin ignores my knob when I automate quickly."

**Fix in prose:**
Use a lock-free single-producer-single-consumer queue for parameter updates. The GUI pushes; the audio pops. Both operations are wait-free. If the queue is full, very rare, the GUI can coalesce updates on its side.

## 11. Blocking sleep as a "poor man's throttle"

**Anti-pattern:**
`std::this_thread::sleep_for(std::chrono::milliseconds(1))` in a subroutine that ended up called by `processBlock`.

**Why it's a bug:**
Any sleep on the audio thread is a guaranteed dropout for at least the sleep duration.

**Fix in prose:**
Remove the sleep. Whatever throttling was intended must be event-driven, not time-driven, from within the audio thread.

## 12. Timer starting from processBlock

**Anti-pattern:**
Audio detects an event and calls `timer.startTimer(50)` to schedule a UI update.

**Why it's a bug:**
`Timer::startTimer` interacts with the message manager and may allocate its internal scheduling entry.

**Fix in prose:**
Set an atomic flag from the audio thread. Have a persistent `Timer` (started once from the message thread) poll the flag at its regular tick.

## 13. Logging via juce::Logger

**Anti-pattern:**
`juce::Logger::writeToLog(...)` in `processBlock`.

**Why it's a bug:**
`Logger::writeToLog` opens or writes a file. File I/O = unbounded latency.

**Fix in prose:**
Same as pattern 2: ringbuffer of events with GUI-side drain.

## 14. std::regex in a parameter parser

**Anti-pattern:**
Parameter change handler uses `std::regex` to parse a value string, and that handler runs on the audio thread.

**Why it's a bug:**
`std::regex` construction allocates. Compilation is expensive. Some implementations use `throw` internally.

**Fix in prose:**
Parse strings on the GUI thread when they're entered. Only atomic numeric values cross into the audio thread.

## 15. Shared_ptr refcount that triggers a destructor with allocation

**Anti-pattern:**
A `std::shared_ptr<SampleData>` is swapped on the audio thread. The old one's refcount drops to zero, its destructor runs, and the destructor frees a large buffer.

**Why it's a bug:**
The atomic refcount decrement is fine. The destructor that runs at zero is not, `free` on a large allocation can hit the same latency issues as `malloc`.

**Fix in prose:**
The audio thread swaps atomic pointers only, never holds the last reference. Push the old pointer onto a queue drained by a background thread that runs the destructor there.

## Reading the code well

For each `processBlock`, mentally simulate one worst-case call: highest sample rate, largest block size, all voices active, automation on every parameter. Every line has to survive that. If a line only "usually" works, it's a MEDIUM at best.

Follow calls two or three levels deep. Bugs hide in a utility function called from a filter class called from a voice class called from `processBlock`. The utility function's author never thought about real-time constraints.

Read the class members. Any `std::vector`, `std::string`, `std::map`, `std::function`, `std::mutex`, `juce::String`, `juce::Array` that appears in the audio-processing classes is a candidate for closer inspection, not necessarily a bug, but always a "how does this get used" question.

Look for `TODO`, `FIXME`, `XXX`, and `HACK` in the audio call graph. Those are often real-time-safety debts the original author left themselves.
