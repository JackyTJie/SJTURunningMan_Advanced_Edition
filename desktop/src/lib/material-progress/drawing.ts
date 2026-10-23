/*
 * Copyright (C) 2020 The Android Open Source Project
 * Licensed under Apache-2.0; see public/licenses/Apache-2.0.txt.
 * Modified: Canvas2D port of LinearDrawingDelegate for the official rounded
 * determinate Wavy style. Canvas2D supplies the Android Canvas drawing surface.
 * Default show/hide modes are SHOW_NONE/HIDE_NONE, as in the upstream style.
 */
import { displayedWave, type Wave } from './path';

export interface ProgressSpec {
  width: number;
  thickness: number;
  amplitude: number;
  wavelength: number;
  gap: number;
  stop: number;
  speed: number;
  activeColor: string;
  trackColor: string;
}
const f = Math.fround;

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  // arcTo also works in WebViews predating CanvasRenderingContext2D.roundRect.
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

// LinearDrawingDelegate.drawRoundedBlock, including the merged corner case
// below one stroke-width at either end. Do not replace this with a narrow pill.
function roundedBlock(ctx: CanvasRenderingContext2D, center: number, width: number, height: number, radius: number, clipCenter?: number, clipRight = false) {
  ctx.save();
  if (clipCenter !== undefined) {
    let clipWidth = width;
    if (clipRight) {
      const diff = (clipCenter - radius) - (center - radius);
      if (diff > 0) { clipCenter -= diff / 2; clipWidth += diff; }
    } else {
      const diff = (clipCenter + radius) - (center + radius);
      if (diff < 0) { clipCenter -= diff / 2; clipWidth -= diff; }
    }
    roundedRect(ctx, clipCenter - clipWidth / 2, -height / 2, clipWidth, height, radius);
    ctx.clip();
    ctx.fillRect(clipRight ? center : center - width / 2, -height / 2, width / 2, height);
  }
  roundedRect(ctx, center - width / 2, -height / 2, width, height, radius);
  ctx.fill();
  ctx.restore();
}

/** drawLine with no grow/escape transforms and the default full rounded caps. */
function drawLine(ctx: CanvasRenderingContext2D, spec: ProgressSpec, wave: Wave, start: number, end: number, startGap: number, endGap: number, amplitudeFraction: number, phase: number, active: boolean) {
  const { width, thickness } = spec;
  start = Math.min(1, Math.max(0, start));
  end = Math.min(1, Math.max(0, end));
  startGap = Math.trunc(f(f(startGap * Math.min(start, f(0.01))) / f(0.01)));
  endGap = Math.trunc(f(f(endGap * f(1 - Math.min(1, Math.max(f(0.99), end)))) / f(0.01)));
  const startPx = Math.trunc(f(f(start * width) + startGap));
  const endPx = Math.trunc(f(f(end * width) - endGap));
  if (startPx > endPx) return;
  const radius = thickness / 2;
  const first = startPx + radius, last = endPx - radius;
  ctx.fillStyle = ctx.strokeStyle = active ? spec.activeColor : spec.trackColor;
  ctx.lineWidth = thickness;
  ctx.lineCap = 'round';
  if (startPx === 0 && endPx < thickness) {
    roundedBlock(ctx, first, thickness, thickness, radius, last, true);
  } else if (startPx > endPx - thickness) {
    roundedBlock(ctx, last, thickness, thickness, radius, first, false);
  } else if (active && spec.amplitude > 0 && spec.wavelength > 0 && amplitudeFraction > 0) {
    const curves = displayedWave(wave, width, f(first / width), f(last / width), f(spec.amplitude * amplitudeFraction), phase);
    if (!curves.length) return;
    ctx.beginPath();
    ctx.moveTo(...curves[0][0]);
    for (const c of curves) ctx.bezierCurveTo(...c[1], ...c[2], ...c[3]);
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.moveTo(first, 0);
    ctx.lineTo(last, 0);
    ctx.stroke();
  }
}

/** DeterminateDrawable.draw: track, active segment, then stop indicator. */
export function drawProgress(ctx: CanvasRenderingContext2D, spec: ProgressSpec, wave: Wave, progress: number, amplitude: number, phase: number, known: boolean) {
  const height = spec.thickness + spec.amplitude * 2;
  ctx.clearRect(0, 0, spec.width, height);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, spec.width, height);
  ctx.clip();
  ctx.translate(0, height / 2);
  drawLine(ctx, spec, wave, spec.gap > 0 ? progress : 0, 1, spec.gap, spec.gap, 0, 0, false);
  if (known) {
    drawLine(ctx, spec, wave, 0, progress, 0, 0, amplitude, phase, true);
    const stop = Math.min(spec.stop, spec.thickness);
    if (stop > 0) {
      ctx.fillStyle = spec.activeColor;
      roundedBlock(ctx, spec.width - spec.thickness / 2, stop, stop, stop / 2);
    }
  }
  ctx.restore();
}
