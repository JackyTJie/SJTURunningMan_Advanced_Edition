import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const OUT = '/tmp/ui-shots';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1200, height: 840 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
page.on('console', (message) => {
  if (message.type() === 'error') console.log('[console]', message.text());
});
page.on('pageerror', (error) => console.log('[pageerror]', error.message));
await page.addInitScript({ path: 'e2e/mock-init.js' });
await page.goto('http://localhost:4173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('shot', name);
};

await shot('01-consent');

await page.locator('md-dialog[open] md-checkbox').click();
await page.locator('md-dialog[open] md-filled-button').click();
await page.waitForTimeout(600);
await shot('02-workbench');

await page.locator('.preview-card md-filled-tonal-button').click();
await page.waitForTimeout(600);
await shot('03-workbench-preview');

await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(800);
await shot('04-login');

await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '登录' }).click();
await page.waitForTimeout(1000);
await shot('05-workbench-logged-in');

await page.locator('.nav-item').nth(2).click();
await page.waitForTimeout(500);
await shot('06-logs');

await page.locator('.nav-item').nth(1).click();
await page.waitForTimeout(500);
await shot('07-routes');

await page.locator('.route-list-item').nth(1).click();
await page.waitForTimeout(600);
await shot('07b-routes-imported');
await page.locator('.route-list-item').nth(0).click();
await page.waitForTimeout(300);

await page.locator('.nav-item').nth(3).click();
await page.waitForTimeout(500);
await shot('08-about');

await page.locator('.nav-item').nth(0).click();
await page.locator('.top-bar-actions md-icon-button').first().click();
await page.waitForTimeout(600);
await shot('09-workbench-dark');

await page.locator('.nav-item').nth(2).click();
await page.waitForTimeout(500);
await shot('10-logs-dark');

// 二次验证
await page.locator('.nav-item').nth(0).click();
await page.evaluate(() => window.__setMockMode('two_factor'));
await page.locator('md-filled-tonal-button').filter({ hasText: '退出账号' }).click();
await page.waitForTimeout(500);
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(700);
await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '登录' }).click();
await page.waitForTimeout(700);
await shot('11-two-factor');
await page.locator('md-dialog[open] md-text-button').filter({ hasText: '取消' }).click();
await page.waitForTimeout(500);

// 手动备用验证码
await page.evaluate(() => window.__setMockMode('manual'));
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(800);
await shot('12-login-manual');
await page.locator('md-dialog[open] md-text-button').filter({ hasText: '取消' }).click();
await page.waitForTimeout(500);

// 窄窗口
await page.setViewportSize({ width: 1000, height: 700 });
await page.waitForTimeout(500);
await shot('13-workbench-1000');
await page.locator('.nav-item').nth(2).click();
await page.waitForTimeout(400);
await shot('14-logs-1000');

await browser.close();
