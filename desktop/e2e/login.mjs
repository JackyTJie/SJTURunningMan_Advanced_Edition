import assert from 'node:assert/strict';
import { chromium, webkit, expect } from '@playwright/test';

const browser = await (process.env.BROWSER === 'webkit' ? webkit : chromium).launch();
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
  await page.addInitScript({ path: 'e2e/mock-init.js' });
  await page.addInitScript(() => {
    const invoke = window.__TAURI_INTERNALS__.invoke;
    window.__LOGIN_ATTEMPTS__ = 0;
    window.__LOGIN_RESPONSE__ = 'error';
    window.__TAURI_INTERNALS__.invoke = (command, ...args) => {
      if (command !== 'submit_login') return invoke(command, ...args);
      window.__LOGIN_ATTEMPTS__++;
      if (window.__LOGIN_RESPONSE__ === 'hold') {
        return new Promise((_, reject) => { window.__REJECT_LOGIN__ = reject; });
      }
      if (window.__LOGIN_RESPONSE__ === 'error') return Promise.reject('模拟登录失败');
      return invoke(command, ...args);
    };
  });
  await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
  await page.locator('md-dialog[open] md-checkbox').click();
  await page.locator('md-dialog[open] md-filled-button').click();
  await page.getByRole('button', { name: '登录账号', exact: true }).click();

  const dialog = page.locator('md-dialog[open]');
  const account = dialog.locator('[name="username"] input');
  const password = dialog.locator('[name="password"] input');
  const captcha = dialog.locator('[name="captcha"] input');
  const login = dialog.getByRole('button', { name: /^(登录|连接中…)$/ });
  const attempts = () => page.evaluate(() => window.__LOGIN_ATTEMPTS__);
  await expect(captcha).toHaveValue('K7M2');
  await expect(login).toBeDisabled();

  // Incomplete input must neither request login nor erase what is already typed.
  await account.press('Enter');
  await password.fill('test-only-password');
  await password.press('Enter');
  await expect(password).toHaveValue('test-only-password');
  await account.fill('   ');
  await account.press('Enter');
  await expect(login).toBeDisabled();
  await account.fill('student');
  await captcha.fill('');
  await password.press('Enter');
  await dialog.locator('form').evaluate(form => form.requestSubmit());
  await expect(password).toHaveValue('test-only-password');
  await expect(dialog.locator('.notice')).toHaveCount(0);
  assert.equal(await attempts(), 0);
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/tmp/sjturunningman-login-incomplete.png' });
  await captcha.fill('K7M2');
  await expect(login).toBeEnabled();

  // Test composition lifecycle, isComposing and the WebView keyCode 229 fallback.
  await password.evaluate(input => {
    input.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, composed: true }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true, cancelable: true }));
    input.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, composed: true }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, bubbles: true, composed: true, cancelable: true }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 229, bubbles: true, composed: true, cancelable: true }));
  });
  assert.equal(await attempts(), 0, 'IME confirmation must not submit a complete form');
  await expect(password).toHaveValue('test-only-password');

  // Auxiliary buttons must retain their own click and keyboard behavior.
  await dialog.getByRole('button', { name: '显示密码', exact: true }).click();
  await expect(password).toHaveAttribute('type', 'text');
  await dialog.getByRole('button', { name: '隐藏密码', exact: true }).press('Enter');
  await expect(password).toHaveAttribute('type', 'password');
  const refresh = dialog.getByRole('button', { name: '刷新验证码', exact: true });
  await refresh.press('Enter');
  await expect(captcha).toHaveValue('K7M2');
  await expect(password).toHaveValue('test-only-password');
  assert.equal(await attempts(), 0);
  await expect(dialog.locator('.notice')).toHaveCount(0);

  // Actual failures remain visible until the user edits a field.
  for (const field of [account, password, captcha]) {
    await password.fill('test-only-password');
    await login.click();
    await expect(dialog.locator('.notice-error')).toContainText('模拟登录失败');
    await expect(password).toHaveValue('');
    await field.fill(field === password ? 'test-only-password' : field === account ? 'student-edited' : 'k7m2');
    await expect(dialog.locator('.notice')).toHaveCount(0);
  }

  // A synchronous burst of Enter/submit events must make only one request.
  await password.fill('test-only-password');
  await page.evaluate(() => { window.__LOGIN_RESPONSE__ = 'hold'; });
  const before = await attempts();
  await password.evaluate(input => {
    for (let index = 0; index < 3; index++) {
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true, cancelable: true }));
    }
    input.getRootNode().host.closest('form').requestSubmit();
  });
  await expect.poll(attempts).toBe(before + 1);
  await expect(login).toBeDisabled();
  await page.evaluate(() => window.__REJECT_LOGIN__('模拟登录失败'));
  await expect(dialog.locator('.notice-error')).toContainText('模拟登录失败');

  // Once the request settles, ordinary Enter can submit another complete form.
  await password.fill('test-only-password');
  await page.evaluate(() => { window.__LOGIN_RESPONSE__ = 'success'; });
  await password.press('Enter');
  await expect(dialog).toHaveCount(0);
  assert.equal(await attempts(), before + 2);
  console.log('Login interaction checks passed');
} finally {
  await browser.close();
}
