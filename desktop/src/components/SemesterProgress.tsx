/*
 * Copyright (C) 2020 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Modified for SJTU RunningMan: Web adapter for the source-derived determinate
 * rounded Wavy renderer and animation engine in lib/material-progress/.
 * Source revisions and verification: third_party/material-progress/README.md.
 */
import { useLayoutEffect, useRef } from 'react';
import { createWave } from '../lib/material-progress/path';
import { amplitudeOn, amplitudeOff } from '../lib/material-progress/easing';
import { DeterminateMotion, MAX_LEVEL, phaseFraction } from '../lib/material-progress/motion';
import { drawProgress, type ProgressSpec } from '../lib/material-progress/drawing';

interface SemesterProgressProps {
  value: number | null;
  label: string;
}

export function SemesterProgress({ value, label }: SemesterProgressProps) {
  const ref = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const updateRef = useRef<(() => void) | null>(null);
  const known = value !== null && Number.isFinite(value);
  const percent = known ? Math.min(100, Math.max(0, value)) : 0;
  const inputRef = useRef({ known, percent });
  inputRef.current = { known, percent };

  useLayoutEffect(() => {
    const element = ref.current, canvas = canvasRef.current;
    if (!element || !canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // Official amplitude range configuration, expanded from 10–90% to 0–100%
    // so the semester bar keeps flowing at e.g. 9% and after reaching 100%.
    const motion = new DeterminateMotion(amplitudeOn, amplitudeOff, 0, 1);
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let spec: ProgressSpec;
    let wave: ReturnType<typeof createWave>;
    let frame: number | null = null;
    let disposed = false;

    const draw = (now: number) => {
      if (!spec || spec.width <= 0) return;
      const scale = reducedMotion.matches ? 0 : 1;
      motion.frame(now, spec.width, scale);
      const phase = phaseFraction(now, spec.wavelength, spec.speed, scale);
      drawProgress(ctx, spec, wave, Math.fround(motion.value / MAX_LEVEL), motion.amplitude, phase, inputRef.current.known);
    };
    const animate = (now: number) => {
      frame = null;
      if (disposed || document.hidden) return;
      draw(now);
      if (!reducedMotion.matches && inputRef.current.known &&
          (motion.running || (spec.speed !== 0 && motion.amplitude > 0))) {
        frame = requestAnimationFrame(animate);
      }
    };
    const schedule = () => {
      if (frame === null && !document.hidden && !disposed) frame = requestAnimationFrame(animate);
    };
    const update = () => {
      const input = inputRef.current;
      motion.setLevel(input.percent * 100, input.known && !reducedMotion.matches);
      draw(performance.now());
      schedule();
    };
    const measure = () => {
      const css = getComputedStyle(element);
      const number = (name: string) => Number.parseFloat(css.getPropertyValue(`--app-semester-progress-${name}`));
      spec = {
        width: Math.trunc(element.getBoundingClientRect().width),
        thickness: number('thickness'), amplitude: number('amplitude'),
        wavelength: number('wavelength'), gap: number('gap'), stop: number('stop-size'),
        speed: number('speed'),
        activeColor: css.getPropertyValue('--app-semester-progress-active-color').trim(),
        trackColor: css.getPropertyValue('--app-semester-progress-track-color').trim(),
      };
      wave = createWave(spec.width, spec.wavelength);
      const height = spec.thickness + spec.amplitude * 2;
      const ratio = devicePixelRatio || 1;
      canvas.width = Math.ceil(spec.width * ratio);
      canvas.height = Math.ceil(height * ratio);
      canvas.style.width = `${spec.width}px`;
      canvas.style.height = `${height}px`;
      // Use the actual rounded backing dimensions: at e.g. 125% scaling,
      // 10 CSS px occupies 13 backing pixels, not 12.5. This keeps the visible
      // amplitude/thickness in CSS pixels instead of compressing the result.
      ctx.setTransform(canvas.width / Math.max(spec.width, 1), 0, 0, canvas.height / height, 0, 0);
      draw(performance.now());
      schedule();
    };
    const visibilityChanged = () => {
      if (document.hidden && frame !== null) {
        cancelAnimationFrame(frame);
        frame = null;
      } else if (!document.hidden) schedule();
    };
    const motionChanged = () => {
      motion.setLevel(inputRef.current.percent * 100, false);
      draw(performance.now());
      schedule();
    };
    measure();
    updateRef.current = update;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    const themeObserver = new MutationObserver(measure);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    document.addEventListener('visibilitychange', visibilityChanged);
    window.addEventListener('resize', measure);
    reducedMotion.addEventListener('change', motionChanged);
    return () => {
      disposed = true;
      updateRef.current = null;
      if (frame !== null) cancelAnimationFrame(frame);
      observer.disconnect();
      themeObserver.disconnect();
      document.removeEventListener('visibilitychange', visibilityChanged);
      window.removeEventListener('resize', measure);
      reducedMotion.removeEventListener('change', motionChanged);
    };
  }, []);

  useLayoutEffect(() => { updateRef.current?.(); }, [known, percent]);

  return (
    <div
      ref={ref}
      className="semester-progress"
      role={known ? 'progressbar' : 'img'}
      aria-label={label}
      aria-valuemin={known ? 0 : undefined}
      aria-valuemax={known ? 100 : undefined}
      aria-valuenow={known ? percent : undefined}
    >
      <canvas ref={canvasRef} aria-hidden="true" />
    </div>
  );
}
