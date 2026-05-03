package com.sjtu.runner.login

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast

class LoginActivity : Activity() {

    companion object {
        private const val TAG = "LoginActivity"
        private const val JACCOUNT_SCHEME = "jaccount"
        private const val LOGIN_URL = "https://jaccount.sjtu.edu.cn/oauth2/authorize" +
                "?response_type=code" +
                "&scope=profile" +
                "&client_id=9mqzULSXYgUYj5fPOpyL" +
                "&state=8" +
                "&redirect_uri=https://pe.sjtu.edu.cn/oauth2Login"
        private const val MOBILE_USER_AGENT =
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) " +
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 " +
                    "Mobile/15E148 Safari/604.1 Edg/89.0.4389.72"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.userAgentString = MOBILE_USER_AGENT
            CookieManager.getInstance().setAcceptCookie(true)
            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)

            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView?,
                    request: WebResourceRequest?
                ): Boolean {
                    val uri = request?.url ?: return false
                    return handleExternalLoginScheme(uri)
                }

                @Deprecated("Deprecated in Java")
                override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                    val uri = url?.let { Uri.parse(it) } ?: return false
                    return handleExternalLoginScheme(uri)
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    Log.d(TAG, "onPageFinished: $url")
                    
                    // Check if we have cookies for pe.sjtu.edu.cn
                    val cookies = CookieManager.getInstance().getCookie("https://pe.sjtu.edu.cn")
                    Log.d(TAG, "Cookies for pe.sjtu.edu.cn: $cookies")
                    
                    // Check if we have cookies for jaccount.sjtu.edu.cn
                    val jaccountCookies = CookieManager.getInstance().getCookie("https://jaccount.sjtu.edu.cn")
                    Log.d(TAG, "Cookies for jaccount.sjtu.edu.cn: $jaccountCookies")
                    
                    // Check if login is complete by looking for specific cookies or URL patterns
                    val isLoginComplete = when {
                        // Case 1: 跳转到OAuth授权回调页（最核心、最可靠的判断）
                        url?.startsWith("https://pe.sjtu.edu.cn/oauth2Login") == true -> {
                            Log.d(TAG, "Detected oauth2Login page")
                            true
                        }
                        // Case 2: 拿到体育学院的会话Cookie JSESSIONID（API请求必需）
                        !cookies.isNullOrBlank() && cookies.contains("JSESSIONID") -> {
                            Log.d(TAG, "Detected pe.sjtu.edu.cn session cookie")
                            true
                        }
                        // Case 3: 成功跳转到体育学院主站页面（非登录、非授权页）
                        url?.startsWith("https://pe.sjtu.edu.cn") == true &&
                                !url.contains("oauth2/authorize") &&
                                !url.contains("jaccount") -> {
                            Log.d(TAG, "Detected pe.sjtu.edu.cn page after login")
                            true
                        }
                        // ❌ 已删除：仅JAAuthCookie就判定登录完成（导致二次验证提前跳转）
                        else -> false
                    }

                    
                    if (isLoginComplete) {
                        Log.d(TAG, "Login complete, finishing activity")
                        setResult(RESULT_OK)
                        finish()
                    }
                }
                
            }
        }
        setContentView(webView)

        // Clear any existing cookies to start fresh
        CookieManager.getInstance().removeAllCookies(null)
        CookieManager.getInstance().flush()
        
        webView.loadUrl(LOGIN_URL)
    }

    private fun handleExternalLoginScheme(uri: Uri): Boolean {
        val scheme = uri.scheme ?: return false
        if (scheme.equals(JACCOUNT_SCHEME, ignoreCase = true)) {
            return openJwbLogin(uri)
        }

        // Avoid WebView error pages for app-only schemes while keeping normal web navigation intact.
        return scheme != "http" && scheme != "https"
    }

    private fun openJwbLogin(uri: Uri): Boolean {
        return try {
            Log.d(TAG, "Opening jAccount URI with external app: $uri")
            val intent = Intent(Intent.ACTION_VIEW, uri)
            startActivity(intent)
            Toast.makeText(this, "已跳转交我办，请完成登录后返回", Toast.LENGTH_SHORT).show()
            true
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "No app can handle jAccount URI: $uri", e)
            Toast.makeText(this, "未找到交我办，留在网页登录", Toast.LENGTH_LONG).show()
            true
        } catch (e: Exception) {
            Log.w(TAG, "Failed to open jAccount URI: $uri", e)
            Toast.makeText(this, "无法跳转交我办，留在网页登录", Toast.LENGTH_LONG).show()
            true
        }
    }
}
