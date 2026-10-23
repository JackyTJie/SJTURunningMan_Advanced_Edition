# 致谢

本项目站在前人和许多热心同学的肩膀上。

## 项目传承

- **原项目作者** — [@Labyrinth0419](https://github.com/Labyrinth0419)
  创建了优秀的原项目，后续加入「交我办」登录功能。
- **原增强版作者** — [@accelerator-s](https://github.com/accelerator-s)
  添加了新功能与改进，并修复了异地登录问题。

## 贡献者

- [@CEQ151](https://github.com/CEQ151) — 优化电脑版图形界面与 README，并将桌面端迁移到 Rust + Slint
- [@AetherWish](https://github.com/AetherWish) — 贡献了鸿蒙版源码
- [@tangyang0](https://github.com/tangyang0) — 修复了 macOS 上的文件路径 Bug
- [@dajiaohuang](https://github.com/dajiaohuang) — 修复变量未定义 Bug
- [@66CF](https://github.com/66CF) — 将桌面端从 Rust + Slint 迁移到 Tauri 2 + React 19 + Material Design 3，并补齐浏览器自动化检查与 CI

## 依赖与资源

- [Rust](https://www.rust-lang.org/) + [Tauri 2](https://tauri.app/) — 电脑版后端、窗口与打包
- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [@material/web](https://github.com/material-components/material-web) — 电脑版 Material Design 3 界面
- [material / md3.io](https://md3.io/) — 电脑版结束日期选择器与距离滑块（第三方 MD3 组件，MIT）
- [Material Components Android](https://github.com/material-components/material-components-android) — 学期波浪进度条的官方绘制源码（Apache 2.0）；[桌面移植说明](../desktop/third_party/material-progress/README.md)
- [Roboto](https://fonts.google.com/specimen/Roboto) + [Material Symbols](https://fonts.google.com/icons) — 界面字体与图标（Apache 2.0，按实际用到的子集打包）
- [PySide6 / Qt](https://www.qt.io/) — 旧版电脑版界面（v4.4.x 及更早，已退役）
- [Leaflet](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/) — 电脑版路线规划器底图
- [百度地图](https://lbsyun.baidu.com/) — 移动端路线设计页底图
- [Jetpack Compose](https://developer.android.com/jetpack/compose) — 安卓界面
- [SwiftUI](https://developer.apple.com/xcode/swiftui/) — iOS 界面
- [ArkTS](https://developer.huawei.com/consumer/cn/arkts/) — 鸿蒙界面
- [小白调试助手](https://github.com/likuai2010/auto-installer) — 鸿蒙 HAP 安装工具

## 如何加入这个名单

提交被合并的 PR 后，欢迎在同一个 PR 里把自己的名字加到上面的「贡献者」列表。格式：

```markdown
- [@你的用户名](https://github.com/你的用户名) — 做了什么
```

流程见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

---

感谢 [水源社区](https://shuiyuan.sjtu.edu.cn/t/topic/421786) 上参与讨论与反馈的同学。
