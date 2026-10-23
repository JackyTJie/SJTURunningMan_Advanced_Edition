use chrono::NaiveDate;
use regex::Regex;
use reqwest::{
    blocking::{Client, Response},
    cookie::{CookieStore, Jar},
};
use serde_json::Value;
use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::Duration,
};

const ACCOUNT: &str = "https://jaccount.sjtu.edu.cn";
const PORTAL: &str = "https://pe.sjtu.edu.cn";
const CAPTCHA_SOLVER: &str = "https://geek.sjtu.edu.cn/captcha-solver/";
const APP_UA: &str = "Mozilla/5.0 (Linux; Android 12; SM-S9080; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/138.0.7204.67 Mobile Safari/537.36 TaskCenterApp/3.5.0";

#[derive(Clone)]
pub struct Session {
    client: Client,
    jar: Arc<Jar>,
    base: String,
    /// 二次验证页面上提取到的账号、隐藏字段与完成后应访问的地址。
    /// 克隆 Session 时共享，send_code / verify_code 才能看到同一份上下文。
    two_factor: Arc<Mutex<Option<TwoFactorContext>>>,
}
pub struct LoginChallenge {
    pub session: Session,
    pub fields: HashMap<String, String>,
    pub image: Vec<u8>,
}
pub enum LoginResult {
    Authenticated(Session),
    TwoFactor(Session),
}

#[derive(Clone, Debug, Default)]
struct TwoFactorContext {
    /// 服务端 2FA 表单里的账号；缺省时回退到用户输入的账号。
    account: Option<String>,
    /// 2FA 页面上的隐藏字段（如 sid / uuid / csrf token）。提交验证码时原样带回。
    fields: Vec<(String, String)>,
    /// 验证成功后需要访问的地址（通常是 ulogin 或 2FA 完成页）。
    complete_url: Option<String>,
}

pub fn network_error(error: reqwest::Error) -> String {
    if error.is_timeout() {
        "连接超时，请重试".into()
    } else if let Some(status) = error.status() {
        format!("服务器返回 HTTP {}", status.as_u16())
    } else if error.is_decode() {
        "服务器返回了无法解析的数据".into()
    } else {
        "网络连接失败，请检查网络或代理设置".into()
    }
}

/// 验证码图片来自网络：字节数上限不保证解码后内存可控，这里同时限制解码尺寸。
const MAX_CAPTCHA_WIDTH: u32 = 2_048;
const MAX_CAPTCHA_HEIGHT: u32 = 1_024;
const MAX_CAPTCHA_ALLOC: u64 = 16 * 1024 * 1024;

pub fn decode_captcha(bytes: &[u8]) -> Result<image::DynamicImage, String> {
    let mut reader = image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .map_err(|_| "验证码接口未返回有效图片，请刷新重试".to_owned())?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(MAX_CAPTCHA_WIDTH);
    limits.max_image_height = Some(MAX_CAPTCHA_HEIGHT);
    limits.max_alloc = Some(MAX_CAPTCHA_ALLOC);
    reader.limits(limits);
    reader
        .decode()
        .map_err(|_| "验证码接口未返回有效图片，请刷新重试".to_owned())
}

fn checked(response: Result<Response, reqwest::Error>) -> Result<Response, String> {
    response
        .and_then(Response::error_for_status)
        .map_err(network_error)
}

impl Session {
    pub fn new() -> Result<Self, String> {
        let jar = Arc::new(Jar::default());
        let client = Client::builder()
            .cookie_provider(jar.clone())
            .timeout(Duration::from_secs(15))
            .connect_timeout(Duration::from_secs(8))
            .user_agent(APP_UA)
            .redirect(reqwest::redirect::Policy::limited(12))
            .build()
            .map_err(network_error)?;
        Ok(Self {
            client,
            jar,
            base: PORTAL.into(),
            two_factor: Arc::new(Mutex::new(None)),
        })
    }

    pub fn prepare_login() -> Result<LoginChallenge, String> {
        let session = Self::new()?;
        let response = checked(
            session
                .client
                .get(format!("{ACCOUNT}/oauth2/authorize"))
                .header("Referer", ACCOUNT)
                .query(&[
                    ("response_type", "code"),
                    ("scope", "profile"),
                    ("client_id", "9mqzULSXYgUYj5fPOpyL"),
                    ("state", "8"),
                    ("redirect_uri", "https://pe.sjtu.edu.cn/oauth2Login"),
                ])
                .send(),
        )?;
        let html = response.text().map_err(network_error)?;
        let fields = login_fields(&html)?;
        let uuid = fields.get("uuid").ok_or("登录页面缺少验证码信息")?;
        let image = session.fetch_captcha(ACCOUNT, uuid)?;
        Ok(LoginChallenge {
            session,
            fields,
            image,
        })
    }

    fn fetch_captcha(&self, account: &str, uuid: &str) -> Result<Vec<u8>, String> {
        let response = checked(
            self.client
                .get(format!("{account}/jaccount/captcha"))
                // 与旧版一致；学校验证码接口会拒绝没有来源页的请求。
                .header("Referer", account)
                .query(&[
                    ("uuid", uuid),
                    ("t", &chrono::Utc::now().timestamp_millis().to_string()),
                ])
                .send(),
        )?;
        let mut image = Vec::new();
        use std::io::Read;
        response
            .take(512 * 1024 + 1)
            .read_to_end(&mut image)
            .map_err(|_| "验证码图片读取失败，请重试")?;
        if image.len() > 512 * 1024 {
            return Err("验证码图片过大".into());
        }
        decode_captcha(&image)?;
        Ok(image)
    }

    pub fn recognize_captcha(image: &[u8]) -> Result<String, String> {
        // 识别请求只带图片，不复用包含登录 Cookie 的会话。
        let client = Client::builder()
            .timeout(Duration::from_secs(15))
            .build()
            .map_err(network_error)?;
        recognize_captcha_with(&client, CAPTCHA_SOLVER, image)
    }

    pub fn login(
        challenge: LoginChallenge,
        username: &str,
        password: &str,
        captcha: &str,
    ) -> Result<LoginResult, String> {
        Self::login_at(challenge, username, password, captcha, ACCOUNT)
    }

    fn login_at(
        challenge: LoginChallenge,
        username: &str,
        password: &str,
        captcha: &str,
        account: &str,
    ) -> Result<LoginResult, String> {
        if username.trim().is_empty() || password.is_empty() || captcha.trim().is_empty() {
            return Err("请填写账号、密码和图形验证码".into());
        }
        let LoginChallenge {
            session,
            mut fields,
            ..
        } = challenge;
        fields.insert("user".into(), username.trim().into());
        fields.insert("pass".into(), password.into());
        fields.insert("captcha".into(), captcha.trim().into());
        fields.insert("v".into(), String::new());
        fields.insert("lt".into(), "p".into());
        // 保留旧版识别后 1 秒的提交间隔，避免立即提交被判验证码无效。
        std::thread::sleep(Duration::from_secs(1));
        let mut response = checked(
            session
                .client
                .post(format!("{account}/jaccount/ulogin"))
                .header("Referer", account)
                .header("X-Requested-With", "XMLHttpRequest")
                .form(&fields)
                .send(),
        )?;
        let mut url = response.url().clone();
        let mut text = response.text().map_err(network_error)?;
        // 当前登录页通过 AJAX 返回下一跳地址，HTTP 客户端需要主动完成跳转。
        if text.trim_start().starts_with('{') {
            let result: Value =
                serde_json::from_str(&text).map_err(|_| "登录响应格式无效，请重试")?;
            if result["errno"].as_i64() != Some(0) {
                return Err(login_failure(&result));
            }
            let next = result["url"]
                .as_str()
                .filter(|s| !s.is_empty())
                .ok_or("登录响应缺少跳转地址，请重试")?;
            let next = url.join(next).map_err(|_| "登录跳转地址无效")?;
            let account_url = reqwest::Url::parse(account).map_err(|_| "登录地址无效")?;
            let portal_url = reqwest::Url::parse(&session.base).map_err(|_| "校园跑地址无效")?;
            if next.origin() != account_url.origin() && next.origin() != portal_url.origin() {
                return Err("登录响应包含未知跳转地址".into());
            }
            if needs_two_factor(next.as_str()) {
                // 浏览器会导航到 JSON 返回的下一跳并渲染 2FA 页面。这里尝试
                // 加载该页面以提取账号 / 隐藏字段；若下一跳只接受 POST（405）
                // 则忽略失败，继续沿用 ulogin 建立的会话，不能挡住二次验证。
                let mut context = two_factor_context("", next.as_str(), &result);
                if let Ok(page) = session
                    .client
                    .get(next.clone())
                    .header("Referer", account)
                    .send()
                {
                    if page.status().is_success() {
                        let page_url = page.url().clone();
                        if let Ok(page_text) = page.text() {
                            // 只接受真正的 2FA 页面；避免把重定向后的普通登录
                            // 页字段带进验证请求。
                            if needs_two_factor(&page_text)
                                || page_text.to_ascii_lowercase().contains("2fa")
                            {
                                context =
                                    two_factor_context(&page_text, page_url.as_str(), &result);
                            }
                        }
                    }
                }
                context.complete_url = Some(url.to_string());
                if let Ok(mut slot) = session.two_factor.lock() {
                    *slot = Some(context);
                }
                return Ok(LoginResult::TwoFactor(session));
            }
            response = checked(session.client.get(next).header("Referer", account).send())?;
            url = response.url().clone();
            text = response.text().map_err(network_error)?;
        }
        if needs_two_factor(&text) || needs_two_factor(url.as_str()) {
            let mut context = two_factor_context(&text, url.as_str(), &Value::Null);
            context.complete_url = Some(url.to_string());
            if let Ok(mut slot) = session.two_factor.lock() {
                *slot = Some(context);
            }
            return Ok(LoginResult::TwoFactor(session));
        }
        if has_auth_cookie(&session.jar) {
            Ok(LoginResult::Authenticated(session))
        } else {
            Err("登录未成功，请检查账号、密码或刷新图形验证码".into())
        }
    }

    pub fn send_code(&self, method: &str) -> Result<(), String> {
        if !["app", "email", "sms"].contains(&method) {
            return Err("不支持的验证方式".into());
        }
        let value: Value = checked(
            self.client
                .post(format!("{ACCOUNT}/jaccount/2fa/loginVerify"))
                .header("Referer", ACCOUNT)
                .header("X-Requested-With", "XMLHttpRequest")
                .form(&[("c", method)])
                .send(),
        )?
        .json()
        .map_err(network_error)?;
        if value["errno"] == 0 {
            Ok(())
        } else {
            Err("验证码发送失败，请稍后重试".into())
        }
    }

    pub fn verify_code(&self, username: &str, code: &str) -> Result<(), String> {
        self.verify_code_at(ACCOUNT, username, code)
    }

    fn verify_code_at(&self, base: &str, username: &str, code: &str) -> Result<(), String> {
        if code.len() != 6 || !code.bytes().all(|c| c.is_ascii_digit()) {
            return Err("请输入 6 位数字验证码".into());
        }
        let context = self
            .two_factor
            .lock()
            .ok()
            .and_then(|slot| slot.clone())
            .unwrap_or_default();
        let account = context
            .account
            .as_deref()
            .filter(|value| !value.trim().is_empty())
            .unwrap_or(username);
        // trust=true 让服务端把本机记为可信设备，与旧版客户端一致；传 false 时每次登录都会重新要求二次验证。
        let mut fields: Vec<(String, String)> = vec![
            ("account".into(), account.to_owned()),
            ("captcha".into(), code.to_owned()),
            ("trust".into(), "true".into()),
        ];
        for (name, value) in &context.fields {
            if !name.is_empty()
                && !value.is_empty()
                && !matches!(
                    name.as_str(),
                    "account" | "captcha" | "trust" | "pass" | "password"
                )
                && !fields.iter().any(|(existing, _)| existing == name)
            {
                fields.push((name.clone(), value.clone()));
            }
        }
        let value: Value = checked(
            self.client
                .post(format!("{base}/jaccount/2faVerify"))
                .header("Referer", base)
                .header("X-Requested-With", "XMLHttpRequest")
                .form(&fields)
                .send(),
        )?
        .json()
        .map_err(network_error)?;
        if value["errno"].as_i64() != Some(0) {
            return Err(two_factor_failure(&value));
        }
        // 与旧 Python 客户端一致：验证完成后访问登录响应地址，让服务端完成
        // 2FA → OAuth 的跳转。部分部署会返回 405/空响应，因此忽略失败并在
        // 没有拿到认证 Cookie 时回退到重新走 authorize。
        if let Some(complete) = context.complete_url {
            let _ = self
                .client
                .get(&complete)
                .header("Referer", ACCOUNT)
                .send()
                .and_then(reqwest::blocking::Response::error_for_status);
        }
        if !has_auth_cookie(&self.jar) {
            let _ = checked(
                self.client
                    .get(format!("{ACCOUNT}/oauth2/authorize"))
                    .header("Referer", ACCOUNT)
                    .query(&[
                        ("response_type", "code"),
                        ("scope", "profile"),
                        ("client_id", "9mqzULSXYgUYj5fPOpyL"),
                        ("state", "8"),
                        ("redirect_uri", "https://pe.sjtu.edu.cn/oauth2Login"),
                    ])
                    .send(),
            );
        }
        if has_auth_cookie(&self.jar) {
            Ok(())
        } else {
            Err("二次验证已通过，但登录会话未建立，请重新登录".into())
        }
    }

    pub fn authorize(&self, cancel: &AtomicBool) -> Result<(String, Value), String> {
        let check_cancel = || {
            if cancel.load(Ordering::Relaxed) {
                Err("任务已停止".to_owned())
            } else {
                Ok(())
            }
        };
        check_cancel()?;
        let value: Value = checked(
            self.client
                .get(format!("{}/sports/my/uid", self.base))
                .header("Referer", format!("{}/phone/", self.base))
                .send(),
        )?
        .json()
        .map_err(network_error)?;
        if value["code"] != 0 {
            return Err("会话已失效，请重新登录".into());
        }
        let token = value["data"]["uid"]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or("认证响应缺少凭据，请重新登录")?
            .to_owned();
        check_cancel()?;
        let _ = checked(
            self.client
                .get(format!("{}/sports/my/data", self.base))
                .send(),
        );
        check_cancel()?;
        let rules: Value = checked(
            self.client
                .get(format!("{}/api/running/point-rule", self.base))
                .header("Authorization", &token)
                .query(&[("location", "121.44293800000000,31.03159900000000")])
                .send(),
        )?
        .json()
        .map_err(network_error)?;
        check_cancel()?;
        if rules["code"] != 0 {
            return Err("无法获取跑步规则，请重新登录后重试".into());
        }
        Ok((token, rules["data"].clone()))
    }

    /// 只读学期统计：达标公里、完成率与本学期打卡日期。
    /// 这些接口只要 pe.sjtu.edu.cn 的会话 Cookie，不需要 `/sports/my/uid` 换的 token。
    /// 其中学期目标与学期起止日期失败时不阻塞其余数据。
    pub fn semester_stats(&self) -> Result<crate::stats::SemesterStats, String> {
        let data = self.get_json("/sports/my/data", &[], "学期统计")?;
        let summary = &data["data"][0];
        let result_km = json_number(summary.get("resultKm"));
        let total_km = json_number(summary.get("totalKm"));
        let percent = json_number(summary.get("percent"))
            .or_else(|| crate::stats::percent_from_ratio(result_km, total_km));
        let target_km = self
            .get_json("/sports/my/semesterTarget", &[], "学期目标")
            .ok()
            .and_then(|value| json_number(value["data"].get("target")));

        let semester = self.get_json(
            "/sports/running/semester/list",
            &[("type", "1")],
            "学期列表",
        )?;
        let entry = &semester["data"][0];
        let semester_id = entry["semesterId"]
            .as_str()
            .filter(|value| !value.is_empty())
            .ok_or("学期列表缺少 semesterId")?;
        let semester_name = entry["semesterName"]
            .as_str()
            .filter(|value| !value.trim().is_empty())
            .unwrap_or("本学期")
            .to_owned();

        let range = self
            .post_json("/sports/ranking/getUserInfo", "学期日期")
            .ok()
            .and_then(|value| {
                let item = &value["data"]["semesterDateList"][0];
                let start = server_date(item["startDate"].as_str())?;
                let end = server_date(item["endDate"].as_str())?;
                crate::stats::SemesterRange::new(start, end)
            });

        let records = self.get_json(
            "/sports/running/result/list",
            &[("selectId", semester_id), ("type", "1")],
            "跑步记录",
        )?;
        let mut run_days = HashMap::new();
        for week in records["data"].as_array().into_iter().flatten() {
            for record in week["details"].as_array().into_iter().flatten() {
                let Some(date) = server_date(record["timeFrom"].as_str()) else {
                    continue;
                };
                let state = if counts_toward_score(record.get("state")) {
                    crate::stats::DayState::Valid
                } else {
                    crate::stats::DayState::Invalid
                };
                crate::stats::record_day(&mut run_days, date, state);
            }
        }

        Ok(crate::stats::SemesterStats {
            result_km,
            total_km,
            percent,
            target_km,
            semester_name,
            range,
            run_days,
        })
    }

    fn get_json(&self, path: &str, query: &[(&str, &str)], what: &str) -> Result<Value, String> {
        let mut request = self
            .client
            .get(format!("{}{}", self.base, path))
            .header("Referer", format!("{}/phone/", self.base));
        if !query.is_empty() {
            request = request.query(query);
        }
        decode(checked(request.send())?, what)
    }

    fn post_json(&self, path: &str, what: &str) -> Result<Value, String> {
        let request = self
            .client
            .post(format!("{}{}", self.base, path))
            .header("Referer", format!("{}/phone/", self.base))
            .json(&serde_json::json!({}));
        decode(checked(request.send())?, what)
    }

    pub fn upload(&self, token: &str, payload: &Value) -> Result<(), String> {
        let result: Value = checked(
            self.client
                .post(format!("{}/api/running/result/upload", self.base))
                .header("Authorization", token)
                .header("User-Agent", "okhttp/4.10.0")
                .json(payload)
                .send(),
        )?
        .json()
        .map_err(network_error)?;
        let accepted = match &result["data"] {
            Value::Null => false,
            Value::Bool(value) => *value,
            Value::Number(value) => value.as_f64().is_some_and(|v| v != 0.0),
            Value::String(value) => !value.is_empty(),
            Value::Array(value) => !value.is_empty(),
            Value::Object(value) => !value.is_empty(),
        };
        if result["code"] == 0 && accepted {
            Ok(())
        } else {
            Err(format!(
                "上传未成功（code={}）",
                result["code"]
                    .as_i64()
                    .map(|c| c.to_string())
                    .unwrap_or_else(|| "未知".into())
            ))
        }
    }
}

/// 未登录时这些接口会 302 到登录页，跟随跳转后拿到的是 HTML；
/// 统一识别成「登录状态已过期」，并且绝不把响应正文带进错误信息。
const LOGIN_EXPIRED: &str = "登录状态已过期，请重新登录后重试";

fn decode(response: Response, what: &str) -> Result<Value, String> {
    let url = response.url().to_string();
    if url.contains("/login") || url.contains("jaccount") {
        return Err(format!("{what}：{LOGIN_EXPIRED}"));
    }
    let value: Value = response
        .json()
        .map_err(|_| format!("{what}：{LOGIN_EXPIRED}"))?;
    match value.get("code") {
        None | Some(Value::Null) => {}
        Some(code)
            if code.as_i64() == Some(0)
                || code.as_str() == Some("0")
                || code.as_f64() == Some(0.0) => {}
        _ => return Err(format!("{what}：{LOGIN_EXPIRED}")),
    }
    Ok(value)
}

/// 服务器的数值都是字符串（"80.00"、"100.00"、"80"），偶尔带百分号或千分位。
fn json_number(value: Option<&Value>) -> Option<f64> {
    let raw = match value? {
        Value::Number(number) => number.to_string(),
        Value::String(text) => text.trim().to_owned(),
        _ => return None,
    };
    raw.trim_end_matches('%')
        .replace(',', "")
        .parse::<f64>()
        .ok()
        .filter(|value| value.is_finite())
}

/// 服务器日期形如 `2026-09-19 07:52:19`，只取前 10 个字符；解析不出的记录直接跳过。
fn server_date(text: Option<&str>) -> Option<NaiveDate> {
    let head = text?.get(..10)?;
    NaiveDate::parse_from_str(head, "%Y-%m-%d").ok()
}

/// `state == "0"` 计入成绩，12/13 等是无效记录。
fn counts_toward_score(value: Option<&Value>) -> bool {
    let Some(value) = value else {
        return false;
    };
    match value {
        Value::String(text) => text.trim() == "0",
        Value::Number(number) => number.as_i64() == Some(0),
        _ => false,
    }
}

fn login_failure(result: &Value) -> String {
    let error = result["error"].as_str().unwrap_or_default().to_lowercase();
    if error.contains("captcha") || error.contains("验证码") {
        "图形验证码校验失败，请刷新后重试".into()
    } else if ["password", "account", "密码", "账号", "账户", "用户名"]
        .iter()
        .any(|word| error.contains(word))
    {
        "账号或密码未通过验证，请检查后重试".into()
    } else {
        format!(
            "登录未成功（错误码 {}），请稍后重试",
            result["errno"]
                .as_i64()
                .map(|n| n.to_string())
                .unwrap_or_else(|| "未知".into())
        )
    }
}

fn recognize_captcha_with(client: &Client, endpoint: &str, image: &[u8]) -> Result<String, String> {
    if image.is_empty() || image.len() > 512 * 1024 {
        return Err("验证码图片无效".into());
    }
    let part = reqwest::blocking::multipart::Part::bytes(image.to_vec())
        .file_name("captcha.jpg")
        .mime_str("image/jpeg")
        .map_err(|_| "验证码图片类型无效")?;
    let result: Value = checked(
        client
            .post(endpoint)
            .multipart(reqwest::blocking::multipart::Form::new().part("image", part))
            .send(),
    )?
    .json()
    .map_err(network_error)?;
    result["result"]
        .as_str()
        .map(str::trim)
        .filter(|code| {
            !code.is_empty() && code.len() <= 32 && code.bytes().all(|c| c.is_ascii_alphanumeric())
        })
        .map(str::to_owned)
        .ok_or_else(|| "验证码自动识别未返回有效结果，请刷新重试".into())
}

fn has_auth_cookie(jar: &Jar) -> bool {
    // 认证 Cookie 可能限定在 /jaccount，不能用域名根路径判断登录结果。
    let Ok(url) = format!("{ACCOUNT}/jaccount/").parse() else {
        return false;
    };
    jar.cookies(&url)
        .and_then(|value| {
            value.to_str().ok().map(|text| {
                text.split(';')
                    .any(|cookie| cookie.trim().starts_with("JAAuthCookie="))
            })
        })
        .unwrap_or(false)
}

fn two_factor_context(html: &str, url: &str, json: &Value) -> TwoFactorContext {
    let mut fields = hidden_fields(html);
    for key in [
        "sid",
        "uuid",
        "nextToken",
        "token",
        "csrfToken",
        "execution",
    ] {
        let Some(value) = json
            .get(key)
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|value| !value.is_empty() && value.len() <= 512)
        else {
            continue;
        };
        if !fields.iter().any(|(name, _)| name == key) {
            fields.push((key.to_owned(), value.to_owned()));
        }
    }
    TwoFactorContext {
        account: account_from_url(url)
            .or_else(|| account_from_html(html))
            .or_else(|| account_from_json(json)),
        fields,
        complete_url: Some(url.to_owned()),
    }
}

fn clean_account(text: &str) -> Option<String> {
    let text = text.trim();
    (!text.is_empty()
        && text.len() <= 128
        && !text.contains('*')
        && !text.contains('…')
        && !text.contains("{{")
        && !text.chars().any(char::is_whitespace)
        && !matches!(
            text.to_ascii_lowercase().as_str(),
            "null" | "undefined" | "true" | "false" | "account" | "login"
        ))
    .then(|| text.to_owned())
}

fn account_from_json(value: &Value) -> Option<String> {
    let keys = ["account", "user", "username", "loginName", "login_name"];
    let clean = |value: Option<&Value>| value.and_then(Value::as_str).and_then(clean_account);
    for key in keys {
        if let Some(account) = clean(value.get(key)) {
            return Some(account);
        }
    }
    value["entities"]
        .as_array()
        .into_iter()
        .flatten()
        .find_map(|entity| keys.iter().find_map(|key| clean(entity.get(*key))))
}

fn account_from_url(url: &str) -> Option<String> {
    let url = reqwest::Url::parse(url).ok()?;
    ["account", "user", "username"].iter().find_map(|key| {
        url.query_pairs()
            .find(|(name, _)| name == *key)
            .and_then(|(_, value)| clean_account(&value))
    })
}

fn account_from_html(html: &str) -> Option<String> {
    if html.is_empty() {
        return None;
    }
    let patterns = [
        r#"(?is)<input\b[^>]*\b(?:id|name)\s*=\s*["'](?:account|user|username|loginName)["'][^>]*\bvalue\s*=\s*["']([^"']+)["']"#,
        r#"(?is)<input\b[^>]*\bvalue\s*=\s*["']([^"']+)["'][^>]*\b(?:id|name)\s*=\s*["'](?:account|user|username|loginName)["']"#,
        r#"(?is)\b(?:account|username|user|loginName)\s*[:=]\s*["']([^"']+)["']"#,
        r#"(?is)\bdata-account\s*=\s*["']([^"']+)["']"#,
    ];
    patterns.iter().find_map(|pattern| {
        let regex = Regex::new(pattern).ok()?;
        regex
            .captures(html)
            .and_then(|found| found.get(1))
            .and_then(|value| clean_account(value.as_str()))
            .filter(|value| !value.eq_ignore_ascii_case("null"))
    })
}

fn hidden_fields(html: &str) -> Vec<(String, String)> {
    if html.is_empty() {
        return Vec::new();
    }
    let Ok(inputs) = Regex::new(r"(?is)<input\b[^>]*>") else {
        return Vec::new();
    };
    let Ok(type_hidden) = Regex::new(r#"(?is)\btype\s*=\s*["']hidden["']"#) else {
        return Vec::new();
    };
    let Ok(name_re) = Regex::new(r#"(?is)\bname\s*=\s*["']([^"']+)["']"#) else {
        return Vec::new();
    };
    let Ok(value_re) = Regex::new(r#"(?is)\bvalue\s*=\s*["']([^"']*)["']"#) else {
        return Vec::new();
    };
    let mut fields = Vec::new();
    for input in inputs.find_iter(html) {
        let tag = input.as_str();
        if !type_hidden.is_match(tag) {
            continue;
        }
        let Some(name) = name_re
            .captures(tag)
            .and_then(|found| found.get(1))
            .map(|value| value.as_str().trim())
        else {
            continue;
        };
        let name_lower = name.to_ascii_lowercase();
        if name.is_empty()
            || name.len() > 64
            || matches!(
                name_lower.as_str(),
                "account"
                    | "user"
                    | "username"
                    | "loginname"
                    | "captcha"
                    | "trust"
                    | "pass"
                    | "password"
            )
            // 只回传认证 / CSRF 相关字段，避免把页面上的无关 hidden 值带进验证请求。
            || !["sid", "uuid", "csrf", "token", "execution", "lt", "returl", "client", "se"]
                .iter()
                .any(|key| name_lower.contains(key))
        {
            continue;
        }
        let Some(value) = value_re
            .captures(tag)
            .and_then(|found| found.get(1))
            .map(|value| value.as_str())
        else {
            continue;
        };
        if value.len() > 512 || fields.len() >= 32 {
            continue;
        }
        fields.push((name.to_owned(), value.to_owned()));
    }
    // 部分 2FA 页面把一次性 token 放在内联脚本里，而不是隐藏 input。
    for key in ["sid", "uuid", "csrfToken", "execution", "nextToken"] {
        if fields.iter().any(|(name, _)| name == key) {
            continue;
        }
        let Ok(regex) = Regex::new(&format!(r#"(?is)\b{key}\s*[:=]\s*["']([^"'<>]+)["']"#)) else {
            continue;
        };
        if let Some(value) = regex
            .captures(html)
            .and_then(|found| found.get(1))
            .map(|value| value.as_str().trim())
            .filter(|value| !value.is_empty() && value.len() <= 512)
        {
            fields.push((key.to_owned(), value.to_owned()));
        }
    }
    fields
}

fn two_factor_failure(value: &Value) -> String {
    match value["errno"].as_i64().unwrap_or(-1) {
        4 | 5 => "验证码已过期，请重新发送后再试".into(),
        10002 => "二次验证会话已失效，请取消后重新登录".into(),
        1 => "二次验证未登录或会话已失效，请重新登录".into(),
        code => format!("二次验证失败（错误码 {code}），请重新发送或重新登录"),
    }
}

fn needs_two_factor(text: &str) -> bool {
    ["请进行二次验证", "2faVerify", "2fa/loginVerify"]
        .iter()
        .any(|s| text.contains(s))
}

fn login_fields(html: &str) -> Result<HashMap<String, String>, String> {
    let mut fields = HashMap::new();
    for key in ["sid", "returl", "se", "client"] {
        let regex = Regex::new(&format!(r#"\b{key}\s*:\s*["']([^"']*)["']"#))
            .map_err(|_| "登录解析器初始化失败")?;
        let value = regex
            .captures(html)
            .and_then(|m| m.get(1))
            .ok_or("登录页面格式已变更，请稍后重试")?
            .as_str();
        fields.insert(key.into(), value.into());
    }
    let regex = Regex::new(r#"captcha\?uuid=([^&'"\s]+)"#).map_err(|_| "登录解析器初始化失败")?;
    fields.insert(
        "uuid".into(),
        regex
            .captures(html)
            .and_then(|m| m.get(1))
            .ok_or("登录页面缺少验证码")?
            .as_str()
            .into(),
    );
    Ok(fields)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn recognizes_auth_cookie_with_jaccount_path_scope() {
        let url = format!("{ACCOUNT}/jaccount/ulogin").parse().unwrap();
        let jar = Jar::default();
        jar.add_cookie_str("OtherJAAuthCookie=offline-test-only; Path=/; Secure", &url);
        assert!(!has_auth_cookie(&jar));
        jar.add_cookie_str(
            "JAAuthCookie=offline-test-only; Path=/jaccount; Secure",
            &url,
        );
        assert!(has_auth_cookie(&jar));
    }
    #[test]
    fn parses_login_page_without_logging_secrets() {
        let fields = login_fields(
            r#"sid: "s",returl:"r", se: 'e', client: "c"; img.src='captcha?uuid=example&t='"#,
        )
        .unwrap();
        assert_eq!(fields["uuid"], "example");
        assert_eq!(fields["returl"], "r");
        assert!(login_fields("<html>unexpected</html>").is_err());
        assert!(needs_two_factor("2fa/loginVerify"));
    }
    #[test]
    fn extracts_two_factor_account_and_hidden_fields() {
        let html = r#"
            <form action="/jaccount/2faVerify" method="post">
              <input type="hidden" name="sid" value="offline-test-only">
              <input type="hidden" name="account" value="student@sjtu.edu.cn">
              <input type="hidden" name="csrfToken" value="token">
              <input type="hidden" name="password" value="must-not-be-forwarded">
              <input type="text" name="captcha" value="">
            </form>
            <script>var loginContext = { account: "script-account" };</script>
        "#;
        let context = two_factor_context(
            html,
            "https://jaccount.sjtu.edu.cn/jaccount/2fa/login",
            &Value::Null,
        );
        assert_eq!(context.account.as_deref(), Some("student@sjtu.edu.cn"));
        assert!(context
            .fields
            .iter()
            .any(|(name, value)| name == "sid" && value == "offline-test-only"));
        assert!(context
            .fields
            .iter()
            .any(|(name, value)| name == "csrfToken" && value == "token"));
        assert!(!context.fields.iter().any(|(name, _)| name == "account"));
        assert!(!context.fields.iter().any(|(name, _)| name == "password"));
    }

    #[test]
    fn two_factor_context_extracts_json_account_and_maps_errors() {
        let json = serde_json::json!({"account": "json-account", "nextToken": "token"});
        let context = two_factor_context("", "https://jaccount.sjtu.edu.cn/jaccount/2fa", &json);
        assert_eq!(context.account.as_deref(), Some("json-account"));
        assert_eq!(
            context.complete_url.as_deref(),
            Some("https://jaccount.sjtu.edu.cn/jaccount/2fa")
        );
        assert!(two_factor_failure(&serde_json::json!({"errno": 4})).contains("过期"));
        assert!(two_factor_failure(&serde_json::json!({"errno": 10002})).contains("会话已失效"));
        assert!(two_factor_failure(&serde_json::json!({"errno": 7})).contains("错误码 7"));
    }

    #[test]
    fn verification_uses_page_account_and_hidden_fields() {
        let (session, server) = mock(vec![(200, r#"{"errno":0}"#), (200, "<html>done</html>")]);
        let base = session.base.clone();
        session.jar.add_cookie_str(
            "JAAuthCookie=offline-test-only; Path=/jaccount; Secure",
            &format!("{ACCOUNT}/jaccount/").parse().unwrap(),
        );
        *session.two_factor.lock().unwrap() = Some(TwoFactorContext {
            account: Some("page-account".into()),
            fields: vec![("sid".into(), "offline-sid".into())],
            complete_url: Some(format!("{base}/jaccount/complete")),
        });
        session
            .verify_code_at(&base, "typed-account", "123456")
            .unwrap();
        let requests = server.join().unwrap();
        assert_eq!(requests.len(), 2);
        assert!(requests[0].starts_with("POST /jaccount/2faVerify "));
        let body = requests[0].split("\r\n\r\n").nth(1).unwrap();
        let fields: HashMap<_, _> = reqwest::Url::parse(&format!("http://localhost/?{body}"))
            .unwrap()
            .query_pairs()
            .into_owned()
            .collect();
        assert_eq!(fields["account"], "page-account");
        assert_eq!(fields["captcha"], "123456");
        assert_eq!(fields["trust"], "true");
        assert_eq!(fields["sid"], "offline-sid");
        assert!(!body.contains("typed-account"));
        assert!(requests[1].starts_with("GET /jaccount/complete "));
    }

    #[test]
    fn rejects_invalid_verification_input_without_network() {
        let session = Session::new().unwrap();
        assert!(session.send_code("other").is_err());
        for code in ["", "12345", "abcdef", "1234567"] {
            assert!(session.verify_code("", code).is_err());
        }
    }

    fn challenge(session: Session) -> LoginChallenge {
        LoginChallenge {
            session,
            fields: HashMap::from([("uuid".into(), "offline-test-only".into())]),
            image: Vec::new(),
        }
    }

    #[test]
    fn password_login_uses_ajax_and_follows_returned_url() {
        let (session, server) = mock(vec![
            (200, r#"{"errno":0,"url":"/complete-login"}"#),
            (200, "<html>Portal</html>"),
        ]);
        let account = session.base.clone();
        session.jar.add_cookie_str(
            "JAAuthCookie=offline-test-only; Path=/jaccount; Secure",
            &format!("{ACCOUNT}/jaccount/").parse().unwrap(),
        );
        assert!(matches!(
            Session::login_at(
                challenge(session),
                "test-user",
                "test-password",
                "Ab12",
                &account
            ),
            Ok(LoginResult::Authenticated(_))
        ));
        let requests = server.join().unwrap();
        assert_eq!(requests.len(), 2);
        assert!(requests[0].starts_with("POST /jaccount/ulogin "));
        let headers = requests[0].to_ascii_lowercase();
        assert!(headers.contains("x-requested-with: xmlhttprequest\r\n"));
        assert!(headers.contains(&format!("referer: {account}\r\n")));
        let body = requests[0].split("\r\n\r\n").nth(1).unwrap();
        let fields: HashMap<_, _> = reqwest::Url::parse(&format!("http://localhost/?{body}"))
            .unwrap()
            .query_pairs()
            .into_owned()
            .collect();
        assert_eq!(fields["lt"], "p");
        assert_eq!(fields["user"], "test-user");
        assert_eq!(fields["pass"], "test-password");
        assert_eq!(fields["captcha"], "Ab12");
        assert_eq!(fields["uuid"], "offline-test-only");
        assert!(requests[1].starts_with("GET /complete-login "));
    }

    #[test]
    fn password_login_preserves_two_factor_session() {
        let (session, server) = mock(vec![
            (200, r#"{"errno":0,"url":"/jaccount/2faVerify"}"#),
            (
                200,
                r#"<html>2fa/loginVerify
                    <input type="hidden" name="account" value="page-account">
                    <input type="hidden" name="sid" value="offline-sid">
                </html>"#,
            ),
        ]);
        let account = session.base.clone();
        let result = Session::login_at(
            challenge(session),
            "test-user",
            "test-password",
            "Ab12",
            &account,
        )
        .unwrap();
        let LoginResult::TwoFactor(session) = result else {
            panic!("应识别为二次验证");
        };
        let context = session.two_factor.lock().unwrap().clone().unwrap();
        assert_eq!(context.account.as_deref(), Some("page-account"));
        let requests = server.join().unwrap();
        assert_eq!(requests.len(), 2);
        assert!(requests[1].starts_with("GET /jaccount/2faVerify "));
    }

    #[test]
    fn password_login_captures_two_factor_page_fields() {
        let (session, server) = mock(vec![(
            200,
            r#"<html>2fa/loginVerify
                <input type="hidden" name="sid" value="offline-sid">
                <input type="hidden" name="account" value="page-account">
                <input type="hidden" name="csrfToken" value="offline-token">
            </html>"#,
        )]);
        let account = session.base.clone();
        let result = Session::login_at(
            challenge(session),
            "typed-account",
            "test-password",
            "Ab12",
            &account,
        )
        .unwrap();
        let LoginResult::TwoFactor(session) = result else {
            panic!("应识别为二次验证");
        };
        let context = session.two_factor.lock().unwrap().clone().unwrap();
        assert_eq!(context.account.as_deref(), Some("page-account"));
        assert!(context.fields.iter().any(|(name, _)| name == "sid"));
        assert!(context.fields.iter().any(|(name, _)| name == "csrfToken"));
        assert_eq!(server.join().unwrap().len(), 1);
    }

    #[test]
    fn password_login_rejects_failures_without_disclosing_response() {
        for (body, expected) in [
            (
                r#"{"errno":1,"error":"Wrong captcha private-response"}"#,
                "图形验证码校验失败",
            ),
            (
                r#"{"errno":2,"error":"Wrong password private-response"}"#,
                "账号或密码未通过验证",
            ),
            (r#"{"errno":3,"error":"private-response"}"#, "错误码 3"),
            (r#"{"errno":0}"#, "缺少跳转地址"),
            (
                r#"{"errno":0,"url":"https://untrusted.invalid/private-response"}"#,
                "未知跳转地址",
            ),
            ("<html>Login page private-response</html>", "登录未成功"),
        ] {
            let (session, server) = mock(vec![(200, body)]);
            let account = session.base.clone();
            let error = Session::login_at(
                challenge(session),
                "test-user",
                "test-password",
                "Ab12",
                &account,
            )
            .err()
            .unwrap();
            assert!(error.contains(expected));
            assert!(!error.contains("private-response"));
            assert!(!error.contains("test-password"));
            assert_eq!(server.join().unwrap().len(), 1);
        }
    }

    fn mock<B: AsRef<[u8]> + Send + 'static>(
        responses: Vec<(u16, B)>,
    ) -> (Session, std::thread::JoinHandle<Vec<String>>) {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let mut session = Session::new().unwrap();
        session.base = format!("http://{}", listener.local_addr().unwrap());
        session.client = Client::builder()
            .no_proxy()
            .timeout(Duration::from_secs(2))
            .build()
            .unwrap();
        let handle = std::thread::spawn(move || {
            let mut requests = Vec::new();
            for (status, body) in responses {
                let body = body.as_ref();
                let (mut stream, _) = listener.accept().unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(2)))
                    .unwrap();
                let mut request = Vec::new();
                let mut buf = [0u8; 4096];
                loop {
                    let count = stream.read(&mut buf).unwrap();
                    if count == 0 {
                        break;
                    }
                    request.extend_from_slice(&buf[..count]);
                    if let Some(end) = request.windows(4).position(|s| s == b"\r\n\r\n") {
                        let headers = String::from_utf8_lossy(&request[..end]).to_ascii_lowercase();
                        let length = headers
                            .lines()
                            .find_map(|l| {
                                l.strip_prefix("content-length:")
                                    .and_then(|s| s.trim().parse::<usize>().ok())
                            })
                            .unwrap_or(0);
                        if request.len() >= end + 4 + length {
                            break;
                        }
                    }
                }
                requests.push(String::from_utf8_lossy(&request).into_owned());
                write!(stream,"HTTP/1.1 {status} Mock\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",body.len()).unwrap();
                stream.write_all(body).unwrap();
            }
            requests
        });
        (session, handle)
    }

    fn captcha_image() -> Vec<u8> {
        let image = image::RgbImage::from_fn(110, 40, |x, y| {
            image::Rgb(if (x / 10 + y / 10) % 2 == 0 {
                [232, 241, 235]
            } else {
                [35, 104, 73]
            })
        });
        let mut buffer = std::io::Cursor::new(Vec::new());
        image::DynamicImage::ImageRgb8(image)
            .write_to(&mut buffer, image::ImageFormat::Jpeg)
            .unwrap();
        buffer.into_inner()
    }

    #[test]
    fn captcha_request_preserves_referer_and_validates_image() {
        let (session, server) = mock(vec![(200, captcha_image())]);
        let image = session.fetch_captcha(&session.base, "test-only").unwrap();
        assert_eq!(image::load_from_memory(&image).unwrap().width(), 110);
        let requests = server.join().unwrap();
        assert!(requests[0].starts_with("GET /jaccount/captcha?uuid=test-only&t="));
        assert!(requests[0]
            .to_ascii_lowercase()
            .contains(&format!("referer: {}\r\n", session.base)));
        let (session, server) = mock(vec![(403, "")]);
        assert_eq!(
            session
                .fetch_captcha(&session.base, "test-only")
                .unwrap_err(),
            "服务器返回 HTTP 403"
        );
        server.join().unwrap();
        let (session, server) = mock(vec![(200, "private-html-response")]);
        let error = session
            .fetch_captcha(&session.base, "test-only")
            .unwrap_err();
        assert!(error.contains("有效图片"));
        assert!(!error.contains("private-html-response"));
        server.join().unwrap();
    }

    #[test]
    fn recognition_matches_legacy_multipart_without_credentials() {
        let (session, server) = mock(vec![(200, r#"{"result":" Ab12 "}"#)]);
        assert_eq!(
            recognize_captcha_with(&session.client, &session.base, &captcha_image()).unwrap(),
            "Ab12"
        );
        let request = server.join().unwrap().remove(0);
        assert!(request.starts_with("POST / HTTP/1.1"));
        assert!(request.contains("name=\"image\"; filename=\"captcha.jpg\""));
        assert!(request.contains("image/jpeg"));
        let headers = request
            .split("\r\n\r\n")
            .next()
            .unwrap()
            .to_ascii_lowercase();
        assert!(!headers.contains("cookie:"));
        assert!(!headers.contains("authorization:"));
        assert!(!request.contains("name=\"user\""));
        assert!(!request.contains("name=\"pass\""));
    }

    #[test]
    fn recognition_rejects_missing_or_invalid_results() {
        for body in [
            r#"{}"#,
            r#"{"result":""}"#,
            r#"{"result":null}"#,
            r#"{"result":"<private-response>"}"#,
        ] {
            let (session, server) = mock(vec![(200, body)]);
            let error = recognize_captcha_with(&session.client, &session.base, &captcha_image())
                .unwrap_err();
            assert!(error.contains("有效结果"));
            assert!(!error.contains("private-response"));
            server.join().unwrap();
        }
    }

    #[test]
    #[ignore = "访问现有登录与识别服务，仅获取匿名验证码，不进行账号登录"]
    fn live_captcha_can_be_loaded_and_recognized() {
        let challenge = Session::prepare_login().unwrap();
        let image = image::load_from_memory(&challenge.image).unwrap();
        assert!(image.width() > 0 && image.height() > 0);
        assert!(!Session::recognize_captcha(&challenge.image)
            .unwrap()
            .is_empty());
    }

    #[test]
    fn authorization_and_upload_use_expected_endpoints_and_json() {
        let (session, server) = mock(vec![
            (200, r#"{"code":0,"data":{"uid":"offline-test-only"}}"#),
            (200, r#"{"code":0}"#),
            (200, r#"{"code":0,"data":{"rules":{"id":9}}}"#),
            (200, r#"{"code":0,"data":true}"#),
        ]);
        let (token, rules) = session.authorize(&AtomicBool::new(false)).unwrap();
        assert_eq!(rules["rules"]["id"], 9);
        session
            .upload(&token, &serde_json::json!([{ "test":true }]))
            .unwrap();
        let requests = server.join().unwrap();
        assert!(requests[0].starts_with("GET /sports/my/uid "));
        assert!(requests[2].starts_with("GET /api/running/point-rule?location="));
        assert!(requests[3].starts_with("POST /api/running/result/upload "));
        assert!(requests[3].contains(r#"[{"test":true}]"#));
        assert!(requests[3]
            .to_ascii_lowercase()
            .contains("content-type: application/json"));
    }

    fn offline_date(year: i32, month: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(year, month, day).unwrap()
    }

    fn offline_stats_fixture() -> Vec<(u16, &'static str)> {
        vec![
            (
                200,
                r#"{"code":0,"data":[{"totalKm":"91.22","percent":"100.00","resultKm":"80.00"}]}"#,
            ),
            (200, r#"{"code":0,"data":{"target":"80"}}"#),
            (
                200,
                r#"{"code":0,"data":[{"semesterId":"offline-test-only","semesterName":"本学期"}]}"#,
            ),
            (
                200,
                r#"{"code":0,"data":{"semesterDateList":[{"name":"本学期","startDate":"2026-09-14 00:00:00","endDate":"2027-01-03 23:59:59"}]}}"#,
            ),
            (
                200,
                r#"{"code":0,"data":[{"allName":"第一周","details":[{"timeFrom":"2026-09-19 07:52:19","duration":"1200","state":"0"},{"timeFrom":"2026-09-20 08:01:02","duration":"900","state":"12"}]}]}"#,
            ),
        ]
    }

    #[test]
    fn semester_stats_uses_fixed_endpoint_order_and_marks_record_states() {
        let (session, server) = mock(offline_stats_fixture());
        let stats = session.semester_stats().unwrap();
        assert_eq!(stats.result_km, Some(80.0));
        assert_eq!(stats.total_km, Some(91.22));
        assert_eq!(stats.percent, Some(100.0));
        assert_eq!(stats.target_km, Some(80.0));
        assert_eq!(stats.semester_name, "本学期");
        let range = stats.range.expect("夹具里有学期起止日期");
        assert_eq!(range.start, offline_date(2026, 9, 14));
        assert_eq!(range.end, offline_date(2027, 1, 3));
        assert_eq!(stats.run_days.len(), 2);
        assert_eq!(
            stats.run_days[&offline_date(2026, 9, 19)],
            crate::stats::DayState::Valid
        );
        assert_eq!(
            stats.run_days[&offline_date(2026, 9, 20)],
            crate::stats::DayState::Invalid
        );
        let requests = server.join().unwrap();
        assert_eq!(requests.len(), 5);
        assert!(requests[0].starts_with("GET /sports/my/data "));
        assert!(requests[1].starts_with("GET /sports/my/semesterTarget "));
        assert!(requests[2].starts_with("GET /sports/running/semester/list?type=1 "));
        assert!(requests[3].starts_with("POST /sports/ranking/getUserInfo "));
        assert!(requests[3]
            .to_ascii_lowercase()
            .contains("content-type: application/json"));
        assert!(requests[4]
            .starts_with("GET /sports/running/result/list?selectId=offline-test-only&type=1 "));
    }

    #[test]
    fn semester_stats_keeps_valid_record_when_a_day_also_has_an_invalid_one() {
        let mut fixture = offline_stats_fixture();
        fixture[4] = (
            200,
            r#"{"code":0,"data":[{"details":[{"timeFrom":"2026-09-19 07:00:00","state":"13"},{"timeFrom":"2026-09-19 21:00:00","state":"0"},{"timeFrom":"坏日期","state":"0"}]}]}"#,
        );
        let (session, server) = mock(fixture);
        let stats = session.semester_stats().unwrap();
        assert_eq!(stats.run_days.len(), 1);
        assert_eq!(
            stats.run_days[&offline_date(2026, 9, 19)],
            crate::stats::DayState::Valid
        );
        server.join().unwrap();
    }

    #[test]
    fn semester_stats_derives_percent_when_the_server_omits_it() {
        let mut fixture = offline_stats_fixture();
        fixture[0] = (
            200,
            r#"{"code":0,"data":[{"totalKm":"50.00","resultKm":"40.00"}]}"#,
        );
        let (session, server) = mock(fixture);
        let stats = session.semester_stats().unwrap();
        assert_eq!(stats.percent, Some(80.0));
        assert_eq!(crate::stats::format_percent(stats.percent), "80.0%");
        server.join().unwrap();

        let mut fixture = offline_stats_fixture();
        fixture[0] = (200, r#"{"code":0,"data":[{"totalKm":"0","resultKm":"0"}]}"#);
        let (session, server) = mock(fixture);
        let stats = session.semester_stats().unwrap();
        assert_eq!(stats.percent, None);
        assert_eq!(crate::stats::format_percent(stats.percent), "--");
        server.join().unwrap();
    }

    #[test]
    fn semester_stats_treats_non_json_or_error_code_as_expired_session() {
        let (session, server) = mock(vec![(200, "<html>private-response-body</html>")]);
        let error = session.semester_stats().unwrap_err();
        assert!(error.contains("过期"));
        assert!(!error.contains("private-response-body"));
        server.join().unwrap();

        let (session, server) = mock(vec![(
            200,
            r#"{"code":1,"message":"private-response-body"}"#,
        )]);
        let error = session.semester_stats().unwrap_err();
        assert!(error.contains("过期"));
        assert!(!error.contains("private-response-body"));
        server.join().unwrap();
    }

    #[test]
    fn semester_stats_requires_semester_id_before_fetching_records() {
        let mut fixture = offline_stats_fixture();
        fixture[2] = (200, r#"{"code":0,"data":[]}"#);
        fixture.truncate(3);
        let (session, server) = mock(fixture);
        let error = session.semester_stats().unwrap_err();
        assert!(error.contains("semesterId"));
        let requests = server.join().unwrap();
        assert_eq!(requests.len(), 3);
    }

    #[test]
    fn semester_stats_reports_expired_session_after_login_redirect() {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let mut session = Session::new().unwrap();
        session.base = format!("http://{}", listener.local_addr().unwrap());
        session.client = Client::builder()
            .no_proxy()
            .timeout(Duration::from_secs(2))
            .build()
            .unwrap();
        let handle = std::thread::spawn(move || {
            let mut requests = Vec::new();
            for index in 0..2 {
                let (mut stream, _) = listener.accept().unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(2)))
                    .unwrap();
                let mut raw = Vec::new();
                let mut buf = [0u8; 4096];
                loop {
                    let count = stream.read(&mut buf).unwrap();
                    if count == 0 {
                        break;
                    }
                    raw.extend_from_slice(&buf[..count]);
                    if raw.windows(4).any(|slice| slice == b"\r\n\r\n") {
                        break;
                    }
                }
                requests.push(String::from_utf8_lossy(&raw).into_owned());
                let body: &[u8] = if index == 0 {
                    b"redirecting"
                } else {
                    b"<html>private-login-page</html>"
                };
                let head = if index == 0 {
                    "HTTP/1.1 302 Found\r\nLocation: /login\r\n"
                } else {
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                };
                write!(
                    stream,
                    "{head}Content-Length: {}\r\nConnection: close\r\n\r\n",
                    body.len()
                )
                .unwrap();
                stream.write_all(body).unwrap();
            }
            requests
        });
        let error = session.semester_stats().unwrap_err();
        assert!(error.contains("过期"));
        assert!(!error.contains("private-login-page"));
        let requests = handle.join().unwrap();
        assert_eq!(requests.len(), 2);
        assert!(requests[1].starts_with("GET /login "));
    }

    #[test]
    fn server_failures_do_not_expose_response_or_sensitive_query() {
        let (session, server) = mock(vec![(
            200,
            r#"{"code":0,"data":false,"message":"private-response-body"}"#,
        )]);
        let error = session
            .upload("offline-test-only", &serde_json::json!([]))
            .unwrap_err();
        assert!(!error.contains("private-response-body"));
        assert!(!error.contains("offline-test-only"));
        server.join().unwrap();
        let (session, server) = mock(vec![(500, "private-response-body")]);
        assert_eq!(
            session.authorize(&AtomicBool::new(false)).unwrap_err(),
            "服务器返回 HTTP 500"
        );
        server.join().unwrap();
        let (session, server) = mock(vec![(200, "invalid json")]);
        assert!(session
            .authorize(&AtomicBool::new(false))
            .unwrap_err()
            .contains("无法解析"));
        server.join().unwrap();
    }

    #[test]
    fn cancellation_after_first_response_prevents_followup_requests() {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let mut session = Session::new().unwrap();
        session.base = format!("http://{}", listener.local_addr().unwrap());
        session.client = Client::builder()
            .no_proxy()
            .timeout(Duration::from_secs(2))
            .build()
            .unwrap();
        let cancel = Arc::new(AtomicBool::new(false));
        let server_cancel = cancel.clone();
        let server = std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buf = [0u8; 4096];
            let count = stream.read(&mut buf).unwrap();
            assert!(count > 0);
            server_cancel.store(true, Ordering::Relaxed);
            let body = r#"{"code":0,"data":{"uid":"offline-test-only"}}"#;
            write!(stream,"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len()).unwrap();
        });
        assert_eq!(session.authorize(&cancel).unwrap_err(), "任务已停止");
        server.join().unwrap();
    }
}
