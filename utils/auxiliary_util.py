import re
import math
import time as _time
import datetime
import os
import sys

EARTH_RADIUS_METERS = 6371000
TRACK_POINT_DECIMAL_PLACES = 7

def re_search(retext, text):
    m = re.search(retext, text)
    return m.group(1) if m else None


def get_timestamp():
    """返回当前时间的毫秒字符串表示。"""
    return str(round(_time.time() * 1000))



def get_base_path():
    """获取应用程序基础路径：如果已打包（frozen），返回 exe 所在目录，否则返回项目根目录。"""
    if hasattr(sys, 'frozen'):
        # For frozen applications, return the directory where the executable is located
        # This allows finding user-created files like user.txt that are added after compilation
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SportsUploaderError(Exception):
    """自定义异常，用于在 UI 层捕获并呈现错误信息。"""
    pass


def log_output(message, level="info", callback=None):
    """统一日志输出：可传入 UI 回调，否则打印到控制台。

    level 支持 'info'、'warning'、'error'。
    """
    if callback:
        callback(message, level)
        return

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if level == "error":
        print(f"[{timestamp}][ERROR] {message}")
    elif level == "warning":
        print(f"[{timestamp}][WARNING] {message}")
    else:
        print(f"[{timestamp}][INFO] {message}")


def haversine_distance(lat1, lon1, lat2, lon2):
    """计算两点之间的 Haversine 距离，返回米为单位的浮点数。"""
    R = EARTH_RADIUS_METERS
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_current_epoch_ms():
    """返回当前 Unix epoch 毫秒整数。"""
    return int(_time.time() * 1000)