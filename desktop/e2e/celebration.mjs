import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript({ path: 'e2e/mock-init.js' });
  await page.addInitScript(() => {
    window.__emojiDraws = 0;
    const createPattern = CanvasRenderingContext2D.prototype.createPattern;
    CanvasRenderingContext2D.prototype.createPattern = function (...args) {
      if (this.canvas.classList.contains('task-celebration')) window.__emojiDraws++;
      return createPattern.apply(this, args);
    };
  });
  await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
  await page.locator('md-dialog[open] md-checkbox').click();
  await page.locator('md-dialog[open] md-filled-button').click();
  await expect(page.locator('md-dialog[open]')).toHaveCount(0);
  const canvas = page.locator('.task-celebration');
  const emit = (payload) => page.evaluate((value) => window.__emitMockEvent('task-finished', {
    success: 1, failed: 0, stopped: false, progress: 100, status: '任务结束', ...value,
  }), payload);

  for (const payload of [{ stopped: true }, { failed: 1 }, { success: 0 }, { success: 0, failed: 1 }]) {
    await emit(payload);
    await page.waitForTimeout(100);
    await expect(canvas).toHaveCount(0);
  }
  await page.evaluate(() => window.__emitMockEvent('task-error', { message: '测试错误', status: '任务失败' }));
  await expect(canvas).toHaveCount(0);

  const hasParticles = () => canvas.evaluate((element) => {
    const pixels = element.getContext('2d').getImageData(0, 0, element.width, element.height).data;
    for (let index = 3; index < pixels.length; index += 4) if (pixels[index] > 0) return true;
    return false;
  });
  await emit({});
  await expect(canvas).toHaveCount(1);
  await expect.poll(hasParticles).toBe(true);
  await expect(canvas).toHaveCSS('pointer-events', 'none');
  await expect.poll(() => page.evaluate(() => window.__emojiDraws)).toBeGreaterThan(0);
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/sjturunningman-confetti-light.png' });
  // Navigation remains usable, and rerendering keeps the same animation instance.
  const firstCanvas = await canvas.elementHandle();
  await page.locator('md-list-item').filter({ hasText: '任务日志' }).click();
  assert.equal(await firstCanvas.evaluate((element) => element.isConnected), true);
  await expect(canvas).toHaveCount(0, { timeout: 7000 });
  await page.waitForTimeout(200);
  await expect(canvas).toHaveCount(0);

  await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; });
  await emit({});
  await expect.poll(hasParticles).toBe(true);
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/sjturunningman-confetti-dark.png' });
  // A new completion replaces an in-flight animation without overlapping canvases.
  await emit({});
  await expect(canvas).toHaveCount(1);
  await expect.poll(hasParticles).toBe(true);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(canvas).toHaveCount(0);
  await emit({});
  await page.waitForTimeout(200);
  await expect(canvas).toHaveCount(0);
  await expect(page.locator('.notice')).toContainText('任务结束');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await emit({});
  await expect.poll(hasParticles).toBe(true);
  await expect(canvas).toHaveCount(0, { timeout: 7000 });
  // An older WebView without OffscreenCanvas should still render ordinary paper.
  await page.evaluate(() => { window.OffscreenCanvas = undefined; });
  await emit({});
  await expect.poll(hasParticles).toBe(true);
  await expect(canvas).toHaveCount(0, { timeout: 7000 });
  assert.deepEqual(errors, []);
  console.log('Confetti checks passed: outcome gating, rendered particles, navigation, cleanup, repeat runs and reduced motion.');
} finally {
  await browser.close();
}
