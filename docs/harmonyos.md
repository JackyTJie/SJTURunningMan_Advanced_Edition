# HarmonyOS NEXT 端使用指南

版本 **`4.5.0`**，Bundle Name `com.sjtu.runner`（`apps/harmonyos/AppScope/app.json5`）。工程路径 `apps/harmonyos/`。

> **未特别说明的内容与安卓端一致** —— 参数范围、上传流程、日志行为都对齐安卓版；差异仅在安装方式与登录入口。

鸿蒙版由 [@AetherWish](https://github.com/AetherWish) 贡献，工程由 Android 原生工程迁移而来（见 `apps/harmonyos/oh-package.json5`）。

![鸿蒙主界面](./images/harmonyos-main.webp)

## 目录

- [1. 安装 HAP 包](#1-安装-hap-包)
- [2. 登录](#2-登录)
- [3. 参数配置](#3-参数配置)
- [4. 开始上传](#4-开始上传)
- [5. 自定义路线](#5-自定义路线)
- [6. 权限说明](#6-权限说明)
- [7. 与其他端的差异](#7-与其他端的差异)
- [8. 已知的 ArkTS 工具链陷阱](#8-已知的-arkts-工具链陷阱)
- [9. 路线长度与预览限制](#9-路线长度与预览限制)
- [10. 学期进度、日历与自动排计划](#10-学期进度日历与自动排计划)

## 1. 安装 HAP 包

> ⚠️ **强烈建议提前完成华为账号的开发者认证**，以延长调试证书有效期。未认证时调试证书有效期很短，装完没多久就会失效需要重装。

1. **先自行编译出 HAP** —— 本项目**不在 Releases 提供鸿蒙预编译包**，需要用 DevEco Studio 构建并签名，见 [build.md](./build.md#鸿蒙)；
2. 手机上：**设置 → 关于本机 → 连点「软件版本」7 次**，重启后启用开发者选项；
3. 进入 **设置 → 系统 → 开发者选项 → 无线调试**，打开并记录显示的 IP 与端口；
4. PC 与手机连同一网络，下载 [小白调试助手](https://github.com/likuai2010/auto-installer) 并运行，按软件内指引配置安装。

## 2. 登录

1. 首次进入会先显示**使用承诺书**，勾选后点「我承诺，进入软件」；点「退出」会直接结束应用。同意状态保存在 `app_prefs/commitment_accepted`，之后不再弹出；
2. 点击首页标题栏**右上角的账号图标**即可跳转到登录页（未登录时图标下方显示「登录」，已登录显示「账号」；已登录时点击会弹出「退出账号」确认）；
3. 页面加载与登录完成后自动返回，状态卡片显示「已登录」。失效时会自动重新登录。

> ⚠️ 鸿蒙端**无法拉起「交我办」快捷登录**，只能走 JAccount 网页登录。若系统已安装卓易通版「交我办」，登录页会尝试唤起它；未安装时提示后留在网页登录。

## 3. 参数配置

首页**没有底部页签**：标题（「开润」）与右上角的**学期日历**、**账号**、**关于**三个图标按钮在同一行（自绘标题栏，见第 8 节）。「开润」页面从上到下依次为状态卡片、本学期进度卡、路线卡片、任务设置卡片与运行日志区。

| 参数 | 范围 | 默认 | 说明 |
| --- | --- | --- | --- |
| 跑步次数 | 1–30 次 | 1 | 下拉框可选 1/3/5/7/10/15/30，或选「自定义…」手动输入（此时下拉框内显示「自定义」） |
| 开始时间 | 时 0–23 / 分 0–59 / 秒 0–59（即 00:00:00–23:59:59） | 08:00:00 | 点按弹出系统时间选择器（24 小时制、时分秒三列）；每条会加 **±10 分钟 / ±30 秒** 随机波动（说明折叠在标签旁的「圈 i」图标里，点按查看） |
| 结束日期 | 日期选择器 | 昨天 | 以此为最新一条向前生成；点按整行弹出 |
| 跳过已有记录的日期 | 开 / 关 | 开 | 开启时仍上传设定的次数，只把已有记录的那几天挪到**更早**的日期；被跳过的日期会写进运行日志，向前翻到学期起点或 120 天上限仍不够时日志会说明「只找到 N 个可上传的日期」 |
| 跑步距离 | 1–5 km | 4 km | 单条目标距离，滑杆步长 0.1 km；数值紧贴「目标距离」标签右侧显示在同一行（形如 `目标距离 4.0 km`） |
| 跑步路线 | 见下 | 思源湖路线 | 下拉选择，可在新页面连点设置 |

参数范围来自 `apps/harmonyos/entry/src/main/ets/config/AppConfig.ets`。首页与「关于」页的滚动条均为 `BarState.Auto`（滚动时显示，静止后淡出）。

任务设置的每一行都是自绘的 `SettingCard`（`apps/harmonyos/entry/src/main/ets/view/CommonComponents.ets`）：左侧系统符号图标列 + 标签列宽度固定，因此各行的图标左边缘与标签左边缘严格对齐；控件列宽度由 ArkUI 正常测量。为什么不用 `HdsListItemCard` 承载这些交互控件，见第 8 节。

## 4. 开始上传

1. 点底部「开始任务」按钮；
2. 状态卡片显示当前阶段（准备中 / 获取认证 / 生成数据 / 上传中 / 正在停止 / 已完成 / 失败）与进度条；
3. 路线卡片可点「预览路线」按当前设置**离线生成**一条轨迹，显示距离 / 点数 / 跳段数与轨迹散点画布；
4. 完成后日志区给出「任务完成: 成功 N 条，失败 M 条」，可点「清空」清除日志（最多保留 400 条）。

若所选路线长度超过目标距离，会弹出「路线距离提醒」，可选择**削减路线**（自动截断至目标距离）或**取消任务**；点「完整路线」则按整条路线跑步并同步目标距离。

任务进行中可点「停止任务」中断。停止在下一轮循环边界生效；若此时正有一次上传在途，会等该请求返回（最长 20 秒读超时）后再结束，界面不会卡死。

## 5. 自定义路线

1. 进入路线设计页，在地图上**依次连点**选择坐标点；
2. 点越多越贴合，**注意点是有顺序的，且起始点与终止点越接近越好**；
3. 保存后回到主界面，在下拉列表中选中新路线即可开跑；非内置路线可点「删除路线」删除。

具体的坐标格式、坐标系差异，见 [routes.md](./routes.md)。

## 6. 权限说明

`apps/harmonyos/entry/src/main/module.json5` 申请：

| 权限 | 用途 |
| --- | --- |
| `ohos.permission.INTERNET` | 访问 pe.sjtu.edu.cn 上传数据、检查更新 |
| `ohos.permission.GET_NETWORK_INFO` | 判断网络可用性 |

鸿蒙端**不读取定位、不读取电话状态**：轨迹由所选路线离线插值生成，上传坐标由路线坐标加固定偏移得到，与安卓一致。

## 7. 与其他端的差异

| 项 | 安卓 | 鸿蒙 |
| --- | --- | --- |
| 获取方式 | Releases 直接下载 APK | **不提供预编译包**，需自行用 DevEco Studio 编译并签名 |
| 安装方式 | 直接装 APK | 需 HAP + 调试证书（有效期有限） |
| 快捷登录 | 支持交我办 | 不支持，仅 JAccount 网页登录 |
| 权限 | INTERNET / ACCESS_NETWORK_STATE / READ_PHONE_STATE | INTERNET / GET_NETWORK_INFO |
| 参数范围 | 1–30 次 / 1–5 km | 同安卓 |
| 界面组件 | Material 3 (Compose) | 原生 ArkUI（`Navigation` / `NavDestination` + 自绘卡片，见第 8 节） |
| 路线资源 | `route_design.html`（百度地图） | 同一份资源，另存一份（桥接对象仍名为 `AndroidInterface`） |
| 关于 / 更新 | 对话框 | 独立「关于」页 |
| 路线预览配色 | Material 主题色 | 与地图同源的固定蓝橙配色（`RoutePreviewCanvas.ets`） |
| 自动化测试 | JVM 单元测试 | 暂无 |

自行编译与打包见 [build.md](./build.md)；路线坐标系说明见 [routes.md](./routes.md)。

## 8. 开发说明：已知的 ArkTS 工具链陷阱

以下问题能通过编译，只在真机运行时才暴露，改动界面时需要留意。

**界面只用原生 ArkUI，不依赖 UI Design Kit（HDS）。** 早期实现用 `@kit.UIDesignKit` 的
`HdsNavigation` / `HdsNavDestination` / `hdsMaterial` 和 `@kit.ArkUI` 的 `uiMaterial.ImmersiveMaterial`
渲染「沉浸光感」标题栏与磨砂材质，但这些 API **只在比 HarmonyOS 6.0.1（API 21）更新的 SDK 里才有**：
在 API 21 SDK 上构建会直接报 `'uiMaterial' is not exported from Kit '@kit.ArkUI'`、
`'hdsMaterial' is not exported from Kit '@kit.UIDesignKit'`、`Cannot find name 'HdsNavigationAttribute'`。
现改为原生 `Navigation` + `NavDestination`（`pages/Index.ets` 自绘标题栏，`APP_HEADER_HEIGHT` 定义在
`view/CommonComponents.ets`），日志面板用 `backgroundBlurStyle(BlurStyle.Thin)` 叠加半透明底色得到相近的磨砂观感。

要恢复沉浸光感，需要升级 DevEco Studio / SDK 到含 UIDesignKit 的版本，并把 `build-profile.json5` 的
`compileSdkVersion` / `targetSdkVersion` 写成 `'x.y.z(API级别)'`（例如 `'6.0.1(21)'`）后改到新版本号；
`module.json5` 里的 `ohos.arkui.UIMaterial.state` 元数据也要一并加回。

**自定义组件不能直接写在传给外部组件的箭头函数里。** ArkTS 编译器只会把处于声明式 UI 上下文中的
`Foo({...})` 重写成 `new Foo(this, {...})`。把自定义组件写在对象的箭头函数属性里（例如
`new SuffixCustomBuilder((): void => { DistanceSlider({...}) })`）时不会重写，运行到该闭包即抛
`TypeError: class constructor cannot called without 'new'`，应用直接闪退。正确写法是把组件放进 `@Builder`
方法，再由闭包调用该方法：

```typescript
@Builder
DistanceSliderBuilder() {
  DistanceSlider({ /* ... */ })
}

// suffixItem: new SuffixCustomBuilder((): void => { this.DistanceSliderBuilder() })
```

> 验证方法：构建后查看 `entry/build/default/cache/default/default@CompileArkTS/esmodule/debug/` 下的
> 中间产物 `.ts` 文件，确认组件被重写成 `new Foo(this, {...})`；仍是裸调用 `Foo({...})` 就一定会崩。

**（历史教训）HDS 卡片的自定义后缀不参与尺寸测量。** 现已不再依赖 HDS，但这些实测结论解释了 `SettingCard` 的尺寸来源，改造卡片前值得一读。 `HdsListItemCard` 的 `suffixItem` 只接受
`SuffixCustomBuilder`，其后缀内容既不参与卡片的宽度分配、也不参与高度测量：实测把 8 个
选项胶囊放进后缀区时，卡片高度仍是按 `SuffixText` 固定行高算出的 64vp，后缀里的
`Flex` 却按“屏幕宽度”换行并向上溢出，胶囊被画到卡片外、与上一张卡片的按钮重叠。

因此**带交互控件的参数行不要放进 `HdsListItemCard` 的后缀**，改用原生 ArkUI 自绘卡片
（`apps/harmonyos/entry/src/main/ets/view/CommonComponents.ets` 的 `SettingCard`）：卡片外观
（`card_surface` 底色、16vp 圆角、16vp 内边距、系统符号 + 固定宽度的图标列与标签列）与
`HdsListItemCard` 对齐，控件列用 `layoutWeight(1)` / 100% 宽度交给 ArkUI 正常测量，尺寸自适应。
**任务设置的四行全部用 `SettingCard`**（含结束日期这类静态行，用 `valueText` 参数把值右对齐）：
一旦混用 `HdsListItemCard` 与 `SettingCard`，两者的图标列宽度不同（84px vs 78px），
行与行的标签左边缘就会差 21px 左右。

> 需要宽控件的行（目标距离滑杆）用 `SettingCard` 的 `fullWidth` 模式，把标签移到控件上方：
> ArkUI 的 `Text` 有 64vp 的最小宽度且不随内容收缩，并排布局下标签列会吃掉一截宽度。
> `SettingCard` 的标签列宽度也**不能小于 64vp**，否则「跑步次数」这类 4 字标签会折成两行
> （实测 43vp 时四行有三行折行）。

**标签行上的实时读数不要走父组件的 @State。** 目标距离的数值（「目标距离 4.0 km」里的 `4.0 km`）
由 `SettingCard` 用 `@StorageProp('distanceKmText')` 从 AppStorage 读取后渲染在标签行；
写入方是滑杆的 `onDistanceChange`（`AppStorage.setOrCreate('distanceKmText', …)`），初值在
`RunScreen.aboutToAppear()` 里写。原因：ArkUI 会把传给 `@BuilderParam` 的箭头函数编译成
`builder.bind(this)`，闭包里的 `this` 是**子组件**，所以父组件无论用参数还是自己的 @State 拼字符串，
读到的都是陈旧值——实测滑杆已经变成 `1.6`，父组件渲染的读数仍停在 `4.0`（`@Link` 双向绑定同样无效）。
`@StorageProp` 不依赖 `this`，是目前唯一稳定的实时刷新通道。

另外两条硬约束：
- ArkTS 的「尾随闭包写法」要求组件**恰好只有一个** `@BuilderParam`，所以读数插槽不能做成第二个 builder
  （原文报错：`In the trailing lambda case, 'SettingCard' must have one and only one property decorated with '@BuilderParam'.`）。
- 回调用「组件方法引用」（`onDistanceChange: this.onDistanceChange`）传给子组件会让点按滑杆时应用直接退出，
  务必用调用处的箭头函数。

**相邻同类型参数的实参顺序写反，静态检查不会报错。** `generate()` 的前两个数字参数是
`targetDistanceM`（米）与 `startTimeMs`（毫秒时间戳），两者都是 `number`，把实参写反照样编译通过。
曾因此把 `Date.now()` 当成目标距离传给算法（约 `1.79e12` 米），凑距离的圈数涨到十亿级，
预览时直接把堆撑爆导致闪退。调用处请按形参顺序传参并加注释；算法内部对目标距离量纲有兜底自检
（见第 9 节），但根因应在调用处修正。

## 9. 路线长度与预览限制

轨迹是按所选路线离线插值生成的：先把相邻坐标点按目标步长加密，再整段复制若干圈凑到目标距离（`completeLoops = 目标距离 / 单圈长度`）。

因此**路线不能过短**：若在地图上几乎在同一点连点，或在两个挨得极近的点上结束，单圈长度可能只有几厘米，凑到 1–5 km 就需要几十万圈，轨迹点数会瞬间涨到百万级并撑爆内存。鸿蒙端在加密与扩增两个环节都设了上限（`apps/harmonyos/entry/src/main/ets/service/DataGenerator.ets` 的 `MAX_EXPANSION_POINTS`，10 万点），超过时不会闪退，而是在日志区提示：

- 日志区显示「预览失败: 路线过短（单圈仅 x.xx m）…请重新设计路线或选择其他路线」；
- 重新设计一条单圈长度接近目标距离的路线，或直接使用内置「思源湖路线」（单圈约 871 m）即可。

> 该缺陷在安卓端同样存在（同样的算法、同样的复制路径），鸿蒙端为保护运行时内存刻意提前拦截。

此外，进入轨迹生成前还会对**目标距离的量纲**做一次自检：`previewRoute()` 与 `DataGenerator.generate()` 都会拒绝小于 100 m 或大于 50 km（以及非有限数）的目标距离，并在日志区给出原因，例如：

```text
内部错误: 目标距离参数异常（原始值 1791910592.872），应为 1-5km；请重新设置目标距离后重试
```

> 预览曾一度稳定失败并报出「目标距离约为 1791910592.87km」这样的值：真因是
> `apps/harmonyos/entry/src/main/ets/viewmodel/MainViewModel.ets` 的预览调用把 `Date.now()` 与
> 目标距离两个实参写反（毫秒时间戳被当成米数），已按安卓端 `MainViewModel.kt:362-366` 的顺序修正为
> `(targetDistanceM, startTimeMs)`。
>
> 上面这道自检与第 9 节的 `MAX_EXPANSION_POINTS` 上限都是**兜底**：正常配置下永远不会触发，
> 只在未来又出现量纲或顺序错误时把「闪退」降级为「日志报错」。

## 10. 学期进度、日历与自动排计划

这三块数据都来自体育学院网站的只读接口（`service/ApiService.ets` 的 `semesterStats()`），只要求 `pe.sjtu.edu.cn` 的会话 Cookie，不需要上传用的 token。

**本学期进度卡**（首页状态卡下方）显示两项：达标公里（`resultKm`，两位小数）与完成率（服务器给的 `percent` 已是百分数，缺失时用 达标 / 总公里 兜底）。未登录或接口失败时两项都显示 `--`。

**学期日历**（标题栏右上角的日历图标进入）按周一起始逐月展开本学期每一天：

| 样式 | 含义 |
| --- | --- |
| 实心绿 | 计入成绩（服务器 `state == "0"`） |
| 描边 | 有记录但未计入成绩（`state` 为 12/13 等） |
| 灰底 | 区间内没有记录 |
| 空白格 | 月首月尾补齐，或落在学期起止区间之外 |

未登录时显示按月份推断的**占位日历**（1–2 月按上一学年秋季学期、3–7 月按春季、其余按秋季），全部为「未跑」。服务器没给起止日期时（`semesterDateList` 缺失）日历保持占位，日志里会写「服务器未返回本学期起止日期，日历保持占位」。

**自动排计划**只在你**登录成功后**触发一次：按「本学期目标 − 已达标公里」的缺口反推「次数 × 单次距离」——先用单次 5 km 上限摊出次数（上限 30 次），再把缺口平摊到每次并向上取整到 0.01 km，保证这批记录足以补上缺口。例如缺口 21 km 会得到 5 次 × 4.2 km。

生效时：

1. 首页「跑步次数」与「目标距离」被改写成计划的数值（自定义次数的输入框会收起），并弹出提示「已按本学期未完成 X km 自动设为 N 次 × D km」；
2. 结果持久化在 `app_prefs/plan_auto_days` / `plan_auto_distance` / `plan_auto_active`，下次启动仍按计划回填；
3. **手动改过次数或距离后不再自动覆盖**（判断依据是「设为默认值 1 次 / 4 km」或「等于上次自动排的结果」），日志会写「跑步次数 / 单次距离已被手动修改，保持你的设置」。

上传成功后会自动刷新一次学期数据（日历跟着变），但**不会**再次触发自动排计划；换账号或 cookie 失效（重新登录）后日历先打回占位，迟到的响应会被会话序号丢弃。

> 「跳过已有记录的日期」用的就是这里拉到的打卡日期：任何有记录的日期（无论是否计入成绩）都会被跳过。学期起止日期同时充当前向搜索的边界。
