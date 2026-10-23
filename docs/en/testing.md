# Testing Guide

## Current state

| Platform | Automated tests | Notes |
| --- | --- | --- |
| Android | ✅ Yes | Unit + instrumented tests, below |
| Desktop | ✅ Yes | Rust unit tests, local HTTP mocks, backend/real-WebView smoke tests, Playwright interaction and screenshot checks |
| iOS | ❌ None | No test target |
| HarmonyOS | ❌ None | Manual acceptance only (see below) |
| CI | ✅ Desktop tests | `desktop-check.yml` runs frontend build, fmt / clippy / unit tests and Chromium mock IPC interaction checks on Ubuntu; installers run only in the release workflow |

**Additional tests are welcome** — see [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## Android

### Unit tests (no device needed)

```bash
cd apps/android
./gradlew test
```

Report: `app/build/reports/tests/testDebugUnitTest/index.html`

Existing cases:

| File | Coverage |
| --- | --- |
| `app/src/test/java/com/sjtu/runner/data/DataGeneratorTest.kt` | Route distance correction, truncate mode reaching target, full-loop mode, over-long route truncation, pace clamped to rules, payload matching the upload schema |
| `app/src/test/java/com/sjtu/runner/update/UpdateCheckerTest.kt` | Version parsing (prefix / prerelease), newer tag detected, older/equal ignored |
| `app/src/test/java/com/sjtu/runner/stats/SemesterStatsTest.kt` | Semester range validity, calendar week splitting (Monday-first, month title only on the first row), counted / invalid / no-run states and "counted is never overwritten", completion-rate and kilometre formatting, plan derived from the semester gap |
| `app/src/test/java/com/sjtu/runner/stats/RunScheduleTest.kt` | Continuous backwards generation when skipping is off, already-recorded days moved earlier with the count unchanged when it is on, the 120-day and semester-start bounds, skipped-day log wording |

### Instrumented tests (device or emulator)

```bash
cd apps/android
./gradlew connectedAndroidTest
```

Case: `app/src/androidTest/java/com/sjtu/runner/AppInstrumentedTest.kt`.

### Adding a test

- Pure logic (data generation, version compare, coordinate math) → `app/src/test/`, JUnit 4.
- Anything needing a Context or UI → `app/src/androidTest/`, AndroidX JUnit + Espresso / Compose Test.

### Semester data manual acceptance (device, valid account required)

Automated tests only cover pure logic (semester range, calendar states, date scheduling). Check these on a device:

- [ ] Not logged in: "本学期进度" shows `--` and "学期日历" is a placeholder calendar saying "服务器未返回本学期起止日期。"
- [ ] After a successful login both cards sync automatically with no manual refresh; after logging out they return to `--` and the placeholder calendar
- [ ] The calendar distinguishes counted (solid green), invalid (outlined) and no-run (grey) days, days outside the semester are blank cells, weeks start on Monday
- [ ] A failed semester sync logs one line, leaves the login state untouched and never logs you out
- [ ] The first sync after login fills "run count × distance per run" from the semester gap; once you edit either value by hand the plan is no longer rearranged and the log says why
- [ ] Auto-filled count and distance survive a restart
- [ ] With "skip days that already have a record" on, recorded days move to earlier dates and the count still equals what was configured; with it off, dates are generated continuously backwards from the end date
- [ ] Overlay notices collapse after 5 seconds without pushing content below down; the same text stays in the Task log
- [ ] On other tabs the compact running bar can stop the task, and nothing further is sent after stopping
- [ ] Contrast of the three calendar states and card colors is correct in both light and dark themes
- [ ] Logs and preferences contain no cookie, uid or server response body

---

## Desktop

Automated tests and static checks:

```bash
pnpm --dir desktop install --frozen-lockfile
pnpm --dir desktop build                  # tsc --noEmit + vite build
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 -m unittest discover -s scripts -p "test_*.py"
```

### Backend offline smoke

The release binary's `--smoke-test target/smoke` starts no window. It verifies default-route parsing, offline track generation, input bounds and the placeholder calendar, then writes `smoke-result.json`. It never logs in or uploads.

`--login-smoke-test target/login-smoke` anonymously fetches and recognises a captcha and writes `login-smoke-result.json`; it submits no account and stores no real captcha. `--map-smoke-test target/map-smoke` starts the local map server, writes `preview-url.txt` and `planner-url.txt`, and keeps running for browser checks (tiles, Referer, attribution, error states); stop it with Ctrl+C.

### Real-WebView smoke

```bash
./target/release/sjturunningman --ui-smoke-test target/ui-smoke
```

This opens a real Tauri window, waits for React to render, then checks the workbench, `md-*` component registration, the track SVG, the consent dialog (open / check / close), the map embedded in the preview card (iframe, frame-ready message, no "已在地图中显示当前轨迹" top notice, no "Collapse map" on the workbench, and SVG restored after collapsing in Route management) and all four navigation pages. The result is written to `target/ui-smoke/ui-smoke-result.json`; the exit code is 0 when `success` is `true`. It uses an isolated data directory and never logs in or uploads.

### Playwright visual and interaction checks (optional)

`desktop/e2e/` runs the production frontend in Chromium with a mocked IPC layer. It covers form binding, select, switch, theme, segmented buttons, login, two-factor, task events and logs. It never contacts SJTU services and does not replace real-WebView acceptance.

```bash
pnpm --dir desktop build
pnpm --dir desktop exec vite preview --port 4173 --strictPort   # terminal 1
node desktop/e2e/check.mjs                                      # terminal 2: assertions
node desktop/e2e/screenshot.mjs                                 # screenshots in /tmp/ui-shots
```

### Manual checklist

- [ ] The consent dialog gates entry; Exit closes the app.
- [ ] Incomplete login disables submission; typing and IME confirmation neither send a request nor clear the password. Visibility / CAPTCHA refresh never log in. Clicking Login or pressing Enter on a complete form submits once; editing after failure clears the old error.
- [ ] Runs 0 / 31, distance NaN / 0 / 1.19 / 5.01 / 6, malformed date are rejected; the start time can only be chosen through the picker and is always valid.
- [ ] Chinese text, light/dark themes, Tab / Enter / Space, display scaling and small-window scrolling work; the native title bar follows the theme.
- [ ] Navigation, cards, buttons, text fields, selects, switches and dialogs use Material Design 3 roles and shapes; no other UI component library is mixed in.
- [ ] Offline tracks match the selected distance at 1.20 / 1.21 / 4 / 5 km without an extra 200 m; open routes reverse, closed routes loop; gaps over 150 m are highlighted in red with a warning.
- [ ] Dragging the distance slider updates the track automatically and clears the stale mark without a top notice; changing runs/date/start time marks it stale, and switching routes shows the raw route again; regenerating updates map, summary and distance together.
- [ ] The slider spans 1.20–5.00 km; Home / End and arrow keys stay within bounds, both distance displays agree, old values below 1.20 km restore to the minimum, and automatic plans respect that minimum.
- [ ] The plan summary updates live with runs, distance, date and start time; a short window can scroll to the route selector.
- [ ] The runs field matches the date/time field height and its helper lines up with the distance helper; the three preview metrics share text baselines; the route menu aligns with the select and is not hidden by the task bar.
- [ ] Clicking start time opens a compact 12-hour time-picker dialog (about 328 px wide, not fullscreen); choosing hour/minute and AM/PM (no seconds) and confirming fills the field, cancel or Esc leaves it unchanged, and the field and summary show `hh:mm AM/PM`.
- [ ] Notices appear as a top-right snackbar, do not push content down, and auto-dismiss after about six seconds; success/error use the matching MD3 container colors.
- [ ] In the single-column layout, the end-date calendar and route dropdown paint above the preview card instead of being covered.
- [ ] Default route, import from the Routes page, duplicate names, persistence and copy-only deletion work; the source remains untouched.
- [ ] "Open in map" embeds the map in the preview card with matching endpoints and track; the workbench has no "Collapse map" button, while Route management can collapse to the SVG; the planner still opens in the browser and its TXT can be imported.
- [ ] With a valid account, automatic CAPTCHA recognition, refresh/manual fallback, and app/email/SMS verification work; the password is cleared from the field immediately after submission.
- [ ] Two-factor verification: app / email / SMS delivery works; a six-digit code submitted within its validity window succeeds; resending invalidates the previous code; errors distinguish expiry, lost session and other codes.
- [ ] After login the semester progress and calendar refresh automatically; while logged out or after a failed refresh they keep placeholders and logout restores them.
- [ ] The calendar distinguishes counted runs (solid blue), invalid records (red outline) and rest days (grey); dates outside the semester are blank; the two log columns scroll without overflow at the 1000×700 minimum window.
- [ ] A failed semester refresh writes one log line only and does not change the login state.
- [ ] In an authorized live run, progress and outcomes are accurate; failed POST requests are not retried.
- [ ] Stop and close prevent further records; an in-flight request may take up to 15 seconds; the UI stays responsive.
- [ ] Logout clears the session; preferences, logs and screenshots contain no real credentials.
- [ ] Smoke results and logs contain no cookies, uid or server response bodies.
- [ ] Updates are checked on demand; network failures are reported.
- [ ] The Windows exe has the expected icon/version, works away from assets, needs WebView2, and depends on no Python/Qt/MSYS2 DLLs.
- [ ] macOS Intel/ARM binaries combine into a universal app; the DMG contains the app and an Applications link; Chinese text is fully visible.
- [ ] Linux amd64/arm64 debs install on matching Ubuntu 24.04 hosts; validate X11, Wayland, WebKitGTK dependencies and the file picker.

Windows/macOS checks do not replace other-platform validation. Offline, mock and `--ui-smoke-test` cannot establish live authentication, two-factor, or upload success.

## iOS manual checklist

- [ ] The project compiles in Xcode without warnings
- [ ] The login page brings up JAccount OAuth2
- [ ] "Start task" after configuring parameters fetches the UID
- [ ] The log scrolls live with per-record progress
- [ ] An expired session shows a working "re-login" button
- [ ] The floating bottom dock shows a matching icon and label for Workbench / Routes / Logs / About; all four switch on tap, the selected capsule can be dragged sideways and snaps to an adjacent item, and horizontal page swipes also switch tabs; while a task runs, non-workbench tabs also show the compact status bar with "stop task"
- [ ] After login the progress card shows qualified kilometres and completion rate; both are `--` when logged out
- [ ] The semester calendar on the Logs tab expands month by month starting on Monday, with solid-green / outlined / grey cells matching the server records
- [ ] With "skip days that already have records" on, recorded days move to earlier dates and the record count is unchanged, the skipped dates are listed in the log; with it off, days are generated consecutively backwards
- [ ] When the look-back hits the semester start or the 120-day cap and still cannot cover the count, the log reports that only N uploadable days were found; when there are none, the task does not start and says so
- [ ] After login the run count and distance per run are set automatically from the missing kilometres with a notice overlay; if you edited either value they stay unchanged and the reason is logged only; auto values survive an app restart
- [ ] After at least one successful upload, the progress card and calendar refresh once

---

## HarmonyOS manual checklist

After changing HarmonyOS code, build once with hvigor (see [build.md](./build.md#harmonyos)), then walk through this list:

**Startup and gate**

- [ ] `assembleHap` succeeds; the installed app starts with no jscrash (in particular, `class constructor cannot called without 'new'` means a custom component was written inside an arrow function — see [harmonyos.md](./harmonyos.md#8-known-arkts-toolchain-traps))
- [ ] First launch shows the full-screen "使用承诺书" card; "我承诺，进入软件" is disabled until the checkbox is ticked
- [ ] "退出" ends the app immediately; after accepting, a restart does not show the gate again

**Login**

- [ ] The main screen has no bottom tab bar; the title "开润" sits on the same row as the account/about icon buttons
- [ ] Tapping the top-right account icon (labelled "登录" when signed out) opens the login page; the Web page loads with a progress bar
- [ ] After login it returns automatically and the status card reads "已登录，点击可退出"; the account icon label becomes "账号"
- [ ] While signed in, tapping the account icon opens the "退出账号" confirmation; confirming returns to the logged-out state
- [ ] Tapping the top-right "关于" icon opens the standalone About page

**Parameters**

- [ ] The Runs dropdown offers 1/3/5/7/10/15/30; picking "自定义…" and typing `0` / `31` clamps back into 1–30
- [ ] After picking "自定义…" the dropdown itself reads 自定义 and the number field appears next to it (no extra empty button)
- [ ] Tapping the start time opens a 24-hour hour/minute/second picker; changing a value and confirming fills it back in (hour caps at 23, minute and second at 59)
- [ ] Tapping the ⓘ icon next to the start-time label explains the jitter rule
- [ ] The whole end-date row is tappable, opens the date picker, and defaults to yesterday
- [ ] Distance slider spans 1–5 km; its value sits on the same line as the "目标距离" label and updates live while dragging, and the "距离" stat card reflects the final value
- [ ] A scrollbar appears on the home page and the About page while scrolling and fades out when idle

**Routes**

- [ ] The dropdown lists the built-in route plus custom routes (with point count and the "内置" marker)
- [ ] "设计新路线" opens the map page; after tapping points and saving it returns to the main page and a toast shows the point count
- [ ] Deleting a non-built-in route asks for confirmation; the built-in route cannot be deleted
- [ ] "预览路线" renders without being logged in (scatter plot plus distance / point / jump-count summary)

**Upload**

- [ ] A 1-run, 4 km configuration finishes and shows "任务完成: 成功 1 条，失败 0 条"
- [ ] The status card steps through 准备中 → 获取认证 → 生成数据 → 上传中 → 已完成 with the progress bar advancing
- [ ] "停止任务" interrupts a running task and the UI does not freeze
- [ ] The log is colour-coded per level (INFO/WARN/ERROR/SUCCESS), auto-scrolls to the bottom, and "清空" works
- [ ] When the selected route is longer than the target distance, "路线距离提醒" appears and all three buttons behave as their hint text says
- [ ] An expired cookie shows the top re-login banner; "登录" returns to the login page

**About and updates**

- [ ] The About page shows version `v4.5.0`, the disclaimer and the project credits (including "鸿蒙版维护：Github@AetherWish")
- [ ] Entering the About page does not jam the content against the back bar: there is a safe area below the back icon and the "关于" title, and the first screen is not covered by the title bar
- [ ] "检查更新" reports either "已是最新版本" or "发现新版本"; on a weak network it shows "检查更新失败：…"
- [ ] The "仓库" and "水源" buttons open the browser

**Theme**

- [ ] After switching the system to dark mode, background / card / text contrast is correct with no white-on-white or black-on-black mismatches

---

## Before committing

```bash
# Android: make sure unit tests pass
cd apps/android && ./gradlew test

# General: confirm no build artifacts or local config got staged
git status
```

See the PR checklist in [CONTRIBUTING.md](../../CONTRIBUTING.md).
