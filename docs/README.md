# 文档索引

本目录是 SJTU 一键校园跑工具的完整使用与开发文档。根目录的 [README](../README.md) 只作门面与导航，细节都在这里。

> **English**: [docs/en](./en/README.md)

## 按平台阅读

| 平台 | 版本 | 文档 | 适用场景 |
| --- | --- | --- | --- |
| 电脑版（Windows / macOS / Linux） | `v4.5.0` | [desktop.md](./desktop.md) | 桌面图形界面，功能最全，带路线预览 |
| macOS 安装与首次打开 | `v4.5.0` | [macos.md](./macos.md) | DMG 安装、Gatekeeper 拦截的处理 |
| 安卓 | `4.5.0` | [android.md](./android.md) | 手机一键跑步，安装 APK 即用 |
| iOS | `4.5.0` | [ios.md](./ios.md) | iPhone，需自行用 Xcode 编译安装 |
| 鸿蒙 NEXT | `4.5.0` | [harmonyos.md](./harmonyos.md) | 华为鸿蒙设备，需 HAP 调试安装 |

## 通用主题

| 文档 | 内容 |
| --- | --- |
| [routes.md](./routes.md) | 路线规划器、路线导入、各平台坐标系差异（BD09 / WGS84） |
| [build.md](./build.md) | 从源码构建与打包各平台 |
| [testing.md](./testing.md) | 测试指南：怎么跑、跑什么、手动验收清单 |
| [faq.md](./faq.md) | 常见问题与故障排除 |
| [credits.md](./credits.md) | 致谢与贡献者名单 |

## 项目治理

| 文件 | 内容 |
| --- | --- |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 如何参与贡献：分支、提交、构建前置、PR 自检 |
| [SECURITY.md](../SECURITY.md) | 漏洞报告通道与凭据安全须知 |
| [AGENTS.md](../AGENTS.md) | 给 AI 编码助手（Claude Code / Cursor 等）的仓库地图 |
| [CHANGELOG.md](../CHANGELOG.md) | 版本更新日志 |
| 归档分支 `archive/python-qtui-legacy` | 最后一版 Python + Qt 客户端的只读快照（tag `python-qtui-final`），不再维护，仅用于比对旧版行为 |

## 仓库结构

```
SJTURunningMan_Advanced_Edition/
├── desktop/                Tauri 2 电脑版（React 19 前端 + src-tauri/ Rust 后端）
├── Cargo.toml              桌面 Cargo workspace（版本号在 desktop/src-tauri/Cargo.toml）
├── assets/                 图标、内置路线（assets/Routes/）
├── build_windows.ps1       Windows 打包脚本
├── route_planner.html      电脑版路线规划器（默认百度，可切 OpenStreetMap）
├── apps/
│   ├── android/            安卓工程（Kotlin / Jetpack Compose）
│   ├── ios/                iOS 工程（Swift / SwiftUI）
│   └── harmonyos/          鸿蒙工程（ArkTS / stage 模型）
├── docs/                   本文档目录
└── .github/workflows/      发布流水线 release.yml
```

## 阅读顺序建议

1. 先读根 [README](../README.md) 了解项目定位与免责声明；
2. 找到你要用的平台，读对应平台文档；
3. 需要自定义路线就看 [routes.md](./routes.md)；
4. 遇到问题查 [faq.md](./faq.md)；
5. 想改代码，从 [build.md](./build.md) 和 [CONTRIBUTING.md](../CONTRIBUTING.md) 开始。
