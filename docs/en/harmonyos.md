# HarmonyOS NEXT Guide

Version **`4.5.0`**, bundle name `com.sjtu.runner` (`apps/harmonyos/AppScope/app.json5`). Project path: `apps/harmonyos/`.

> **Anything not stated here matches the Android build** — parameter ranges, upload flow and logging are aligned. Only the install procedure and login entry point differ.

The HarmonyOS build was contributed by [@AetherWish](https://github.com/AetherWish); the project was migrated from the Android native project (see `apps/harmonyos/oh-package.json5`).

![HarmonyOS main screen](../images/harmonyos-main.webp)

## Contents

- [1. Installing the HAP](#1-installing-the-hap)
- [2. Login](#2-login)
- [3. Parameters](#3-parameters)
- [4. Starting an upload](#4-starting-an-upload)
- [5. Custom routes](#5-custom-routes)
- [6. Permissions](#6-permissions)
- [7. Differences from other platforms](#7-differences-from-other-platforms)
- [8. Known ArkTS toolchain traps](#8-known-arkts-toolchain-traps)
- [9. Route length and preview limits](#9-route-length-and-preview-limits)
- [10. Semester progress, calendar and auto plan](#10-semester-progress-calendar-and-auto-plan)

## 1. Installing the HAP

> ⚠️ **Complete Huawei developer verification first** to extend the debug certificate validity. Without it the debug certificate expires quickly and you must reinstall.

1. **Build the HAP yourself first** — this project **does not ship a prebuilt HarmonyOS package** in Releases. Build and sign it with DevEco Studio, see [build.md](./build.md#harmonyos).
2. On the phone: **Settings → About → tap "Software version" 7 times**, restart, and developer options are enabled.
3. Go to **Settings → System → Developer options → Wireless debugging**, enable it and note the IP and port.
4. Connect the PC and phone to the same network, download [小白调试助手](https://github.com/likuai2010/auto-installer) and run it, following its on-screen instructions.

## 2. Login

1. On first launch a **commitment notice** appears; tick the box and tap "我承诺，进入软件". Tapping "退出" terminates the app. Acceptance is stored in `app_prefs/commitment_accepted` and the notice is not shown again.
2. Tap the **account icon in the top-right corner of the title bar** to reach the login page (it reads "登录" when signed out and "账号" when signed in; tapping it while signed in asks whether to sign out).
3. The page returns automatically when loading finishes; the status card then reads "已登录". If the cookie expires the app re-opens the login page.

> ⚠️ HarmonyOS **cannot** launch the one-tap "交我办" login — web login only. If "交我办" is installed the login page tries to launch it; otherwise it tells you and stays on the web page.

## 3. Parameters

The main screen has **no bottom tab bar**: the title ("开润") sits on the same row as the **semester calendar**, **account** and **about** icon buttons in the top-right corner (self-drawn title bar, see section 8). The "开润" page shows the status card, the semester progress card, the route card, the task settings cards and the run log, from top to bottom.

| Parameter | Range | Default | Notes |
| --- | --- | --- | --- |
| Runs | 1–30 | 1 | Dropdown with 1/3/5/7/10/15/30, or "自定义…" to type a number (the control then reads 自定义) |
| Start time | hour 0–23 / minute 0–59 / second 0–59 (i.e. 00:00:00–23:59:59) | 08:00:00 | Tapping opens the system time picker (24-hour, three columns); each record gets a random **±10 min / ±30 s** jitter (the explanation is folded behind the ⓘ icon next to the label) |
| End date | Date picker | Yesterday | Records are generated backwards from this date; tapping the whole row opens the picker |
| Skip days with records | on / off | on | Still uploads the configured number of runs, but moves the days that already have a record to **earlier** dates; skipped dates are logged, and when the 120-day cap or the semester start is hit the log says only N dates could be used |
| Distance | 1–5 km | 4 km | Per-record target distance, slider step 0.1 km; the value sits on the same line as the "目标距离" label, immediately to its right (`目标距离 4.0 km`) |
| Route | See below | 思源湖路线 | Dropdown; design a new one on a separate page |

Ranges come from `apps/harmonyos/entry/src/main/ets/config/AppConfig.ets`. The home page and the About page both use `BarState.Auto` scrollbars (visible while scrolling, then fading out).

Every task-settings row is a hand-rolled `SettingCard` (`apps/harmonyos/entry/src/main/ets/view/CommonComponents.ets`): a symbol column plus a fixed-width label column, so all rows share exactly the same icon and label left edges; the control column is measured normally by ArkUI. For why `HdsListItemCard` is not used for these rows, see section 8.

## 4. Starting an upload

1. Tap **开始任务** in the bottom action bar.
2. The status card shows the current stage (准备中 / 获取认证 / 生成数据 / 上传中 / 正在停止 / 已完成 / 失败) and a progress bar.
3. **预览路线** generates one track offline from the current settings and shows distance / point count / jump count plus a scatter canvas.
4. When finished the log reports "任务完成: 成功 N 条，失败 M 条". **清空** clears the log (capped at 400 entries).

If the selected route is longer than the target distance, a "路线距离提醒" dialog offers **削减路线** (truncate to the target) or **取消任务**; choosing the full route runs the whole route and syncs the target distance.

While a task is running you can tap **停止任务** to abort it. The stop takes effect at the next loop boundary; if an upload is already in flight, the task ends once that request returns (read timeout 20 s at most) and the UI never freezes.

## 5. Custom routes

1. On the route design page, **tap points in order** on the map.
2. More points fit the road better; **order matters, and the first and last points should be close together**.
3. After saving, pick the new route in the main-screen dropdown. Non-built-in routes can be removed with **删除路线**.

Coordinate format and coordinate-system differences: [routes.md](./routes.md).

## 6. Permissions

Declared in `apps/harmonyos/entry/src/main/module.json5`:

| Permission | Purpose |
| --- | --- |
| `ohos.permission.INTERNET` | Upload data to pe.sjtu.edu.cn, check for updates |
| `ohos.permission.GET_NETWORK_INFO` | Detect network availability |

HarmonyOS **does not read location or phone state**: tracks are interpolated offline from the selected route and upload coordinates are the route coordinates plus a fixed offset, exactly as on Android.

## 7. Differences from other platforms

| Item | Android | HarmonyOS |
| --- | --- | --- |
| How to get it | Download the APK from Releases | **No prebuilt package** — build and sign it yourself with DevEco Studio |
| Install | APK | HAP + debug certificate (limited validity) |
| One-tap login | Yes | No, JAccount web login only |
| Permissions | INTERNET / ACCESS_NETWORK_STATE / READ_PHONE_STATE | INTERNET / GET_NETWORK_INFO |
| Parameters | 1–30 runs / 1–5 km | Same as Android |
| UI toolkit | Material 3 (Compose) | Plain ArkUI (`Navigation` / `NavDestination` plus self-drawn cards, see section 8) |
| Route asset | `route_design.html` (Baidu Maps) | Same asset, stored separately (the bridge object is still named `AndroidInterface`) |
| About / updates | Dialog | Dedicated "About" page |
| Route preview colours | Material theme colours | Fixed blue/orange palette matching the map (`RoutePreviewCanvas.ets`) |
| Automated tests | JVM unit tests | None yet |

Building and packaging: [build.md](./build.md). Coordinate systems: [routes.md](./routes.md).

## 8. Known ArkTS toolchain traps

These compile fine and only fail at runtime on a device, so keep them in mind when changing the UI.

**The UI uses plain ArkUI only and does not depend on the UI Design Kit (HDS).** The earlier implementation
rendered an "immersive material" title bar through `HdsNavigation` / `HdsNavDestination` / `hdsMaterial` from
`@kit.UIDesignKit` and `uiMaterial.ImmersiveMaterial` from `@kit.ArkUI`. Those APIs **only exist in SDKs newer
than HarmonyOS 6.0.1 (API 21)**: building against the API 21 SDK fails outright with
`'uiMaterial' is not exported from Kit '@kit.ArkUI'`, `'hdsMaterial' is not exported from Kit '@kit.UIDesignKit'`
and `Cannot find name 'HdsNavigationAttribute'`. The app now uses native `Navigation` + `NavDestination`
(`pages/Index.ets` draws its own title bar, `APP_HEADER_HEIGHT` lives in `view/CommonComponents.ets`), and the
log panel gets a similar frosted look from `backgroundBlurStyle(BlurStyle.Thin)` over a translucent background.

To bring the immersive material back, upgrade DevEco Studio / the SDK to a version that ships the UI Design Kit,
write `compileSdkVersion` / `targetSdkVersion` in `build-profile.json5` as `'x.y.z(API level)'` (for example
`'6.0.1(21)'`) and bump them to the new version, and add the `ohos.arkui.UIMaterial.state` metadata back to
`module.json5`.

**Never put a custom component directly inside an arrow function passed to an external component.** The ArkTS
compiler only rewrites `Foo({...})` into `new Foo(this, {...})` when the call sits in a declarative-UI context.
Written as an arrow-function property of an object — for example
`new SuffixCustomBuilder((): void => { DistanceSlider({...}) })` — the call is not rewritten, and evaluating the
closure throws `TypeError: class constructor cannot called without 'new'`, crashing the app. Put the component in
an `@Builder` method and call that method from the closure instead:

```typescript
@Builder
DistanceSliderBuilder() {
  DistanceSlider({ /* ... */ })
}

// suffixItem: new SuffixCustomBuilder((): void => { this.DistanceSliderBuilder() })
```

> To verify: after building, inspect the intermediate `.ts` files under
> `entry/build/default/cache/default/default@CompileArkTS/esmodule/debug/` and confirm the component became
> `new Foo(this, {...})`. A bare `Foo({...})` call there will always crash.

**(Historical) A custom suffix on an HDS card does not take part in size measurement.** HDS is no longer a dependency, but these measurements explain where `SettingCard`'s dimensions come from, so they are worth reading before changing the cards. `HdsListItemCard`'s `suffixItem`
accepts only a `SuffixCustomBuilder`, and that suffix contributes neither to the card's width allocation nor to
its height measurement. Measured: with eight option chips in the suffix, the card stayed 64vp tall (the fixed
`SuffixText` line height) while the `Flex` inside wrapped against the *screen* width and grew upwards, drawing
the chips outside the card and on top of the previous card's buttons.

So **never put an interactive control row in a `HdsListItemCard` suffix**. Use a plain ArkUI card instead — the
`SettingCard` in `apps/harmonyos/entry/src/main/ets/view/CommonComponents.ets`: it matches the HDS card look
(`card_surface` background, 16vp radius, 16vp padding, a system symbol plus fixed-width icon and label columns)
while the control column uses `layoutWeight(1)` / full width and is measured normally by ArkUI.
**All four task-settings rows use `SettingCard`** — including static rows such as the end date, which pass
`valueText` to right-align the value. Mixing `HdsListItemCard` with `SettingCard` makes the label left edges
differ by roughly 21px, because the two icon columns are 84px and 78px wide respectively.

> Rows that need a wide control (the target-distance slider) pass `fullWidth` to `SettingCard`, which moves the
> label above the control: ArkUI's `Text` has a 64vp minimum width and does not shrink to its content, so a
> side-by-side layout costs the label column a chunk of width. The `SettingCard` label column must therefore
> **not be narrower than 64vp**, or four-character labels such as "跑步次数" wrap onto two lines (measured: at
> 43vp three of the four rows wrapped).

**A live readout in a label row must not come from the parent's `@State`.** The target-distance value (the
`4.0 km` in "目标距离 4.0 km") is rendered by `SettingCard` from `@StorageProp('distanceKmText')`; the writer
is the slider's `onDistanceChange` (`AppStorage.setOrCreate('distanceKmText', …)`) and the initial value is
written in `RunScreen.aboutToAppear()`. The reason: ArkUI compiles the arrow function passed to `@BuilderParam`
into `builder.bind(this)`, so `this` inside that closure is the *child* component — anything the parent renders
from its own `@State` or passes as a parameter reads a stale value (measured: the slider had already reached
`1.6` while the parent-rendered readout stayed at `4.0`; `@Link` two-way binding does not help either).
`@StorageProp` does not depend on `this`, and is the only channel that has proven to refresh in real time.

Two further hard constraints:
- ArkTS requires a component used with the trailing-closure syntax to have **exactly one** `@BuilderParam`, so
  the readout cannot be added as a second builder slot (error: `In the trailing lambda case, 'SettingCard' must
  have one and only one property decorated with '@BuilderParam'.`).
- Passing a callback as a component *method reference* (`onDistanceChange: this.onDistanceChange`) makes the app
  exit as soon as the slider is tapped; always use an arrow function at the call site.

**Swapping two adjacent arguments of the same type is not caught statically.** The first two numeric
parameters of `generate()` are `targetDistanceM` (metres) and `startTimeMs` (a millisecond timestamp); both are
`number`, so reversing them still compiles. That is how `Date.now()` once reached the algorithm as the target
distance (about `1.79e12` m): the loop count needed to cover it climbed into the billions and the preview blew
the heap. Pass arguments in declaration order and comment the call site; the algorithm also sanity-checks the
distance unit (section 9), but the call site is where the bug must be fixed.

## 9. Route length and preview limits

Tracks are interpolated offline from the selected route: neighbouring coordinates are densified to the target
step, then the whole path is repeated enough times to cover the target distance
(`completeLoops = target distance / single-loop length`).

So **a route must not be too short**. If you tap almost the same spot over and over, or end on two points only
centimetres apart, the single loop may be a few centimetres long; covering 1–5 km then needs hundreds of
thousands of loops and the track grows to millions of points, exhausting memory. HarmonyOS caps both the
densified path and the expansion (`MAX_EXPANSION_POINTS`, 100 000 points, in
`apps/harmonyos/entry/src/main/ets/service/DataGenerator.ets`), so instead of crashing it reports:

- the log pane shows "预览失败: 路线过短（单圈仅 x.xx m）…请重新设计路线或选择其他路线";
- design a route whose single-loop length is close to the target distance, or use the built-in
  "思源湖路线" (single loop ≈ 871 m).

> The same defect exists on Android (identical algorithm and path repetition); HarmonyOS only intercepts it
> early to protect runtime memory.

Before entering track generation the **unit (dimensionality) of the target distance** is also checked:
`previewRoute()` and `DataGenerator.generate()` both reject target distances below 100 m or above 50 km (and
non-finite values) and report the reason in the log, for example:

```text
内部错误: 目标距离参数异常（原始值 1791910592.872），应为 1-5km；请重新设置目标距离后重试
```

> Preview used to fail consistently with a "target distance of about 1791910592.87 km". The real cause was an
> argument-order mistake in `apps/harmonyos/entry/src/main/ets/viewmodel/MainViewModel.ets`: `Date.now()` and
> the target distance were passed in the wrong order (a millisecond timestamp arrived as metres). It is now
> fixed to `(targetDistanceM, startTimeMs)`, matching Android `MainViewModel.kt:362-366`.
>
> That check and the `MAX_EXPANSION_POINTS` cap from section 9 are both **safety nets**: they never trigger
> with a valid configuration and only downgrade a future unit/order mistake from a crash to a log error.

## 10. Semester progress, calendar and auto plan

All three come from read-only Sports Department endpoints (`semesterStats()` in `service/ApiService.ets`). They only need the `pe.sjtu.edu.cn` session cookie, not the token used for uploading.

**Semester progress card** (below the status card) shows two numbers: passed kilometres (`resultKm`, two decimals) and completion rate (the server's `percent` is already 0–100; when it is missing the app falls back to passed / total). Both read `--` when logged out or when the request fails.

**Semester calendar** (calendar icon in the top-right corner) expands the whole semester month by month, weeks starting on Monday:

| Style | Meaning |
| --- | --- |
| Solid green | Counts towards the score (server `state == "0"`) |
| Outlined | Has a record but does not count (`state` 12/13 etc.) |
| Grey | No record in the range |
| Blank cell | Padding at the start/end of a month, or outside the semester range |

Logged out, the app shows a **placeholder calendar** guessed from the current month (Jan–Feb → previous academic year's autumn, Mar–Jul → spring, otherwise autumn), all cells "not run". When the server omits the start/end dates (`semesterDateList` missing) the calendar keeps the placeholder and the log says `服务器未返回本学期起止日期，日历保持占位`.

**Auto plan** runs once, **right after a successful login**: it turns the gap (`target − passed`) into runs × per-run distance — first spreading the gap over the 5 km per-run cap (at most 30 runs), then distributing it so every run is rounded up to 0.01 km, which guarantees the batch covers the gap. A 21 km gap, for example, becomes 5 runs × 4.2 km.

When it applies:

1. the 跑步次数 and 目标距离 inputs on the home page are rewritten (the custom-runs input collapses) and a toast reads `已按本学期未完成 X km 自动设为 N 次 × D km`;
2. the result is persisted under `app_prefs/plan_auto_days` / `plan_auto_distance` / `plan_auto_active`, so the next launch fills the inputs from it again;
3. **manual edits win**: once you change runs or distance the app stops overwriting them (the test is "still the defaults 1 × 4 km" or "equal to the last auto plan") and logs `跑步次数 / 单次距离已被手动修改，保持你的设置`.

A successful upload refreshes the semester data (the calendar follows) but **does not** trigger the auto plan again. Switching accounts or losing the cookie resets the calendar to the placeholder first, and late responses are dropped by a session serial.

> The "skip days with records" switch uses exactly these dates: any day with a record — counted or not — is skipped. The semester start date also bounds the backwards search.
