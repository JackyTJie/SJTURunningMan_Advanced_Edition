//! Tauri 适配层：把现有 Rust 业务模块接到 React 界面。
//!
//! 这里只做参数校验、状态编排、后台线程与事件派发。轨迹生成、网络请求、
//! 路线解析、统计口径仍然完全留在各自的业务模块里。

use crate::{
    api::{LoginChallenge, LoginResult, Session},
    maps::MapServer,
    preview,
    route::{self, Point, Route},
    settings::{self, RunConfig, Settings},
    stats::{self, CalendarWeek, DayState, SemesterStats},
    task::{self, Event, Preview},
    update,
};
use serde::{Deserialize, Serialize};
use std::{
    collections::HashSet,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex, MutexGuard,
    },
    time::{Duration, Instant},
};
use tauri::{AppHandle, Emitter, Manager, State, WindowEvent};

const APP_VERSION: &str = env!("APP_VERSION");

// ---------------------------------------------------------------------------
// 状态
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq)]
struct PreviewInputs {
    runs: String,
    distance: String,
    date: String,
    time: String,
    route: String,
}

pub struct AppState {
    dir: PathBuf,
    maps: Option<MapServer>,
    map_output: Option<PathBuf>,
    routes: Vec<Route>,
    selected: usize,
    preview: Option<Preview>,
    preview_inputs: Option<PreviewInputs>,
    session: Option<Session>,
    challenge: Option<LoginChallenge>,
    /// 正在等待手机确认的扫码登录；`qr_generation` 用来丢弃上一轮扫码的迟到事件。
    qr_cancel: Option<Arc<AtomicBool>>,
    qr_generation: u64,
    two_factor: Option<Session>,
    user: String,
    cancel: Arc<AtomicBool>,
    busy: bool,
    close_after_stop: bool,
    verification_attempts: u8,
    /// 每次登录 / 退出都递增，晚到的学期响应只有序号匹配才允许写回。
    session_serial: u64,
    stats: Option<SemesterStats>,
    /// 客户端自动填进输入框的（次数, 距离），用来分辨「用户手改过」。
    auto_plan: Option<(String, String)>,
    /// 只在登录 / 二次验证之后的那次学期响应里自动排计划。
    auto_adjust_pending: bool,
    /// 损坏且无法备份的设置文件不要被后续自动保存覆盖。
    preserve_settings: bool,
    startup_warning: Option<String>,
    startup_logs: Vec<String>,
    /// `--ui-smoke-test` 的输出目录；正常启动为 None。
    smoke_output: Option<PathBuf>,
}

impl AppState {
    fn selected_route(&self) -> Result<Route, String> {
        self.routes
            .get(self.selected)
            .cloned()
            .ok_or_else(|| "请选择有效路线".into())
    }

    fn route_by_name(&self, name: &str) -> Result<(usize, Route), String> {
        self.routes
            .iter()
            .enumerate()
            .find(|(_, route)| route.name == name)
            .map(|(index, route)| (index, route.clone()))
            .ok_or_else(|| "请选择有效路线".into())
    }

    fn reload_routes(&mut self, select: &str) -> Result<Vec<String>, String> {
        let (routes, skipped) = route::list(&self.dir)?;
        self.routes = routes;
        self.selected = self
            .routes
            .iter()
            .position(|route| route.name == select)
            .unwrap_or(0);
        self.preview = None;
        self.preview_inputs = None;
        Ok(skipped)
    }

    fn clear_preview(&mut self) {
        self.preview = None;
        self.preview_inputs = None;
    }

    /// 停止扫码登录的订阅线程；线程会在下一次读超时后自行退出。
    /// 同时递增序号，上一轮扫码的迟到事件不会再写回界面。
    fn stop_qr(&mut self) {
        if let Some(cancel) = self.qr_cancel.take() {
            cancel.store(true, Ordering::Relaxed);
        }
        self.qr_generation += 1;
    }
}

fn lock<'a>(state: &'a State<'_, Mutex<AppState>>) -> Result<MutexGuard<'a, AppState>, String> {
    state
        .lock()
        .map_err(|_| "应用状态不可用，请重启程序".to_string())
}

// ---------------------------------------------------------------------------
// 传给界面的数据
// ---------------------------------------------------------------------------

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsView {
    dark: bool,
    runs: String,
    distance: String,
    time: String,
    route: String,
    skip_existing: bool,
}

impl From<&Settings> for SettingsView {
    fn from(value: &Settings) -> Self {
        Self {
            dark: value.dark,
            runs: value.runs.clone(),
            distance: value.distance.clone(),
            time: value.time.clone(),
            route: value.route.clone(),
            skip_existing: value.skip_existing,
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RouteView {
    name: String,
    imported: bool,
    can_delete: bool,
    distance_km: f64,
    point_count: usize,
}

impl From<&Route> for RouteView {
    fn from(value: &Route) -> Self {
        Self {
            name: value.name.clone(),
            imported: value.path.is_some(),
            can_delete: value.path.is_some(),
            distance_km: route::distance(&value.points) / 1_000.0,
            point_count: value.points.len(),
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RouteDetail {
    name: String,
    imported: bool,
    can_delete: bool,
    points: Vec<Point>,
    distance_km: f64,
    point_count: usize,
    jumps: usize,
    jump_segments: Vec<usize>,
    warning: Option<String>,
}

impl From<&Route> for RouteDetail {
    fn from(value: &Route) -> Self {
        let jumps = route::jumps(&value.points);
        Self {
            name: value.name.clone(),
            imported: value.path.is_some(),
            can_delete: value.path.is_some(),
            points: value.points.clone(),
            distance_km: route::distance(&value.points) / 1_000.0,
            point_count: value.points.len(),
            jumps,
            jump_segments: jump_segments(&value.points),
            warning: if jumps > 0 {
                Some(format!("发现 {jumps} 个超过 150 m 的跳段，请检查后再使用"))
            } else {
                None
            },
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CalendarDayView {
    day: u8,
    state: &'static str,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CalendarWeekView {
    title: String,
    days: [CalendarDayView; 7],
}

fn day_code(state: DayState) -> &'static str {
    match state {
        DayState::None => "none",
        DayState::Valid => "valid",
        DayState::Invalid => "invalid",
    }
}

fn calendar_view(weeks: &[CalendarWeek]) -> Vec<CalendarWeekView> {
    weeks
        .iter()
        .map(|week| CalendarWeekView {
            title: week.title.clone(),
            days: std::array::from_fn(|index| CalendarDayView {
                day: week.days[index].day,
                state: day_code(week.days[index].state),
            }),
        })
        .collect()
}

fn placeholder_calendar() -> Vec<CalendarWeekView> {
    calendar_view(&stats::placeholder_weeks(stats::today_cst()))
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Bootstrap {
    version: String,
    date: String,
    settings: SettingsView,
    routes: Vec<RouteView>,
    selected: RouteDetail,
    calendar: Vec<CalendarWeekView>,
    semester_km: String,
    semester_percent: String,
    warning: Option<String>,
    logs: Vec<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PreviewView {
    summary: String,
    distance_m: f64,
    duration_s: i64,
    points: Vec<Point>,
    jump_segments: Vec<usize>,
}

fn preview_summary(data: &Preview) -> String {
    format!(
        "实际轨迹 {:.2} km · {} 分 {:02} 秒 · {} 个点",
        data.distance_m / 1_000.0,
        data.duration_s / 60,
        data.duration_s % 60,
        data.points.len()
    )
}

impl From<&Preview> for PreviewView {
    fn from(value: &Preview) -> Self {
        Self {
            summary: preview_summary(value),
            distance_m: value.distance_m,
            duration_s: value.duration_s,
            points: value.points.clone(),
            jump_segments: jump_segments(&value.points),
        }
    }
}

/// 供前端把超过 150 m 的跳段标成错误色。阈值与旧版离线预览一致。
fn jump_segments(points: &[Point]) -> Vec<usize> {
    points
        .windows(2)
        .enumerate()
        .filter(|(_, pair)| route::haversine(pair[0], pair[1]) > 150.0)
        .map(|(index, _)| index + 1)
        .collect()
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RouteListResult {
    routes: Vec<RouteView>,
    selected: RouteDetail,
    selected_name: String,
    logs: Vec<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LoginPreparation {
    captcha: String,
    /// 自动识别成功时由界面暂存，提交登录时原样带回；不写日志、不落盘。
    captcha_code: Option<String>,
    manual: bool,
    notice: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct QrPreparation {
    /// 本轮扫码的序号；界面只用序号相同的事件。
    generation: u64,
    /// 二维码图片的 data URL。
    qr: String,
    notice: String,
}

/// 扫码登录的后台线程通过事件推给界面：换码、登录成功、需要二次验证或失败。
#[derive(Clone, Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum QrEvent {
    Image {
        generation: u64,
        qr: String,
    },
    Authenticated {
        generation: u64,
        user: String,
        notice: String,
    },
    TwoFactor {
        generation: u64,
        user: String,
        notice: String,
    },
    Failed {
        generation: u64,
        message: String,
    },
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthOutcome {
    stage: &'static str,
    user: String,
    notice: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VerifyOutcome {
    verified: bool,
    locked: bool,
    message: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PlanView {
    runs: String,
    distance: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct StatsPayload {
    km: String,
    percent: String,
    weeks: Option<Vec<CalendarWeekView>>,
    run_days: usize,
    plan: Option<PlanView>,
    logs: Vec<String>,
    notice: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LogoutResult {
    weeks: Vec<CalendarWeekView>,
    km: String,
    percent: String,
    notice: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TaskStarted {
    count: usize,
    skipped: usize,
    truncated: bool,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MapOpenResult {
    notice: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PreviewMapResult {
    url: String,
    notice: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PreviewRequest {
    runs: String,
    distance: String,
    date: String,
    time: String,
    route: String,
}

impl PreviewRequest {
    fn inputs(&self) -> PreviewInputs {
        PreviewInputs {
            runs: self.runs.clone(),
            distance: self.distance.clone(),
            date: self.date.clone(),
            time: self.time.clone(),
            route: self.route.clone(),
        }
    }

    fn config(&self) -> Result<RunConfig, String> {
        RunConfig::parse(&self.runs, &self.distance, &self.date, &self.time)
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsInput {
    dark: bool,
    runs: String,
    distance: String,
    time: String,
    route: String,
    skip_existing: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TaskRequest {
    runs: String,
    distance: String,
    date: String,
    time: String,
    route: String,
    skip_existing: bool,
}

// ---------------------------------------------------------------------------
// 事件负载
// ---------------------------------------------------------------------------

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct LogPayload {
    message: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProgressPayload {
    value: i32,
    status: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct StatusPayload {
    status: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct FinishedPayload {
    success: u32,
    failed: u32,
    stopped: bool,
    status: String,
    progress: i32,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ErrorPayload {
    message: String,
    status: String,
}

fn maybe_exit(app: &AppHandle) {
    let state = app.state::<Mutex<AppState>>();
    let Ok(mut app_state) = state.lock() else {
        return;
    };
    if !app_state.close_after_stop {
        return;
    }
    app_state.close_after_stop = false;
    drop(app_state);
    app.exit(0);
}

// ---------------------------------------------------------------------------
// 启动数据
// ---------------------------------------------------------------------------

#[tauri::command]
pub fn bootstrap(state: State<'_, Mutex<AppState>>) -> Result<Bootstrap, String> {
    let app = lock(&state)?;
    let selected = app.selected_route()?;
    // 前端只需要持久化过的部分；这里从磁盘再读一次，避免把默认值当成用户设置。
    let stored = settings::load(&app.dir).unwrap_or_default();
    let settings = SettingsView::from(&stored);
    Ok(Bootstrap {
        version: format!("v{APP_VERSION}"),
        date: settings::yesterday(),
        settings,
        routes: app.routes.iter().map(RouteView::from).collect(),
        selected: RouteDetail::from(&selected),
        calendar: placeholder_calendar(),
        semester_km: "--".into(),
        semester_percent: "--".into(),
        warning: app.startup_warning.clone(),
        logs: app.startup_logs.clone(),
    })
}

#[tauri::command]
pub fn select_route(
    state: State<'_, Mutex<AppState>>,
    name: String,
) -> Result<RouteDetail, String> {
    let mut app = lock(&state)?;
    let (index, route) = app.route_by_name(&name)?;
    app.selected = index;
    app.clear_preview();
    Ok(RouteDetail::from(&route))
}

#[tauri::command]
pub fn preview_route(
    state: State<'_, Mutex<AppState>>,
    request: PreviewRequest,
) -> Result<PreviewView, String> {
    let config = request.config()?;
    let mut app = lock(&state)?;
    let (_, route) = app.route_by_name(&request.route)?;
    let data = task::generate(
        &route.points,
        &config,
        "preview",
        chrono::Utc::now().timestamp_millis(),
        &serde_json::json!({}),
    )?;
    app.selected = app
        .routes
        .iter()
        .position(|item| item.name == request.route)
        .unwrap_or(app.selected);
    app.preview = Some(data.clone());
    app.preview_inputs = Some(request.inputs());
    Ok(PreviewView::from(&data))
}

#[tauri::command]
pub fn import_route(
    state: State<'_, Mutex<AppState>>,
    path: String,
) -> Result<RouteListResult, String> {
    let mut app = lock(&state)?;
    let name = route::import(&app.dir, Path::new(&path))?;
    let logs = app.reload_routes(&name)?;
    let selected = app.selected_route()?;
    Ok(RouteListResult {
        routes: app.routes.iter().map(RouteView::from).collect(),
        selected: RouteDetail::from(&selected),
        selected_name: selected.name.clone(),
        logs,
    })
}

#[tauri::command]
pub fn delete_route(
    state: State<'_, Mutex<AppState>>,
    name: String,
) -> Result<RouteListResult, String> {
    let mut app = lock(&state)?;
    if app.busy {
        return Err("任务运行中不能删除路线".into());
    }
    let (_, route) = app.route_by_name(&name)?;
    route::delete(&app.dir, &route)?;
    let logs = app.reload_routes("default")?;
    let selected = app.selected_route()?;
    Ok(RouteListResult {
        routes: app.routes.iter().map(RouteView::from).collect(),
        selected: RouteDetail::from(&selected),
        selected_name: selected.name.clone(),
        logs,
    })
}

#[tauri::command]
pub fn save_settings(
    state: State<'_, Mutex<AppState>>,
    settings: SettingsInput,
) -> Result<(), String> {
    let app = lock(&state)?;
    if app.preserve_settings {
        return Ok(());
    }
    let plan_auto =
        app.auto_plan.as_ref() == Some(&(settings.runs.clone(), settings.distance.clone()));
    settings::save(
        &app.dir,
        &Settings {
            dark: settings.dark,
            runs: settings.runs,
            distance: settings.distance,
            time: settings.time,
            route: settings.route,
            skip_existing: settings.skip_existing,
            plan_auto,
        },
    )
}

// ---------------------------------------------------------------------------
// 地图与外部链接
// ---------------------------------------------------------------------------

/// 把地图页面发布到本机服务，返回可嵌入 WebView 的地址。验证模式只写地址文件。
fn publish_map_page(state: &mut AppState, name: &str, html: String) -> Result<String, String> {
    if state.maps.is_none() {
        state.maps = Some(MapServer::start()?);
    }
    let url = state
        .maps
        .as_ref()
        .ok_or("地图服务未启动")?
        .publish(name, html)?;
    if let Some(dir) = &state.map_output {
        std::fs::write(dir.join(format!("{name}-url.txt")), &url)
            .map_err(|_| "无法保存地图验证地址".to_string())?;
    }
    Ok(url)
}

fn open_map_page(state: &mut AppState, name: &str, html: String) -> Result<(), String> {
    let url = publish_map_page(state, name, html)?;
    if state.map_output.is_none() {
        webbrowser::open(&url).map_err(|_| "无法打开系统浏览器".to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub fn preview_map(
    state: State<'_, Mutex<AppState>>,
    request: PreviewRequest,
) -> Result<PreviewMapResult, String> {
    let mut app = lock(&state)?;
    let (_, route) = app.route_by_name(&request.route)?;
    let fresh = app.preview_inputs.as_ref() == Some(&request.inputs());
    let points = match app.preview.as_ref().filter(|_| fresh) {
        Some(data) => data.points.clone(),
        None => {
            let distance = request.distance.parse::<f64>().map_err(|_| "距离无效")?;
            if !(settings::MIN_DISTANCE_KM..=settings::MAX_DISTANCE_KM).contains(&distance) {
                return Err("距离应在 1.20–5.00 km 之间".into());
            }
            // 预览缓存缺失时按上传同一口径重采样：不加固定距离补偿。
            route::resample(&route::corrected(&route.points), distance * 1_000.0, 10.0)?
        }
    };
    let html = route::preview_html(&points, &route.name);
    let url = publish_map_page(&mut app, "preview", html)?;
    Ok(PreviewMapResult { url, notice: None })
}

#[tauri::command]
pub fn open_planner(state: State<'_, Mutex<AppState>>) -> Result<MapOpenResult, String> {
    let mut app = lock(&state)?;
    open_map_page(
        &mut app,
        "planner",
        include_str!("../../../route_planner.html").into(),
    )?;
    Ok(MapOpenResult {
        notice: Some("规划器已打开：导出 TXT 后通过「导入 TXT」添加".into()),
    })
}

#[tauri::command]
pub fn open_external(kind: String) -> Result<(), String> {
    let url = match kind.as_str() {
        "shuiyuan" => "https://shuiyuan.sjtu.edu.cn/t/topic/421786",
        "project" => "https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition",
        _ => return Err("未知的外部链接".into()),
    };
    webbrowser::open(url).map_err(|_| "无法打开浏览器".to_string())
}

// ---------------------------------------------------------------------------
// 登录、二次验证与学期统计
// ---------------------------------------------------------------------------

#[tauri::command]
pub async fn prepare_login(state: State<'_, Mutex<AppState>>) -> Result<LoginPreparation, String> {
    {
        let mut app = lock(&state)?;
        app.challenge = None;
        app.stop_qr();
    }
    let prepared = tauri::async_runtime::spawn_blocking(|| {
        let challenge = Session::prepare_login()?;
        let captcha = Session::recognize_captcha(&challenge.image);
        Ok::<_, String>((challenge, captcha))
    })
    .await
    .map_err(|error| format!("登录准备任务失败：{error}"))??;
    let (challenge, captcha) = prepared;
    let image = preview::captcha_data_url(&challenge.image)?;
    let mut app = lock(&state)?;
    app.challenge = Some(challenge);
    match captcha {
        Ok(code) => Ok(LoginPreparation {
            captcha: image,
            captcha_code: Some(code),
            manual: false,
            notice: "图形验证码已自动识别，填写账号和密码即可登录".into(),
        }),
        Err(error) => Ok(LoginPreparation {
            captcha: image,
            captcha_code: None,
            manual: true,
            notice: format!("自动识别暂不可用：{error}。可刷新重试，或手动填写备用验证码。"),
        }),
    }
}

#[tauri::command]
pub async fn submit_login(
    state: State<'_, Mutex<AppState>>,
    username: String,
    password: String,
    captcha: String,
) -> Result<AuthOutcome, String> {
    let username = username.trim().to_owned();
    if username.is_empty() || password.is_empty() {
        return Err("请填写账号和密码".into());
    }
    if captcha.trim().is_empty() {
        return Err("验证码尚未识别，请点击刷新重试；识别异常时也可手动填写".into());
    }
    let challenge = {
        let mut app = lock(&state)?;
        app.challenge
            .take()
            .ok_or_else(|| "请先刷新图形验证码".to_string())?
    };
    let login_name = username.clone();
    let result = tauri::async_runtime::spawn_blocking(move || {
        Session::login(challenge, &login_name, &password, &captcha)
    })
    .await
    .map_err(|error| format!("登录任务失败：{error}"))?;
    let mut app = lock(&state)?;
    match result {
        Ok(LoginResult::Authenticated(session)) => {
            app.session = Some(session);
            app.user = username.clone();
            app.two_factor = None;
            app.verification_attempts = 0;
            app.session_serial += 1;
            app.auto_adjust_pending = true;
            Ok(AuthOutcome {
                stage: "authenticated",
                user: username,
                notice: "登录成功，会话仅保留在内存中".into(),
            })
        }
        Ok(LoginResult::TwoFactor(session)) => {
            app.two_factor = Some(session);
            app.user = username.clone();
            app.verification_attempts = 0;
            Ok(AuthOutcome {
                stage: "two_factor",
                user: username,
                notice: "请选择验证方式并发送验证码".into(),
            })
        }
        Err(error) => Err(error),
    }
}

#[tauri::command]
pub async fn prepare_qr_login(
    app: AppHandle,
    state: State<'_, Mutex<AppState>>,
) -> Result<QrPreparation, String> {
    let generation = {
        let mut current = lock(&state)?;
        current.stop_qr();
        current.challenge = None;
        current.qr_generation
    };
    let cancel = Arc::new(AtomicBool::new(false));
    let prepared = {
        let cancel = cancel.clone();
        tauri::async_runtime::spawn_blocking(move || {
            let (session, uuid) = Session::prepare_qr_login()?;
            let mut channel = session.open_qr_channel(&uuid)?;
            let ticket = channel.wait_ticket(&cancel)?;
            let image = session.qr_image(&uuid, &ticket)?;
            Ok::<_, String>((session, uuid, channel, image))
        })
        .await
        .map_err(|error| format!("二维码准备任务失败：{error}"))?
    };
    let (session, uuid, channel, image) = prepared?;
    let qr = preview::qr_data_url(&image)?;
    {
        let mut current = lock(&state)?;
        if current.qr_generation != generation {
            return Err("二维码登录已取消".into());
        }
        current.qr_cancel = Some(cancel.clone());
    }
    spawn_qr_watcher(app, generation, cancel, session, uuid, channel);
    Ok(QrPreparation {
        generation,
        qr,
        notice: "打开「交我办」App 或微信，扫描二维码并在手机上确认登录".into(),
    })
}

/// 订阅通道，等待手机确认；每 60 秒换一张二维码，与学校登录页保持一致。
fn spawn_qr_watcher(
    app: AppHandle,
    generation: u64,
    cancel: Arc<AtomicBool>,
    session: Session,
    uuid: String,
    mut channel: crate::qr::Channel,
) {
    std::thread::spawn(move || {
        let mut last_request = Instant::now();
        loop {
            if cancel.load(Ordering::Relaxed) {
                channel.close();
                return;
            }
            if last_request.elapsed() >= crate::qr::REFRESH_INTERVAL {
                last_request = Instant::now();
                if channel.request().is_err() {
                    fail_qr(&app, &cancel, generation, "二维码刷新失败，请重新获取");
                    channel.close();
                    return;
                }
            }
            match channel.poll_signal() {
                Ok(Some(crate::qr::Signal::Ticket(ticket))) => {
                    let refreshed = session
                        .qr_image(&uuid, &ticket)
                        .and_then(|image| preview::qr_data_url(&image));
                    let qr = match refreshed {
                        Ok(qr) => qr,
                        Err(message) => {
                            fail_qr(&app, &cancel, generation, &message);
                            channel.close();
                            return;
                        }
                    };
                    if cancel.load(Ordering::Relaxed) {
                        channel.close();
                        return;
                    }
                    let _ = app.emit("qr-login", QrEvent::Image { generation, qr });
                }
                Ok(Some(crate::qr::Signal::Login)) => {
                    finish_qr_login(&app, &cancel, generation, &session, &uuid);
                    channel.close();
                    return;
                }
                Ok(Some(crate::qr::Signal::Other)) | Ok(None) => {}
                Err(message) => {
                    fail_qr(&app, &cancel, generation, &message);
                    channel.close();
                    return;
                }
            }
        }
    });
}

fn finish_qr_login(
    app: &AppHandle,
    cancel: &AtomicBool,
    generation: u64,
    session: &Session,
    uuid: &str,
) {
    if cancel.load(Ordering::Relaxed) {
        return;
    }
    let result = session.express_login(uuid);
    if cancel.load(Ordering::Relaxed) {
        return;
    }
    let state = app.state::<Mutex<AppState>>();
    let Ok(mut current) = state.lock() else {
        return;
    };
    if current.qr_generation != generation {
        return;
    }
    match result {
        Ok(LoginResult::Authenticated(session)) => {
            current.stop_qr();
            current.session = Some(session);
            current.user.clear();
            current.challenge = None;
            current.two_factor = None;
            current.verification_attempts = 0;
            current.session_serial += 1;
            current.auto_adjust_pending = true;
            drop(current);
            let _ = app.emit(
                "qr-login",
                QrEvent::Authenticated {
                    generation,
                    user: String::new(),
                    notice: "扫码登录成功，会话仅保留在内存中".into(),
                },
            );
        }
        Ok(LoginResult::TwoFactor(session)) => {
            let account = session.two_factor_account().unwrap_or_default();
            current.stop_qr();
            current.two_factor = Some(session);
            current.user = account.clone();
            current.verification_attempts = 0;
            drop(current);
            let _ = app.emit(
                "qr-login",
                QrEvent::TwoFactor {
                    generation,
                    user: account,
                    notice: "扫码登录需要二次验证，请选择验证方式".into(),
                },
            );
        }
        Err(message) => {
            drop(current);
            fail_qr(app, cancel, generation, &message);
        }
    }
}

fn fail_qr(app: &AppHandle, cancel: &AtomicBool, generation: u64, message: &str) {
    if cancel.load(Ordering::Relaxed) {
        return;
    }
    let state = app.state::<Mutex<AppState>>();
    let Ok(current) = state.lock() else {
        return;
    };
    // 已经开了新一轮扫码时，旧线程的失败不再打扰界面。
    if current.qr_generation != generation {
        return;
    }
    drop(current);
    let _ = app.emit(
        "qr-login",
        QrEvent::Failed {
            generation,
            message: message.to_owned(),
        },
    );
}

#[tauri::command]
pub async fn send_code(
    state: State<'_, Mutex<AppState>>,
    method: String,
) -> Result<String, String> {
    let method = match method.as_str() {
        "app" | "email" | "sms" => method,
        _ => return Err("未知的验证方式".into()),
    };
    let session = {
        let app = lock(&state)?;
        app.two_factor
            .clone()
            .ok_or_else(|| "请先完成账号密码登录".to_string())?
    };
    tauri::async_runtime::spawn_blocking(move || session.send_code(&method))
        .await
        .map_err(|error| format!("发送验证码任务失败：{error}"))??;
    Ok("验证码已发送，请查收".into())
}

#[tauri::command]
pub async fn verify_code(
    state: State<'_, Mutex<AppState>>,
    code: String,
) -> Result<VerifyOutcome, String> {
    let (session, user) = {
        let app = lock(&state)?;
        (
            app.two_factor
                .clone()
                .ok_or_else(|| "请先完成账号密码登录".to_string())?,
            app.user.clone(),
        )
    };
    let result = tauri::async_runtime::spawn_blocking(move || session.verify_code(&user, &code))
        .await
        .map_err(|error| format!("验证任务失败：{error}"))?;
    let mut app = lock(&state)?;
    match result {
        Ok(()) => {
            app.session = app.two_factor.take();
            app.session_serial += 1;
            app.auto_adjust_pending = true;
            Ok(VerifyOutcome {
                verified: true,
                locked: false,
                message: "二次验证成功".into(),
            })
        }
        Err(error) => {
            app.verification_attempts += 1;
            if app.verification_attempts >= 5 {
                app.two_factor = None;
                app.user.clear();
                Ok(VerifyOutcome {
                    verified: false,
                    locked: true,
                    message: "二次验证已达 5 次，请重新登录".into(),
                })
            } else {
                Ok(VerifyOutcome {
                    verified: false,
                    locked: false,
                    message: error,
                })
            }
        }
    }
}

#[tauri::command]
pub fn cancel_login(state: State<'_, Mutex<AppState>>) -> Result<(), String> {
    let mut app = lock(&state)?;
    app.challenge = None;
    app.stop_qr();
    app.two_factor = None;
    app.user.clear();
    app.verification_attempts = 0;
    Ok(())
}

#[tauri::command]
pub fn logout(state: State<'_, Mutex<AppState>>) -> Result<LogoutResult, String> {
    let mut app = lock(&state)?;
    app.session = None;
    app.challenge = None;
    app.stop_qr();
    app.two_factor = None;
    app.user.clear();
    app.session_serial += 1;
    app.stats = None;
    app.auto_adjust_pending = false;
    app.clear_preview();
    Ok(LogoutResult {
        weeks: placeholder_calendar(),
        km: "--".into(),
        percent: "--".into(),
        notice: "已退出账号，内存会话已清除".into(),
    })
}

fn adjust_plan(
    app: &mut AppState,
    data: &SemesterStats,
    runs: &str,
    distance: &str,
    logs: &mut Vec<String>,
) -> Option<(PlanView, String)> {
    let (Some(target), Some(done)) = (data.target_km, data.result_km) else {
        logs.push("服务器未返回本学期目标或已完成公里数，跑步计划保持不变".into());
        return None;
    };
    let remaining = target - done;
    let Some(plan) = stats::auto_plan(remaining) else {
        logs.push("本学期没有待补的公里数，跑步计划保持不变".into());
        return None;
    };
    let defaults = Settings::default();
    let untouched = runs == defaults.runs && distance == defaults.distance;
    let current = (runs.to_owned(), distance.to_owned());
    if !untouched && app.auto_plan.as_ref() != Some(&current) {
        logs.push("跑步次数 / 单次距离已被手动修改，保持你的设置".into());
        return None;
    }
    let adjusted = PlanView {
        runs: plan.runs.to_string(),
        distance: stats::format_plan_km(plan.distance_km),
    };
    app.auto_plan = Some((adjusted.runs.clone(), adjusted.distance.clone()));
    let notice = format!(
        "已按本学期未完成 {} 自动设为 {} 次 × {} km",
        stats::format_km(Some(remaining)),
        plan.runs,
        adjusted.distance
    );
    logs.push(notice.clone());
    Some((adjusted, notice))
}

#[tauri::command]
pub async fn sync_stats(
    state: State<'_, Mutex<AppState>>,
    runs: String,
    distance: String,
) -> Result<StatsPayload, String> {
    let (session, serial) = {
        let app = lock(&state)?;
        (
            app.session
                .clone()
                .ok_or_else(|| "请先登录账号".to_string())?,
            app.session_serial,
        )
    };
    let result = tauri::async_runtime::spawn_blocking(move || session.semester_stats())
        .await
        .map_err(|error| format!("学期数据任务失败：{error}"))?;
    let mut app = lock(&state)?;
    if serial != app.session_serial || app.session.is_none() {
        return Err("登录状态已变更，已忽略过期的学期数据".into());
    }
    let data = match result {
        Ok(data) => data,
        Err(error) => {
            app.auto_adjust_pending = false;
            return Err(format!("学期数据同步失败：{error}"));
        }
    };
    let mut logs = Vec::new();
    let weeks = match data.range {
        Some(range) => {
            logs.push(format!("学期数据已同步 · {} 天有记录", data.run_days.len()));
            Some(calendar_view(&stats::calendar_weeks(range, &data.run_days)))
        }
        None => {
            logs.push("服务器未返回本学期起止日期，日历保持占位".into());
            None
        }
    };
    let adjust = app.auto_adjust_pending;
    app.auto_adjust_pending = false;
    app.stats = Some(data.clone());
    let mut plan = None;
    let mut notice = None;
    if adjust {
        if let Some((adjusted, message)) = adjust_plan(&mut app, &data, &runs, &distance, &mut logs)
        {
            plan = Some(adjusted);
            notice = Some(message);
        }
    }
    Ok(StatsPayload {
        km: stats::format_km(data.result_km),
        percent: stats::format_percent(data.percent),
        weeks,
        run_days: data.run_days.len(),
        plan,
        logs,
        notice,
    })
}

fn spawn_stats_refresh(app: AppHandle) {
    let (session, serial) = {
        let state = app.state::<Mutex<AppState>>();
        let Ok(state) = state.lock() else {
            return;
        };
        (state.session.clone(), state.session_serial)
    };
    let Some(session) = session else {
        return;
    };
    std::thread::spawn(move || {
        let result = session.semester_stats();
        let mut payload = None;
        let mut error = None;
        {
            let state = app.state::<Mutex<AppState>>();
            let Ok(mut app_state) = state.lock() else {
                return;
            };
            if serial != app_state.session_serial || app_state.session.is_none() {
                return;
            }
            match result {
                Ok(data) => {
                    let mut logs = Vec::new();
                    let weeks = match data.range {
                        Some(range) => {
                            logs.push(format!("学期数据已同步 · {} 天有记录", data.run_days.len()));
                            Some(calendar_view(&stats::calendar_weeks(range, &data.run_days)))
                        }
                        None => {
                            logs.push("服务器未返回本学期起止日期，日历保持占位".into());
                            None
                        }
                    };
                    app_state.stats = Some(data.clone());
                    payload = Some(StatsPayload {
                        km: stats::format_km(data.result_km),
                        percent: stats::format_percent(data.percent),
                        weeks,
                        run_days: data.run_days.len(),
                        plan: None,
                        logs,
                        notice: None,
                    });
                }
                Err(message) => error = Some(format!("学期数据同步失败：{message}")),
            }
        }
        if let Some(payload) = payload {
            let _ = app.emit("stats-updated", payload);
        }
        if let Some(message) = error {
            let _ = app.emit("app-log", LogPayload { message });
        }
    });
}

#[tauri::command]
pub async fn check_update() -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(|| update::check(APP_VERSION))
        .await
        .map_err(|error| format!("检查更新任务失败：{error}"))?
}

// ---------------------------------------------------------------------------
// 任务
// ---------------------------------------------------------------------------

#[tauri::command]
pub fn start_task(
    app: AppHandle,
    state: State<'_, Mutex<AppState>>,
    request: TaskRequest,
) -> Result<TaskStarted, String> {
    let config = RunConfig::parse(
        &request.runs,
        &request.distance,
        &request.date,
        &request.time,
    )?;
    let mut app_state = lock(&state)?;
    if app_state.busy {
        return Err("任务正在运行".into());
    }
    let session = app_state
        .session
        .clone()
        .ok_or_else(|| "请先登录账号".to_string())?;
    let (_, route) = app_state.route_by_name(&request.route)?;
    let occupied: HashSet<_> = app_state
        .stats
        .as_ref()
        .map(|data| data.run_days.keys().copied().collect())
        .unwrap_or_default();
    let earliest = app_state
        .stats
        .as_ref()
        .and_then(|data| data.range)
        .map(|range| range.start);
    let plan = task::schedule(&config, request.skip_existing, &occupied, earliest)?;
    if plan.dates.is_empty() {
        return Err(
            "设定次数内的日期都已有记录，可关闭「跳过已有记录的日期」或改用更早的结束日期".into(),
        );
    }
    let started = TaskStarted {
        count: plan.dates.len(),
        skipped: plan.skipped.len(),
        truncated: plan.truncated,
    };
    let cancel = Arc::new(AtomicBool::new(false));
    app_state.cancel = cancel.clone();
    app_state.busy = true;
    let user = app_state.user.clone();
    let inputs = PreviewInputs {
        runs: request.runs,
        distance: request.distance,
        date: request.date,
        time: request.time,
        route: request.route,
    };
    let points = route.points;
    drop(app_state);
    let worker = app.clone();
    std::thread::spawn(move || {
        let result =
            task::run(
                &session,
                &points,
                &config,
                &plan,
                &user,
                &cancel,
                |event| match event {
                    Event::Log(message) => {
                        let _ = worker.emit("task-log", LogPayload { message });
                    }
                    Event::Progress(value, status) => {
                        let _ = worker.emit("task-progress", ProgressPayload { value, status });
                    }
                    Event::Preview(data) => {
                        {
                            let state = worker.state::<Mutex<AppState>>();
                            if let Ok(mut app_state) = state.lock() {
                                app_state.preview = Some(data.clone());
                                app_state.preview_inputs = Some(inputs.clone());
                            };
                        }
                        let _ = worker.emit("task-preview", PreviewView::from(&data));
                    }
                    Event::Finished {
                        success,
                        failed,
                        stopped,
                    } => {
                        {
                            let state = worker.state::<Mutex<AppState>>();
                            if let Ok(mut app_state) = state.lock() {
                                app_state.busy = false;
                            };
                        }
                        let status = format!(
                            "{} · 成功 {success} 条，失败 {failed} 条",
                            if stopped {
                                "任务已停止"
                            } else {
                                "任务结束"
                            }
                        );
                        let progress = if stopped { 0 } else { 100 };
                        let _ = worker.emit(
                            "task-finished",
                            FinishedPayload {
                                success,
                                failed,
                                stopped,
                                status: status.clone(),
                                progress,
                            },
                        );
                        let _ = worker.emit("app-log", LogPayload { message: status });
                        if success > 0 {
                            spawn_stats_refresh(worker.clone());
                        }
                        maybe_exit(&worker);
                    }
                },
            );
        if let Err(error) = result {
            {
                let state = worker.state::<Mutex<AppState>>();
                if let Ok(mut app_state) = state.lock() {
                    app_state.busy = false;
                };
            }
            let _ = worker.emit(
                "task-error",
                ErrorPayload {
                    message: error,
                    status: "任务失败".into(),
                },
            );
            maybe_exit(&worker);
        }
    });
    Ok(started)
}

#[tauri::command]
pub fn stop_task(state: State<'_, Mutex<AppState>>, app: AppHandle) -> Result<(), String> {
    let app_state = lock(&state)?;
    app_state.cancel.store(true, Ordering::Relaxed);
    drop(app_state);
    let _ = app.emit(
        "task-status",
        StatusPayload {
            status: "正在停止，等待当前网络请求结束…".into(),
        },
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// 启动
// ---------------------------------------------------------------------------

const UI_PROBE_SCRIPT: &str = r#"
(async () => {
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const result = { success: false, checks: {}, text: '' };
  const has = (text) => document.body.innerText.includes(text);
  try {
    await wait(400);
    document.querySelectorAll('md-dialog').forEach((dialog) => { dialog.quick = true; });
    result.checks.workbenchRendered = has('跑步参数');
    result.checks.materialWeb = !!customElements.get('md-filled-button');
    await document.fonts.ready;
    result.checks.fontsLoaded =
      document.fonts.check('16px Roboto') && document.fonts.check('24px "Material Symbols Rounded"');
    result.checks.primaryToken = getComputedStyle(document.documentElement)
      .getPropertyValue('--md-sys-color-primary')
      .trim()
      .startsWith('#');
    result.checks.routeMap = document.querySelectorAll('.map-line').length;
    result.checks.consentDialog = !!document.querySelector('md-dialog[open]');
    const checkbox = document.querySelector('md-dialog[open] md-checkbox');
    if (checkbox) {
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
      await wait(300);
    }
    result.checks.consentChecked = !!(checkbox && checkbox.checked);
    const accept = document.querySelector('md-dialog[open] md-filled-button');
    if (accept && !accept.disabled) {
      const target = accept.shadowRoot?.querySelector('button') ?? accept;
      target.click();
      await wait(500);
    }
    result.checks.consentClosed = document.querySelectorAll('md-dialog[open]').length === 0;
    result.checks.noWorkbenchCollapse = !Array.from(
      document.querySelectorAll('.preview-card md-outlined-button'),
    ).some((element) => element.textContent?.includes('收起地图'));
    // 路线管理保留地图切换；先收起自动加载的地图，再验证重新展开。
    document.querySelectorAll('.nav-item')[1]?.click();
    await wait(1200);
    const initialCollapse = Array.from(document.querySelectorAll('.preview-card md-outlined-button'))
      .find((element) => element.textContent?.includes('收起地图'));
    if (initialCollapse) {
      (initialCollapse.shadowRoot?.querySelector('button') ?? initialCollapse).click();
      await wait(250);
    }
    result.checks.routeMap = document.querySelectorAll('.map-line').length;
    // 预览地图应嵌在卡片里，而不是交给系统浏览器。
    const mapButton = Array.from(document.querySelectorAll('.preview-card md-outlined-button'))
      .find((element) => element.textContent?.includes('在地图中打开'));
    result.checks.mapButton = !!mapButton;
    if (mapButton) {
      const mapReady = new Promise((resolve) => {
        const onMessage = (event) => {
          if (event.data?.type === 'sjturm-map-ready') {
            window.removeEventListener('message', onMessage);
            resolve(true);
          }
        };
        window.addEventListener('message', onMessage);
        setTimeout(() => {
          window.removeEventListener('message', onMessage);
          resolve(false);
        }, 8000);
      });
      (mapButton.shadowRoot?.querySelector('button') ?? mapButton).click();
      result.checks.inlineMapReady = await mapReady;
      await wait(1200);
      const frame = document.querySelector('.route-map-live iframe');
      result.checks.inlineMap = !!frame;
      result.checks.inlineMapSrc = frame?.getAttribute('src') ?? '';
      result.checks.noMapNotice = !document.body.innerText.includes('已在地图中显示当前轨迹');
      const collapseButton = Array.from(
        document.querySelectorAll('.preview-card md-outlined-button'),
      ).find((element) => element.textContent?.includes('收起地图'));
      result.checks.inlineMapToggle = !!collapseButton;
      if (collapseButton) {
        (collapseButton.shadowRoot?.querySelector('button') ?? collapseButton).click();
        await wait(250);
        result.checks.inlineMapCollapsed =
          !document.querySelector('.route-map-live iframe') &&
          document.querySelectorAll('.map-line').length > 0;
      }
    }
    const nav = document.querySelectorAll('.nav-item');
    result.checks.navItems = nav.length;
    if (nav[1]) { nav[1].click(); await wait(350); }
    result.checks.routesPage = has('路线列表');
    if (nav[2]) { nav[2].click(); await wait(350); }
    result.checks.logsPage = has('学期日历');
    if (nav[3]) { nav[3].click(); await wait(350); }
    result.checks.aboutPage = has('更新与社区');
    result.text = document.body.innerText.slice(0, 1200);
    const required = [
      'workbenchRendered',
      'materialWeb',
      'fontsLoaded',
      'primaryToken',
      'consentDialog',
      'consentChecked',
      'consentClosed',
      'noWorkbenchCollapse',
      'mapButton',
      'inlineMap',
      'inlineMapReady',
      'inlineMapToggle',
      'inlineMapCollapsed',
      'noMapNotice',
      'routesPage',
      'logsPage',
      'aboutPage',
    ];
    result.success =
      required.every((key) => result.checks[key] === true) &&
      result.checks.navItems === 4 &&
      result.checks.routeMap > 0 &&
      String(result.checks.inlineMapSrc).startsWith('http://127.0.0.1:');
  } catch (error) {
    result.error = String(error);
  }
  await window.__TAURI_INTERNALS__.invoke('smoke_probe', { report: result });
})();
"#;

#[tauri::command]
pub fn ui_ready(app: AppHandle, state: State<'_, Mutex<AppState>>) -> Result<(), String> {
    let enabled = match state.lock() {
        Ok(app_state) => app_state.smoke_output.is_some(),
        Err(_) => false,
    };
    if enabled {
        std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(800));
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.eval(UI_PROBE_SCRIPT);
            }
        });
    }
    Ok(())
}

#[tauri::command]
pub fn smoke_probe(
    app: AppHandle,
    state: State<'_, Mutex<AppState>>,
    report: serde_json::Value,
) -> Result<(), String> {
    let dir = {
        let app_state = lock(&state)?;
        app_state
            .smoke_output
            .clone()
            .ok_or_else(|| "当前不是 UI 冒烟测试模式".to_string())?
    };
    std::fs::create_dir_all(&dir).map_err(|_| "无法创建冒烟测试目录".to_string())?;
    std::fs::write(
        dir.join("ui-smoke-result.json"),
        serde_json::to_vec_pretty(&report).map_err(|_| "无法序列化冒烟结果".to_string())?,
    )
    .map_err(|_| "无法写入冒烟结果".to_string())?;
    let success = report["success"].as_bool().unwrap_or(false);
    app.exit(if success { 0 } else { 1 });
    Ok(())
}

fn install_panic_log() {
    let path = settings::data_dir()
        .map(|dir| dir.join("crash.log"))
        .unwrap_or_else(|_| std::env::temp_dir().join("sjturunningman-crash.log"));
    std::panic::set_hook(Box::new(move |info| {
        if let Ok(previous) = std::fs::read_to_string(&path) {
            let kept: Vec<_> = previous.lines().rev().take(100).collect();
            let text = kept.into_iter().rev().collect::<Vec<_>>().join("\n");
            let _ = std::fs::write(&path, format!("{text}\n{info}\n"));
        } else if let Some(dir) = path.parent() {
            let _ = std::fs::create_dir_all(dir);
            let _ = std::fs::write(&path, format!("{info}\n"));
        }
    }));
}

fn load_state(
    dir: PathBuf,
    map_output: Option<PathBuf>,
    smoke_output: Option<PathBuf>,
) -> AppState {
    let (prefs, warning) = match settings::load(&dir) {
        Ok(prefs) => (prefs, None),
        Err(error) => (Settings::default(), Some(error)),
    };
    let preserve_settings = warning.is_some() && dir.join("settings.json").exists();
    let mut startup_logs = Vec::new();
    let routes = match route::list(&dir) {
        Ok((routes, skipped)) => {
            startup_logs.extend(
                skipped
                    .into_iter()
                    .map(|problem| format!("跳过无法解析的路线：{problem}")),
            );
            routes
        }
        Err(error) => {
            startup_logs.push(error);
            let points = route::parse(route::DEFAULT_ROUTE).expect("内置路线必须可解析");
            vec![Route {
                name: "default".into(),
                path: None,
                points,
            }]
        }
    };
    let selected = routes
        .iter()
        .position(|route| route.name == prefs.route)
        .unwrap_or(0);
    let auto_plan = if prefs.plan_auto {
        Some((prefs.runs.clone(), prefs.distance.clone()))
    } else {
        None
    };
    if let Some(warning) = &warning {
        startup_logs.push(warning.clone());
    }
    AppState {
        dir,
        maps: None,
        map_output,
        routes,
        selected,
        preview: None,
        preview_inputs: None,
        session: None,
        challenge: None,
        qr_cancel: None,
        qr_generation: 0,
        two_factor: None,
        user: String::new(),
        cancel: Arc::new(AtomicBool::new(false)),
        busy: false,
        close_after_stop: false,
        verification_attempts: 0,
        session_serial: 0,
        stats: None,
        auto_plan,
        auto_adjust_pending: false,
        preserve_settings,
        startup_warning: warning,
        startup_logs,
        smoke_output,
    }
}

fn run_smoke(mode: &str, output: PathBuf) {
    let _ = std::fs::create_dir_all(&output);
    match mode {
        "--login-smoke-test" => {
            let started = Instant::now();
            let result = (|| {
                let challenge = Session::prepare_login()?;
                let captcha = Session::recognize_captcha(&challenge.image);
                let image = crate::api::decode_captcha(&challenge.image)?;
                Ok::<_, String>((captcha, image))
            })();
            let (success, report) = match result {
                Ok((captcha, image)) => {
                    let recognized = captcha.is_ok();
                    (
                        recognized,
                        serde_json::json!({
                            "success": recognized,
                            "image_width": image.width(),
                            "image_height": image.height(),
                            "automatically_recognized": recognized,
                            "manual_input_visible": !recognized,
                            "account_login_attempted": false,
                            "elapsed_ms": started.elapsed().as_millis(),
                        }),
                    )
                }
                Err(error) => (
                    false,
                    serde_json::json!({
                        "success": false,
                        "error": error,
                        "account_login_attempted": false,
                        "elapsed_ms": started.elapsed().as_millis(),
                    }),
                ),
            };
            let path = output.join("login-smoke-result.json");
            let _ = std::fs::write(path, serde_json::to_vec_pretty(&report).unwrap());
            if !success {
                eprintln!("Login smoke test failed: {report}");
                std::process::exit(1);
            }
            println!("{report}");
        }
        "--map-smoke-test" => {
            let data_dir = output.join("data");
            let _ = std::fs::create_dir_all(&data_dir);
            let mut state = load_state(data_dir, Some(output.clone()), None);
            let config = RunConfig::parse("1", "4", &settings::yesterday(), "08:00:00")
                .expect("默认参数有效");
            let route = state.selected_route().expect("默认路线存在");
            let preview = task::generate(
                &route.points,
                &config,
                "preview",
                chrono::Utc::now().timestamp_millis(),
                &serde_json::json!({}),
            )
            .expect("离线预览可生成");
            let html = route::preview_html(&preview.points, &route.name);
            open_map_page(&mut state, "preview", html).expect("地图服务可启动");
            open_map_page(
                &mut state,
                "planner",
                include_str!("../../../route_planner.html").into(),
            )
            .expect("规划器可发布");
            println!("map smoke pages published in {}", output.display());
            loop {
                std::thread::sleep(Duration::from_secs(3600));
            }
        }
        _ => {
            let data_dir = output.join("data");
            let _ = std::fs::create_dir_all(&data_dir);
            let state = load_state(data_dir, None, None);
            let config = RunConfig::parse("1", "4", &settings::yesterday(), "08:00:00")
                .expect("默认参数有效");
            let route = state.selected_route().expect("默认路线存在");
            let preview = task::generate(
                &route.points,
                &config,
                "preview",
                chrono::Utc::now().timestamp_millis(),
                &serde_json::json!({}),
            )
            .expect("离线预览可生成");
            let invalid = RunConfig::parse("0", "4", &settings::yesterday(), "08:00:00").is_err();
            let calendar = placeholder_calendar();
            let report = serde_json::json!({
                "version": APP_VERSION,
                "routes": state.routes.len(),
                "route": route.name,
                "preview": preview_summary(&preview),
                "preview_points": preview.points.len(),
                "input_validation": invalid,
                "calendar_weeks": calendar.len(),
                "account_login_or_upload_attempted": false,
                "ui": "Tauri 2 + React 19 + @material/web",
            });
            let path = output.join("smoke-result.json");
            let _ = std::fs::write(&path, serde_json::to_vec_pretty(&report).unwrap());
            println!("{report}");
        }
    }
}

pub fn run() {
    install_panic_log();
    let args: Vec<String> = std::env::args().collect();
    let mode = args.get(1).cloned().unwrap_or_default();
    if mode.starts_with("--") && mode != "--ui-smoke-test" {
        let output = args
            .get(2)
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("target/smoke"));
        run_smoke(&mode, output);
        return;
    }
    let ui_smoke = mode == "--ui-smoke-test";
    let smoke_output = ui_smoke.then(|| {
        args.get(2)
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("target/ui-smoke"))
    });
    let dir = if let Some(output) = &smoke_output {
        let dir = output.join("data");
        if let Err(error) = std::fs::create_dir_all(&dir) {
            eprintln!("{error}");
            std::process::exit(1);
        }
        dir
    } else {
        match settings::data_dir() {
            Ok(dir) => dir,
            Err(error) => {
                eprintln!("{error}");
                std::process::exit(1);
            }
        }
    };
    let state = load_state(dir, None, smoke_output);
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(Mutex::new(state))
        .setup(|app| {
            let smoke = app
                .state::<Mutex<AppState>>()
                .lock()
                .ok()
                .and_then(|state| state.smoke_output.clone());
            if let Some(dir) = smoke {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    std::thread::sleep(Duration::from_secs(20));
                    let path = dir.join("ui-smoke-result.json");
                    if !path.exists() {
                        let report = serde_json::json!({
                            "success": false,
                            "error": "UI smoke test timed out before the frontend reported readiness",
                        });
                        let _ = std::fs::write(path, serde_json::to_vec_pretty(&report).unwrap());
                        handle.exit(1);
                    }
                });
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            bootstrap,
            select_route,
            preview_route,
            import_route,
            delete_route,
            save_settings,
            preview_map,
            open_planner,
            open_external,
            prepare_login,
            prepare_qr_login,
            submit_login,
            send_code,
            verify_code,
            cancel_login,
            logout,
            sync_stats,
            check_update,
            start_task,
            stop_task,
            ui_ready,
            smoke_probe,
        ])
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let state = window.state::<Mutex<AppState>>();
                let mut app_state = match state.lock() {
                    Ok(state) => state,
                    Err(_) => return,
                };
                if app_state.busy {
                    api.prevent_close();
                    app_state.cancel.store(true, Ordering::Relaxed);
                    app_state.close_after_stop = true;
                    drop(app_state);
                    let _ = window.emit(
                        "task-status",
                        StatusPayload {
                            status: "正在停止任务，完成后退出…".into(),
                        },
                    );
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn qr_events_match_the_frontend_contract() {
        for (event, kind) in [
            (
                QrEvent::Image {
                    generation: 3,
                    qr: "data:image/png;base64,AA".into(),
                },
                "image",
            ),
            (
                QrEvent::Authenticated {
                    generation: 3,
                    user: String::new(),
                    notice: "ok".into(),
                },
                "authenticated",
            ),
            (
                QrEvent::TwoFactor {
                    generation: 3,
                    user: "student".into(),
                    notice: "ok".into(),
                },
                "twoFactor",
            ),
            (
                QrEvent::Failed {
                    generation: 3,
                    message: "expired".into(),
                },
                "failed",
            ),
        ] {
            let value = serde_json::to_value(event).unwrap();
            assert_eq!(value["kind"], kind);
            assert_eq!(value["generation"], 3);
        }
        let value = serde_json::to_value(QrEvent::Failed {
            generation: 1,
            message: "expired".into(),
        })
        .unwrap();
        assert_eq!(
            value,
            serde_json::json!({"kind": "failed", "generation": 1, "message": "expired"})
        );
    }

    #[test]
    fn qr_preparation_uses_camel_case_fields() {
        let value = serde_json::to_value(QrPreparation {
            generation: 2,
            qr: "data:image/png;base64,AA".into(),
            notice: "ok".into(),
        })
        .unwrap();
        assert_eq!(value["generation"], 2);
        assert_eq!(value["qr"], "data:image/png;base64,AA");
        assert_eq!(value["notice"], "ok");
    }
}
