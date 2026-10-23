/*
 * Copyright (C) 2020 The Android Open Source Project
 * Material Components Android portions: Apache-2.0.
 * Copyright 2006 Google Inc. / Copyright 2018 Google LLC
 * Skia contour measurement/chopping portions: BSD-3-Clause (Skia-BSD.txt).
 * Modified: TypeScript port of the cubic-only, open contour required by the
 * rounded determinate LinearDrawingDelegate. See third_party/material-progress.
 */
export type Point = readonly [number, number];
export type Cubic = readonly [Point, Point, Point, Point];
const f = Math.fround;
const MAX_T = 0x3fffffff;
const scalarT = (t: number) => f(f(t) * f(1 / f(MAX_T)));
const mix = (a: number, b: number, t: number) => f(f(f(b - a) * t) + a);
const lerp = (a: Point, b: Point, t: number): Point => [mix(a[0], b[0], t), mix(a[1], b[1], t)];

// SkChopCubicAt: de Casteljau, preserving the cubic instead of flattening it.
export function chop(c: Cubic, t: number): readonly [Cubic, Cubic] {
  const ab = lerp(c[0], c[1], t), bc = lerp(c[1], c[2], t), cd = lerp(c[2], c[3], t);
  const abc = lerp(ab, bc, t), bcd = lerp(bc, cd, t), mid = lerp(abc, bcd, t);
  return [[c[0], ab, abc, mid], [mid, bcd, cd, c[3]]];
}

interface Segment { distance: number; curve: number; t: number }

/** Android PathMeasure's Skia cubic contour measurement, default resScale=1. */
export class CubicMeasure {
  readonly curves: readonly Cubic[];
  readonly segments: Segment[] = [];
  length = 0;

  constructor(curves: readonly Cubic[]) {
    this.curves = curves;
    curves.forEach((c, i) => this.measure(c, i, 0, MAX_T, 0));
  }

  private measure(c: Cubic, curve: number, min: number, max: number, depth: number) {
    // SkContourMeasure.cubic_too_curvy: max coordinate deviation from the
    // 1/3 and 2/3 points on the chord, tolerance 0.5, at most 8 subdivisions.
    const curvy = [1, 2].some((i) => {
      const t = f(i / 3);
      const p = lerp(c[0], c[3], t);
      return Math.max(Math.abs(f(c[i][0] - p[0])), Math.abs(f(c[i][1] - p[1]))) > 0.5;
    });
    if (depth < 8 && ((max - min) >> 10) && curvy) {
      const [left, right] = chop(c, 0.5);
      const mid = (min + max) >> 1;
      this.measure(left, curve, min, mid, depth + 1);
      this.measure(right, curve, mid, max, depth + 1);
    } else {
      const dx = f(c[3][0] - c[0][0]), dy = f(c[3][1] - c[0][1]);
      const next = f(this.length + f(Math.hypot(dx, dy)));
      if (next > this.length) this.segments.push({ distance: next, curve, t: scalarT(max) });
      this.length = next;
    }
  }

  at(distance: number): { curve: number; t: number } {
    distance = f(Math.min(this.length, Math.max(0, distance)));
    let low = 0, high = this.segments.length - 1;
    while (low < high) {
      const mid = (low + high) >> 1;
      if (this.segments[mid].distance < distance) low = mid + 1;
      else high = mid;
    }
    const seg = this.segments[low], prev = this.segments[low - 1];
    const startT = prev?.curve === seg.curve ? prev.t : 0;
    const startD = prev?.distance ?? 0;
    const t = f(startT + f(f(f(seg.t - startT) * f(distance - startD)) / f(seg.distance - startD)));
    return { curve: seg.curve, t };
  }

  /** SkContourMeasure.getSegment(): measure first; return exact cubic pieces. */
  segment(start: number, end: number): Cubic[] {
    if (!this.segments.length || start > end || end <= 0) return [];
    const first = this.at(start), last = this.at(end);
    const result: Cubic[] = [];
    for (let i = first.curve; i <= last.curve; i++) {
      const t0 = i === first.curve ? first.t : 0;
      const t1 = i === last.curve ? last.t : 1;
      if (t0 === t1) continue;
      let c = this.curves[i];
      if (t0 > 0) c = chop(c, t0)[1];
      if (t1 < 1) c = chop(c, f(f(t1 - t0) / f(1 - t0)))[0];
      result.push(c);
    }
    return result;
  }
}

/** LinearDrawingDelegate.invalidateCachedPaths(): amplitude stays at +/-1. */
export function createWave(width: number, wavelength: number) {
  const cycles = Math.max(1, Math.trunc(width / wavelength));
  const adjustedWavelength = f(width / cycles);
  const half = f(adjustedWavelength / 2), smoothness = f(0.48);
  const curves: Cubic[] = [];
  const x = (v: number) => f(f(v) * half);
  for (let i = 0; i <= cycles; i++) {
    curves.push([[x(2 * i), 1], [x(f(2 * i + smoothness)), 1], [x(f(2 * i + 1 - smoothness)), -1], [x(2 * i + 1), -1]]);
    curves.push([[x(2 * i + 1), -1], [x(f(2 * i + 1 + smoothness)), -1], [x(f(2 * i + 2 - smoothness)), 1], [x(2 * i + 2), 1]]);
  }
  return { measure: new CubicMeasure(curves), adjustedWavelength };
}

export type Wave = ReturnType<typeof createWave>;

/** LinearDrawingDelegate.calculateDisplayedPath(), including phase compensation. */
export function displayedWave(wave: Wave, width: number, start: number, end: number, amplitude: number, phase: number): Cubic[] {
  const cycles = f(width / wave.adjustedWavelength);
  const phaseInPath = f(phase / cycles), ratio = f(cycles / f(cycles + 1));
  const startD = f(f(f(start + phaseInPath) * ratio) * wave.measure.length);
  const endD = f(f(f(end + phaseInPath) * ratio) * wave.measure.length);
  const translation = f(-f(phase * wave.adjustedWavelength));
  return wave.measure.segment(startD, endD).map((c) => c.map((p) =>
    [f(p[0] + translation), f(p[1] * amplitude)] as Point) as unknown as Cubic);
}
