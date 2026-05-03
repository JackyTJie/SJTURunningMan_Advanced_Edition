package com.sjtu.runner.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.sjtu.runner.viewmodel.MainViewModel
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel) {
    val log by viewModel.log.collectAsStateWithLifecycle()
    val running by viewModel.running.collectAsStateWithLifecycle()
    
    // 重新登录状态
    var isReloginRequired by remember { mutableStateOf(false) }

    // 天数状态
    var days by remember { mutableIntStateOf(1) }
    var showCustomDays by remember { mutableStateOf(false) }
    var customDaysText by remember { mutableStateOf("") }

    // 时间状态
    var timeHour by remember { mutableIntStateOf(8) }
    var timeMinute by remember { mutableIntStateOf(0) }
    var showCustomTime by remember { mutableStateOf(false) }

    // 日期状态
    var dateText by remember {
        mutableStateOf(LocalDate.now().minusDays(1).format(DateTimeFormatter.ISO_LOCAL_DATE))
    }
    var showDatePicker by remember { mutableStateOf(false) }

    // 距离锁定为 1-5km
    var distanceKm by remember { mutableIntStateOf(5) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "交我润",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.ExtraBold)
                    )
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 参数配置区
            ElevatedCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        "任务参数",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    
                    Divider(thickness = 0.5.dp, color = MaterialTheme.colorScheme.outlineVariant)

                    // 1. 跑步天数 (下拉选择 + 自定义)
                    SettingItem(icon = Icons.Default.DateRange, label = "跑步天数") {
                        if (!showCustomDays) {
                            DropdownSelection(
                                items = listOf("1 天", "3 天", "5 天", "7 天", "10 天", "15 天", "30 天", "自定义"),
                                selected = "$days 天",
                                onSelect = {
                                    if (it == "自定义") {
                                        showCustomDays = true
                                    } else {
                                        days = it.replace(" 天", "").toInt()
                                    }
                                }
                            )
                        } else {
                            OutlinedTextField(
                                value = customDaysText,
                                onValueChange = { customDaysText = it.filter { c -> c.isDigit() } },
                                modifier = Modifier.width(110.dp),
                                placeholder = { Text("天数") },
                                trailingIcon = {
                                    IconButton(onClick = {
                                        days = customDaysText.toIntOrNull() ?: 1
                                        showCustomDays = false
                                    }) { Icon(Icons.Default.Check, "确定") }
                                },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                singleLine = true,
                                shape = RoundedCornerShape(8.dp)
                            )
                        }
                    }

                    // 2. 开始时间 (下拉选择 + 自定义)
                    SettingItem(icon = Icons.Default.Schedule, label = "开始时间") {
                        if (!showCustomTime) {
                            DropdownSelection(
                                items = (6..22).map { "%02d:00".format(it) } + "自定义",
                                selected = "%02d:%02d".format(timeHour, timeMinute),
                                onSelect = {
                                    if (it == "自定义") {
                                        showCustomTime = true
                                    } else {
                                        val parts = it.split(":")
                                        timeHour = parts[0].toInt()
                                        timeMinute = parts[1].toInt()
                                    }
                                }
                            )
                        } else {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                OutlinedTextField(
                                    value = if (timeHour < 10) "0$timeHour" else timeHour.toString(),
                                    onValueChange = { timeHour = it.toIntOrNull()?.coerceIn(0, 23) ?: timeHour },
                                    modifier = Modifier.width(60.dp),
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    singleLine = true,
                                    shape = RoundedCornerShape(8.dp)
                                )
                                Text(" : ", modifier = Modifier.padding(horizontal = 4.dp), fontWeight = FontWeight.Bold)
                                OutlinedTextField(
                                    value = if (timeMinute < 10) "0$timeMinute" else timeMinute.toString(),
                                    onValueChange = { timeMinute = it.toIntOrNull()?.coerceIn(0, 59) ?: timeMinute },
                                    modifier = Modifier.width(60.dp),
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    singleLine = true,
                                    shape = RoundedCornerShape(8.dp)
                                )
                                IconButton(onClick = { showCustomTime = false }) {
                                    Icon(Icons.Default.Check, "确定")
                                }
                            }
                        }
                    }

                    // 3. 起始日期 (图形化日历选择)
                    SettingItem(icon = Icons.Default.CalendarToday, label = "起始日期") {
                        OutlinedTextField(
                            value = dateText,
                            onValueChange = { },
                            modifier = Modifier
                                .width(160.dp)
                                .clickable { if (!running) showDatePicker = true },
                            readOnly = true,
                            enabled = false, // 禁用以便让整个区域可点击
                            colors = OutlinedTextFieldDefaults.colors(
                                disabledTextColor = MaterialTheme.colorScheme.onSurface,
                                disabledBorderColor = MaterialTheme.colorScheme.outline,
                                disabledTrailingIconColor = MaterialTheme.colorScheme.primary,
                            ),
                            trailingIcon = {
                                Icon(Icons.Default.EditCalendar, null)
                            },
                            singleLine = true,
                            shape = RoundedCornerShape(8.dp)
                        )
                    }

                    // 4. 目标距离：锁定 1-5km
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.DirectionsRun, null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("目标距离", style = MaterialTheme.typography.bodyMedium)
                            Spacer(modifier = Modifier.weight(1f))
                            Text(
                                "$distanceKm km",
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        Slider(
                            value = distanceKm.toFloat(),
                            onValueChange = { distanceKm = it.toInt() },
                            valueRange = 1f..5f,
                            steps = 3,
                            colors = SliderDefaults.colors(
                                thumbColor = MaterialTheme.colorScheme.primary,
                                activeTrackColor = MaterialTheme.colorScheme.primary
                            )
                        )
                    }
                }
            }

            // 重新登录提示
            if (isReloginRequired) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                        contentColor = MaterialTheme.colorScheme.onErrorContainer
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(Icons.Default.Warning, null, modifier = Modifier.size(24.dp))
                        Column {
                            Text("检测到cookie过期", fontWeight = FontWeight.Bold)
                            Text("请重新登录以继续上传", fontSize = 12.sp)
                        }
                        Spacer(modifier = Modifier.weight(1f))
                        Button(
                            onClick = { 
                                isReloginRequired = false
                                // 这里会触发MainActivity中的重新登录逻辑
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.error,
                                contentColor = MaterialTheme.colorScheme.onError
                            ),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("重新登录")
                        }
                    }
                }
            }

            // 控制按钮组
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = {
                        viewModel.startUpload(days, distanceKm, timeHour, timeMinute, dateText)
                    },
                    enabled = !running,
                    modifier = Modifier
                        .weight(1f)
                        .height(56.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.PlayArrow, null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("开始任务")
                }

                Button(
                    onClick = { viewModel.stopUpload() },
                    enabled = running,
                    modifier = Modifier
                        .weight(1f)
                        .height(56.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                        disabledContainerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.3f)
                    )
                ) {
                    Icon(Icons.Default.Stop, null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("停止任务")
                }
            }

            // 日志面板
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "运行日志",
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.padding(start = 4.dp)
                )
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(300.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                    shape = RoundedCornerShape(12.dp),
                    border = CardDefaults.outlinedCardBorder()
                ) {
                    val scrollState = rememberScrollState()
                    LaunchedEffect(log) {
                        scrollState.animateScrollTo(scrollState.maxValue)
                    }
                    Box(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = log.ifEmpty { "就绪。点击“开始任务”启动。" },
                            fontFamily = FontFamily.Monospace,
                            fontSize = 12.sp,
                            lineHeight = 18.sp,
                            modifier = Modifier.verticalScroll(scrollState),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }

    // 图形化日期选择器
    if (showDatePicker) {
        val datePickerState = rememberDatePickerState(
            initialSelectedDateMillis = LocalDate.parse(dateText)
                .atStartOfDay(ZoneId.of("UTC"))
                .toInstant()
                .toEpochMilli()
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    datePickerState.selectedDateMillis?.let {
                        dateText = Instant.ofEpochMilli(it)
                            .atZone(ZoneId.of("UTC"))
                            .toLocalDate()
                            .format(DateTimeFormatter.ISO_LOCAL_DATE)
                    }
                    showDatePicker = false
                }) { Text("确定") }
            },
            dismissButton = {
                TextButton(onClick = { showDatePicker = false }) { Text("取消") }
            }
        ) {
            DatePicker(state = datePickerState)
        }
    }
}

@Composable
fun SettingItem(
    icon: ImageVector,
    label: String,
    content: @Composable () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, tint = MaterialTheme.colorScheme.secondary, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.width(12.dp))
            Text(label, style = MaterialTheme.typography.bodyMedium)
        }
        content()
    }
}

@Composable
fun DropdownSelection(items: List<String>, selected: String, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(
            onClick = { expanded = true },
            shape = RoundedCornerShape(8.dp),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
        ) {
            Text(selected, style = MaterialTheme.typography.bodyMedium)
            Icon(Icons.Default.ArrowDropDown, null)
        }
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            modifier = Modifier.background(MaterialTheme.colorScheme.surface)
        ) {
            items.forEach { item ->
                DropdownMenuItem(
                    text = { Text(item) },
                    onClick = {
                        onSelect(item)
                        expanded = false
                    }
                )
            }
        }
    }
}
