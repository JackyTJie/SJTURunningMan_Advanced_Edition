# Credits

This project stands on the work of its predecessors and many helpful contributors.

## Lineage

- **Original author** — [@Labyrinth0419](https://github.com/Labyrinth0419)
  Created the original project and later added the "交我办" login flow.
- **Original enhanced-edition author** — [@accelerator-s](https://github.com/accelerator-s)
  Added features and improvements, and fixed off-campus login issues.

## Contributors

- [@CEQ151](https://github.com/CEQ151) — improved the desktop GUI and README, and migrated the desktop client to Rust + Slint
- [@AetherWish](https://github.com/AetherWish) — contributed the HarmonyOS source
- [@tangyang0](https://github.com/tangyang0) — fixed a file-path bug on macOS
- [@dajiaohuang](https://github.com/dajiaohuang) — fixed an undefined-variable bug

## Dependencies and assets

- [Rust](https://www.rust-lang.org/) + [Tauri 2](https://tauri.app/) — desktop backend, windowing and packaging
- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [@material/web](https://github.com/material-components/material-web) — Material Design 3 desktop UI
- [material / md3.io](https://md3.io/) — desktop end-date picker and distance slider (third-party MD3 component, MIT)
- [Material Components Android](https://github.com/material-components/material-components-android) — official drawing source for the wavy semester progress indicator (Apache 2.0); [desktop port notes](../../desktop/third_party/material-progress/README.md)
- [Roboto](https://fonts.google.com/specimen/Roboto) + [Material Symbols](https://fonts.google.com/icons) — UI fonts and icons (Apache 2.0, bundled as used subsets)
- [PySide6 / Qt](https://www.qt.io/) — legacy desktop UI (v4.4.x and earlier, retired)
- [Leaflet](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/) — desktop route planner base map
- [Baidu Maps](https://lbsyun.baidu.com/) — mobile route design base map
- [Jetpack Compose](https://developer.android.com/jetpack/compose) — Android UI
- [SwiftUI](https://developer.apple.com/xcode/swiftui/) — iOS UI
- [ArkTS](https://developer.huawei.com/consumer/cn/arkts/) — HarmonyOS UI
- [小白调试助手](https://github.com/likuai2010/auto-installer) — HarmonyOS HAP installer

## How to join this list

Once your PR is merged, add yourself to the contributor list in the same PR:

```markdown
- [@your-handle](https://github.com/your-handle) — what you did
```

See [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

Thanks to everyone on [Shuiyuan](https://shuiyuan.sjtu.edu.cn/t/topic/421786) who discussed and reported issues.
