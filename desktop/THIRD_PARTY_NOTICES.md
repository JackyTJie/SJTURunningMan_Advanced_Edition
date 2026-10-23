# Third-party notices

SJTU RunningMan desktop bundles the following assets and libraries.

## Runtime

- **Material Components Android — linear wavy progress drawing and motion** — Apache
  License 2.0, Copyright (C) 2020 The Android Open Source Project.
  Ported to TypeScript/Canvas2D for animated semester progress; this is not an official
  Material Web component. Source revision and modifications:
  [`third_party/material-progress/README.md`](third_party/material-progress/README.md).
  Bundled license: `public/licenses/Apache-2.0.txt`.
- **AndroidX dynamic animation / AOSP PathInterpolator** — Apache License 2.0,
  Copyright The Android Open Source Project. Source-derived spring/easing port;
  revisions and changes are listed in the progress port notes above.
- **Skia cubic contour measurement and subdivision** — BSD-3-Clause,
  Copyright Google Inc. / Google LLC. TypeScript adaptation; bundled license:
  `public/licenses/Skia-BSD.txt`.
- **@material/web** — Apache License 2.0, Copyright Google LLC.
  <https://github.com/material-components/material-web>
- **material (md3.io) 3.2.4** — MIT License, Copyright (c) 2025 floor.
  End-date picker and distance slider; <https://github.com/floor/material>.
  Bundled license: `public/licenses/material-MIT.txt`.
- **React / React DOM** — MIT License, Copyright Meta Platforms, Inc. and affiliates.
- **Tauri** — Apache License 2.0 / MIT License, Copyright Tauri Programme within the Commons Conservancy.

## Fonts

- **Roboto** — Apache License 2.0, Copyright Google Inc.
  Bundled subset: `desktop/public/fonts/roboto-latin.woff2`.
- **Material Symbols Rounded** — Apache License 2.0, Copyright Google LLC.
  Bundled subset: `desktop/public/fonts/material-symbols-rounded.woff2`.
  The subset only contains the icon ligatures used by this application.

The full Apache License 2.0 text is included at
[`desktop/public/fonts/LICENSE-Apache-2.0.txt`](public/fonts/LICENSE-Apache-2.0.txt).

## Map pages

The locally served preview and planner pages load Leaflet and map tiles from
third-party providers at runtime (Baidu Maps / OpenStreetMap). Those services
are not bundled and remain subject to their own terms.
