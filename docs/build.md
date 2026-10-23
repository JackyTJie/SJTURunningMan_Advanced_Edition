# 从源码构建

四个平台各自独立构建，互不依赖。改哪个平台就构建哪个。

| 平台 | 目录 | 工具链 | 产物 |
| --- | --- | --- | --- |
| 电脑版 | 仓库根 + `desktop/` | Rust 1.95+ / Tauri 2 / pnpm + Node 22+ | `.exe` / `.dmg` / `.deb` |
| 安卓 | `apps/android/` | Gradle 9.4.1 + AGP 8.13.0 + Kotlin 2.2.10 | `.apk` / `.aab` |
| iOS | `apps/ios/` | Xcode 16+ | `.ipa` |
| 鸿蒙 | `apps/harmonyos/` | DevEco Studio / hvigor | `.hap` |

---

## 电脑版

### 直接运行源码

只想把电脑版跑起来，不需要制作安装包：

```bash
git clone https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition.git
cd SJTURunningMan_Advanced_Edition
pnpm --dir desktop install --frozen-lockfile
pnpm --dir desktop tauri dev
```

需要 Rust 1.95+、Node.js 22+、pnpm 11+，以及对应平台的 Tauri 系统依赖。电脑版使用操作系统 WebView（Windows WebView2 / macOS WKWebView / Linux WebKitGTK），不携带 Chromium、Qt 或 Python。首次启动仍需阅读并勾选使用承诺书。

> `pnpm tauri dev` 会同时启动 Vite（端口 1420）与 Tauri 窗口。直接 `cargo run` 属于 Tauri 开发模式，会连接这个 dev server；单独运行它不会加载前端。生产构建请带 `custom-protocol` feature。

### 前端与原生构建

```bash
# 使用当前 stable Rust；Cargo.lock 固定全部依赖
pnpm --dir desktop install --frozen-lockfile
pnpm --dir desktop build            # tsc --noEmit + vite build
cargo test --workspace --locked
cargo build --release --locked -p sjturunningman --features custom-protocol

# 或让 Tauri CLI 一次完成前端与打包
pnpm --dir desktop tauri build
```

Windows：安装 Rust 1.95+、Node 22+、pnpm 11+，并准备 MSVC Build Tools 或 MinGW-w64 工具链。运行 `./build_windows.ps1`（会先构建前端）→ `dist/SJTURunningMan.exe`。`.cargo/config.toml` 为 MSVC 配置静态 CRT；本轮实际验证的是 GNU 工具链。用户机器需要 WebView2 Runtime（Windows 10/11 通常已预装）。

macOS（需安装 Xcode Command Line Tools）：

```bash
rustup target add x86_64-apple-darwin aarch64-apple-darwin
pnpm --dir desktop build
MACOSX_DEPLOYMENT_TARGET=11.0 cargo build --release --locked --features custom-protocol --target x86_64-apple-darwin
MACOSX_DEPLOYMENT_TARGET=11.0 cargo build --release --locked --features custom-protocol --target aarch64-apple-darwin
mkdir -p dist
lipo -create target/x86_64-apple-darwin/release/sjturunningman target/aarch64-apple-darwin/release/sjturunningman -output dist/SJTURunningMan
python3 scripts/package_desktop.py macos --binary dist/SJTURunningMan
```

Linux（Ubuntu 24.04，支持 X11 / Wayland）：

```bash
sudo apt-get install build-essential pkg-config libssl-dev libxdo-dev \
  libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev \
  libayatana-appindicator3-dev libsoup-3.0-dev
pnpm --dir desktop build
cargo build --release --locked --features custom-protocol
python3 scripts/package_desktop.py linux --binary target/release/sjturunningman --arch amd64
# ARM64: build on an ARM64 host and use --arch arm64.
```

`APP_VERSION` 可覆盖显示版本，否则 `desktop/src-tauri/build.rs` 取 `desktop/src-tauri/Cargo.toml` 的 `package.version`；发 tag 时 `release.yml` 会断言两者一致。Python 仅运行构建机的打包脚本，不随应用分发。Release 把前端资源与字体子集嵌入二进制，不打包 Chromium / Qt / Python；Linux 运行时应使用系统 WebKitGTK。旧 Python 模块、`requirements.txt` 与 PyInstaller 配置已全部移除，仓库里只剩 `scripts/` 下的打包脚本用到 Python。

### 桌面检查与发布构建

`Native desktop checks`（`.github/workflows/desktop-check.yml`）在桌面代码 push / PR 时运行，也支持 Actions 页的 **Run workflow**。它在 Ubuntu 上先安装前端依赖并执行 `tsc --noEmit` + Vite 构建，再跑 `cargo fmt`、`cargo clippy`、`cargo test` 和打包布局测试，不构建任何安装包，通常几分钟内结束。

Windows exe、macOS universal2 DMG、Linux amd64 / arm64 deb 的构建、打包验证与上传由 [`.github/workflows/release.yml`](../.github/workflows/release.yml) 在推送 tag 或手动发布时完成。macOS 为 ad-hoc 签名，不包含 Apple Developer ID 或公证。真实 WebView 的 `--ui-smoke-test` 需要图形会话，默认在本地执行，不放进发布流水线。

### 自动发布流水线

[`.github/workflows/release.yml`](../.github/workflows/release.yml) 在推送 tag（`4.5.0` 与 `v4.5.0` 两种写法都认）或手动 `workflow_dispatch` 时触发，并行构建五类产物 + 一份校验文件，合成草稿 Release：

| 产物 | 运行环境 |
| --- | --- |
| `SJTURunningMan_<ver>_windows.exe` | windows-latest |
| `SJTURunningMan_<ver>_macOS.dmg` | macos-latest（universal2） |
| `SJTURunningMan_<ver>_linux_amd64.deb` | ubuntu-24.04 |
| `SJTURunningMan_<ver>_linux_arm64.deb` | ubuntu-24.04-arm |
| `SJTURunningMan_<ver>_android.apk` | ubuntu-latest（自签名） |
| `SHA256SUMS.txt` | release 作业汇总生成 |

桌面使用 stable Rust（当前锁定依赖要求 Rust 1.95+）、Node 22+、pnpm 11+ 和 Cargo.lock。两个 deb 构建在 Ubuntu 24.04 上，声明 glibc ≥ 2.39，并依赖 WebKitGTK 4.1 / GTK 3。macOS 通过 lipo 合并两套 Rust 目标；Windows 内嵌现有图标。应用运行不需要 Python。

> **iOS 与鸿蒙 NEXT 不在这个流水线里**，Releases 也不提供它们的预编译包，目前都只手工构建：
>
> - **iOS** —— 技术上可以用 macos runner 自动化，但需要 Apple 签名身份（证书 + 描述文件）；没有签名的包装不上，所以现阶段不做。
> - **鸿蒙 NEXT** —— 华为的命令行工具包必须登录华为账号下载且链接短期有效，不适合无人值守的 CI；签名还需要 AppGallery Connect 签发的 keystore / 证书 / profile 三件套。

**正确的发布顺序**：推 tag → 工作流构建 → 生成草稿并挂上全部产物 → 人工审核 → 点发布。不要反过来先手动建 release 再推 tag，`action-gh-release` 会去更新已存在的 release，而 `draft: true` 会把已发布的打回草稿。

#### 产物校验

每个构建作业都会用 `actions/attest-build-provenance` 给产物生成**来源证明**：证书由 GitHub OIDC 签发，绑定本次工作流运行与提交，**本机无法伪造**。用户侧可以验证：

```bash
# 需要 gh CLI 2.49 及以上
gh attestation verify SJTURunningMan_<ver>_windows.exe --repo JackyTJie/SJTURunningMan_Advanced_Edition
```

注意这只是**构建来源**的证明，不等于软件可信 —— 能触发这个工作流的人同样能签出有效证明。安卓 APK 另有自签名，是另一个层面的保证。

#### 权限

工作流全局只有 `contents: read`，写权限按作业提升：`release` 作业要 `contents: write`；五个构建作业各要 `id-token: write`（换 OIDC token）与 `attestations: write`（存证）。这样敏感的 OIDC 权限不会落在 `meta` 这类不需要它的作业上。

#### Release 正文自动生成

推 tag 之后，草稿的正文由 `release` 作业动态拼出来，结构固定：

| 部分 | 来源 |
| --- | --- |
| 标题、发布时间 | 时间取 **tag 指向提交的时间**，比工作流运行时间更贴近语义 |
| 适用平台与版本号 | 桌面端用 tag 版本；Android / HarmonyOS 从各自工程文件读（`build.gradle.kts` 的 `versionName`、`app.json5` 的 `versionName`）—— 读不到就显示 `?`，不会失败 |
| `<details>` 折叠的 **What's Changed** | 调 GitHub 的 `releases/generate-notes` 接口生成 |
| **新功能 / 优化 / 修复 / 致谢** | **空段落 + `<!-- 提示 -->`**，发布会前手写 |
| **下载表格** | 各平台产物的链接与 SHA256，附完整性 / 来源证明的校验说明 |

两个注意点：

- `generate_release_notes` 是**关闭**的 —— What's Changed 是我们自己取来放进 `<details>` 的，开着会在正文末尾再追加一份，重复；
- `append_body` 默认关闭，重跑会**覆盖**正文而不是往后堆，所以改完正文重跑不会出现两份表格。

### 发布前需要配置的 Secrets

安卓产物是**自签名**的，签名材料必须放在仓库 Secrets 里，否则 `build-android` 作业会直接失败（不会退化成未签名包 —— 那种包装不上，发出去更糟）：

| Secret | 内容 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | keystore 文件的 base64（**单行，不要换行**） |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 口令 |
| `ANDROID_KEY_ALIAS` | 密钥别名 |
| `ANDROID_KEY_PASSWORD` | 密钥口令 |

生成并配置：

```bash
keytool -genkeypair -v \
  -keystore release.jks -alias sjturunningman \
  -keyalg RSA -keysize 4096 -validity 10000 -storetype PKCS12

base64 -i release.jks | tr -d '\n' | gh secret set ANDROID_KEYSTORE_BASE64
gh secret set ANDROID_KEYSTORE_PASSWORD
gh secret set ANDROID_KEY_ALIAS
gh secret set ANDROID_KEY_PASSWORD
```

> ⚠️ **务必留存 `release.jks` 与两个口令。** 换了 keystore 就等于换了签名，之后发的 APK 无法覆盖安装到已有用户的设备上，只能卸载重装。

---

## 安卓

```bash
cd apps/android

# 调试包
./gradlew assembleDebug

# 发布包（需配置签名）
./gradlew assembleRelease
```

产物在 `app/build/outputs/apk/`。

- 包名 `com.sjtu.runner`，`minSdk = 26`、`targetSdk = 34`、`compileSdk = 34`；
- 版本号在 `app/build.gradle.kts` 的 `versionCode` / `versionName`；
- 未配置签名时 `assembleRelease` 产出的是未签名包。签名需要 `keystore` 相关属性（见 `app/build.gradle.kts` 的 `signingConfigs`）。

> 依赖版本集中在 `gradle/libs.versions.toml`（版本目录），改版本优先改那里。

## iOS

```bash
cd apps/ios
open SJTURunningMan.xcodeproj
```

在 Xcode 中配置 Team ID 与 Bundle ID 后构建，步骤详见 [ios.md](./ios.md#3-配置签名)。

命令行检查工程与 scheme：

```bash
xcodebuild -project apps/ios/SJTURunningMan.xcodeproj -list
```

## 鸿蒙

用 **DevEco Studio** 打开 `apps/harmonyos/` 工程，选择合适的签名后构建 HAP；也可以直接命令行构建：

**Windows**

```powershell
cd apps/harmonyos
.\hvigorw assembleHap
```

**macOS / Linux**

```bash
cd apps/harmonyos
./hvigorw assembleHap
```

工程里提交了 `hvigorw` / `hvigorw.bat` / `hvigorw.js` 包装脚本（与 DevEco Studio 自带的一致，仅 `hvigorw.js` 有一处本地补丁，见下）。脚本会自动找到 DevEco Studio 并推导出 `DEVECO_SDK_HOME` / `NODE_HOME` / `HVIGOR_TOOLS_HOME`：

- Windows（`hvigorw.bat`）：先看 `DEVECO_STUDIO_PATH`，再看 `%ProgramFiles%\Huawei\DevEco Studio` 与 `D:\HUAWEI\DevEco Studio`，最后查注册表 `HKCU/HKLM\Software\Huawei\DevEcoStudio` 与卸载信息里的 `InstallLocation`；
- macOS / Linux（`hvigorw`）：先看 `DEVECO_STUDIO_PATH`，再依次探测 `/Applications/DevEco-Studio.app/Contents`、`~/Applications/DevEco-Studio.app/Contents`、`/opt/deveco-studio`、`/usr/local/deveco-studio`、`~/deveco-studio`。

若探测不到，可手动指定（路径按本机实际安装位置调整）：

```powershell
$env:DEVECO_SDK_HOME  = 'D:\HUAWEI\DevEco Studio\sdk'
$env:NODE_HOME        = 'D:\HUAWEI\DevEco Studio\tools\node'
$env:HVIGOR_TOOLS_HOME = 'D:\HUAWEI\DevEco Studio\tools\hvigor'
cd apps/harmonyos
.\hvigorw assembleHap
```

> **`hvigorw.js` 的本地补丁**：原始文件位于 DevEco 的 `tools/hvigor/bin/`，它用 `path.resolve(__dirname, "..")` 推断 hvigor 安装目录（即 `tools/hvigor`）。把脚本搬进 `apps/harmonyos/` 后 `..` 会变成 `apps/`，导致包装脚本试图把不存在的 `apps/hvigor` 链进工程缓存并报 `EEXIST` / 生成空占位目录。补丁让该表达式优先使用 `HVIGOR_TOOLS_HOME`（变量存在且目录真实存在时才采用），否则**逐字节回落到原表达式**，因此其它安装布局、macOS 与 Linux 不受影响。升级 DevEco Studio 后需重新拷贝该文件并重新打这一处补丁（搜索 `HVIGOR_TOOLS_HOME` 即可定位）。

完全不走包装脚本时，仍可直接调用 DevEco 自带的 hvigor：

```powershell
$env:DEVECO_SDK_HOME = 'D:\HUAWEI\DevEco Studio\sdk'
& 'D:\HUAWEI\DevEco Studio\tools\node\node.exe' `
  'D:\HUAWEI\DevEco Studio\tools\hvigor\bin\hvigorw.js' `
  --mode module -p product=default assembleHap --no-daemon
```

- Bundle Name `com.sjtu.runner`，版本在 `AppScope/app.json5`（`versionName` 与安卓端保持一致）；
- 产物在 `entry/build/default/outputs/default/`；
- 未做开发者认证时，调试证书有效期很短，安装前请先完成认证（见 [harmonyos.md](./harmonyos.md#1-安装-hap-包)）。

---

## 清理本地构建残留

构建产物、虚拟环境等已在 `.gitignore` 中，但会占本地磁盘（`.venv/` 约 1.2 GB、`dist/` 约 238 MB、`build/` 约 86 MB、`apps/android/app/build/` 约 107 MB）。清理前**先 dry-run 确认要删什么**：

```bash
git clean -Xdn     # 预览：只列被 .gitignore 忽略的文件
git clean -Xdf     # 执行删除（不可恢复，确认无误再跑）
```

`-X` 只删被忽略的文件，不会碰你的源码改动。
