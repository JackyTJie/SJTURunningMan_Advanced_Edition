# 常见问题与故障排除

## 通用

### 上传失败怎么办

此版本已兼容异地登录。若仍失败，按顺序排查：

1. **清除应用数据** —— 手机：**设置 → 应用管理 → 找到本应用 → 存储 → 清除数据 + 清除缓存**，然后重开应用重新登录；
2. **检查 Cookie 有效性** —— Cookie 通常只有几小时到几天的有效期，过期后需重新登录获取；手动粘贴时确认没有遗漏字符；
3. **检查网络** —— 换 WiFi / 移动数据试，确认没被校园网限制；
4. **等一会儿** —— 可能是交我办服务器维护或故障，稍后重试。

### 第一次跑该选多少

**选 1 次**，距离 2 km 以上，先验证账号与流程都通，再上量。

### 为什么不要选 1 km

路线补点算法在极短距离下容易凑不满，最终可能不足 1 km。推荐 **2 km 及以上**。

### 多设备登录

同一账号在多台设备同时登录可能导致 Cookie 失效。别在多个设备上同时挂着。

### Cookie 安全

Cookie 等同于登录凭证，**不要分享给任何人**，也不要贴进 issue、日志或截图里。详见 [SECURITY.md](../SECURITY.md)。

---

## 电脑版

### 启动被 SmartScreen / Gatekeeper 拦

Windows 核对文件来源后可从「更多信息」进入相应启动选项；macOS 安装见 [macos.md](macos.md)。

### 预览路线打不开

界面内预览无需网络。地图按钮在预览卡片内嵌显示由仅限本机访问的 HTTP 页面提供的 OpenStreetMap 地图，正常发送 OSM 要求的 Referer，不再打开系统浏览器，也不再显示引擎切换或状态条。若底图加载失败，请检查 Leaflet / OSM 的网络访问；卡片内会提示加载失败并保留轨迹，重启客户端后重新打开地图即可。仍看到旧版「403 / Access blocked」时，确认没有从旧的 `file://` 页面打开，见 [desktop.md](desktop.md)。

### 打包出来的 exe 没有图标

使用 `build_windows.ps1` 构建原生 exe（会先构建 React 前端）；图标与版本信息由 `desktop/src-tauri/build.rs` / Tauri 打包配置内嵌。仓库已不再提供 PyInstaller 配置，旧的打包命令也无法构建 Tauri 客户端。

### 导入的路线重启后不见了

路线副本位于系统用户数据目录的 `routes/`，不受安装目录是否可写影响。核对当前系统用户和程序提示的数据目录错误。旧 `Routes/`、`user.txt` 需通过导入 TXT 迁移。

### 导入没反应或提示格式错误

在「路线管理」页点击「导入 TXT」，选择 UTF-8 文本，每行是 BD09 `经度,纬度`。上限 2 MB、30,000 个相邻去重后的点。取消文件选择不会产生修改，详见 [routes.md](routes.md)。

### 图形验证码如何处理

桌面客户端会将图形验证码自动识别后填入验证码输入框，可直接修改。识别异常时可刷新重试，或在同一输入框手动填写。登录修复保留了旧版识别后的提交间隔，并处理学校返回的登录跳转。已实测账号登录与交我办二次验证；学校要求的 6 位二次验证码仍需本人接收并填写。

---

## 安卓 / 鸿蒙

### 装不上 APK / HAP

- **安卓**：在安装提示里允许「未知来源应用」；
- **鸿蒙**：调试证书有效期很短，先完成**华为开发者认证**再装，否则装完很快失效。

### 鸿蒙拉不起「交我办」

鸿蒙端**不支持**快捷登录，只能走 JAccount 网页登录。这是平台限制，非缺陷。

### 应用一直停在登录页

1. 确认手机能正常访问 `pe.sjtu.edu.cn`；
2. 清除应用数据后重试；
3. 若 SJTU SSO 正在维护，等一段时间再试。

---

## iOS

| 现象 | 处理 |
| --- | --- |
| **「Failed to register bundle identifier」** | 把 Bundle ID 改成唯一的（见 [ios.md](./ios.md#设置-bundle-identifier可选)） |
| **装不上 / 「不受信任的开发者」** | iPhone：**设置 → 通用 → VPN 与设备管理** → 点你的开发者描述文件 → 信任 |
| **登录页打不开** | 确认 iPhone 有网。应用走 JAccount OAuth2，SJTU SSO 挂了就只能等 |
| **Cookie 过期** | 应用会检测并显示「重新登录」按钮，点它重新登录 |
| **签名报错** | 确认 Team ID 正确，且 Xcode → Settings → Accounts 里有有效的开发者证书 |
| **「No devices registered」（免费账号）** | 免费账号只能在 1–2 台设备上跑。连上 iPhone 构建运行一次，Xcode 会自动注册；但免费账号无法把应用分享给他人 |

---

## 验证下载的安装包

从 Releases 下载之后，可以核对两件事。

### 1. 完整性 —— 文件在传输中没被改动

Release 正文里有每个产物的 SHA256，也可以把 `SHA256SUMS.txt` 一起下下来核对：

```bash
# macOS / Linux：与 SHA256SUMS.txt 放在同一目录
sha256sum -c SHA256SUMS.txt
```

```powershell
# Windows PowerShell
Get-FileHash .\SJTURunningMan_<版本>_windows.exe -Algorithm SHA256
```

两边的值一致即为完整。

### 2. 构建来源 —— 是 CI 构建的，不是从某台本机传的

每个产物都带一份**来源证明**，由 GitHub OIDC 签发，绑定具体的提交与工作流运行：

```bash
# 需要 gh CLI 2.49 及以上：https://cli.github.com/
gh attestation verify SJTURunningMan_<版本>_windows.exe \
  --repo JackyTJie/SJTURunningMan_Advanced_Edition
```

通过时会打印签名证书与工作流信息。**这份证明在本机无法伪造** —— 它能证明这个文件是 GitHub Actions 按 `release.yml` 在对应提交上构建出来的。

> 说明：来源证明只能证明「怎么构建的」，不能证明「软件可信」—— 能触发该工作流的人同样能签出有效证明。安卓 APK 除来源证明外还有一层**自签名**，用于保证同一作者的版本可以覆盖升级，两者是不同层面的保证。

### 提示文件损坏 / 打不开

先按上面第 1 步核对 SHA256：

- **对得上** —— 文件是完整的，问题多半是系统拦截（Windows SmartScreen、macOS Gatekeeper，见下方对应条目）；
- **对不上** —— 下载过程中损坏了，重新下载即可。

## 还没解决？

- 先搜 [Issues](https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/issues) 有没有同样的问题；
- 没有的话按 [bug 模板](https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/issues/new/choose) 提一个，**记得脱敏**：不要贴 Cookie、密码、验证码、真实姓名学号；
- 安全问题走 [SECURITY.md](../SECURITY.md) 的私有通道，不要开公开 issue。
