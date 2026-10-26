import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
page.on('pageerror', (error) => console.log('[pageerror]', error.message));
await page.addInitScript({ path: 'e2e/mock-init.js' });
await page.addInitScript(() => {
  const invoke = window.__TAURI_INTERNALS__.invoke;
  window.__SUBMIT_FAILS__ = false;
  window.__TAURI_INTERNALS__.invoke = (command, ...args) => {
    if (command === 'submit_login' && window.__SUBMIT_FAILS__) {
      return Promise.reject('模拟登录失败');
    }
    return invoke(command, ...args);
  };
});
await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(900);

const calls = async (command) =>
  page.evaluate((name) => window.__MOCK_CALLS__.filter((call) => call.command === name).length, command);

// 承诺书
await page.locator('md-dialog[open] md-checkbox').click();
await page.locator('md-dialog[open] md-filled-button').click();
await page.waitForTimeout(400);

// 打开登录并切到扫码
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(600);
const dialog = page.locator('md-dialog[open]');
const modeQr = dialog.locator('md-outlined-segmented-button').filter({ hasText: '扫码登录' });
const modePassword = dialog.locator('md-outlined-segmented-button').filter({ hasText: '账号密码' });
const qrImage = dialog.locator('img[alt="JAccount 登录二维码"]');
await modeQr.click();
await expect(qrImage).toBeVisible();
await expect(dialog.locator('.qr-heading')).toHaveText('手机扫码登录');
await expect(dialog.locator('.qr-status')).toContainText('等待扫码确认');
assert.equal(await calls('prepare_qr_login'), 1);
assert.equal(await dialog.locator('md-filled-button').count(), 0, '扫码模式不应出现密码登录按钮');
await page.screenshot({ path: '/tmp/sjturunningman-login-qr.png' });

// 后端换码事件只接受当前这一轮
const firstGeneration = await page.evaluate(() => window.__LAST_QR_GENERATION__);
const refreshed = await page.evaluate(() => window.__QR_IMAGES__.refreshed);
await page.evaluate(
  ({ generation, image }) => window.__emitMockEvent('qr-login', { kind: 'image', generation, qr: image }),
  { generation: firstGeneration, image: refreshed },
);
await expect(qrImage).toHaveAttribute('src', refreshed);

// 失败事件显示错误并可刷新重取
await page.evaluate(
  (generation) =>
    window.__emitMockEvent('qr-login', {
      kind: 'failed',
      generation,
      message: '二维码已失效，请重新获取后再扫码',
    }),
  firstGeneration,
);
await expect(dialog.locator('.notice-error')).toContainText('二维码已失效');
await expect(dialog.locator('.qr-heading')).toHaveText('二维码已失效');
await expect(dialog.locator('.qr-status')).toContainText('刷新二维码后即可重新扫码');
await dialog.getByRole('button', { name: '刷新二维码' }).click();
await expect(dialog.locator('.qr-status')).toContainText('等待扫码确认');
await expect.poll(() => calls('prepare_qr_login')).toBe(2);
const secondGeneration = await page.evaluate(() => window.__LAST_QR_GENERATION__);
assert.notEqual(secondGeneration, firstGeneration, '刷新后应换到新一轮扫码');

// 切回密码模式会停止扫码订阅并重新取验证码
await modePassword.click();
await expect(dialog.locator('[name="captcha"] input')).toHaveValue('K7M2');

// 再次扫码；旧一轮的结果必须被忽略，新一轮登录成功后关闭窗口
await modeQr.click();
await expect(qrImage).toBeVisible();
const thirdGeneration = await page.evaluate(() => window.__LAST_QR_GENERATION__);
await page.evaluate(
  (generation) =>
    window.__emitMockEvent('qr-login', {
      kind: 'authenticated',
      generation,
      user: 'student',
      notice: '过期的扫码结果',
    }),
  secondGeneration,
);
await page.waitForTimeout(250);
assert.equal(await page.locator('md-dialog[open]').count(), 1, '过期事件不应关闭登录窗口');
await page.evaluate(
  (generation) =>
    window.__emitMockEvent('qr-login', {
      kind: 'authenticated',
      generation,
      user: '',
      notice: '扫码登录成功，会话仅保留在内存中',
    }),
  thirdGeneration,
);
await expect(page.locator('md-dialog[open]')).toHaveCount(0);
await expect(page.locator('.drawer-status')).toHaveText('已连接 · ***');

// 密码错误后自动换验证码，不需要再手动刷新
await page.locator('md-filled-tonal-button').filter({ hasText: '退出账号' }).click();
await page.waitForTimeout(500);
await page.evaluate(() => { window.__SUBMIT_FAILS__ = true; });
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(700);
const before = await calls('prepare_login');
const passwordDialog = page.locator('md-dialog[open]');
await passwordDialog.locator('[name="username"] input').fill('student');
await passwordDialog.locator('[name="password"] input').fill('test-only-password');
await passwordDialog.locator('[name="captcha"] input').fill('K7M2');
await passwordDialog.locator('md-filled-button').filter({ hasText: '登录' }).click();
await expect(passwordDialog.locator('.notice-error')).toContainText('模拟登录失败');
await expect.poll(() => calls('prepare_login')).toBe(before + 1);
await expect(passwordDialog.locator('[name="captcha"] input')).toHaveValue('K7M2');
await page.screenshot({ path: '/tmp/sjturunningman-login-captcha-refreshed.png' });

console.log('QR login checks passed');
await browser.close();
