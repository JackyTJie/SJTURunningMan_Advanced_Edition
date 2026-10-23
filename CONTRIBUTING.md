# 贡献指南

感谢你愿意参与。本项目分四个互相独立的平台，**先确定你要改哪一个**，再按对应流程来。

## 目录速查

| 平台 | 目录 | 语言 / 框架 |
| --- | --- | --- |
| 电脑版 | `desktop/` 前端 + `desktop/src-tauri/`（根 Cargo workspace） | Tauri 2 + React 19 + TypeScript + Rust |
| 安卓 | `apps/android/` | Kotlin + Jetpack Compose |
| iOS | `apps/ios/` | Swift + SwiftUI |
| 鸿蒙 | `apps/harmonyos/` | ArkTS |

各平台的构建前置与命令见 [docs/build.md](docs/build.md)。

> ⚠️ 四个平台**互不引用**，改一个不会影响另一个。请不要在平台之间做"顺手统一"，那会放大改动面。

## 开发环境

### 电脑版

```bash
pnpm --dir desktop install --frozen-lockfile
pnpm --dir desktop tauri dev
pnpm --dir desktop build
cargo test --workspace --locked
```

### 安卓

需要 JDK 17+ 与 Android SDK。依赖版本集中在 `apps/android/gradle/libs.versions.toml`，改版本优先改那里。

### iOS

macOS + Xcode 16+，签名配置见 [docs/ios.md](docs/ios.md#3-配置签名)。

### 鸿蒙

DevEco Studio，签名与 HAP 构建见 [docs/build.md](docs/build.md#鸿蒙)。

## 分支与提交

- 从 `master` 切分支：`feat/<主题>`、`fix/<主题>`、`docs/<主题>`；
- 一个 PR 只做一件事，避免把格式化、重构和功能混在一起；
- 提交信息用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 前缀：

  ```
  feat(android): 增加自定义路线点顺序校验
  fix(desktop): 修复 macOS 下 Routes 目录路径拼接错误
  docs: 拆分 README 为分平台文档
  ```

- 提交信息说清**做了什么**；**为什么**不显然时补一段正文。
- **归档分支 `archive/python-qtui-legacy` 只读**：最后一版 Python + Qt 客户端的快照（tag `python-qtui-final`），只用来比对旧版行为。不要从它往 `master` 恢复代码，也不要在那条分支上提改动。

## 提交前自检

- [ ] 改动只涉及一个平台（跨平台改动请在 PR 说明里讲清理由）；
- [ ] 电脑版按 [docs/testing.md](docs/testing.md#电脑版) 过一遍手动清单；
- [ ] 安卓改了逻辑 → 跑 `cd apps/android && ./gradlew test`；
- [ ] 没有把构建产物、`local.properties`、IDE 配置、`.DS_Store` 带进提交；
- [ ] 没有提交任何凭据：Cookie、密码、验证码、keystore、`.env`；
- [ ] 改了界面 → 更新了对应文档里的截图（见下）。

## 文档与截图

- 用户可见的行为变更，请同步更新 `docs/` 下的对应文档；中文改了，`docs/en/` 的镜像也请一并更新；
- 截图规范（尺寸、命名、体积、脱敏要求）见 [docs/images/README.md](docs/images/README.md)；
- **截图前先登出或打码** —— 不要出现账号、Cookie、验证码、真实姓名学号。

## 版本号

各平台版本号互相独立，位置：

| 平台 | 文件 | 字段 |
| --- | --- | --- |
| 电脑版 | `desktop/src-tauri/Cargo.toml` | `package.version` |
| 安卓 | `apps/android/app/build.gradle.kts` | `versionName` / `versionCode` |
| iOS | `apps/ios/SJTURunningMan.xcodeproj/project.pbxproj` | `MARKETING_VERSION` |
| 鸿蒙 | `apps/harmonyos/AppScope/app.json5` | `versionName` / `versionCode` |

发版由维护者打 `v*` tag 触发 `release.yml`；tag 必须与 `desktop/src-tauri/Cargo.toml` 的 `version` 一致，工作流会断言，不一致直接失败。**不要**在功能 PR 里顺手改版本号。

## 不要提交的东西

`AGENTS.md` 与 `.gitignore` 已覆盖，这里再列一遍最常犯的：

- 构建产物：`build/`、`dist/`、`apps/android/app/build/`、`*.apk`、`*.hap`、`*.ipa`；
- 依赖目录：`.venv/`、`node_modules/`、`oh_modules/`；
- IDE / 工具：`.idea/`、`.vscode/`、`.claude/`、`.qwen/`、`.cursor/`；
- 本地配置：`local.properties`、keystore 与签名配置；
- 系统文件：`.DS_Store`。

清理本地残留（**先 dry-run**）：

```bash
git clean -Xdn     # 预览
git clean -Xdf     # 执行
```

## 提交 PR

1. Fork 并推分支；
2. 按 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md) 填写：改了什么、为什么、怎么验证的、影响哪个平台；
3. 如果修的是 issue，在描述里写 `Closes #123`；
4. 等待 review。界面改动请附上截图或录屏。

## 安全问题

**不要用公开 issue 报安全问题**，走 [SECURITY.md](SECURITY.md) 的私有通道。

## 致谢

PR 合并后，欢迎在同一个 PR 里把自己加到 [docs/credits.md](docs/credits.md) 的贡献者列表。
