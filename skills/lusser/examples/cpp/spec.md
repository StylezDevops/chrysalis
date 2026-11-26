# Spec: Lock-free SPSC ring buffer for audio-thread parameter changes

Context: JUCE plugin. The message thread pushes parameter-change events; the audio
thread drains them in processBlock. Must never allocate, lock, or block on the audio thread.

Budget: 8 parts
Assumed p: 0.95

## Clauses

- C1. push(event) from the producer thread returns false and leaves the buffer unchanged when the buffer is full; it never blocks or allocates.
- C2. pop(event&) from the consumer thread returns false when empty; it never blocks or allocates.
- C3. Events are delivered in the order pushed (FIFO), with none lost or duplicated, for any interleaving of one producer and one consumer.
- C4. [critical] The audio thread path (pop) contains no locks, no heap allocation, no exceptions and no syscalls, verified, not assumed.
- C5. Capacity is fixed at construction; capacity of 0 or a non-power-of-two is rejected at construction with a clear error.
- C6. Behaviour is identical on x64 and arm64 (Apple Silicon) builds.

## Ambiguities

- A1. Q: When full, should push drop the oldest event (overwrite) or reject the newest (return false)?
      Resolution: Reject newest and return false; caller coalesces on the message thread. Overwrite could drop a "note off". (spec owner, 2026-09-30)
- A2. Q: Is "event" a fixed-size POD, or may it carry a std::string / heap member?
      Resolution: Fixed-size trivially-copyable struct only; static_assert it. (spec owner, 2026-09-30)
- A3. Q: Does "one producer" mean exactly one thread ever, or one at a time with a happens-before between handovers?
      Resolution: Exactly one producer thread for the object's lifetime. Document it; do not try to support handover. (spec owner, 2026-09-30)
