# UID获取失败问题修复记录

## 问题描述
APP在连续运行后出现UID获取失败，Logcat显示：
```
E MiuiNotifUtil: Error getPackageUid
android.content.pm.PackageManager$NameNotFoundException
```
```
E DatabaseUtils: java.lang.SecurityException: Package com.tencent.mm is not owned by uid 10262
```

## 根本原因
1. **缺少系统权限**：APP没有 `READ_PHONE_STATE` 权限，导致系统拒绝分配UID
2. **进程残留冲突**：连续运行APP时，旧进程未完全退出，导致新进程UID分配失败
3. **Android系统限制**：系统认为APP身份不合法，拒绝网络请求

## 修复方案

### 1. 权限修复
**文件**: `app/src/main/AndroidManifest.xml`
```xml
<!-- 添加以下权限 -->
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
```

### 2. 安全获取系统UID
**文件**: `app/src/main/java/com/sjtu/runner/MainActivity.kt`
```kotlin
companion object {
    fun getAppUid(context: android.content.Context): Int {
        return try {
            context.packageManager
                .getApplicationInfo(context.packageName, 0)
                .uid
        } catch (e: Exception) {
            -1
        }
    }
}
```

### 3. 添加调试信息
**文件**: `app/src/main/java/com/sjtu/runner/network/ApiService.kt`
```kotlin
// 在getUid()方法中添加
val androidUid = context?.let { 
    try {
        it.packageManager.getApplicationInfo(it.packageName, 0).uid
    } catch (e: Exception) {
        -1
    }
}
println("DEBUG: Android System UID: $androidUid, Package: ${context?.packageName}")
```

### 4. 优化context传递
**文件**: `app/src/main/java/com/sjtu/runner/viewmodel/MainViewModel.kt`
```kotlin
// 从:
private val api = ApiService()
init {
    api.setContext(application)
}

// 改为:
private val api = ApiService(application)
```

## 验证方法

### 1. 查看Logcat输出
运行APP后，在Logcat中搜索：
```
DEBUG: Android System UID:
```
- **正常情况**: `DEBUG: Android System UID: 10262` (正常数字)
- **异常情况**: `DEBUG: Android System UID: -1` (权限或进程问题)

### 2. 运行步骤
1. **停止旧进程**: Android Studio → `Run → Stop 'app'`
2. **重新运行**: Android Studio → `Run → Run 'app'`
3. **查看日志**: 确认系统UID获取成功

## 预防措施

### 1. 开发时注意事项
- **不要连续运行APP**: 每次运行前先停止旧进程
- **检查权限**: 确保所有必要权限都已声明
- **查看系统日志**: 关注UID相关错误信息

### 2. 代码规范
- **使用安全方式获取UID**: 使用 `getApplicationInfo().uid` 而不是直接调用系统API
- **添加错误处理**: 所有UID获取操作都应包含try-catch
- **输出调试信息**: 关键操作添加日志输出

## 技术原理

### 1. Android进程模型
- 第一次运行: 进程干净 → UID正常分配
- 第二次运行: 旧进程残留 → UID冲突 → 系统拒绝分配

### 2. 权限系统
- `INTERNET`: 允许网络访问
- `READ_PHONE_STATE`: 允许读取设备标识（包括UID）
- 缺少任一权限都会导致UID获取失败

### 3. 小米/Android系统特性
- 部分Android系统（特别是MIUI）对UID分配有更严格的限制
- 多进程应用需要特殊处理UID获取

## 故障排除

### 如果问题仍然存在

1. **检查权限是否生效**
   ```bash
   adb shell dumpsys package com.sjtu.runner | grep permission
   ```

2. **彻底清除应用数据**
   ```bash
   adb shell pm clear com.sjtu.runner
   ```

3. **重启设备**
   - 清除系统层的进程UID缓存

4. **检查AndroidManifest合并**
   - 确保没有其他配置文件覆盖权限设置

## 相关文件
- `AndroidManifest.xml` - 权限声明
- `MainActivity.kt` - 系统UID获取方法
- `ApiService.kt` - 网络请求和UID调试
- `MainViewModel.kt` - ViewModel和context传递

## 更新记录
- **2025-05-03**: 初始修复，添加READ_PHONE_STATE权限和安全UID获取方法
- **2025-05-03**: 添加调试信息和优化context传递

## 参考
- [Android官方文档 - 权限](https://developer.android.com/guide/topics/permissions/overview)
- [Android进程和UID管理](https://developer.android.com/guide/components/activities/process-lifecycle)
- [PackageManager API](https://developer.android.com/reference/android/content/pm/PackageManager)