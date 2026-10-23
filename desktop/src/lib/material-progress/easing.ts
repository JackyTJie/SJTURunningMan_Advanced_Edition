/*
 * Copyright (C) 2006, 2013, 2022 The Android Open Source Project
 * Apache-2.0; modified: Web port of Android PathInterpolator/Path.cpp sampling.
 * See third_party/material-progress/README.md for source and theme controls.
 */
import type { Point } from './path';
const f = Math.fround;

export function pathInterpolator(x1: number, y1: number, x2: number, y2: number) {
  // Path.cpp.cubicCoordinateCalculation, endpoints (0,0) and (1,1).
  const coordinate = (t: number, p1: number, p2: number) => {
    const inv = f(1 - t), inv2 = f(inv * inv), t2 = f(t * t);
    return f(f(f(f(f(3 * inv2) * t) * p1) + f(f(f(3 * inv) * t2) * p2)) + f(t2 * t));
  };
  const point = (t: number): Point => [coordinate(t, f(x1), f(x2)), coordinate(t, f(y1), f(y2))];
  const errorSquared = f(f(0.002) * f(0.002));
  const points: { t: number; p: Point }[] = [{ t: 0, p: [0, 0] }, { t: 1, p: [1, 1] }];
  const subdivide = (a: { t: number; p: Point }, b: { t: number; p: Point }) => {
    const t = f(f(a.t + b.t) / 2), p = point(t);
    const dx = f(p[0] - f(f(a.p[0] + b.p[0]) / 2));
    const dy = f(p[1] - f(f(a.p[1] + b.p[1]) / 2));
    return { t, p, needed: f(f(dx * dx) + f(dy * dy)) > errorSquared };
  };
  // Path.cpp.addBezier: midpoint and quarter-point inflection checks.
  let doubleCheck = true;
  for (let i = 0; i < points.length - 1;) {
    const mid = subdivide(points[i], points[i + 1]);
    let needed = mid.needed;
    if (!needed && doubleCheck) {
      needed = subdivide(points[i], mid).needed;
      if (needed) doubleCheck = false;
    }
    if (needed) points.splice(i + 1, 0, mid);
    else i++;
  }
  const count = points.length;
  return (fraction: number) => {
    if (fraction <= 0) return 0;
    if (fraction >= 1) return 1;
    let low = 0, high = count - 1;
    while (high - low > 1) {
      const mid = (low + high) >> 1;
      if (fraction < points[mid].p[0]) high = mid;
      else low = mid;
    }
    const range = f(points[high].p[0] - points[low].p[0]);
    if (range === 0) return points[low].p[1];
    const t = f(f(f(fraction) - points[low].p[0]) / range);
    return f(points[low].p[1] + f(t * f(points[high].p[1] - points[low].p[1])));
  };
}

// m3_sys_motion_easing_standard / emphasized_accelerate control points.
export const amplitudeOn = pathInterpolator(0.2, 0, 0, 1);
export const amplitudeOff = pathInterpolator(0.3, 0, 0.8, 0.2);
