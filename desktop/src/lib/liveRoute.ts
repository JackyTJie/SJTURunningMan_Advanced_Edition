import { useEffect, useMemo, useRef, useState } from 'react';
import type { Point } from './backend';
import { MAX_DISTANCE_KM } from './distance';

export function meters(a: Point, b: Point) {
  const rad = Math.PI / 180;
  const h = Math.sin((b.lat - a.lat) * rad / 2) ** 2
    + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin((b.lon - a.lon) * rad / 2) ** 2;
  return 12742000 * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Match route.rs calibration and open-route return / closed-route looping rules.
export function routeGeometry(raw: Point[]) {
  const points = raw.map(p => ({ lon: p.lon - 0.00651271494735 + 0.000094, lat: p.lat - 0.00560888976477 - 0.000700 }));
  if (points.length < 2) return { points, lengths: [], total: 0 };
  const cycle = [...points];
  if (meters(points[0], points.at(-1)!) > 15) cycle.push(...points.slice(0, -1).reverse());
  else cycle.push(points[0]);
  const lengths = cycle.slice(1).map((p, i) => meters(cycle[i], p));
  return { points: cycle, lengths, total: lengths.reduce((a, b) => a + b, 0) };
}

export function trimRoute(geometry: ReturnType<typeof routeGeometry>, distance: number): Point[] {
  if (geometry.total < 1 || !Number.isFinite(distance)) return [];
  const result = [geometry.points[0]];
  let remaining = Math.max(0, Math.min(distance, MAX_DISTANCE_KM * 1000));
  let index = 0;
  while (remaining > 1e-8 && result.length < 30000) {
    const length = geometry.lengths[index];
    const a = geometry.points[index];
    const b = geometry.points[index + 1];
    if (length > 1e-8) {
      const fraction = Math.min(remaining / length, 1);
      result.push({ lon: a.lon + (b.lon - a.lon) * fraction, lat: a.lat + (b.lat - a.lat) * fraction });
      remaining -= Math.min(remaining, length);
    }
    index = (index + 1) % geometry.lengths.length;
  }
  return result;
}

export function useLiveRoute(raw: Point[], distanceKm: number | undefined) {
  const geometry = useMemo(() => routeGeometry(raw), [raw]);
  const target = (distanceKm ?? 0) * 1000;
  const current = useRef(target);
  const previousGeometry = useRef(geometry);
  const [distance, setDistance] = useState(target);
  useEffect(() => {
    if (distanceKm === undefined) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (previousGeometry.current !== geometry || reduced.matches) {
      previousGeometry.current = geometry;
      current.current = target;
      setDistance(target);
      return;
    }
    const responseMs = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--motion-route-response')) || 45;
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const delta = target - current.current;
      current.current = Math.abs(delta) < 0.05 ? target : current.current + delta * (1 - Math.exp(-Math.max(0, now - last) / responseMs));
      last = now;
      setDistance(current.current);
      if (current.current !== target) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, geometry, distanceKm]);
  return { points: useMemo(() => trimRoute(geometry, distance), [geometry, distance]), bounds: geometry.points };
}
