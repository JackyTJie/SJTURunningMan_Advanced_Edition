/*
 * Copyright (C) 2017, 2020 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0; see public/licenses/Apache-2.0.txt.
 * Modified: TypeScript port of the Material determinate animation and the
 * AndroidX critically damped SpringForce/SpringAnimation used by that drawable.
 */
const f = Math.fround;
export const MAX_LEVEL = 10000;

// SpringForce.updateValues, damping ratio 1, stiffness VERY_LOW (50).
export function springStep(value: number, velocity: number, target: number, milliseconds: number, durationScale = 1) {
  const frequency = Math.sqrt(f(50 / durationScale));
  const dt = Math.trunc(milliseconds) / 1000;
  const displacement = value - target;
  const coeffB = velocity + frequency * displacement;
  const decay = Math.pow(Math.E, -frequency * dt);
  return {
    value: f((displacement + coeffB * dt) * decay + target),
    velocity: f((displacement + coeffB * dt) * decay * -frequency + coeffB * decay),
  };
}

// DrawableWithAnimatedVisibilityChange.getPhaseFraction. Android uses uptime;
// performance.now is the Web monotonic uptime, supplied in integer milliseconds.
export function phaseFraction(uptimeMs: number, wavelength: number, speed: number, durationScale = 1) {
  if (speed === 0 || durationScale === 0) return 0;
  const cycle = Math.trunc(f(f(f(1000 * wavelength) / speed) * durationScale));
  if (cycle === 0) return 0;
  const phase = f((Math.trunc(uptimeMs) % cycle) / cycle);
  return phase < 0 ? f((phase % 1) + 1) : phase;
}

// Android PathInterpolator samples an easing path with 0.002 approximation
// error, then interpolates its x/y tables (see easing.ts).
export type Easing = (fraction: number) => number;

export class DeterminateMotion {
  value = 0;
  velocity = 0;
  amplitude = 1; // DrawingDelegate.ActiveIndicator initial value.
  amplitudeTarget = 0;
  target = 0;
  private pending: number | null = null;
  private springRunning = false;
  private lastFrame: number | null = null;
  private amplitudeStart: number | null = null;
  private amplitudeReverse = false;

  constructor(
    readonly easingOn: Easing,
    readonly easingOff: Easing,
    // BaseProgressIndicatorSpec.waveAmplitudeRampProgressMin/Max. Keep the
    // official defaults; callers can configure the official full-range option.
    readonly amplitudeMin = 0.1,
    readonly amplitudeMax = 0.9,
  ) {}

  private amplitudeForLevel(level: number) {
    return level >= f(this.amplitudeMin * MAX_LEVEL) && level <= f(this.amplitudeMax * MAX_LEVEL) ? 1 : 0;
  }

  setLevel(level: number, animate: boolean) {
    level = Math.trunc(Math.max(0, Math.min(MAX_LEVEL, level)));
    if (!animate) {
      this.target = this.value = level;
      this.velocity = 0;
      this.pending = null;
      this.springRunning = false;
      this.lastFrame = null;
      this.amplitudeStart = null;
      this.amplitude = this.amplitudeTarget = this.amplitudeForLevel(level);
    } else if (this.springRunning) {
      // onLevelChange sets the spring's start value from the drawable's float
      // fraction, preserving Android's level -> fraction -> level rounding.
      this.value = f(f(this.value / MAX_LEVEL) * MAX_LEVEL);
      this.pending = level;
    } else {
      this.target = level;
      this.springRunning = true;
      this.lastFrame = null;
    }
  }

  frame(now: number, width: number, durationScale = 1) {
    now = Math.trunc(now);
    if (durationScale === 0) {
      this.setLevel(this.pending ?? this.target, false);
      return;
    }
    if (this.springRunning) {
      if (this.lastFrame !== null) {
        const dt = Math.trunc((now - this.lastFrame) / durationScale);
        let next;
        if (this.pending !== null) {
          const half = Math.trunc(dt / 2);
          next = springStep(this.value, this.velocity, this.target, half, durationScale);
          this.target = this.pending;
          this.pending = null;
          next = springStep(next.value, next.velocity, this.target, half, durationScale);
        } else {
          next = springStep(this.value, this.velocity, this.target, dt, durationScale);
        }
        this.value = next.value;
        this.velocity = next.velocity;
        // SpringAnimation.getValueThreshold(): minimum visible change * .75;
        // DeterminateDrawable: minimum visible change = MAX_LEVEL / width.
        const threshold = f(f(MAX_LEVEL / Math.max(width, 1)) * 0.75);
        if (Math.abs(this.velocity) < threshold * 62.5 && Math.abs(f(this.value - this.target)) < threshold) {
          this.value = this.target;
          this.velocity = 0;
          this.springRunning = false;
        }
      }
      this.lastFrame = now;
      this.updateAmplitudeTarget(now);
    }
    if (this.amplitudeStart !== null) {
      const elapsed = f(Math.min(1, (now - this.amplitudeStart) / (500 * durationScale)));
      const fraction = this.amplitudeReverse ? f(1 - elapsed) : elapsed;
      this.amplitude = (this.amplitudeReverse ? this.easingOff : this.easingOn)(fraction);
      if (elapsed >= 1) this.amplitudeStart = null;
    }
  }

  private updateAmplitudeTarget(now: number) {
    const level = Math.trunc(this.value);
    const target = this.amplitudeForLevel(level);
    if (target !== this.amplitudeTarget) {
      // DeterminateDrawable cancels a running ValueAnimator, then starts or
      // reverses it. A cancelled/reversed animator begins at the reverse end.
      this.amplitudeTarget = target;
      this.amplitudeReverse = target === 0;
      this.amplitudeStart = now;
    } else if (this.amplitudeStart === null) {
      this.amplitude = target;
    }
  }

  get running() { return this.springRunning || this.amplitudeStart !== null; }
}
