package com.sjtu.runner.network

import android.content.Context
import android.webkit.CookieManager
import com.google.gson.Gson
import com.google.gson.JsonElement
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import java.net.CookieManager as JavaNetCookieManager
import java.net.CookiePolicy

class ApiService(private val context: Context? = null) {

    fun setContext(context: Context) {
        // Keep for backward compatibility
    }

    // 新增：自定义CookieJar，同步WebView的CookieManager
    private class WebViewCookieJar : CookieJar {
        private val webViewCookieManager = CookieManager.getInstance()

        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            // 将OkHttp的Cookie同步到WebView
            cookies.forEach { cookie ->
                webViewCookieManager.setCookie(url.toString(), cookie.toString())
            }
            webViewCookieManager.flush() // 持久化Cookie
        }

        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            // 从WebView读取Cookie给OkHttp
            val cookieStr = webViewCookieManager.getCookie(url.toString()) ?: return emptyList()
            return cookieStr.split("; ")
                .mapNotNull { Cookie.parse(url, it) }
        }
    }

    // 替换原有的client初始化，使用自定义CookieJar
    private val client = OkHttpClient.Builder()
        .cookieJar(WebViewCookieJar())
        .build()

    // 新增：精准判断是否为jAccount登录页（仅登录页才触发重新登录）
    private fun isJAccountLoginPage(content: String): Boolean {
        return content.contains("Login jAccount")
                || content.contains("jaccount.sjtu.edu.cn")
                || content.contains("扫码登录")
                || content.contains("Scan QR code")
                || content.contains("统一身份认证")
    }

    suspend fun getUid(): String? = withContext(Dispatchers.IO) {
        // 先获取 Android 系统 UID 用于调试
        val androidUid = context?.let {
            try {
                it.packageManager.getApplicationInfo(it.packageName, 0).uid
            } catch (e: Exception) {
                -1
            }
        }
        println("DEBUG: Android System UID: $androidUid, Package: ${context?.packageName}")
        // Get cookies from Android CookieManager (set by WebView)
        val androidCookie = CookieManager.getInstance().getCookie("https://pe.sjtu.edu.cn")
        println("DEBUG: Android cookies for pe.sjtu.edu.cn: $androidCookie")
        val requestBuilder = Request.Builder()
            .url("https://pe.sjtu.edu.cn/sports/my/uid")
            .header("User-Agent", "okhttp/4.10.0")
        // Add cookies from Android CookieManager if available
        if (!androidCookie.isNullOrBlank()) {
            requestBuilder.header("Cookie", androidCookie)
        }
        val request = requestBuilder.build()
        val response = client.newCall(request).execute()
        val body = response.body?.string() ?: return@withContext null
        // Log the raw response for debugging
        println("DEBUG: Raw response body: $body")
        println("DEBUG: Response code: ${response.code}")
        println("DEBUG: Response headers: ${response.headers}")
        // 替换原判断逻辑：仅精准匹配jAccount登录页特征
        if (isJAccountLoginPage(body) || response.code == 302 || response.code == 403) {
            println("DEBUG: Response is jAccount login page/redirect - cookie已过期")

            // 尝试重新登录（已移除清空Cookie的危险操作）
            if (context != null) {
                println("DEBUG: 尝试重新登录获取cookie...")
                // 这里无法直接启动Activity，需要在上层处理
                return@withContext null
            }
            return@withContext null
        }

        try {
            // First, try to parse as a JsonElement to check the structure
            val jsonElement = Gson().fromJson(body, com.google.gson.JsonElement::class.java)

            if (jsonElement.isJsonObject) {
                // It's a JSON object
                val map = Gson().fromJson(body, Map::class.java)
                if (map["code"] == 0.0) {
                    (map["data"] as? Map<*, *>)?.get("uid")?.toString()
                } else {
                    println("DEBUG: API returned error code: ${map["code"]}, message: ${map["message"]}")
                    null
                }
            } else if (jsonElement.isJsonPrimitive && jsonElement.asJsonPrimitive.isString) {
                // It's a raw string - might be the UID directly
                val uidString = jsonElement.asString
                println("DEBUG: API returned raw string: $uidString")
                // Check if it looks like a UID (numeric or alphanumeric)
                if (uidString.isNotBlank() && uidString.matches(Regex("[a-zA-Z0-9]+"))) {
                    uidString
                } else {
                    null
                }
            } else {
                println("DEBUG: Unexpected JSON structure: $jsonElement")
                null
            }
        } catch (e: com.google.gson.JsonSyntaxException) {
            // Not valid JSON at all - might be HTML or plain text
            println("DEBUG: Not valid JSON. Response might be HTML/plain text: ${body.take(200)}...")

            // Check if it's a plain string UID (just digits or alphanumeric without quotes)
            val trimmedBody = body.trim()
            if (trimmedBody.matches(Regex("[a-zA-Z0-9]+"))) {
                trimmedBody
            } else {
                null
            }
        }
    }

    suspend fun upload(authToken: String, payload: List<Map<String, Any>>): UploadResult =
        withContext(Dispatchers.IO) {
            val json = Gson().toJson(payload)
            // Get cookies from Android CookieManager (set by WebView)
            val androidCookie = CookieManager.getInstance().getCookie("https://pe.sjtu.edu.cn")
            println("DEBUG: Android cookies for upload: $androidCookie")
            val requestBuilder = Request.Builder()
                .url("https://pe.sjtu.edu.cn/api/running/result/upload")
                .header("Authorization", authToken)
                .header("Content-Type", "application/json; charset=utf-8")
                .post(RequestBody.create("application/json; charset=utf-8".toMediaType(), json))
            // Add cookies from Android CookieManager if available
            if (!androidCookie.isNullOrBlank()) {
                requestBuilder.header("Cookie", androidCookie)
            }
            val request = requestBuilder.build()
            val response = client.newCall(request).execute()
            val respBody = response.body?.string() ?: ""
            println("DEBUG: Upload response code: ${response.code}")
            println("DEBUG: Upload response body: ${respBody.take(200)}")
            // 检测是否因cookie过期导致上传失败（复用jAccount登录页判断）
            if (isJAccountLoginPage(respBody) || response.code == 403 || response.code == 401) {
                println("DEBUG: 上传失败，可能cookie已过期")
                return@withContext UploadResult(false, "cookie已过期，需要重新登录", true)
            }
            try {
                val resMap = Gson().fromJson(respBody, Map::class.java)
                val code = (resMap["code"] as? Double)?.toInt() ?: -1
                UploadResult(code == 0, resMap["message"]?.toString() ?: "未知错误", false)
            } catch (e: Exception) {
                UploadResult(false, respBody, false)
            }
        }

    data class UploadResult(val success: Boolean, val message: String, val needRelogin: Boolean = false)
}
