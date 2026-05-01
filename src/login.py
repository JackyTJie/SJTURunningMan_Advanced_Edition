from time import sleep
import requests
import os, sys

from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from tenacity import retry, retry_if_exception_type, wait_fixed
from utils.auxiliary_util import re_search, get_timestamp

# 二次验证方式
_2FA_METHODS = {
    '1': ('app', '交我办'),
    '2': ('email', '邮箱'),
    '3': ('sms', '短信'),
}

def get_jalogin_from_authorize(session, client_id, redirect_uri, scope="profile", state="8"):
    """
    模拟浏览器访问 /oauth2/authorize 并返回最终的 /jaccount/jalogin?... URL。
    """
    authorize_url = "https://jaccount.sjtu.edu.cn/oauth2/authorize"
    params = {
        "response_type": "code",
        "scope": scope,
        "client_id": client_id,
        "state": state,
        "redirect_uri": redirect_uri,
    }
    # 发起请求并允许重定向；session 会保存 cookies
    r = session.get(authorize_url, params=params, allow_redirects=True, timeout=10)

    # 优先在重定向历史中寻找 jalogin
    for resp in (r.history + [r]):
        if "jaccount.sjtu.edu.cn/jaccount/jalogin" in resp.url:
            return resp.url

    # 兜底：从页面中提取 jalogin 链接
    m = re_search(r'''(https?://jaccount\.sjtu\.edu\.cn/jaccount/jalogin\?[^\s"'<>]+)''', r.text)
    if m:
        return m.group(1)

    raise RuntimeError("未能从 authorize 的重定向/页面中获取 jalogin URL")

# 创建一个新的 session
def _create_session():
    session = requests.Session()
    session.headers = {'Referer':'https://jaccount.sjtu.edu.cn'}
    session.mount('http://', HTTPAdapter(max_retries=3))
    session.mount('https://', HTTPAdapter(max_retries=3))
    return session

# 获得登录界面网页(html)，便于之后从中提取必要信息
@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _get_login_page(session, url):
    return session.get(url)

# 获得验证码图片(jpeg)
@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _get_captcha(session, captcha_url):
    session.get(captcha_url)
    captcha_jpeg = session.get(captcha_url)
    image_path = "captcha.jpeg"
    with open(image_path, "wb") as f:
        f.write(captcha_jpeg.content)


# 调用外部模型识别验证码
def _identify_captcha():
    captcha_solver_url = "https://geek.sjtu.edu.cn/captcha-solver/"
    image_path = "captcha.jpeg"

    with open(image_path, "rb") as f:
        files = {"image": ("captcha.jpg", f, "image/jpeg")}
        response = requests.post(captcha_solver_url, files=files)

    try:
        result = response.json().get("result")
        os.remove("captcha.jpeg")
        return result
    except Exception:
        raise RuntimeError("验证码识别失败")

@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _post_login_request(session, login_page, username, password, captcha_code):
    # 从页面中获得其他必要参数
    sid = re_search(r'sid: "(.*?)"', login_page)
    returl = re_search(r'returl:"(.*?)"', login_page)
    se = re_search(r'se: "(.*?)"', login_page)
    client = re_search(r'client: "(.*?)"', login_page)
    uuid_val = re_search(r'captcha\?uuid=(.*?)&t=', login_page)

    # 构建提交 data
    data = {'sid': sid, 'returl': returl, 'se': se, 'client': client, 'user': username,
            'pass': password, 'captcha': captcha_code, 'v': '', 'uuid': uuid_val}

    # 发起 post 请求
    res = session.post('https://jaccount.sjtu.edu.cn/jaccount/ulogin', data=data)
    return res


def _is_2fa_page(text):
    """检测是否为二次验证页面"""
    return ("请进行二次验证" in text
            or "2faVerify" in text
            or "2fa/loginVerify" in text)


def _send_2fa_code(session, method):
    """发送二次验证码"""
    url = "https://jaccount.sjtu.edu.cn/jaccount/2fa/loginVerify"
    resp = session.post(url, data={'c': method}, headers={
        'X-Requested-With': 'XMLHttpRequest',
    })
    result = resp.json()
    if result.get('errno', -1) != 0:
        raise RuntimeError(f"验证码发送失败: {result.get('error', '未知错误')}")


def _verify_2fa_code(session, username, code):
    """提交二次验证码并返回 errno"""
    url = "https://jaccount.sjtu.edu.cn/jaccount/2faVerify"
    resp = session.post(url, data={
        'account': username,
        'captcha': code,
        'trust': 'true',
    }, headers={'X-Requested-With': 'XMLHttpRequest'})
    result = resp.json()
    return result.get('errno', -1)


def _handle_2fa(session, response, username, two_fa_cb=None):
    """
    处理异地登录二次验证。
    two_fa_cb 需提供:
      select_method() -> 'app'/'email'/'sms' 或 None(取消)
      get_code() -> 6位验证码 或 'r'(重发) 或 None(取消)
      show_message(msg) -> 显示提示
    """
    if two_fa_cb is None:
        raise RuntimeError("检测到异地登录需要二次验证，请在界面中操作")

    two_fa_cb['show_message']("检测到异地登录，需要二次验证")

    method = two_fa_cb['select_method']()
    if not method:
        raise RuntimeError("已取消二次验证")

    _send_2fa_code(session, method)
    two_fa_cb['show_message']("验证码已发送，请查收")

    for attempt in range(5):
        code = two_fa_cb['get_code']()
        if not code:
            raise RuntimeError("已取消二次验证")

        if code.lower() == 'r':
            _send_2fa_code(session, method)
            two_fa_cb['show_message']("验证码已重新发送")
            continue

        if not code.isdigit() or len(code) != 6:
            two_fa_cb['show_message']("验证码应为6位数字，请重新输入")
            continue

        errno = _verify_2fa_code(session, username, code)
        if errno == 0:
            sleep(1)
            # 重新访问完成登录重定向
            try:
                session.get(response.url)
            except Exception:
                pass
            return
        elif errno in (4, 5):
            _send_2fa_code(session, method)
            two_fa_cb['show_message']("验证码已过期，已重新发送")
        else:
            remaining = 4 - attempt
            two_fa_cb['show_message'](f"验证码错误，还可重试 {remaining} 次")

    raise RuntimeError("二次验证失败: 超过最大尝试次数")


def login(username, password, two_fa_cb=None):
    session = _create_session()

    url = get_jalogin_from_authorize(
        session,
        client_id="9mqzULSXYgUYj5fPOpyL",
        redirect_uri="https://pe.sjtu.edu.cn/oauth2Login"
    )

    login_resp = _get_login_page(session, url)

    # 如果直接进入2FA页面
    if _is_2fa_page(login_resp.text) or _is_2fa_page(login_resp.url):
        _handle_2fa(session, login_resp, username, two_fa_cb)
        return session

    login_page = login_resp.text

    captcha_id = re_search(r'img.src = \'captcha\?(.*)\'', login_page) + get_timestamp()  # type: ignore
    captcha_url = 'https://jaccount.sjtu.edu.cn/jaccount/captcha?' + captcha_id

    _get_captcha(session, captcha_url)
    captcha_code = _identify_captcha()

    sleep(1)

    res = _post_login_request(session, login_page, username, password, captcha_code)

    # 检查是否触发了二次验证
    if _is_2fa_page(res.text) or _is_2fa_page(res.url):
        _handle_2fa(session, res, username, two_fa_cb)
        return session

    # 检查登录结果
    cookie_names = {c.name for c in session.cookies}
    if 'JAAuthCookie' in cookie_names:
        return session

    raise RuntimeError("登录失败，请检查用户名和密码")