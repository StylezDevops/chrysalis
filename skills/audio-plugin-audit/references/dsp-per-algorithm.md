# DSP correctness, per-algorithm deep dive

Load this when the SKILL.md DSP checklist has flagged something and the fix needs algorithm-specific detail, or when the plugin under review is one of the algorithm classes below.

## Filters

### IIR biquad, the workhorse

Coefficient calculation for a Direct Form I or II biquad is where most numerical trouble lives.

Common failure modes:

- **Cutoff at or above Nyquist.** `tan(π · f / sr)` blows up as `f → sr/2`. Clamp cutoff to something like `sr * 0.499` before computing coefficients.
- **Cutoff at 0 Hz.** Some coefficient formulas divide by cutoff. Clamp to something like `20 Hz` minimum, or handle 0 as a special case (pass-through or full-attenuation depending on filter type).
- **Q approaching zero.** Formulas often have `1/Q`, divide-by-zero. Clamp Q to `0.1` minimum.
- **Q very high.** Poles approach the unit circle. Numerically stable at 32-bit float only up to Q around 20-40; above that consider double precision.
- **State denormals.** After the input goes silent, the recursive filter state can decay through denormal values. `juce::ScopedNoDenormals` at the top of `processBlock` handles it globally on x86 by setting FTZ/DAZ.
- **Coefficient interpolation between calls.** If coefficients change abruptly between blocks, the filter can burst. Either smooth the source parameter (cutoff, Q) before computing coefficients, or interpolate the coefficients themselves per-sample. Smoothing the source is usually less costly.

### State variable filter (SVF, Chamberlin, TPT)

Trapezoidal-integrator variants (TPT) are numerically better-behaved than the classic Chamberlin form at high cutoffs. If the code uses the classic form, note the sample-rate ceiling above which it will misbehave.

### One-pole

Rarely a source of bugs, but check that the coefficient uses the correct formula for the sample rate, `a = exp(-2π · fc / sr)` is the standard form.

## Oscillators

### Naive polynomial oscillators

`sin(phase)` where `phase` advances linearly is only correct at low frequencies. As the frequency approaches Nyquist, aliasing dominates the output. For a sine, aliasing is mild (the fundamental is the only partial). For a saw or square, aliasing is catastrophic, you get audible whistling as frequency changes.

### Bandlimited synthesis

Recognised patterns:

- **BLEP (bandlimited step)**: corrects the discontinuity at each transition of a naive saw or square. Look for a `polyBLEP` or `blep` function called at each phase wrap.
- **BLIT (bandlimited impulse train)**: sums windowed sinc impulses.
- **Wavetable with mip-mapping**: separate tables per octave, each bandlimited to its octave.
- **Additive up to Nyquist**: sums sinusoids, culling those above Nyquist.

If none of the above are present and the oscillator generates saw, square, triangle, or ramp waveforms, it aliases.

### Phase accumulator

- Use a `float` or `double` phase in [0, 1) or [0, 2π). Wrap by subtraction after increment, not `fmod`.
- Very high frequencies with float phase lose precision. For frequencies above ~10 kHz, prefer `double`.
- Phase reset (sync) should not click. Blend the pre-reset value into the post-reset over a few samples if the discontinuity is audible.

## Wavetables

### Interpolation

- **No interpolation (nearest neighbour):** audibly gritty even at moderate table sizes. Almost never acceptable.
- **Linear:** the minimum. Introduces first-order high-frequency roll-off.
- **Cubic (Hermite, Catmull-Rom):** noticeably better; standard for musical wavetables.
- **Windowed sinc:** best quality, higher CPU cost. Reserve for slow-changing tables where quality matters most.

### Mip-mapping

A single wavetable played at every pitch either aliases (if not bandlimited) or sounds dull at high pitches (if bandlimited to fundamental only). Mip-mapping keeps multiple bandlimited copies per octave and picks the correct copy based on playback frequency.

Check that:

- Mip levels exist and are populated on load.
- The selection logic picks the correct level for the current playback rate.
- Interpolation between mip levels (to avoid audible switching) is at least crossfaded.

### Wavetable morphing

Interpolating between two wavetables (position parameter) needs to interpolate the samples themselves, not switch abruptly. Check for:

- Position smoothed to prevent clicks on automation.
- Linear interpolation between the two tables' samples per output sample.
- Both tables at the same phase.

### Wraparound

If table size is a power of two, use `phaseIndex & (size - 1)`. Otherwise, an explicit wrap. Check that indices are never negative from unsigned/signed conversion accidents.

## Samplers

### Loop points

Loops require the loop-end sample to connect seamlessly to the loop-start sample. Options:

- **Zero-crossing loops:** the author chose loop points at zero crossings. Works for simple material.
- **Crossfade loops:** blend from loop-end back to loop-start over some number of samples. Standard for musical samples.
- **Sustain-region loops:** the whole sustained portion is treated as one section that plays continuously.

Check that whichever technique is in use is applied consistently, and that loop points near the file boundaries are handled (a loop-end past end-of-file → crash or noise).

### Sample rate conversion

The sample is at some rate; the host is at another; the note pitch shifts it further. The effective ratio is `(hostRate / sampleRate) × (2 ^ (semitonesShift / 12))`. Interpolation needs to handle any ratio.

- **Linear** works for small ratios (subtle pitch changes) but degrades quickly.
- **Cubic** is the standard for musical use.
- **Windowed sinc** is best; expensive.

Check that the interpolation is applied to the source samples, not to whatever comes out of a naive nearest-neighbour lookup.

### Voice management

For a polyphonic sampler, check:

- Voice pool size fixed at construction, not grown on note-on.
- Voice-stealing algorithm defined for the "all voices busy" case (steal quietest, steal oldest, steal same-note, reject).
- Note-off delivered to the correct voice (matching noteNumber, matching MIDI channel if per-channel voicing).
- Voice release doesn't leak, completed voices returned to the free pool.

### Envelope edges

- **Attack of zero:** should not click. Either enforce a small minimum (e.g. 1 ms) or ramp the sample-start from zero.
- **Release of zero:** should not click on note-off. Same treatment.
- **Note-off during attack:** the envelope should go straight to release from wherever it was, not jump to max.
- **Note-off during release:** ignore (already in release) or restart release from current level.
- **Retrigger during release:** either resume from current level (legato) or restart from zero (mono retrigger), defined behaviour, not accidental.

### Sample loading

Never on the audio thread. Load on a background thread, then atomically swap the sample-data pointer. The audio thread checks the pointer at a safe boundary (end of the current block) and switches.

## Waveshapers (CSAW territory)

### Aliasing from the nonlinearity

Any nonlinearity generates harmonics. If the input already contains high frequencies, the harmonics land above Nyquist and fold back as aliasing. The fix is oversampling:

- Upsample by 2×–8× before the shaper.
- Apply the nonlinearity at the oversampled rate.
- Downsample back to host rate with a proper anti-alias filter.

Check that the oversampling ratio is fixed at construction or on `prepareToPlay`, not per-block. Check that the anti-alias filters at both ends have adequate stopband attenuation.

### DC offset

Asymmetric nonlinearities (any curve that isn't odd around zero) generate a DC component from any signal, and grow it further from any signal with DC. Check for a DC blocker after the shaper, typically a one-pole high-pass at ~5–20 Hz.

### Gain compensation

As drive increases, output level increases. Users experience this as "louder = better" and reach for more drive. Compensating output gain against input drive keeps the perceived level constant across the drive range and makes A/B comparison honest.

### Bounded output

Some nonlinearities (`tanh`, `atan`) are bounded and safe. Others (`x + x³`, polynomial expansions) grow unbounded for large inputs and can generate huge output values or NaN. Check that whatever's in use is safe across the full input range, or clamped before the shaper.

### Table-based shapers

If the shaper uses a lookup table, check:

- Interpolation between table entries (linear minimum).
- Input clamped to the table's input range.
- Table large enough to avoid stepping artefacts (a few thousand entries is typical).

## Delays and reverbs

### Circular buffer

- Size in samples = `ceil(maxDelayTime * maxSampleRate)`. Rounded up to power of two if using `& mask` indexing.
- Read and write pointers wrap consistently.
- Initialisation to zero on `prepareToPlay`.
- Buffer cleared on parameter changes that would otherwise leave stale audio in the tail.

### Feedback stability

Feedback gain in a plain delay loop must be `< 1.0` or the delay is a runaway integrator. Common check: clamp the user-facing feedback parameter to [0, 0.99] or similar.

For reverbs with multiple feedback paths (Schroeder, FDN, Freeverb), stability requires the eigenvalues of the feedback matrix to be inside the unit circle. Check that the matrix is well-known-stable (Householder, Hadamard) or that the code has an explicit stability argument in comments.

### Delay time modulation

Modulating a delay tap position changes the effective playback rate, chorus and flanger effects work this way. But naive integer read pointers cause pitch quantisation and clicks. Requirements:

- Fractional delay read with at least linear interpolation.
- All-pass or higher-order interpolation for high-quality effects.
- Time changes smoothed so the rate doesn't jump.

### Allpass and diffusion

Diffusion sections in reverbs use nested all-pass filters. State needs zeroing on `prepareToPlay`. Coefficients (allpass gain) chosen for smooth diffusion without ringing, typical values 0.5–0.7.
