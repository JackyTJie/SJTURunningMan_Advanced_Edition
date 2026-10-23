// Animated source port: data, boundaries, movement, reduced motion and resizing.
// Run with the preview server on :4173: node e2e/progress.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { chromium, expect } from '@playwright/test';

const mock = readFileSync(new URL('./mock-init.js', import.meta.url), 'utf8');
const browser = await chromium.launch();
try {
  for (const percent of ['0%', '0.5%', '9%', '50%', '80%', '99%', '100%', '125%', '-5%', '--']) {
    const page = await browser.newPage({ viewport: { width: 1200, height: 840 }, deviceScaleFactor: percent === '80%' ? 1.25 : 1 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.addInitScript({ content: `${mock}\nstatsPayload.percent = ${JSON.stringify(percent)};` });
    await page.goto('http://localhost:4173/');
    await page.locator('md-dialog[open] md-checkbox').click();
    await page.locator('md-dialog[open] md-filled-button').click();
    const bar = page.locator('.semester-progress');
    await expect(bar).toHaveAttribute('role', 'img');
    await expect(bar).not.toHaveAttribute('aria-valuenow');
    await expect(bar.locator('canvas')).toBeVisible();

    await page.locator('.top-bar md-filled-tonal-button').click();
    const fields = page.locator('md-dialog[open] md-outlined-text-field input');
    await fields.nth(0).fill('student');
    await fields.nth(1).fill('mock-only');
    await page.locator('md-dialog[open] md-filled-button').click();
    await expect(page.locator('.semester-value').first()).toContainText('62.40');

    const raw = Number.parseFloat(percent);
    const known = Number.isFinite(raw);
    const clamped = known ? Math.min(100, Math.max(0, raw)) : null;
    await expect(bar).toHaveAttribute('role', known ? 'progressbar' : 'img');
    if (known) await expect(bar).toHaveAttribute('aria-valuenow', String(clamped));
    else await expect(bar).not.toHaveAttribute('aria-valuenow');
    const geometry = await bar.locator('canvas').evaluate((canvas) => ({
      width: canvas.width / devicePixelRatio,
      outerWidth: canvas.getBoundingClientRect().width,
      height: canvas.getBoundingClientRect().height,
    }));
    assert.ok(geometry.width > 0 && Math.abs(geometry.width - geometry.outerWidth) < 1);
    assert.equal(geometry.height, 10);

    if (['9%', '99%', '100%'].includes(percent)) {
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.waitForTimeout(100);
      const before = await bar.locator('canvas').evaluate((canvas) => canvas.toDataURL());
      await page.waitForTimeout(200);
      assert.notEqual(await bar.locator('canvas').evaluate((canvas) => canvas.toDataURL()), before,
        `wave must move at ${percent}, outside the upstream default range`);
    }

    if (percent === '80%') {
      await bar.screenshot({ path: '/tmp/semester-progress-light.png' });
      const before = await bar.locator('canvas').getAttribute('width');
      await page.setViewportSize({ width: 1000, height: 700 });
      await expect(bar.locator('canvas')).not.toHaveAttribute('width', before);
      await page.locator('.top-bar-actions md-icon-button').first().click();
      await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
      await bar.screenshot({ path: '/tmp/semester-progress-dark.png' });
      await page.locator('.task-bar').screenshot({ path: '/tmp/semester-progress-footer.png' });
      const pixels = () => bar.locator('canvas').evaluate((canvas) => canvas.toDataURL());
      const staticBefore = await pixels();
      await page.waitForTimeout(200);
      assert.equal(await pixels(), staticBefore, 'reduced motion freezes the wave');
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.waitForTimeout(100);
      const movingBefore = await pixels();
      await page.waitForTimeout(200);
      assert.notEqual(await pixels(), movingBefore, 'wave moves while progress stays at 80%');
      await expect(bar).toHaveAttribute('aria-valuenow', '80');
      // A hidden WebView must not keep repainting; returning resumes the wave.
      await page.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, value: true });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      const hiddenBefore = await pixels();
      await page.waitForTimeout(200);
      assert.equal(await pixels(), hiddenBefore, 'hidden window pauses repainting');
      await page.evaluate(() => {
        delete document.hidden;
        document.dispatchEvent(new Event('visibilitychange'));
      });
      await page.waitForTimeout(200);
      assert.notEqual(await pixels(), hiddenBefore, 'visible window resumes repainting');
      // Task events must not change the semester total to the upload percentage.
      await page.evaluate(() => window.__emitMockEvent('task-progress', { value: 25, status: '正在上传' }));
      await expect(bar).toHaveAttribute('aria-valuenow', '80');
    }
    await page.close();
  }
  console.log('semester progress checks passed (data, boundaries, movement, reduced motion, visibility, resize, theme, task events)');
} finally {
  await browser.close();
}
