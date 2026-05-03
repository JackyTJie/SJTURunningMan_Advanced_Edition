package com.sjtu.runner.viewmodel

import android.app.Application
import android.content.Intent
import android.webkit.CookieManager
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.sjtu.runner.data.DataGenerator
import com.sjtu.runner.login.LoginActivity
import com.sjtu.runner.network.ApiService
import com.sjtu.runner.utils.GpsUtil
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import kotlin.random.Random

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val api = ApiService(application)
    
    // 用于重新登录的回调
    var onReloginRequired: (() -> Unit)? = null

    private val _log = MutableStateFlow("")
    val log: StateFlow<String> = _log

    private val _running = MutableStateFlow(false)
    val running: StateFlow<Boolean> = _running

    private var job: Job? = null

    fun startUpload(
        days: Int,
        distanceKm: Int,
        hour: Int,
        minute: Int,
        dateStr: String?
    ) {
        job = viewModelScope.launch(Dispatchers.IO) {
            _running.value = true
            _log.value = ""

            try {
                logMsg("步骤1: 获取 UID...")
                val uid = api.getUid()
                if (uid == null) {
                    logMsg("UID 获取失败，可能cookie已过期，尝试重新登录...")
                    triggerRelogin()
                    return@launch
                }
                logMsg("UID 获取成功: $uid")

                logMsg("步骤2: 准备路线坐标...")
                val coordinates = GpsUtil.readCoordinates(getApplication())
                logMsg("路线点数量: ${coordinates.size}")

                val targetDistanceM = distanceKm * 1000

                val startDate = if (dateStr.isNullOrBlank()) {
                    LocalDate.now().minusDays(1)
                } else {
                    LocalDate.parse(dateStr, DateTimeFormatter.ISO_LOCAL_DATE)
                }

                for (i in 0 until days) {
                    if (!_running.value) break

                    val date = startDate.minusDays(i.toLong())

                    // 随机化起跑时间：在选定时间的基础上 +- 10分钟，且秒数随机
                    // 10分钟 = 600秒，范围为 [-600, 600]
                    val randomOffsetSec = Random.nextLong(-600, 601)

                    val startTimeInstant = date.atTime(hour, minute)
                        .atZone(java.time.ZoneId.systemDefault())
                        .toInstant()
                        .plusSeconds(randomOffsetSec)

                    val startTimeMs = startTimeInstant.toEpochMilli()
                    val displayTime = startTimeInstant.atZone(java.time.ZoneId.systemDefault())
                        .format(DateTimeFormatter.ofPattern("HH:mm:ss"))

                    logMsg("生成第 ${i + 1}/$days 条数据 ($date $displayTime)...")
                    val (payload, actualDist) = DataGenerator.generate(
                        coordinates,
                        uid,
                        targetDistanceM,
                        startTimeMs,
                        intervalSeconds = 3,
                        log = { msg -> logMsg(msg) }
                    )
                    logMsg("实际距离: ${String.format("%.2f", actualDist)} m")

                    logMsg("上传第 ${i + 1}/$days 条...")
                    val result = api.upload(uid, payload)
                    
                    if (result.success) {
                        logMsg("第 ${i + 1} 条上传成功")
                    } else {
                        if (result.needRelogin) {
                            logMsg("上传失败: ${result.message}，尝试重新登录...")
                            triggerRelogin()
                            break
                        } else {
                            logMsg("失败: ${result.message}")
                        }
                    }
                }
                logMsg("全部任务完成")
            } catch (e: CancellationException) {
                logMsg("任务已手动停止")
            } catch (e: Exception) {
                logMsg("错误: ${e.message}")
            } finally {
                _running.value = false
            }
        }
    }

    fun stopUpload() {
        job?.cancel()
        _running.value = false
    }

    private fun logMsg(msg: String) {
        viewModelScope.launch(Dispatchers.Main) {
            _log.value = _log.value + "\n${java.time.LocalTime.now().withNano(0)} $msg"
        }
    }
    
    private fun triggerRelogin() {
        viewModelScope.launch(Dispatchers.Main) {
            // 清除旧cookie
            CookieManager.getInstance().removeAllCookies(null)
            CookieManager.getInstance().flush()
            
            // 通知上层需要重新登录
            onReloginRequired?.invoke()
        }
    }
}