package com.sjtu.runner

import android.content.Intent
import android.os.Bundle
import android.webkit.CookieManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.ViewModelProvider
import com.sjtu.runner.login.LoginActivity
import com.sjtu.runner.ui.MainScreen
import com.sjtu.runner.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {

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

    private val viewModel by lazy {
        ViewModelProvider(this)[MainViewModel::class.java]
    }

    private val loginLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            logMsg("重新登录成功，重新加载界面...")
            setContent {
                MainScreen(viewModel)
            }
        } else {
            logMsg("重新登录失败")
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 设置重新登录回调
        viewModel.onReloginRequired = {
            runOnUiThread {
                logMsg("检测到cookie过期，正在重新登录...")
                loginLauncher.launch(Intent(this, LoginActivity::class.java))
            }
        }

        val cookie = CookieManager.getInstance().getCookie("https://jaccount.sjtu.edu.cn")
        if (cookie?.contains("JAAuthCookie") == true) {
            setContent {
                MainScreen(viewModel)
            }
        } else {
            logMsg("未检测到登录状态，启动登录页面...")
            loginLauncher.launch(Intent(this, LoginActivity::class.java))
        }
    }
    
    private fun logMsg(msg: String) {
        println("MainActivity: $msg")
    }
}