package com.sjtu.runner.login

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient

class LoginActivity : Activity() {

    companion object {
        private const val TAG = "LoginActivity"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
            CookieManager.getInstance().acceptCookie()

            webViewClient = object : WebViewClient() {
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
                
                override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                    Log.d(TAG, "shouldOverrideUrlLoading: $url")
                    return super.shouldOverrideUrlLoading(view, url)
                }
            }
        }
        setContentView(webView)

        // Clear any existing cookies to start fresh
        CookieManager.getInstance().removeAllCookies(null)
        CookieManager.getInstance().flush()
        
        webView.loadUrl(
            "https://jaccount.sjtu.edu.cn/oauth2/authorize" +
                    "?response_type=code" +
                    "&scope=profile" +
                    "&client_id=9mqzULSXYgUYj5fPOpyL" +
                    "&state=8" +
                    "&redirect_uri=https://pe.sjtu.edu.cn/oauth2Login"
        )
    }
}