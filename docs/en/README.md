# Documentation Index

This directory is the English mirror of the project documentation. The root [README](../../README.md) is just the front page and navigation.

> **中文**: [docs/](../README.md)

## By platform

| Platform | Version | Document | When to use |
| --- | --- | --- | --- |
| Desktop (Windows / macOS / Linux) | `v4.5.0` | [desktop.md](./desktop.md) | Full-featured GUI with route preview |
| macOS install & first launch | `v4.5.0` | [macos.md](./macos.md) | DMG install, getting past Gatekeeper |
| Android | `4.5.0` | [android.md](./android.md) | Install the APK and go |
| iOS | `4.5.0` | [ios.md](./ios.md) | iPhone; requires building with Xcode |
| HarmonyOS NEXT | `4.5.0` | [harmonyos.md](./harmonyos.md) | Huawei devices; HAP sideload |

## General topics

| Document | Content |
| --- | --- |
| [routes.md](./routes.md) | Route planner, route import, coordinate systems (BD09 / GCJ02 / WGS84) |
| [build.md](./build.md) | Building and packaging each platform from source |
| [testing.md](./testing.md) | Testing guide: how to run, what is covered, manual checklists |
| [faq.md](./faq.md) | Troubleshooting |
| [credits.md](./credits.md) | Credits and contributors |

## Project governance

| File | Content |
| --- | --- |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Branching, commits, build prerequisites, PR checklist |
| [SECURITY.md](../../SECURITY.md) | Vulnerability reporting and credential safety |
| [AGENTS.md](../../AGENTS.md) | Repository map for AI coding assistants |
| [CHANGELOG.md](../../CHANGELOG.md) | Release history |
| Branch `archive/python-qtui-legacy` | Read-only snapshot of the last Python + Qt client (tag `python-qtui-final`); unmaintained, kept only to compare against legacy behaviour |

## Repository layout

```
SJTURunningMan_Advanced_Edition/
├── desktop/                Tauri 2 desktop (React 19 frontend + src-tauri/ Rust backend)
├── Cargo.toml              Desktop Cargo workspace (version lives in desktop/src-tauri/Cargo.toml)
├── assets/                 Icons and built-in routes (assets/Routes/)
├── build_windows.ps1       Windows packaging script
├── route_planner.html      Desktop route planner (Baidu by default, OpenStreetMap optional)
├── apps/
│   ├── android/            Android project (Kotlin / Jetpack Compose)
│   ├── ios/                iOS project (Swift / SwiftUI)
│   └── harmonyos/          HarmonyOS project (ArkTS / stage model)
├── docs/                   This documentation
└── .github/workflows/      release.yml
```

## Suggested reading order

1. Read the root [README](../../README.md) for the project's purpose and disclaimer.
2. Open the document for the platform you intend to use.
3. For custom routes, read [routes.md](./routes.md).
4. Stuck? Check [faq.md](./faq.md).
5. Want to change code? Start with [build.md](./build.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).
