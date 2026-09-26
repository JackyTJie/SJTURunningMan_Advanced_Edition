"""GitHub Release 版本检查。

从 GitHub Release 列表里取版本号最大的一个（含预发布版），与本机
``config.global_version`` 比较，并按当前平台挑选对应的安装包直链。
"""

import sys

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

import src.config as config

GITHUB_REPO = "JackyTJie/SJTURunningMan_Advanced_Edition"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
RELEASE_PAGE = f"https://github.com/{GITHUB_REPO}/releases/tag"

REQUEST_TIMEOUT = 8
MAX_RELEASES = 30

# 当前平台优先匹配的安装包后缀
PLATFORM_SUFFIXES = {
    "win32": (".exe",),
    "darwin": (".dmg",),
    "linux": (".deb",),
}


def parse_version(text):
    """把 tag 拆成 (数字元组, 预发布后缀)。

    例如 ``"v4.4.0"`` 得到 ``((4, 4, 0), "")``，
    ``"4.4.0-beta1"`` 得到 ``((4, 4, 0), "beta1")``。
    """
    if not text:
        return (), ""
    raw = str(text).strip().lstrip("vV")
    head, _, tail = raw.partition("-")
    numbers = []
    for chunk in head.split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        numbers.append(int(digits))
    return tuple(numbers), tail


def is_newer(remote_tag, local_tag):
    """远程 tag 是否比本地版本新。版本号相同时，稳定版优先于预发布版。"""
    remote_numbers, remote_pre = parse_version(remote_tag)
    local_numbers, local_pre = parse_version(local_tag)
    if not remote_numbers:
        return False
    if remote_numbers != local_numbers:
        return remote_numbers > local_numbers
    return (not remote_pre) and bool(local_pre)


def pick_asset(assets, platform=None):
    """按当前平台挑选安装包下载直链，找不到返回空串。"""
    suffixes = PLATFORM_SUFFIXES.get(platform or sys.platform, ())
    if not suffixes:
        return ""
    for asset in assets or []:
        name = (asset.get("name") or "").lower()
        if name.endswith(suffixes):
            return asset.get("browser_download_url") or ""
    return ""


def fetch_latest_release():
    """返回 (tag, release 页面链接, assets)。

    取列表里版本号最大的非 draft release，预发布版也参与比较。
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"SJTURunningMan/{config.global_version}",
    }
    response = requests.get(
        RELEASES_API,
        headers=headers,
        params={"per_page": MAX_RELEASES},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    best = None
    best_key = None
    for item in response.json():
        if item.get("draft"):
            continue
        numbers, pre = parse_version(item.get("tag_name"))
        if not numbers:
            continue
        # 数字大的更新；数字相同则稳定版排在预发布版之后
        key = (numbers, 0 if pre else 1)
        if best_key is None or key > best_key:
            best_key = key
            best = item

    if best is None:
        raise RuntimeError("未找到可用的 Release")

    tag = best.get("tag_name") or ""
    html_url = best.get("html_url") or f"{RELEASE_PAGE}/{tag}"
    return tag, html_url, best.get("assets") or []


def short_error(exc):
    """把异常转成给用户看的一行短提示。"""
    if isinstance(exc, requests.exceptions.Timeout):
        return "连接超时"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "网络不可用"
    if isinstance(exc, requests.exceptions.HTTPError):
        response = getattr(exc, "response", None)
        if response is not None:
            if response.status_code == 403:
                return "请求过于频繁 (403)"
            return f"HTTP {response.status_code}"
    return str(exc) or exc.__class__.__name__


class UpdateCheckSignals(QObject):
    """QRunnable 不能带信号，用一个 QObject 承载。"""

    # 是否有新版本, 提示文案, 跳转链接
    checked = Signal(bool, str, str)
    failed = Signal(str)


class UpdateCheckTask(QRunnable):
    """后台检查更新，交给 QThreadPool 跑。

    不用 QThread：无 parent 的 QThread 若在窗口销毁后仍在运行，
    解释器退出时会触发 "QThread: Destroyed while thread is still running" 而 abort。
    QThreadPool 在退出时会等待任务结束，没有这个问题。
    """

    def __init__(self):
        super().__init__()
        self.signals = UpdateCheckSignals()
        self._stopped = False
        self._done = False

    @property
    def done(self):
        """任务是否已跑完（用于清理引用）。"""
        return self._done

    def stop(self):
        """窗口已关闭时调用，避免再发信号。"""
        self._stopped = True

    def run(self):
        try:
            self._check()
        finally:
            self._done = True

    def _check(self):
        try:
            tag, html_url, assets = fetch_latest_release()
            if self._stopped:
                return
            if is_newer(tag, config.global_version):
                self.signals.checked.emit(True, f"发现新版本 {tag}", pick_asset(assets) or html_url)
            else:
                self.signals.checked.emit(False, f"已是最新版本 {config.global_version}", "")
        except Exception as exc:
            if not self._stopped:
                self.signals.failed.emit(short_error(exc))
