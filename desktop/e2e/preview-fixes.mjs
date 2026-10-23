import assert from 'node:assert/strict';
import fs from 'node:fs';
import { chromium, webkit } from '@playwright/test';

const browser = await (process.env.BROWSER === 'webkit' ? webkit : chromium).launch();
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
  await page.addInitScript({ path: 'e2e/mock-init.js' });
  await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const alignment = await page.locator('.checkbox-row').evaluate(el => {
    const box = el.querySelector('md-checkbox').getBoundingClientRect();
    const span = el.querySelector('span');
    const text = span.getBoundingClientRect();
    return Math.abs(box.y + box.height / 2 - (text.y + parseFloat(getComputedStyle(span).lineHeight) / 2));
  });
  assert.ok(alignment < 1, `checkbox must align to the first text line: ${alignment}`);
  await page.screenshot({ path: '/tmp/sjturunningman-consent-fixed.png' });
  await page.locator('md-dialog[open] md-checkbox').click();
  await page.locator('md-dialog[open] md-filled-button').click();
  await page.waitForTimeout(500);
  const slider = page.getByRole('slider', { name: '单次距离' });
  const rect = await slider.boundingBox();
  await page.mouse.move(rect.x + rect.width * 0.431, rect.y + rect.height / 2);
  await page.mouse.down();
  await page.mouse.move(rect.x + rect.width * 0.437, rect.y + rect.height / 2, { steps: 4 });
  await page.mouse.up();
  const value = Number(await slider.getAttribute('aria-valuenow'));
  assert.ok(Math.abs(value * 10 - Math.round(value * 10)) > 0.001, 'pointer movement must not snap to 0.1 km');
  assert.equal(await page.locator('.preview-card md-filled-tonal-button').count(), 0);

  // Exercise the real map template with deterministic tile lifecycle events.
  const html = fs.readFileSync('src-tauri/src/route_preview.html', 'utf8').replace('__TITLE__', 'Test').replace('__POINTS__', '[{"lon":121.4,"lat":31},{"lon":121.41,"lat":31.01}]');
  const map = await browser.newPage();
  await map.addInitScript(() => {
    const handlers = {};
    window.tileHandlers = handlers;
    const layer = { addTo() { return this; }, on(name, fn) { handlers[name] = fn; return this; } };
    const overlay = () => ({ addTo() { return this; }, bindPopup() { return this; }, setLatLng() {}, setLatLngs() {}, clearLayers() {} });
    window.L = {
      map: () => ({ getContainer: () => document.querySelector('#map'), on() {}, fitBounds() {} }),
      tileLayer: () => layer, polyline: overlay, layerGroup: overlay, circleMarker: overlay,
    };
  });
  await map.route('http://map.test/', route => route.fulfill({ contentType: 'text/html', body: html }));
  await map.goto('http://map.test/');
  await map.evaluate(() => {
    window.testTile = document.createElement('img');
    testTile.style.cssText = 'position:absolute;left:0;top:0;width:256px;height:256px';
    document.querySelector('#map').append(testTile);
    tileHandlers.tileloadstart({ tile: testTile });
    tileHandlers.tileerror({ tile: testTile });
  });
  await map.waitForTimeout(700);
  assert.equal(await map.locator('#map-error.show').count(), 1, 'total tile failure should be reported');
  await map.evaluate(() => {
    tileHandlers.tileunload({ tile: testTile });
    tileHandlers.tileloadstart({ tile: testTile });
    tileHandlers.tileload({ tile: testTile });
  });
  await map.waitForTimeout(700);
  assert.equal(await map.locator('#map-error.show').count(), 0, 'recovered tiles must clear the warning');
  await map.evaluate(() => {
    const obsolete = testTile.cloneNode();
    document.querySelector('#map').append(obsolete);
    tileHandlers.tileerror({ tile: obsolete });
    tileHandlers.tileunload({ tile: obsolete });
    obsolete.remove();
  });
  await map.waitForTimeout(700);
  assert.equal(await map.locator('#map-error.show').count(), 0, 'unloaded zoom tiles must not trigger warnings');
  console.log('Preview fixes passed');
} finally { await browser.close(); }
