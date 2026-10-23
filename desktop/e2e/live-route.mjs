import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
  await page.addInitScript({ path: 'e2e/mock-init.js' });
  await page.addInitScript(() => {
    window.__HOLD_MAP__ = true;
    const invoke = window.__TAURI_INTERNALS__.invoke;
    window.__TAURI_INTERNALS__.invoke = (command, ...args) =>
      command === 'preview_map' && window.__HOLD_MAP__ ? Promise.resolve(null) : invoke(command, ...args);
  });
  await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
  await page.locator('md-dialog[open] md-checkbox').click();
  await page.locator('md-dialog[open] md-filled-button').click();
  await page.waitForTimeout(500);
  const slider = page.getByRole('slider', { name: '单次距离' });
  await slider.focus();
  await slider.press('Home');
  await page.waitForTimeout(700);
  assert.equal(await slider.getAttribute('aria-valuenow'), '1.2');
  // Hold backend responses: geometry must continue updating without IPC completion.
  await page.evaluate(() => {
    const invoke = window.__TAURI_INTERNALS__.invoke;
    window.__TAURI_INTERNALS__.invoke = (command, ...args) => command === 'preview_route' ? new Promise(() => {}) : invoke(command, ...args);
  });
  const frames = await page.evaluate(async () => {
    const read = () => ({
      path: document.querySelector('.map-line').getAttribute('d'),
      start: document.querySelector('.map-start circle').getAttribute('cx'),
      end: document.querySelector('.map-end circle').getAttribute('cx'),
    });
    const samples = [read()];
    document.querySelector('m-slider').dispatchEvent(new CustomEvent('input', { detail: { value: 1.5 }, bubbles: true }));
    for (let i = 0; i < 10; i++) {
      await new Promise(requestAnimationFrame);
      samples.push(read());
    }
    return samples;
  });
  assert.ok(new Set(frames.map(f => f.path)).size > 3, 'route must update across animation frames without backend response');
  assert.ok(new Set(frames.map(f => f.end)).size > 3, 'endpoint must move over intermediate positions');
  assert.equal(new Set(frames.map(f => f.start)).size, 1, 'projection must stay fixed');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await slider.press('Home');
  await page.waitForTimeout(80);
  const reduced = await page.locator('.map-line').getAttribute('d');
  assert.equal(reduced, frames[0].path, 'shortening returns to the same endpoint; reduced motion settles immediately');
  await page.evaluate(() => { window.__HOLD_MAP__ = false; });
  await page.locator('md-outlined-button').filter({ hasText: '在地图中打开' }).click();
  await page.waitForTimeout(300);
  const iframe = await page.locator('.route-map-frame').elementHandle();
  await slider.press('ArrowRight');
  await page.waitForTimeout(350);
  assert.ok(await iframe.evaluate(el => el.isConnected), 'distance changes must preserve the embedded map');
  await page.screenshot({ path: '/tmp/sjturunningman-live-route.png' });
  console.log('Live route checks passed');
} finally {
  await browser.close();
}
