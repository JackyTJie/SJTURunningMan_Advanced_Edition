# 文档截图规格

`docs/` 下各文档引用的截图都放在本目录。**文件名是对外契约**：替换图片时保持文件名不变，文档中的链接无需改动。

## 当前文件

| 文件 | 尺寸 | 内容 | 体积 |
| --- | --- | --- | --- |
| `desktop-tauri-light.webp` | 1000×651 | Tauri 2 + MD3 电脑版浅色工作台，含计划摘要与内嵌路线地图 | 约 43 KB |
| `desktop-tauri-dark.webp` | 1000×651 | Tauri 2 + MD3 电脑版深色工作台，含计划摘要与内嵌路线地图 | 约 40 KB |
| `desktop-tauri-login.webp` | 1000×700 | JAccount 登录窗口（账号密码 / 扫码分段切换），验证码输入框与图片已遮挡 | 约 20 KB |
| `desktop-tauri-login-qr.webp` | 1000×700 | 扫码登录面板，示例二维码不可用 | 约 27 KB |
| `desktop-tauri-logs.webp` | 1000×700 | 学期日历与运行日志两栏 | 约 17 KB |
| `desktop-tauri-routes.webp` | 1000×700 | 导入路线、跳段警告与删除入口 | 约 21 KB |
| `desktop-native-light.webp` | 1000×732 | 旧 Rust + Slint 浅色界面（历史对照） | 约 21 KB |
| `desktop-native-dark.webp` | 1000×732 | 旧 Rust + Slint 深色界面（历史对照） | 约 21 KB |
| `desktop-main.webp` | 1000×686 | 旧 Qt 电脑版主界面（历史对照，非当前界面） | 37 KB |
| `desktop-preview.webp` | 1000×727 | 旧版本机地图页的 OSM 轨迹图（含当时的底图状态条；现预览地图嵌入卡片、固定 OSM 且不显示状态条） | 约 56 KB |
| `android-main.webp` | 480×1056 | 安卓工作台：本学期进度、任务设置与四页底部导航 | 24 KB |
| `android-route.webp` | 480×1056 | 安卓路线设计页：地图上已连点若干坐标 | 40 KB |
| `ios-main.webp` | 480×1044 | iOS 工作台：本学期进度、任务设置与四页底部导航 | 22 KB |
| `harmonyos-main.webp` | 480×1069 | 鸿蒙主界面：账号页与跑步参数页 | 26 KB |
| `macos-install-dmg.webp` | 1000×652 | macOS：DMG 挂载后拖拽安装到 Applications | 15 KB |
| `macos-gatekeeper.webp` | 534×580 | macOS：首次打开被 Gatekeeper 拦截的弹窗 | 19 KB |
| `macos-open-anyway.webp` | 1000×849 | macOS：系统设置 → 隐私与安全性 → 仍要打开 | 41 KB |

全部为 WebP。`desktop-tauri-*` 由生产前端截图生成，部分界面用 mock IPC 数据填充；旧 Rust + Slint 与 Qt 截图保留作历史对照。

应用界面截图（桌面端 `desktop-tauri-*`、安卓、iOS、鸿蒙）按手机 480 px / 桌面 1000 px 宽存放，其中 `desktop-main.webp` 是迁移前的旧 Qt 界面，仅作历史对照。最后三张是 macOS 的**安装流程**截图，内容是系统弹窗与系统设置界面，按原始比例裁剪，未套用统一宽度。

**尺寸约定**：手机端统一缩到 **480 px 宽**，桌面端 **1000 px 宽**。文档渲染时 GitHub 会把图片压到容器宽度（约 850 px）以内，再大的分辨率只是徒增仓库体积 —— 480 px 下字段名、按钮、日志文字仍然清晰可辨。

原始截图分辨率更高（安卓 1080×2376、iOS 678×1376、鸿蒙 707×1574），但**不做放大**，只按上述宽度等比缩小。

## 替换 / 新增图片

文件名不变，用同名文件覆盖即可，**所有文档链接无需改动**：

```bash
# 手机端：缩到 480 px 宽（> 表示只在原图更大时才缩放），去元数据，质量 80
magick ~/shot.png -resize '480x>' -strip -quality 80 docs/images/android-main.webp

# 桌面端：缩到 1000 px 宽
magick ~/shot.png -resize '1000x>' -strip -quality 80 docs/images/desktop-preview.webp
```

- `-strip` 会去掉 EXIF / GPS 等元数据，截图请保留这个参数；
- 单张控制在 100 KB 以内，总量控制在 250 KB 以内；超了就降 `-quality` 或降宽度；
- 新增图片：先加到上表，再在文档里引用，命名格式 `<平台>-<用途>.webp`（全小写、连字符分隔）。

## 截图规范

- **尺寸**：截图时可以按真机分辨率截（方便自己看清），但**入库前一律缩到 480 px（手机）/ 1000 px（桌面）宽**，且不要放大。
- **格式**：统一 WebP。PNG/JPEG 截图转 WebP 通常能小 3–4 倍。若某处必须用 PNG，压到 100 KB 以内。
- **内容**：界面语言保持应用原文（中文）。**避免出现账号、Cookie、验证码、真实姓名学号** —— 截图前先登出或打码，这些图会随文档公开。
- **裁剪**：只保留相关区域，去掉桌面任务栏、手机状态栏的多余部分；不要叠加红框、箭头以外的装饰。
