# iOS 版使用指南

版本 **`4.5.0`**（`MARKETING_VERSION`，与 `apps/ios/SJTURunningMan/AppConfig.swift` 的 `versionName` 一致），Bundle ID `SJTU.SJTURunningMan`。工程路径 `apps/ios/`。

iOS 版**没有预编译安装包**，需要用 Xcode 自行编译并签名后安装到 iPhone。

![iOS 主界面](./images/ios-main.webp)

## 目录

- [1. 环境要求](#1-环境要求)
- [2. 克隆并打开工程](#2-克隆并打开工程)
- [3. 配置签名](#3-配置签名)
- [4. 编译并运行](#4-编译并运行)
- [5. 使用](#5-使用)
- [6. 学期数据](#6-学期数据)
- [7. 文件结构](#7-文件结构)

## 1. 环境要求

- **macOS** + **Xcode 16 或更高**
- 一个 **Apple Developer 账号**（免费账号即可）
- 一台 **iPhone**，iOS 版本需满足 `IPHONEOS_DEPLOYMENT_TARGET = 26.5`

## 2. 克隆并打开工程

```bash
git clone https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition.git
cd SJTURunningMan_Advanced_Edition/apps/ios
open SJTURunningMan.xcodeproj
```

## 3. 配置签名

### 设置 Team ID

1. 在 Xcode 左侧导航栏选中顶层的 **SJTURunningMan** 工程；
2. 进入 **Signing & Capabilities** 标签；
3. 在 **Team** 下拉中选择你的开发者团队，Xcode 会自动填入 Team ID。

或者直接编辑 `SJTURunningMan.xcodeproj/project.pbxproj`，把 `YOUR_TEAM_ID` 换成你 10 位的 Apple Developer Team ID。

> **去哪找 Team ID**：[developer.apple.com/account](https://developer.apple.com/account) → **Membership** → 页面顶部的 **Team ID**。

### 设置 Bundle Identifier（可选）

默认是 `SJTU.SJTURunningMan`。若用免费开发者账号，通常需要改成唯一的，比如 `com.你的名字.SJTURunningMan`：

1. 选中工程 → **Signing & Capabilities**；
2. 修改 **Bundle Identifier** 为唯一值；
3. Xcode 会自动生成描述文件。

## 4. 编译并运行

### 方式 A：直接用 Xcode（最简单）

1. 用数据线把 iPhone 连到 Mac；
2. 在 Xcode 顶栏把构建目标选成你的 iPhone；
3. 点 **Play ▶**（或 `Cmd+R`）。

首次运行可能遇到：

- **「Enable Developer Mode on this iPhone?」** —— 手机上点 OK，然后去 **设置 → 隐私与安全性 → 开发者模式** 打开，重启手机；
- 免费账号报 **「Failed to register bundle identifier」** —— 按上一节把 Bundle ID 改成唯一的；
- 需要**信任开发者证书** —— iPhone 上 **设置 → 通用 → VPN 与设备管理 → 开发者 App → 信任**。

### 方式 B：打包 ipa 后侧载（不需要数据线）

1. Xcode 菜单 **Product → Archive**（如有需要先 `Cmd+Shift+K` 清理）；
2. 在 Archives 窗口选中归档，点 **Distribute App**；
3. 选择 **Custom → Export as .ipa**；
4. 保存 `.ipa`，用 AltStore / SideStore 等侧载工具安装。

## 5. 使用

界面与安卓版、电脑版的功能一致；底部是悬浮的 Liquid Glass Dock，四项为 **工作台 / 路线 / 任务日志 / 关于软件**，选中胶囊可左右拖动，也可点按或左右滑动页面切换。任务运行时，非工作台页签底部会保留一条紧凑状态条与「停止任务」。

1. **登录** —— 应用打开 JAccount OAuth2 登录页，用学号密码登录；
2. **设置参数** —— 在「工作台」配置跑步次数、时间、结束日期、距离（1–5 km，默认 4 km）；
3. **开始** —— 点「开始任务」，应用会：
   - 从体育平台获取你的 UID；
   - 依据路线坐标生成 GPS 轨迹数据；
   - 配速在 4–6 min/km 之间随机；
   - 逐天上传轨迹数据。
4. **观察** —— 「任务日志」页的实时日志显示进度，逐条显示上传结果；
5. **重新登录** —— 会话过期时应用会提示重新登录。

## 6. 学期数据

登录成功后应用会在后台只读同步本学期数据，无需手动刷新；与安卓版、电脑版同一套口径。

- **「本学期进度」卡片**（工作台）：显示当前学期的**达标公里**与**完成率**。未登录或同步失败时显示 `--`，日历保持占位。
- **「学期日历」**（任务日志）：周一起始、逐月展开本学期每一天。实心绿 = 计入成绩，描边 = 无效记录，灰 = 未跑，空白格 = 不在学期内。服务器未给出学期起止时提示「服务器未返回本学期起止日期。」
- **跳过已有记录的日期**（工作台开关，默认开启）：学期日历里已有记录的那几天会自动挪到更早的日期，上传条数仍等于设定次数；向前最多翻 120 天且不越过学期起点，凑不够时如实提示不足。关闭后按结束日期连续向前生成。
- **登录后自动设定跑步计划**：登录成功后的第一次学期数据同步按本学期未完成公里数反推「跑步次数 × 单次距离」（单次 1–5 km、次数不超过 30 次，向上取整保证补上缺口）并填入界面；这两个值被你手动改过就保持不变，只在日志说明原因。自动填入的值跨启动保留。
- 任务有成功上传后，「本学期进度」与学期日历会自动刷新一次，当天记录随即出现在日历上。
- 学期数据只在本次会话内展示，**不落盘**；同步失败只记一行日志，不改变登录状态、不会自动登出。

## 7. 文件结构

```
apps/ios/
├── SJTURunningMan/
│   ├── SJTURunningManApp.swift      应用入口
│   ├── LoginView.swift              JAccount OAuth2 WebView
│   ├── MainView.swift               四个页签与界面组装
│   ├── MainViewModel.swift          上传逻辑、学期统计与状态
│   ├── ApiService.swift             HTTP 客户端（取 UID、上传结果、学期统计）
│   ├── SemesterStats.swift          学期统计纯逻辑与日历展开
│   ├── RunSchedule.swift            上传日期排布与跳过已有记录
│   ├── Components.swift             卡片、学期日历、开关等共享组件
│   ├── Dialogs.swift                承诺书、路线冲突等弹窗
│   ├── DataGenerator.swift          GPS 轨迹生成
│   ├── GpsUtil.swift                坐标工具
│   ├── RouteManager.swift           路线管理
│   ├── RouteDesignView.swift        路线设计页
│   └── route_coordinates            SJTU 校园预录路线坐标点
├── SJTURunningMan.xcodeproj/        Xcode 工程
└── README.md                        目录内简短指引
```

故障排查见 [faq.md](./faq.md)；自行编译与其他平台见 [build.md](./build.md)。
