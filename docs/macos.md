# macOS 使用指南

电脑版的 macOS 部分。功能与 Windows 版一致，差异只在**安装方式**与**首次打开被系统拦截的处理**上。

通用功能（参数含义、路线预览、上传流程、数据生成逻辑）见 [desktop.md](./desktop.md)，本文不重复。

## 系统要求

| 项 | 要求 |
| --- | --- |
| macOS | 构建部署目标为 **11.0**；实际兼容性待 macOS 真机验证 |
| 架构 | Apple Silicon 与 Intel **通吃**，同一份 universal 包 |

> Tauri 2 构建不再依赖 PySide6。工作流配置 Intel / Apple Silicon 分别构建后合并，并使用 macOS 系统 WKWebView；Apple 签名与公证仍需单独处理。

## 安装

1. 到 [Releases](https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/releases) 下载 `SJTURunningMan_<版本>_macOS.dmg`；
2. 双击挂载，把窗口里的 **SJTURunningMan.app** 拖到 **Applications** 文件夹；

![拖拽安装](./images/macos-install-dmg.webp)

3. 推出磁盘映像（在访达侧边栏点映像名旁的 ⏏）。

## 首次打开：处理 Gatekeeper 拦截

本工具没有 Apple 开发者签名与公证，macOS 会拦截首次运行。**这是预期行为，不代表文件有问题。**

### 现象

双击应用后弹出：

> **"SJTURunningMan" Not Opened**
> Apple could not verify "SJTURunningMan" is free of malware that may harm your Mac or compromise your privacy.

![Gatekeeper 拦截弹窗](./images/macos-gatekeeper.webp)

弹窗里**只有 "Move to Trash" 和 "Done"** —— 没有直接放行的按钮。这是 macOS 15 起的变化：放行入口被移到了系统设置里，不再直接给"打开"按钮。

### 处理

1. 点 **Done**（**不要**点 Move to Trash，那会把应用删掉）；
2. 打开 **系统设置 → 隐私与安全性**，向下滚动到「安全性」一节；
3. 会看到一条关于 `SJTURunningMan` 的提示，点右侧的 **仍要打开 / Open Anyway**；

![在系统设置中放行](./images/macos-open-anyway.webp)

4. 系统会再确认一次，输入登录密码或使用 Touch ID 即可。

放行一次之后，之后每次打开都不会再拦。

### 如果系统设置里没有这条提示

先**再双击一次应用**，让它触发拦截，这条记录才会出现在隐私与安全性里。

若仍然没有，可以在访达里**按住 Control 点击**（或右键）应用图标，选择「打开」，再在弹窗里点「打开」。这条路径在较老的 macOS 上同样可用。

### 仍打不开：手动去掉隔离属性

从网络下载的文件会带 `com.apple.quarantine` 属性。上面的步骤本质上就是让系统解除它，也可以用命令直接做：

```bash
xattr -d com.apple.quarantine /Applications/SJTURunningMan.app
```

> 这条命令会移除该应用的隔离标记。只对你**自己确认过来源**的应用使用。

## 卸载

1. 把 `/Applications/SJTURunningMan.app` 拖进废纸篓；
2. 参数、路线副本和生成的 HTML 位于 `~/Library/Application Support/cn.sjtu.SJTURunningMan`。如需连同本地数据卸载，再自行移除该目录。

## 从源码运行

安装 stable Rust（1.95+）和 Xcode Command Line Tools 后运行：

```bash
cargo run --locked -p sjturunningman
cargo test --workspace --locked
```

Intel / Apple Silicon 分别编译、lipo 合并、签名和 DMG 打包见 [build.md](build.md#电脑版)。Python 只用于运行打包脚本，不随应用分发。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| **「Apple could not verify…」** | 见上一节，走 系统设置 → 隐私与安全性 → 仍要打开 |
| **提示应用已损坏 / 移到废纸篓** | 文件下载不完整，重新下载；仍不行则用上面的 `xattr -d` 命令 |
| **提示需要 Rosetta** | 不需要。通用包已包含两种架构，若被要求说明拿到的是旧包，重新下载 |
| **打开后闪退** | 核对当前安装包的构建目标和版本；在「访达 → 应用程序 → 实用工具 → 控制台」里搜索 `SJTURunningMan` 查看崩溃日志 |
| **图标显示成默认图标** | 退出应用、重新挂载 DMG 再拖一次；直接运行 `dist/` 里的可执行文件不会带图标 |

其他功能性问题见 [faq.md](./faq.md)。
