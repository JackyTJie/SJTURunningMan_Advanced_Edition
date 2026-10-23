import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 840 } });
page.on('pageerror', (error) => console.log('[pageerror]', error.message));
await page.addInitScript({ path: 'e2e/mock-init.js' });
await page.goto(process.env.E2E_BASE_URL || 'http://localhost:4173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(900);

const calls = async (command) =>
  page.evaluate((name) => window.__MOCK_CALLS__.filter((call) => call.command === name), command);
const lastCall = async (command) => {
  const list = await calls(command);
  return list[list.length - 1];
};

// 承诺书
await page.locator('md-dialog[open] md-checkbox').click();
await page.locator('md-dialog[open] md-filled-button').click();
await page.waitForTimeout(500);
assert.equal(await page.locator('md-dialog[open]').count(), 0, 'consent dialog should close');
await expect(page.locator('.route-map-live iframe')).toHaveCount(1);
const initialMapUrl = await page.locator('.route-map-live iframe').getAttribute('src');
const initialMapCalls = (await calls('preview_map')).length;
assert.ok(initialMapCalls > 0, 'startup should automatically request the online map');

// md3.io 居中日历：定位、跨月、取消与确认。
const datePicker = page.locator('m-datepicker');
const dateValue = () => datePicker.evaluate((element) => element.value);
const openDate = async () => {
  // The picker closes asynchronously; reopening before that finishes races its cleanup.
  await expect(datePicker.locator('dialog')).not.toBeVisible();
  await datePicker.locator('.mtrl-datepicker__trigger').click();
  await expect(datePicker.locator('dialog')).toBeVisible();
  await datePicker.locator('dialog').evaluate(async (panel) => {
    await Promise.all(panel.getAnimations().map((animation) => animation.finished.catch(() => {})));
  });
};
assert.equal(await dateValue(), '2026-10-21');
await openDate();
await expect(datePicker.locator('dialog')).toHaveCSS('opacity', '1');
const calendarBounds = await datePicker.locator('dialog').boundingBox();
assert.ok(Math.abs(calendarBounds.x + calendarBounds.width / 2 - 600) < 2, 'calendar must center horizontally');
assert.ok(Math.abs(calendarBounds.y + calendarBounds.height / 2 - 420) < 2, 'calendar must center vertically');
await page.screenshot({ path: '/tmp/sjturunningman-date-light.png' });
await datePicker.getByRole('button', { name: '下个月', exact: true }).click();
await expect(datePicker.locator('.mtrl-datepicker__month-selector')).toHaveText('11月');
await page.keyboard.press('Escape');
assert.equal(await dateValue(), '2026-10-21', 'browsing and Escape must keep the value');
await openDate();
await datePicker.locator('[data-date="2026-10-20"]').click();
await datePicker.getByRole('button', { name: '确定', exact: true }).click();
assert.equal(await dateValue(), '2026-10-20');
await expect(datePicker.locator('dialog')).not.toBeVisible();
await openDate();
await datePicker.locator('[data-date="2026-10-19"]').click();
await datePicker.getByRole('button', { name: '取消', exact: true }).click();
assert.equal(await dateValue(), '2026-10-20', 'cancel must discard the selected date');

// 表单输入进入 React 状态并传给后端
const fields = page.locator('md-outlined-text-field');
await fields.nth(0).locator('input').fill('3');
const distanceSlider = page.getByRole('slider', { name: '单次距离' });
await distanceSlider.focus();
await distanceSlider.press('End');
assert.equal(await distanceSlider.getAttribute('aria-valuenow'), '5');
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('5.00 km');
await distanceSlider.press('Home');
assert.equal(await distanceSlider.getAttribute('aria-valuenow'), '1.2');
await expect(page.locator('.distance-value')).toHaveText('1.20 km');
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('1.20 km');
await distanceSlider.press('ArrowLeft');
assert.equal(await distanceSlider.getAttribute('aria-valuenow'), '1.2');
await distanceSlider.press('ArrowRight');
assert.equal(Number(await distanceSlider.getAttribute('aria-valuenow')), 1.21);
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('1.21 km');
await distanceSlider.press('End');
for (let step = 0; step < 5; step++) await distanceSlider.press('Shift+ArrowLeft');
assert.equal(Number(Number(await distanceSlider.getAttribute('aria-valuenow')).toFixed(2)), 4.5);
await page.screenshot({ path: '/tmp/sjturunningman-md3-slider.png' });
assert.equal(await page.locator('.distance-value').innerText(), '4.50 km');
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('4.50 km');
assert.equal(await page.locator('.plan-summary-title').innerText(), '3 次 · 合计 13.5 km');
assert.equal(await page.locator('.plan-summary-detail').innerText(), '10月20日截止 · 08:00 AM 前后起跑');
const metricBaselines = await page.locator('.preview-card .metric').evaluateAll((metrics) =>
  metrics.slice(0, 3).map((metric) => ({
    label: metric.querySelector('.metric-label').getBoundingClientRect().y,
    value: metric.querySelector('.metric-value').getBoundingClientRect().y,
  })),
);
assert.ok(metricBaselines.length === 3, 'preview should show three metrics');
assert.ok(
  metricBaselines.every((row) => Math.abs(row.label - metricBaselines[0].label) < 0.5),
  'metric labels should share one baseline',
);
assert.ok(
  metricBaselines.every((row) => Math.abs(row.value - metricBaselines[0].value) < 0.5),
  'metric values should share one baseline',
);
// 单次距离变化后自动同步预览，且不弹顶部提示。
await page.waitForTimeout(500);
const autoPreviewCall = await lastCall('preview_route');
assert.equal(autoPreviewCall.args.request.distance, '4.5', 'distance change should refresh the preview');
assert.equal(autoPreviewCall.args.request.date, '2026-10-20');
assert.equal(await page.locator('.notice').count(), 0, 'automatic preview should stay silent');
assert.equal(await page.locator('.route-map-stale').count(), 0, 'automatic preview should clear stale state');
await page.waitForTimeout(200);
assert.equal(await fields.nth(0).evaluate((element) => element.value), '3');
assert.equal(await page.locator('.preview-card md-filled-tonal-button').count(), 0, 'workbench previews automatically without an extra action');
await expect(page.locator('.route-map-live iframe')).toHaveAttribute('src', initialMapUrl);
assert.equal((await calls('preview_map')).length, initialMapCalls, 'parameter changes must keep the map loaded');
await expect(page.locator('md-outlined-button').filter({ hasText: '收起地图' })).toHaveCount(0);
await expect(page.locator('.preview-card .card-actions')).toHaveCount(0);
// Dates do not invalidate the distance-based workbench geometry.
await openDate();
await page.keyboard.press('Escape');
await expect(page.locator('.route-map-stale')).toHaveCount(0);
await openDate();
await datePicker.locator('[data-date="2026-10-20"]').press('ArrowLeft');
await page.keyboard.press('Enter');
await expect(page.locator('.route-map-stale')).toHaveCount(0);
assert.equal(await dateValue(), '2026-10-19');
await openDate();
await datePicker.locator('[data-date="2026-10-20"]').click();
await datePicker.getByRole('button', { name: '确定', exact: true }).click();
await expect(page.locator('.route-map-stale')).toHaveCount(0);

// 路线管理保留地图切换，工作台直接显示在线地图。
await page.locator('.nav-item').nth(1).click();
await expect(page.locator('.route-map-live iframe')).toHaveCount(1);
await page.locator('md-outlined-button').filter({ hasText: '收起地图' }).click();
await page.locator('md-outlined-button').filter({ hasText: '在地图中打开' }).click();
await page.waitForTimeout(400);
const mapFrame = page.locator('.route-map-live iframe');
assert.equal(await mapFrame.count(), 1, 'map should render inline');
assert.ok((await mapFrame.getAttribute('src')).startsWith('http://127.0.0.1:'));
await page.locator('md-outlined-button').filter({ hasText: '收起地图' }).click();
await page.waitForTimeout(200);
assert.equal(await page.locator('.route-map-live iframe').count(), 0, 'map should collapse');
assert.ok((await page.locator('.route-map .map-line').count()) > 0, 'svg preview should return');
await expect(page.locator('.preview-card md-filled-tonal-button')).toHaveCount(0);
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('4.50 km');
const originalRoutePath = await page.locator('.route-map .map-line').first().getAttribute('d');
await page.locator('.route-list-item').nth(1).click();
await expect(page.locator('.route-list-item').nth(1)).toHaveClass(/is-active/);
await expect(page.locator('.route-map .map-line').first()).not.toHaveAttribute('d', originalRoutePath);
await expect(page.locator('.preview-card .metric-value').first()).toHaveText('4.50 km');
await expect(page.locator('.route-map-stale')).toHaveCount(0);
await page.locator('.route-list-item').first().click();
await expect(page.locator('.route-map .map-line').first()).toHaveAttribute('d', originalRoutePath);

await page.locator('.nav-item').nth(0).click();
await expect(page.locator('.route-map-live iframe')).toHaveCount(1);

// 开关
await page.locator('md-switch').click();
await page.waitForTimeout(500);
const settingsCall = await lastCall('save_settings');
assert.equal(settingsCall.args.settings.skipExisting, false);

// 路线选择
const select = page.locator('.plan-card .route-select');
await select.click();
await page.waitForTimeout(400);
const selectBounds = await select.boundingBox();
const menuBounds = await select.evaluate((element) => {
  const menu = element.shadowRoot?.querySelector('md-menu');
  const surface = menu?.shadowRoot?.querySelector('.menu');
  if (!surface) return null;
  const rect = surface.getBoundingClientRect();
  return { x: rect.x, y: rect.y, bottom: rect.bottom };
});
const taskbarBounds = await page.locator('.task-bar').boundingBox();
assert.ok(menuBounds, 'route menu should be open');
assert.ok(Math.abs(menuBounds.x - selectBounds.x) < 2, 'route menu must align with the select');
assert.ok(menuBounds.y >= selectBounds.y + selectBounds.height - 1, 'route menu must open below the select');
if (menuBounds.bottom > taskbarBounds.y) {
  const menuOnTop = await page.evaluate(
    ({ x, y }) => Boolean(document.elementFromPoint(x, y)?.closest('md-select-option')),
    { x: menuBounds.x + 20, y: taskbarBounds.y + 5 },
  );
  assert.ok(menuOnTop, 'route menu must paint above the task bar');
}
await page.locator('md-select-option').filter({ hasText: 'south-gate-loop' }).click();
await page.waitForTimeout(500);
assert.equal((await lastCall('select_route')).args.name, 'south-gate-loop');
await expect(page.locator('.preview-card iframe')).toHaveAttribute('title', /south-gate-loop/);

// 开始时间：图二的输入式时间选择器，12 小时制，只选时 / 分，不再输入秒。
assert.equal(
  await page.locator('.time-field md-outlined-text-field').evaluate((element) => element.value),
  '08:00 AM',
);
await page.locator('.time-field').click();
await page.waitForTimeout(300);
const timeDialog = page.locator('.mtrl-time-picker__dialog');
await expect(timeDialog).toBeVisible();
const timeBounds = await timeDialog.boundingBox();
assert.ok(timeBounds.width <= 360, 'time picker must stay compact, not fullscreen');
assert.ok(timeBounds.height < 500, 'time picker must stay compact, not fullscreen');
assert.equal(await page.locator('.mtrl-time-picker__seconds').count(), 0, 'seconds must not be shown');
assert.equal(await page.locator('.mtrl-time-picker__period-pm').count(), 1, 'AM/PM selector must be shown');
assert.equal(await page.locator('.mtrl-time-picker__period-am').getAttribute('aria-checked'), 'true');
const hourInput = page.locator('.mtrl-time-picker__hours');
assert.equal(await hourInput.inputValue(), '08');
await hourInput.fill('09');
await page.locator('.mtrl-time-picker__minutes').fill('50');
await page.locator('.mtrl-time-picker__period-pm').click();
await expect(page.locator('.mtrl-time-picker__period-pm')).toHaveAttribute('aria-checked', 'true');
await page.locator('.mtrl-time-picker__confirm').click();
await page.waitForTimeout(400);
await expect(timeDialog).not.toBeVisible();
assert.equal(
  await page.locator('.time-field md-outlined-text-field').evaluate((element) => element.value),
  '09:50 PM',
);
assert.ok((await page.locator('.plan-summary-detail').innerText()).includes('09:50 PM'));

// 重新打开沿用已选时间；取消丢弃草稿。
await page.locator('.time-field').click();
await page.waitForTimeout(300);
assert.equal(await hourInput.inputValue(), '09');
await expect(page.locator('.mtrl-time-picker__period-pm')).toHaveAttribute('aria-checked', 'true');
await hourInput.fill('11');
await page.locator('.mtrl-time-picker__cancel').click();
await page.waitForTimeout(300);
await expect(timeDialog).not.toBeVisible();
assert.equal(
  await page.locator('.time-field md-outlined-text-field').evaluate((element) => element.value),
  '09:50 PM',
  'cancel must keep the committed time',
);

// 主题
await page.locator('.top-bar-actions md-icon-button').first().click();
await page.waitForTimeout(400);
assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark');
assert.equal((await lastCall('save_settings')).args.settings.dark, true);
assert.equal((await lastCall('plugin:window|set_theme')).args.value, 'dark');
assert.equal((await lastCall('plugin:window|set_background_color')).args.value, '#1a1b1f');
await openDate();
await expect(datePicker.locator('dialog')).toHaveCSS('opacity', '1');
await page.screenshot({ path: '/tmp/sjturunningman-date-dark.png' });
await page.keyboard.press('Escape');

// 关于页 / 分段按钮
await page.locator('.nav-item').nth(3).click();
await page.waitForTimeout(400);
await page.locator('md-outlined-segmented-button').filter({ hasText: '隐私' }).click();
await page.waitForTimeout(300);
assert.ok((await page.locator('.about-list').innerText()).includes('Cookie'), 'privacy tab should switch');

// 登录
await page.locator('.nav-item').nth(0).click();
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(700);
const loginFields = page.locator('md-dialog[open] md-outlined-text-field');
const captchaInput = page.locator('md-dialog[open] md-outlined-text-field[name="captcha"] input');
await expect(captchaInput).toHaveValue('K7M2');
await expect(page.locator('md-dialog[open] .notice')).toHaveCount(0);
await captchaInput.fill('k7m2');
await page.getByRole('button', { name: '刷新验证码', exact: true }).click();
await expect(captchaInput).toHaveValue('K7M2');
await captchaInput.fill('k7m2');
await loginFields.nth(0).locator('input').fill('student');
await loginFields.nth(1).locator('input').fill('secret-password');
await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '登录' }).click();
await page.waitForTimeout(800);
const loginCall = await lastCall('submit_login');
assert.equal(loginCall.args.username, 'student');
assert.equal(loginCall.args.captcha, 'k7m2');
assert.equal(await page.locator('md-dialog[open]').count(), 0, 'login dialog should close');
await expect(page.locator('.session-pill')).toHaveCount(0);
await expect(page.locator('.drawer-status')).toHaveText('已连接 · st***');
assert.ok((await page.locator('.semester-value').first().innerText()).includes('62.40'));

// 首页日历复用登录后同步的记录，并在跨月导航后保留标注。
await openDate();
await expect(datePicker.locator('[data-date="2026-10-20"]')).toHaveAttribute('part', /record-valid/);
await expect(datePicker.locator('[data-date="2026-10-21"]')).toHaveAttribute('aria-label', /无效记录/);
await page.screenshot({ path: '/tmp/sjturunningman-date-records.png' });
await datePicker.getByRole('button', { name: '上个月', exact: true }).click();
await expect(datePicker.locator('[data-date="2026-09-19"]')).toHaveAttribute('part', /record-valid/);
await page.keyboard.press('Escape');

// 开始任务 + 事件
await page.locator('md-filled-button').filter({ hasText: '开始任务' }).click();
await page.waitForTimeout(400);
assert.ok((await page.locator('md-dialog[open]').innerText()).includes('确认开始任务'));
await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '确认开始' }).click();
await page.waitForTimeout(500);
const startCall = await lastCall('start_task');
assert.equal(startCall.args.request.runs, '3');
assert.equal(startCall.args.request.distance, '4.5');
assert.equal(startCall.args.request.date, '2026-10-20');
assert.equal(startCall.args.request.time, '21:50:00');
assert.equal(await datePicker.evaluate((element) => element.disabled), true);
assert.equal(startCall.args.request.route, 'south-gate-loop');
assert.equal(await distanceSlider.isDisabled(), true);
await expect(page.locator('.task-status-text')).toBeVisible();
await expect(page.locator('.task-bar md-filled-button')).toContainText('停止任务');
await page.evaluate(() => {
  window.__emitMockEvent('task-log', { message: '第 1 条上传成功' });
  window.__emitMockEvent('task-progress', { value: 50, status: '正在上传第 1/1 条' });
  window.__emitMockEvent('task-finished', {
    success: 1,
    failed: 0,
    stopped: false,
    status: '任务结束 · 成功 1 条，失败 0 条',
    progress: 100,
  });
});
await page.waitForTimeout(500);
await expect(page.locator('.task-status-text')).toHaveCount(0);
await expect(page.locator('.task-bar')).not.toContainText('任务结束');
assert.ok((await page.locator('.notice').innerText()).includes('任务结束'));

// 退出 + 二次验证账号回填
await page.evaluate(() => window.__setMockMode('two_factor'));
await page.locator('md-filled-tonal-button').filter({ hasText: '退出账号' }).click();
await page.waitForTimeout(500);
await openDate();
await expect(datePicker.locator('[part~=record-valid]')).toHaveCount(0);
await expect(datePicker.locator('[part~=record-invalid]')).toHaveCount(0);
await page.keyboard.press('Escape');
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await page.waitForTimeout(700);
await loginFields.nth(1).locator('input').fill('test-only-password');
await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '登录' }).click();
await page.waitForTimeout(600);
const twoFactorText = await page.locator('md-dialog[open]').innerText();
assert.ok(twoFactorText.includes('完成二次验证'));
assert.ok(twoFactorText.includes('student'), '2FA dialog should show the account');

// 自动识别失败时，同一输入框可手动填写并提交。
await page.locator('md-dialog[open] md-text-button').filter({ hasText: '取消' }).click();
await page.evaluate(() => window.__setMockMode('manual'));
await page.locator('md-filled-tonal-button').filter({ hasText: '登录账号' }).click();
await expect(captchaInput).toHaveValue('');
await expect(captchaInput).toBeEnabled();
await captchaInput.fill('K7M2');
await loginFields.nth(1).locator('input').fill('test-only-password');
await page.locator('md-dialog[open] md-filled-button').filter({ hasText: '登录' }).click();
await expect(page.locator('md-dialog[open]')).toHaveCount(0);
assert.equal((await lastCall('submit_login')).args.captcha, 'K7M2');

// 日志页含事件与用户操作
await page.waitForTimeout(400);
await page.locator('.nav-item').nth(2).click();
await page.waitForTimeout(400);
const logText = await page.locator('.log-list').innerText();
assert.ok(logText.includes('第 1 条上传成功'));
assert.ok(logText.includes('登录成功'));

console.log('all functional checks passed');
await browser.close();
