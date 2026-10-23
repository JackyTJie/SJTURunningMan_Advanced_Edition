# Material determinate linear Wavy progress: desktop source port

The desktop semester bar ports Google's **rounded determinate Wavy style**.
The original Java/C++ sources are retained here without modifications for audit;
they are not compiled into the desktop binary. Runtime code is in
`desktop/src/lib/material-progress/`, with the React adapter in
`desktop/src/components/SemesterProgress.tsx`.

This is a source-derived port, not a Google-shipped Web component. It covers the
semester bar's configuration, not the entire Android widget API, circular
styles, or indeterminate loading styles.

## Pinned upstream sources

- [Material Components Android](https://github.com/material-components/material-components-android/tree/66b0eeb53afeb6025ffbbd37734b08e5bce197ed/lib/java/com/google/android/material/progressindicator):
  `66b0eeb53afeb6025ffbbd37734b08e5bce197ed`, Apache-2.0. Drawing delegates,
  DeterminateDrawable, visibility drawable, indicator/spec classes, style and
  drawing/motion tokens are retained here.
- [AndroidX dynamic animation](https://github.com/androidx/androidx/tree/39d4ffd2a6d42d25c4f98cda5a7508487a975651/dynamicanimation/dynamicanimation/src/main/java/androidx/dynamicanimation/animation):
  `39d4ffd2a6d42d25c4f98cda5a7508487a975651`, Apache-2.0. SpringForce,
  SpringAnimation and DynamicAnimation sources.
- [Skia](https://github.com/google/skia/tree/b33356d6ccf1fe2692e3b616b257f07f78414c47/src/core):
  `b33356d6ccf1fe2692e3b616b257f07f78414c47`, BSD-3-Clause.
  SkContourMeasure.cpp and SkGeometry.cpp for Android PathMeasure semantics.
- AOSP `android-16.0.0_r1`, Apache-2.0:
  [Path.cpp](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/libs/hwui/jni/Path.cpp)
  and [PathInterpolator.java](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/core/java/android/view/animation/PathInterpolator.java).

Copyrights are retained in the source files. Full licenses and runtime
attribution are bundled under `desktop/public/licenses/`.

## Drawing and motion mapping

- `path.ts`: original .48 cubic controls, integer cycle fitting, extra phase
  cycle, and the cubic-only Skia contour measurement (float32, .5 tolerance,
  depth 8, integer T values and distance-to-T interpolation). Cubics are chopped
  at measured distances **before** amplitude scaling, with original phase
  adjustment and compensating translation. No SVG dash-length approximation.
- `drawing.ts`: Canvas2D replaces Android Canvas. Same track/active/stop draw
  order, integer rounding, gap ramp below 1%, round caps, bounds clipping and
  merged rounded-block geometry for segments shorter than one stroke width.
- `motion.ts`: integer monotonic milliseconds replace Android uptime. Phase is
  `(uptime % trunc(1000 * wavelength / speed)) / cycle`, including signed speeds.
  The progress spring uses stiffness 50, damping ratio 1, velocity preservation,
  half-frame handling on retarget and the original width-dependent equilibrium
  thresholds (.75 pixel / 62.5 velocity multiplier). Wave amplitude is enabled
  at 10%–90%, using the 500 ms start/reverse ValueAnimator behaviour.
- `easing.ts`: original adaptive .002-error Path.cpp approximation, including
  midpoint/quarter-point inflection checks, and PathInterpolator binary lookup.
  Theme controls in motion-tokens.xml: standard (.2,0,0,1), emphasized accelerate
  (.3,0,.8,.2). No substituted CSS easing solver.
- The upstream style defaults to SHOW_NONE/HIDE_NONE, so no entrance/exit effect
  is added. Non-default grow/escape modes, custom corners and Android-only
  configuration APIs are not exposed by this semester component.

## App configuration and platform adaptation

Upstream tokens are retained: thickness 4dp, amplitude 3dp, determinate
wavelength 40dp, gap 4dp, stop size 4dp. CSS pixels replace dp; backing resolution
follows devicePixelRatio. Colours use the MD3 primary/secondary-container roles.

**The Android default waveSpeed is 0 (stationary).** This app explicitly sets it
to **40 CSS px/s** to enable continuous movement with the official algorithm.
The completion percentage stays unchanged. The semester bar explicitly configures
`waveAmplitudeRampProgressMin = 0` and `waveAmplitudeRampProgressMax = 1`, so it
keeps full amplitude over the entire 0–100% range, including 9% and 100%. The
motion engine retains the upstream 10%–90% defaults for reference tests. At 0%
there is no completed length to draw; very short segments below one stroke width
still use the original merged rounded-block geometry.

Browser reduced-motion maps to animator duration scale 0: progress jumps to the
target, phase is zero, no continuous repaint. Unavailable data displays a
neutral track and accessible no-data label. Unmount cancels animation; hidden
documents pause repaint requests and resume using monotonic time. Widths below
one wavelength clamp to one cycle to avoid upstream zero-cycle division in tiny
Web layouts; normal semester layouts are much wider than this guard.

## Verification and limits

From desktop/, start the preview server on port 4173, then run:

```bash
pnpm build
pnpm preview --host 127.0.0.1 --port 4173
# Second terminal, also in desktop/:
node e2e/progress-reference.mjs
node e2e/progress.mjs
pnpm check:e2e
```

Independent reference fixtures and their reproducible generators are in
`desktop/e2e/reference/`:

- **224 paths** generated with native skia-python==144.1 PathMeasure.getSegment:
  widths 39–1000, four progress levels, four phases, two amplitudes. All path
  lengths match exactly; maximum cubic coordinate discrepancy is
  **0.000003814697265625 CSS px** (float/matrix rounding).
- **189 spring cases** generated by compiling and executing the **unmodified
  original AndroidX SpringForce.java**, with host annotation/state stubs.
  Every float32 output matches exactly.
- **2002 easing samples** generated by compiling the **unchanged original AOSP
  Path.cpp approximation routines**, with host SkPoint stub, and using the
  PathInterpolator lookup. Every float32 output matches exactly.
- **33 fixed-phase native Skia raster frames** at zero, short, threshold, middle,
  near-complete and complete progress. Chromium Canvas maximum average alpha
  error is **0.118 / 255 per pixel**; maximum average premultiplied colour error
  is **0.047 / 255 per channel**. Regression limit: .25 / 255 for each frame.
  Individual clipped-edge alpha pixels can differ by up to **140 / 255**:
  browser clip antialiasing differs from the native reference's hard clipping.
- UI checks verify real pixel changes with a fixed 80% value, reduced motion,
  hidden/resumed documents, resize, theme, no data, clamping and isolation from
  upload events. Motion tests also verify settling and the endpoint amplitude.

Skia/Python/Java/C++ are test reference tools only, not application dependencies.
Native Skia geometry/raster comparisons are not screenshots of a running
Android widget. There is no Android emulator on this host. No claim of
pixel-identical Android/WebView rendering or identical frame timing is made:
antialiasing, density, clock origin and refresh rates can differ even with the
same drawing and animation logic.
