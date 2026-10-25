package com.sjtu.runner.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.CloudDownload
import androidx.compose.material.icons.outlined.Code
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sjtu.runner.config.AppConfig
import com.sjtu.runner.ui.theme.LocalAppColors
import com.sjtu.runner.update.UpdateChecker
import com.sjtu.runner.update.UpdateResult

private fun openUrl(context: android.content.Context, url: String) {
    if (url.isBlank()) return
    runCatching {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }
}

/**
 * 「关于软件」页：与电脑版的三张卡片一一对应 —— 软件信息、更新与社区、使用说明。
 *
 * 更新检查只在点击「检查更新」时发起，结果只以一行文字呈现，不弹窗。
 */
@Composable
fun AboutPanel(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val appColors = LocalAppColors.current
    var result by remember { mutableStateOf<UpdateResult?>(null) }
    var checking by remember { mutableStateOf(false) }

    LaunchedEffect(checking) {
        if (!checking) return@LaunchedEffect
        result = UpdateChecker.checkForUpdates()
        checking = false
    }

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        SectionCard(title = "交我润", icon = Icons.Outlined.Info) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "SJTU RunningMan",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.width(10.dp))
                StatusPill(
                    text = "v${AppConfig.VERSION_NAME}",
                    color = MaterialTheme.colorScheme.primary
                )
            }
            Text(
                "安卓客户端 · Kotlin 与 Jetpack Compose",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            SectionDivider()
            Text(
                "三改：Github@JackyTJie\n二改：Github@accelerator-s\n原作者：Github@Labyrinth0419",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        SectionCard(title = "更新与社区", icon = Icons.Outlined.CloudDownload) {
            Text(
                when (val current = result) {
                    is UpdateResult.UpToDate -> "已是最新版本 ${current.latestTag}"
                    is UpdateResult.UpdateAvailable -> "发现新版本 ${current.latest.tag}"
                    is UpdateResult.Failed -> "检查更新失败：${current.reason}"
                    null -> "尚未检查更新。"
                },
                style = MaterialTheme.typography.bodySmall,
                color = when (result) {
                    is UpdateResult.UpToDate, is UpdateResult.UpdateAvailable -> appColors.success
                    is UpdateResult.Failed -> MaterialTheme.colorScheme.error
                    null -> MaterialTheme.colorScheme.onSurfaceVariant
                }
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                if (checking) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp), strokeWidth = 2.dp)
                        Text("检查中…", style = MaterialTheme.typography.labelLarge)
                    }
                } else {
                    OutlinedButton(onClick = { checking = true }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("检查更新")
                    }
                }
            }
            SectionDivider()
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                LinkButton(icon = Icons.Outlined.Code, label = "仓库") {
                    openUrl(context, AppConfig.GITHUB_REPO_URL)
                }
                LinkButton(icon = Icons.AutoMirrored.Outlined.OpenInNew, label = "水源") {
                    openUrl(context, AppConfig.SHUIYUAN_TOPIC_URL)
                }
                val latest = (result as? UpdateResult.UpdateAvailable)?.latest
                if (latest != null) {
                    LinkButton(icon = Icons.Outlined.CloudDownload, label = "下载") {
                        openUrl(context, latest.url)
                    }
                }
            }
        }

        SectionCard(title = "使用说明", icon = Icons.Outlined.Info) {
            Text(
                AppConfig.DISCLAIMER_TEXT,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun LinkButton(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit
) {
    OutlinedButton(onClick = onClick) {
        Icon(icon, null, modifier = Modifier.padding(end = 6.dp))
        Text(label)
    }
}
