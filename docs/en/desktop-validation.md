# Desktop migration verification

> This document is chronological. From 2026-10-22 the desktop client uses **Tauri 2 + React 19 + Material Design 3**; the earlier sections document the retired **Rust + Slint** UI and are kept for history.

Date: 2026-10-16. Environment: Windows x86_64, Rust 1.95.0 (MSYS2 GNU), Slint 1.15.1.

## Verified

- Formatting and Clippy with warnings denied.
- 26 offline Rust tests plus one opt-in live CAPTCHA test covering input boundaries, routes and sampling, payload timestamps, versions, HTTP authentication/upload/error redaction, cancellation, path-scoped cookies, and AJAX login. Map-service tests cover loopback binding, referrer policy, Host/path isolation, updates, HEAD/non-GET handling, and releasing the port on shutdown.
- 3 Python packaging-layout tests, mocking system packaging commands to validate macOS plist/link/signing/DMG layout and Linux deb control/desktop files.
- Actual Release exe built by `build_windows.ps1`, with embedded icon and version.
- Standalone copy with no assets directory and PATH restricted to Windows system directories: offline smoke test exits with code 0 and produces 28 screenshots covering four pages × two themes × two window sizes, modals, running states, empty/long logs, wrapped notices, and dropdowns. Assertions cover mouse opening, keyboard selection/confirmation, disabled selection, and clearing logs.
- PE import table contains only Windows system DLLs, with no Python, Qt, or MSYS2 DLL dependency.
- Workflow YAML parses. Android and subsequent release jobs are byte-for-byte unchanged; no mobile code changes.

## Size and startup

This UI revision’s Windows Release: **10,208,256 bytes (9.735 MiB)**, product version `4.5.0`. SHA256: `11c4934652c337823c14a684ef0f496c122a20d3fe343f52f1805662e9367c2e`. The offline GUI check exited with code 0 and produced 28 screenshots. During the earlier login fix, the packaged anonymous CAPTCHA check received a 110×40 image and an automatically recognized code; the separate live account check is described below. Earlier migration builds reached input-idle in 753 / 715 / 731 ms; these are historical measurements, not a new timing run for this UI revision.

Startup is measured from PowerShell Start-Process to WaitForInputIdle, not a cross-machine or cold-cache first-frame benchmark. The smoke-result.json timing includes an intentional 300 ms screenshot delay and is not pure startup latency.

The old Qt build was not rebuilt under equivalent conditions, so no size-reduction percentage or speedup factor is claimed. Runtime and old background assets have been removed from the native package.

## Not verified

- Windows MSVC builds or other Windows versions.
- Actual macOS Intel/ARM builds, signing, installation, and runtime; Linux amd64/arm64 builds, deb installation, X11/Wayland, and file pickers.
- Exercise uploads and email/SMS second-factor verification. Account login, My SJTU app verification, and read-only portal authorization were checked separately against live services; mocks do not validate other live workflows.
- Coverage was not measured; 80% coverage is not claimed.

The new desktop-check.yml configures three-OS build/test/static checks and Windows/Linux screenshot smoke tests. That CI has not been triggered in this session.

## Migration details

- Automatic CAPTCHA recognition through the legacy service is preserved. Manual entry appears only as a fallback after recognition failure.
- Coordinate calibration, fixed 200 m distance compensation, start-time variation, and payload fields are preserved. Sampling is reimplemented and retains corners to avoid shortening distances. (That compensation was removed in the 2026-10-22 Tauri migration; see the “Tauri 2 + React 19 migration” section below.)
- Long routes are automatically truncated; the old Qt option to keep the complete route is removed. Preview shows actual generated length.
- Import legacy TXT routes into the new user data directory. The legacy Python modules `src/` and `utils/` and `assets/resources_rc.py` have been removed together: the latter was only a side-effect import of `src/info_dialog.py`, and none of its embedded `:/resources/` entries were referenced by any code or existed as loose files, so nothing needed migrating.

## CAPTCHA regression fix

An anonymous live request reproduced HTTP 403 without Referer; restoring the legacy header returned HTTP 200 and a 110×40 JPEG. Rust’s live image retrieval and automatic-recognition test passes without submitting account credentials. Regression tests check Referer, JPEG validation, multipart format, absence of login credentials in recognition requests, and invalid recognition results.

Opt in with `cargo test --locked -p sjturunningman live_captcha_can_be_loaded_and_recognized -- --ignored`. The packaged executable’s `--login-smoke-test <output-directory>` checks that normal UI callbacks receive the image and recognized result, without submitting a login or saving CAPTCHA images or codes.

## Account-login regression fix

An authorized live account check reproduced the original request returning to the login page. Adding the page's `lt=p` password-login marker and AJAX header, then following the `errno=0` response URL, restored the next authentication step. Immediate CAPTCHA submission was rejected; restoring the legacy one-second delay after recognition reached two-factor verification. Errors use controlled categories without exposing server messages or credentials.

The same check sent one My SJTU app code, verified the user-provided code, checked the authentication cookie, and completed read-only portal authorization and rule retrieval. It called the production `Session` implementation; the temporary test entry point was removed. No exercise record was uploaded, and no credentials, codes, cookies, or tokens were saved. Interactive acceptance of the final window remains for the user; this live account check exercised the shared network implementation.

Regression tests cover the password-login form marker, AJAX/Referer headers, returned redirects, two-factor handling, controlled CAPTCHA/password errors, missing/untrusted redirects, and response redaction. Second-factor requests and the final authorization redirect restore Referer; completion checks the authentication cookie rather than accepting HTTP 200 alone.

## Branding and About fix

The sidebar reuses the original icon. This UI revision replaces the earlier handwritten SVG wordmark with a clean system sans-serif `RunningMan` label. About provides the legacy Shuiyuan discussion and GitHub links with existing icons and appropriate dark-theme colors. Both links retain their legacy destinations and open in the system browser. Update notices still direct users to GitHub Releases.

Release screenshots check the wordmark, original icon, link icons, vertical button alignment, and About in both themes at the minimum window size. Link bindings and destinations were inspected; no Shuiyuan login was performed. macOS/Linux visuals still require device acceptance.

## Browser-map HTTP 403 fix

The original maps opened from `file://`, without an HTTP Referer; the planner also specified `no-referrer`, conflicting with [OSM tile requirements](https://operations.osmfoundation.org/policies/tiles/). An on-demand in-memory HTTP service now binds only to `127.0.0.1`, uses a fresh per-run page path, and sends `strict-origin-when-cross-origin`. Both pages use the official `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. Tiles are not proxied, referrers are not forged, and there is no bulk prefetch; normal browser caching follows server headers.

The actual Release executable's `--map-smoke-test` invokes production UI callbacks. Headed Chrome displayed maps in both preview and planner, with sampled tile HTTP 200, an actual loopback HTTP Referer, and visible attribution. Selecting two planner points exported valid BD09 TXT. An isolated browser intercepted tiles with simulated HTTP 403: both pages reported failures and the preview retained its track. Simulated cases sent no live OSM tile requests. Local screenshots/export are under ignored `output/playwright/`. No account login or record upload was performed; macOS/Linux were not tested this turn.

## UI cleanup and layout revision

Promotional headers, uppercase section labels, and decorative numbering are removed. The Header row is reduced to 32 px with a 22 px Chinese title. Sidebar items are 40 px with a soft active fill. About uses compact application, update/community, and usage cards, preserving the forest-green themes, original icon, and community links.

Inputs and dropdowns share 38 px height, a soft 1 px border, and 8 px corners. Toolbar buttons are 34 px, secondary buttons 36 px, and Clear logs 32 px with content-sized width. The log description sits below its title, text is aligned top-left, and empty logs have a placeholder. The plan card follows content height with a fixed gap before its hint.

The full task bar appears only on the workspace, with a 6 px track filled from the left. Other pages show a compact status and Stop button only during a task. Long notices grow with wrapped text. All 28 Release screenshots were rendered by the actual application; the page/theme/size matrix, long text, and modals were visually reviewed using offline states only. Screenshots and assertions are under ignored `target/ui-modernization/release/`. macOS/Linux visuals still need device verification.

## macOS CJK rendering fix

The newly added macOS runtime check (`desktop-check.yml` now runs `--smoke-test` on the packaged app, see below) produced the first real macOS screenshots and showed that **no Chinese glyph renders at all**: Windows/Linux screenshots of the same build are correct, while macOS keeps only digits and Latin letters -- "跑步次数 / 次" renders as " / ", "单次距离 / km" as " / km", and the consent dialog shows an empty title and body with just the `1.`-`4.` list markers, while `RunningMan`, `v4.5.0`, and `BD09` render normally.

Pixel inspection shows a zero advance width for the Han characters (the slash sits flush against the label origin): the selected font has no such glyphs and no system fallback supplied them. The UI font was previously requested by **name** only (macOS: `PingFang SC`); that name does not resolve in a session-less environment, so Slint fell back to a Latin-only font.

Fix: at startup, walk a candidate list of "family name + system font file path", read the file, register it with `slint::fontique_07::shared_collection()` into Slint's own font collection, use the first family that registers as the UI font, and append it as a fallback for the Han script (`Hani`). Candidates: macOS `PingFang.ttc` / `Hiragino Sans GB.ttc` / `STHeiti Medium.ttc` / `Arial Unicode.ttf`, Windows `msyh.ttc` / `simhei.ttf`, Linux Noto Sans CJK / WenQuanYi Zen Hei; if none is usable the previous system family name is kept. Registration and fallback results are written to `smoke-result.json` as `ui_font` and `font_candidates`. This also removes the dependency on system font enumeration behaviour; no visual regression was found on Windows/Linux.

At that time, `slint` therefore enabled `unstable-fontique-07` (Slint's official runtime font registration interface; see the `fontique_07` module docs). macOS still needed one manual confirmation of Chinese text on real hardware.

## macOS title-bar repair (2026-10-17)

The project previously pinned Slint 1.15.1. On macOS, that version could leave the native title bar, including the traffic-light area, blank or transparent; the opaque background in the Slint window cannot repair the system title bar itself. The desktop client now uses Slint 1.18.0 and updates the font-registration API to `unstable-fontique-011` / `fontique_011`. Slint 1.18.0 includes the macOS fix for native-title-bar transparency handling; see the [Slint 1.18.0 release notes](https://github.com/slint-ui/slint/blob/v1.18.0/CHANGELOG.md).

This change was checked with a temporary Rust 1.99.1 toolchain using `cargo check --workspace --locked` and `cargo test --workspace --locked`: 28 tests passed and one live CAPTCHA test was ignored; the macOS font test was ignored because winit requires the test to run on the main thread. A macOS Release window was not launched, so the traffic-light area still needs manual inspection in the actual application window.

## Baidu / OpenStreetMap dual engine (2026-10-17)

> As of 2026-10-22 the route preview uses OpenStreetMap only; the planner keeps both engines. The record below reflects the earlier state.

OSM was unusable from the user's network, and the Rust rewrite had dropped the old Qt client's Baidu basemap. This change puts the provider choice back inside the HTML pages: both preview and planner **default to Baidu Maps** with an in-page OpenStreetMap switch, without touching the Slint UI. The coordinate contract is unchanged: the planner stores BD09, Baidu clicks are stored as-is, OSM clicks are WGS84 and converted to BD09 before storage; the preview receives GCJ02 and converts to BD09 for Baidu or WGS84 for OSM at display time.

Verified on local macOS 27 arm64, Rust 1.99.1, Release build: `--map-smoke-test` generated both pages and Headless Chrome 154 + CDP drove them:

- Both pages load Baidu by default ("百度地图已加载" / Baidu map loaded) with basemap tiles; the Baidu AK accepts the loopback page. A planner click near the centre stores BD09 `121.442938, 31.031568`.
- Switching to OSM keeps collected points (2 before and after); Leaflet loads from unpkg on demand. On this network OSM tiles return `ERR_CONNECTION_RESET`; the page shows its basemap failure notice while the track and point collection remain usable. This matches the user's OSM report and justifies the Baidu default.
- In OSM mode a click is also stored as BD09 (`121.444655, 31.030156`), in the same range as Baidu mode. Switching back and forth rebuilds the map with the expected marker count.
- Marker deletion verified: in Baidu mode a marker click takes the point count 1 → 0 and the bubbling map click no longer adds a replacement; the next map click restores 1. OSM marker deletion also goes 1 → 0 → 1.
- Baidu BMap initialisation needs `'unsafe-eval'`. The CSP now allows it and limits Baidu hosts (`api.map.baidu.com`, `*.baidu.com`, `*.bdimg.com`, `*.bdstatic.com`, http/https); OSM/unpkg sources are unchanged, and form actions, base-uri, and frame-ancestors remain locked down.
- The Baidu loader uses `referrerpolicy="no-referrer"`; the page keeps `strict-origin-when-cross-origin` for OSM.

Not yet verified: Baidu/OSM rendering on real Windows/Linux, Baidu AK behaviour on other networks, and real uploads. `--map-smoke-test` proves launch and coordinate contracts; rendering is covered by the browser checks above.

## Semester statistics and semester calendar (2026-10-21)

The workspace gains a read-only "本学期进度" (this semester's progress) card showing qualifying distance and completion rate, and the Logs page becomes a semester calendar on the left with the run log on the right. Only `desktop/` changed; the mobile clients are untouched.

- Statistics come from five read-only requests in a fixed order: `GET /sports/my/data` → `GET /sports/my/semesterTarget` → `GET /sports/running/semester/list?type=1` → `POST /sports/ranking/getUserInfo` (empty JSON body) → `GET /sports/running/result/list?selectId=<semesterId>&type=1`. They need only the `pe.sjtu.edu.cn` session cookie, not the token exchanged through `/sports/my/uid`. A redirect to `/login`, a non-JSON body, or `code != 0` is all reported as an expired login, with a controlled message that never carries the response body. A missing `semesterId` fails immediately instead of requesting the record list.
- Pure logic lives in the new `desktop/src/stats.rs`: semester-range guards (`end < start` or a span over 400 days yields nothing), a Monday-first month-by-month calendar grid, blank cells at month edges, "counts toward score" winning over an invalid record on the same day, and `--` / one-decimal percent formatting. Parsing lives in `Session::semester_stats`. The UI uses a flat row model plus seven explicit `DayCell` elements to avoid Slint's restriction on nesting `if` / `for` inside repeated rows.
- Refresh triggers: successful login, successful two-factor verification, and a task that uploaded at least one record. Each login or refresh increments a session serial, so late responses from a previous account or after logout are discarded. Failures write one log line and leave the login state alone.
- Automation: `cargo test --workspace --locked` gives 44 passing tests with 1 live-CAPTCHA test ignored (plus 2 binary tests). New coverage includes request order, login redirects, `code != 0`, a missing `semesterId`, a valid plus invalid record on the same day, deriving a missing percentage, and calendar cases for month/year crossings, padded blank cells, out-of-range dates, and placeholder ranges. `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --locked -- -D warnings` are clean on Rust 1.99.1.
- `--smoke-test` gained two deterministic fixtures: logged-in statistics values on the workspace page, and a fixed semester range (starting 2026-09-14) for the calendar, containing a scoring record, an invalid record, and a date outside the range. Screenshots went from 28 to 30, and `snapshot_count` is now derived from the PNGs actually present in the output directory instead of a hardcoded number; the report also carries `semester_stats_placeholder` and `semester_stats_fixture_rows`. Pixel counts for this build (light theme, 1493×1093 window, per-channel tolerance ±3 for the calendar colours and ±6 for the accent) confirm that the 30th screenshot contains all three calendar colours: 2609 px scoring, 544 px invalid, 33787 px rest day. The 29th screenshot carries 14741 accent pixels of `#236849`, 4232 of them in the left half, against 10611 and only 134 in the left half for the placeholder `02-screen.png`, so the statistics card really does render the fixture values. All fixture values and dates are local constants; the test never logs in or uploads.
- Not yet verified: qualifying distance and completion rate from a real account, invalid-record colours and date attribution on real data, the card and two-column layout on real macOS/Linux hosts, and whether the halves overflow at the 1040×700 minimum window. The 28-screenshot figures earlier in this document describe earlier builds and are left unchanged.

## Tauri 2 + React 19 migration verification (2026-10-22)

Environment: macOS arm64, Rust 1.95.0, Node 24.18.1, pnpm 11.22.0, Tauri 2.12.5, React 19.3.1, `@material/web` 2.5.0. The sections above document the retired Rust + Slint UI and are kept for history; this section covers the current desktop client.

### Structure and dependencies

- The frontend lives in `desktop/` (React 19 + TypeScript + Vite 8). Components come only from `@material/web` (including the labs outlined/elevated card, navigation drawer and segmented button); no other UI component library is used.
- The Rust business modules moved unchanged to `desktop/src-tauri/src/`. `api.rs`, `route.rs`, `task.rs`, `settings.rs`, `stats.rs`, `maps.rs` and `update.rs` keep their request, sampling, coordinate, scheduling and statistics logic. The new `commands.rs` only adapts them to Tauri commands, state and background threads. `preview.rs` now validates captcha images and returns a data URL; track rendering moved to themed SVG in the frontend.
- Removed `slint`, `slint-build`, `tiny-skia` and `rfd`; added `tauri`, `tauri-build`, `tauri-plugin-dialog` and `base64`. The Cargo workspace member is now `desktop/src-tauri`.
- The version source remains `desktop/src-tauri/Cargo.toml`; `build.rs` keeps the `APP_VERSION` override and Windows resource handling.

### Design system

- Colours are generated from the seed `#335C9C` with Google's official `material-color-utilities`, covering the MD3 light/dark roles including surface containers, fixed, inverse, outline and error. The generator is `desktop/scripts/generate-theme.mjs`; the output is committed as `desktop/src/styles/tokens.css`. The old brand green is gone.
- Typography follows the MD3 type scale. Roboto and Material Symbols Rounded are bundled as used subsets (about 42 KB + 60 KB); Chinese falls back to PingFang SC / Microsoft YaHei UI / Noto Sans CJK.
- Shapes: 16 px cards, 28 px dialogs, fully rounded buttons, 4 px text fields. Elevation uses MD3 tokens; motion uses 150/250/400 ms with standard easing and respects `prefers-reduced-motion`.
- Pages: a 248 px permanent navigation drawer; a two-column workbench; a route list plus preview on the routes page; a two-column calendar/log page; and an About page with a hero and update/usage cards. Dialogs cover consent, login, two-factor, route deletion and task confirmation.

### Automated results

- `cargo test --workspace --locked`: 58 passed, 1 ignored (live captcha network test). New tests cover 2FA page field extraction, hidden-field submission and error-code mapping.
- `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --locked -- -D warnings`: clean.
- `pnpm --dir desktop build`: typecheck and Vite production build pass. JS is about 571 KB (142 KB gzip); CSS about 38 KB.
- `python3 -m unittest discover -s scripts -p "test_*.py"`: 5 packaging-layout tests pass, including the WebKitGTK 4.1 / GTK 3 deb dependencies.
- A release build (`cargo build --release -p sjturunningman --features custom-protocol`) with `--ui-smoke-test target/ui-smoke` passed every real-WKWebView check: workbench, Material components, route SVG, consent open/check/close, all four pages, loaded Roboto / Material Symbols fonts, the generated primary token, `navItems = 4`, exit code 0.
- The Playwright mock check (`desktop/e2e/check.mjs`) passed form binding, select, switch, theme, segmented buttons, automatic-captcha login, semester statistics, task events, two-factor account display and logs. `desktop/e2e/screenshot.mjs` produced 15 screenshots at 1200×840 / 1000×700 across light, dark, four pages and dialogs.
- Backend `--smoke-test`: default route, 4.00 km offline preview, invalid-input rejection and the 26-week placeholder calendar pass.

### Migration notes

- A bare `cargo run` is a Tauri development build and connects to `http://localhost:1420`; use `pnpm --dir desktop tauri dev`. Release and packaging builds must pass `--features custom-protocol`, otherwise the production asset protocol is not active.
- The real window uses the system WebView; Linux needs WebKitGTK 4.1 and Windows needs the WebView2 Runtime.
- `--smoke-test` is now a headless backend check; use `--ui-smoke-test` for the real interface. Playwright is only a mocked visual/interaction check.
- The route preview map is now embedded in the preview card; the planner still opens in the system browser. The coordinate contract, upload payload and automatic plan logic are unchanged. Sampling now uses the selected per-run distance exactly: the fixed 200 m compensation is removed, and the map preview fallback samples the same distance as the uploaded track.

### Not yet verified

- Windows MSVC / WebView2 and Linux WebKitGTK / X11 / Wayland builds, installation and visuals on real hardware.
- Run uploads still need live acceptance. Account login and two-factor verification were re-tested by the user with a real account on 2026-10-22.
- A native macOS window screenshot (this environment has no screen-recording permission); the real-window DOM smoke test passed.

## Two-factor verification submission fix (2026-10-22)

### Symptom

After entering a correct JAccount username, password and six-digit two-factor code, the desktop client kept showing "the two-factor code is invalid or expired". The same account worked in the web / Android WebView login.

### Root cause

- After `ulogin` returned the two-factor challenge, the Rust client treated the JSON `url` as a normal page and issued a `GET`. That endpoint may only accept `POST`; the extra request could fail or change the server-side 2FA state, and the page's account / hidden fields were discarded even when it loaded.
- `verify_code` always submitted the typed account with only `account` / `captcha` / `trust`. It did not use the account and `sid` / `uuid` / CSRF token fields carried by the 2FA form.
- Every non-zero `errno` was collapsed into "invalid or expired", so an `Invalid request` or an expired session looked identical to a wrong code.

Android uses the system WebView to load the official login / 2FA pages, so the page itself submits those fields and is unaffected.

### Fix

- `Session` now carries a cloned-shared `TwoFactorContext` with the page / URL / JSON account, whitelisted hidden fields and the completion URL.
- After detecting 2FA, the client tries to load the next page for extraction, but a failed load (for example a POST-only 405) no longer aborts the flow. Fields are only captured from a page that actually contains a 2FA marker.
- Verification prefers the page / URL account, falls back to the typed account, and submits whitelisted fields such as `sid`, `uuid`, `csrf`, `token`, `execution` and `lt`.
- After success it first visits the original `ulogin` completion URL, then falls back to `authorize` when no auth cookie is present.
- Errors are classified by `errno`: 4/5 for expiry, 10002 for invalid request / lost session, 1 for not logged in, and other codes are surfaced.
- The 2FA dialog changes the send button to "Resend" and warns that resending invalidates the previous code.
- New offline tests cover page account / field extraction, the submitted form and error mapping. They contain no real codes or credentials.

### Verification

- `cargo test --workspace --locked`: 58 passed, 1 ignored (live captcha network test).
- `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --locked -- -D warnings`: clean.
- Frontend build, Playwright mock interaction checks and the real Tauri `--ui-smoke-test`: pass.
- On 2026-10-22 the user re-tested with a real account: username, password and the received two-factor code now log in successfully.

### Not covered

- Run-record uploads still need live acceptance.
- The real 2FA page extraction is covered by offline fixtures plus this user retest; re-check `account`, hidden fields and the completion URL after server changes.
- No account, password, code, cookie or token was recorded; diagnostics keep only controlled error categories.

## Route preview map embedded in the card (2026-10-22)

### Symptom

"Open in map" used to launch the loopback map page in the system browser, separating the preview card from the map and forcing users to switch windows while checking a route.

### Fix

- A new `preview_map` command publishes the loopback page and returns its URL without calling `webbrowser::open`; the frontend renders that URL in an iframe inside the preview card, and "Collapse map" returns to the SVG preview.
- The preview page now uses OpenStreetMap only: the Baidu script, engine selector and top status bar are gone, the map fills the card, and a small error chip appears at the bottom-left only when tiles fail.
- The map server still binds only `127.0.0.1`, uses a random path and checks the `Host` header. The preview page's `frame-ancestors` allows only the app itself (`tauri://localhost`, `http(s)://tauri.localhost` and the dev server `http://localhost:1420`); the planner stays at `'none'`. CSP is split: the preview allows only Leaflet / OSM, while the planner keeps Baidu and `'unsafe-eval'`.
- The app CSP gains `frame-src http://127.0.0.1:*`. A successful open no longer shows a top notice; only a stale-parameter fallback is reported inline in the card.
- The map page posts `sjturm-map-ready` to its parent; `--ui-smoke-test` uses it to prove the framed script actually executed, rather than only asserting that an iframe element exists.
- Changing the route, regenerating the preview or editing parameters closes the old map so it cannot show a stale track.

### Verification

- `cargo test --workspace --locked`: 59 passed, 1 ignored (live captcha network test); new tests cover the preview OSM-only CSP / framing and the planner dual-engine CSP / non-framing.
- `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --locked -- -D warnings`: clean.
- Playwright mock `node e2e/check.mjs`: passes with new "Open in map → iframe → Collapse map" assertions.
- macOS WKWebView Release `--ui-smoke-test`: `mapButton`, `inlineMap`, `inlineMapReady`, `inlineMapToggle`, `inlineMapCollapsed` and `noMapNotice` are all true; a screenshot confirmed OpenStreetMap tiles, the track and endpoints render inside the card without a top notice or map status bar.
- Accepted with the default `default` route (0.87 km) in a 1200×840 window.

### Not covered

- Real-device `frame-src` / custom-scheme `frame-ancestors` behaviour on Windows WebView2 and Linux WebKitGTK; the CSP syntax is shared but was not re-tested per platform.
- The embedded page's look in the dark theme (the base map itself stays light), and the bottom-left tile-error chip under a real network failure.

## Preview map and uploaded track share one sampling rule (2026-10-23)

### Symptom

`task.rs` already samples the uploaded track at the selected per-run distance with no fixed 200 m compensation, while the cache-miss fallback in `preview_map` still sampled `distance * 1_000.0 + 200.0`, and `resample`'s `target_m > 5_200.0` limit existed only to accommodate it. Switching, importing or deleting a route clears `preview_inputs`, so the fallback always runs and the embedded map showed 200 m more than the preview card and the uploaded track.

### Fix

- The fallback now samples `distance * 1_000.0`, matching `task.rs`. The step stays a fixed 10.0 m so the map page renders deterministically.
- The fallback validates the distance first and returns "距离应在 1.20–5.00 km 之间" instead of handing invalid parameters to the sampler.
- `resample`'s upper bound drops from 5 200 m to 5 000 m, i.e. `settings::MAX_DISTANCE_KM`; the sampler no longer reserves headroom for compensation.
- The fallback keeps a fixed 10.0 m step: the uploaded track uses a random pace, so the preview cannot and should not reproduce the same point sequence — only the same total distance.

### Verification

- `cargo fmt --all -- --check`: clean.
- New `resampling_stops_at_the_configured_distance`: 5 000 m succeeds, 5 200 m is rejected.

### Not covered

- This host only has the WebKitGTK runtime libraries, not `libwebkit2gtk-4.1-dev`, so `cargo clippy` and `cargo test` must be re-run in CI or on a machine with the development packages.
- Real-device check that the preview card and the embedded map report the same length after switching routes (both should equal the selected per-run distance).

## One source for the deb dependency list (2026-10-23)

### Symptom

`bundle.linux.deb.depends` in `desktop/src-tauri/tauri.conf.json` listed only 2 entries, while CI never runs `tauri build`: the published deb is assembled by `scripts/package_desktop.py`, which hard-coded a second, 17-entry list in `control`. The two lists contradicted each other, and editing one was invisible to the other.

### Fix

- `bundle.linux.deb.depends` in `tauri.conf.json` now carries the full 17-entry release list and is the single source.
- `scripts/package_desktop.py` gained `deb_depends()`, which reads that config and writes it into `control` instead of hard-coding a second copy. `Recommends` stays in the packaging script because Tauri's deb configuration has no such field.

### Verification

- `python3 -m unittest discover -s scripts -p "test_*.py"`: 6 pass, including a new assertion that `control`'s `Depends` matches `tauri.conf.json` exactly; the generated list is item-for-item and order-for-order identical to the previous hard-coded one.

### Not covered

- `tauri build` was not run, so the union of Tauri's own auto-added dependencies with this list is untested; the release path is still the packaging script.
