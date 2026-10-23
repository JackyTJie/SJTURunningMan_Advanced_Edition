import { useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';

/** One celebration per mount, independent of the current page and its rerenders. */
export function TaskCelebration({ onComplete }: { onComplete: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    if (reducedMotion.matches || document.hidden) {
      onComplete();
      return;
    }

    // Keep rendering on the main thread: the desktop CSP disallows blob workers.
    const fire = confetti.create(canvas, { resize: true, disableForReducedMotion: true });
    const css = getComputedStyle(canvas);
    const token = (name: string) => css.getPropertyValue(`--app-confetti-${name}`).trim();
    const options: confetti.Options = {
      particleCount: Number(token('particles-per-side')),
      spread: Number(token('spread')),
      startVelocity: Number(token('velocity')),
      gravity: Number(token('gravity')),
      ticks: Number(token('ticks')),
      colors: token('colors').split(',').map((color) => color.trim()),
      shapes: ['square'],
      scalar: Number(token('scalar')),
    };
    const emojiScalar = Number(token('emoji-scalar'));
    const emojiShapes: confetti.BitmapShape[] = [];
    // Older system WebViews may lack OffscreenCanvas/bitmap text support.
    // Keep the paper celebration available if emoji rasterization is unsupported.
    for (const text of ['🎉', '🏃', '🏅', '⭐', '🦄', '💩']) {
      try {
        const shape = confetti.shapeFromText({ text, scalar: emojiScalar });
        if (typeof shape === 'object' && shape.type === 'bitmap') emojiShapes.push(shape);
      } catch {
        break;
      }
    }
    let disposed = false;
    const finish = () => {
      if (disposed) return;
      disposed = true;
      fire.reset();
      onComplete();
    };
    const handleMotion = () => { if (reducedMotion.matches) finish(); };
    const handleVisibility = () => { if (document.hidden) finish(); };
    reducedMotion.addEventListener('change', handleMotion);
    document.addEventListener('visibilitychange', handleVisibility);
    const bursts = [];
    for (const [x, angle] of [[0.05, 60], [0.95, 120]]) {
      const origin = { x, y: 0.95 };
      bursts.push(fire({ ...options, angle, origin }));
      if (emojiShapes.length > 0) {
        bursts.push(fire({
          ...options,
          angle,
          origin,
          particleCount: Number(token('emoji-per-side')),
          shapes: emojiShapes,
          flat: true,
          scalar: emojiScalar,
        }));
      }
    }
    void Promise.all(bursts).then(finish);

    return () => {
      disposed = true;
      reducedMotion.removeEventListener('change', handleMotion);
      document.removeEventListener('visibilitychange', handleVisibility);
      fire.reset();
      for (const shape of emojiShapes) shape.bitmap.close();
    };
  }, [onComplete]);

  return <canvas ref={canvasRef} className="task-celebration" aria-hidden="true" />;
}
