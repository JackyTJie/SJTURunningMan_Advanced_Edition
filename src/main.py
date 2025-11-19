import time
import datetime
from src.api_client import get_authorization_token_and_rules, upload_running_data
from src.data_generator import generate_running_data_payload
from utils.auxiliary_util import log_output, SportsUploaderError, get_current_epoch_ms

def run_sports_upload(config, progress_callback=None, log_cb=None, stop_check_cb=None):
    """
    核心的跑步数据生成和上传逻辑，接收配置字典和进度回调函数。
    progress_callback: 接收 (current_value, max_value, message)
    log_cb: 接收 (message, level)
    stop_check_cb: 一个函数，调用时返回True表示请求停止
    """

    if stop_check_cb and stop_check_cb():
        log_output("任务被请求停止，正在退出...", "warning", log_cb)
        return False, "任务已停止。"

    auth_token_for_upload = None
    required_signpoints = []

    try:
        log_output("步骤 1/3: 获取认证信息...", callback=log_cb)
        if progress_callback: progress_callback(10, 100, "获取认证信息和跑步规则...")

        if stop_check_cb and stop_check_cb():
            log_output("任务被请求停止，正在退出...", "warning", log_cb)
            return False, "任务已停止。"

        # 获取认证令牌
        auth_token_for_upload, _ = get_authorization_token_and_rules(config, log_cb=log_cb, stop_check_cb=stop_check_cb)

    except SportsUploaderError as e:
        # 将错误返回给上层（UI/线程）处理并记录，避免重复打印同一错误
        return False, str(e)
    except Exception as e:
        return False, str(e)

    if stop_check_cb and stop_check_cb():
        log_output("任务被请求停止，正在退出...", "warning", log_cb)
        return False, "任务已停止。"

    log_output("\n步骤 2/3: 生成跑步数据...", callback=log_cb)
    if progress_callback: progress_callback(40, 100, "生成跑步数据...")
    running_data_payload = None
    total_dist = 0
    total_dur = 0
    try:
        running_data_payload, total_dist, total_dur = generate_running_data_payload(
            config,
            required_signpoints,
            {},
            log_cb=log_cb,
            stop_check_cb=stop_check_cb
        )

    except SportsUploaderError as e:
        log_output(f"生成跑步数据失败: {e}", "error", log_cb)
        return False, str(e)
    except Exception as e:
        log_output(f"未知错误: {e}", "error", log_cb)
        return False, str(e)

    if stop_check_cb and stop_check_cb():
        log_output("任务被请求停止，正在退出...", "warning", log_cb)
        return False, "任务已停止。"

    if running_data_payload and auth_token_for_upload:
        # 生成并上传数据，固定起始时间为每天 8:00
        log_output("\n步骤 3/3: 上传跑步数据...", callback=log_cb)
        total_runs = config.get('RUN_TIMES', 1)  # 从配置获取上传天数
        success_count = 0
        fail_count = 0

        # 计算日期列表 - upload for the past N days (yesterday, the day before yesterday, etc.)
        now = datetime.datetime.now()
        run_hour = config.get('RUN_HOUR', 8)  # 从配置获取运行小时，默认为8点
        run_minute = config.get('RUN_MINUTE', 0)  # 从配置获取运行分钟，默认为0
        run_second = config.get('RUN_SECOND', 0)  # 从配置获取运行秒钟，默认为0

        # Check if custom start date is provided
        start_date_str = config.get('START_DATE', None)
        if start_date_str:
            try:
                # Parse custom start date
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                # Set the time using RUN_HOUR, RUN_MINUTE, and RUN_SECOND
                start_date = start_date.replace(hour=run_hour, minute=run_minute, second=run_second, microsecond=0)
                # Calculate start times going backwards from the custom start date
                start_times = [start_date - datetime.timedelta(days=i) for i in range(total_runs)]
            except ValueError:
                # If date parsing fails, fall back to default behavior
                log_output(f"日期解析失败，使用默认日期: {start_date_str}，格式应为 YYYY-MM-DD", "warning", log_cb)
                start_times = [(now - datetime.timedelta(days=i+1)).replace(hour=run_hour, minute=run_minute, second=run_second, microsecond=0) for i in range(total_runs)]
        else:
            # Calculate start times for the past N days (yesterday, the day before yesterday, etc.)
            start_times = [(now - datetime.timedelta(days=i+1)).replace(hour=run_hour, minute=run_minute, second=run_second, microsecond=0) for i in range(total_runs)]

        for idx, start_dt in enumerate(start_times, 1):
            if stop_check_cb and stop_check_cb():
                log_output("任务被请求停止，正在退出...", "warning", log_cb)
                return False, "任务已停止。"

            # 设置本次发送的开始时间（毫秒）
            config["START_TIME_EPOCH_MS"] = int(start_dt.timestamp() * 1000)

            try:
                log_output(f"开始生成第{idx}/{total_runs}条跑步数据，开始时间: {start_dt}", callback=log_cb)
                running_data_payload, total_dist, total_dur = generate_running_data_payload(
                    config,
                    required_signpoints,
                    {},
                    log_cb=log_cb,
                    stop_check_cb=stop_check_cb
                )
            except SportsUploaderError as e:
                log_output(f"生成跑步数据失败（第{idx}/{total_runs}条）: {e}", "error", log_cb)
                fail_count += 1
                # 更新已完成计数并继续
                log_output(f"已完成{idx}/{total_runs}", "info", log_cb)
                if progress_callback: progress_callback(idx, total_runs, f"已完成{idx}/{total_runs}")
                continue
            except Exception as e:
                log_output(f"未知错误（生成第{idx}/{total_runs}条）: {e}", "error", log_cb)
                fail_count += 1
                log_output(f"已完成{idx}/{total_runs}", "info", log_cb)
                if progress_callback: progress_callback(idx, total_runs, f"已完成{idx}/{total_runs}")
                continue

            try:
                log_output(f"尝试上传第{idx}/{total_runs}条跑步数据...", callback=log_cb)
                response = upload_running_data(
                    config,
                    auth_token_for_upload,
                    running_data_payload,
                    log_cb=log_cb,
                    stop_check_cb=stop_check_cb
                )

                if response.get('code') == 0 and response.get('data'):
                    log_output(f"第{idx}/{total_runs}条上传成功", "success", log_cb)
                    success_count += 1
                else:
                    # 出现任何非成功情况均记录为失败但继续下一条
                    log_output(f"第{idx}/{total_runs}条上传未成功，响应: {response}", "warning", log_cb)
                    fail_count += 1

            except SportsUploaderError as e:
                log_output(f"上传失败（第{idx}/{total_runs}条）: {e}", "error", log_cb)
                fail_count += 1
            except Exception as e:
                log_output(f"未知错误（上传第{idx}/{total_runs}条）: {e}", "error", log_cb)
                fail_count += 1

            log_output(f"已完成{idx}/{total_runs}", "info", log_cb)
            if progress_callback: progress_callback(idx, total_runs, f"已完成{idx}/{total_runs}")

        # 所有条目处理完成
        final_msg = f"完成: {success_count}/{total_runs} 成功，{fail_count}/{total_runs} 失败"
        log_output(final_msg, callback=log_cb)
        if progress_callback: progress_callback(total_runs, total_runs, "已完成")
        return True, final_msg
    else:
        log_output("数据生成或认证失败，上传被跳过。", "error", log_cb)
        if progress_callback: progress_callback(100, 100, "上传被跳过！")
        return False, "数据生成或认证失败，上传被跳过。"