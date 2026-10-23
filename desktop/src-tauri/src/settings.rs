use chrono::{Duration, Local, NaiveDate, NaiveTime};
use serde::{Deserialize, Serialize};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// 桌面端用户可设距离范围；不再另外增加固定距离补偿。
pub const MIN_DISTANCE_KM: f64 = 1.2;
pub const MAX_DISTANCE_KM: f64 = 5.0;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub dark: bool,
    pub runs: String,
    pub distance: String,
    pub time: String,
    pub route: String,
    /// 上传时跳过学期日历里已有记录的日期。
    pub skip_existing: bool,
    /// 记录当前的次数 / 距离是客户端按学期缺口自动填的，不是用户手改的。
    pub plan_auto: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            dark: false,
            runs: "1".into(),
            distance: "4".into(),
            time: "08:00:00".into(),
            route: "default".into(),
            skip_existing: true,
            plan_auto: false,
        }
    }
}

pub fn data_dir() -> Result<PathBuf, String> {
    directories::ProjectDirs::from("cn", "sjtu", "SJTURunningMan")
        .map(|dirs| dirs.data_local_dir().to_path_buf())
        .ok_or_else(|| "无法定位用户数据目录".into())
}

pub fn load(dir: &Path) -> Result<Settings, String> {
    let path = dir.join("settings.json");
    if !path.exists() {
        return Ok(Settings::default());
    }
    let bytes = fs::read(&path).map_err(|_| "无法读取偏好设置")?;
    match serde_json::from_slice::<Settings>(&bytes) {
        Ok(mut settings) => {
            // 兼容旧版本的距离范围；无效数字回到默认值。
            let distance = settings
                .distance
                .trim()
                .parse::<f64>()
                .ok()
                .filter(|v| v.is_finite());
            settings.distance = match distance {
                Some(value) => value.clamp(MIN_DISTANCE_KM, MAX_DISTANCE_KM).to_string(),
                None => Settings::default().distance,
            };
            Ok(settings)
        }
        Err(_) => {
            // 备份坏文件，之后照常保存，否则用户后续的改动永远不会落盘。
            let backup = dir.join("settings.json.bak");
            let _ = fs::remove_file(&backup);
            match fs::rename(&path, &backup) {
                Ok(()) => {
                    Err("偏好设置损坏，已使用默认设置；原文件备份为 settings.json.bak".into())
                }
                Err(_) => Err("偏好设置损坏，已使用默认设置；原文件保留".into()),
            }
        }
    }
}

pub fn save(dir: &Path, settings: &Settings) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|_| "无法创建用户数据目录")?;
    let bytes = serde_json::to_vec_pretty(settings).map_err(|_| "无法序列化偏好设置")?;
    fs::write(dir.join("settings.json"), bytes).map_err(|_| "无法保存偏好设置".into())
}

#[derive(Clone, Debug)]
pub struct RunConfig {
    pub runs: u32,
    pub distance_km: f64,
    pub date: NaiveDate,
    pub time: NaiveTime,
}

impl RunConfig {
    pub fn parse(runs: &str, distance: &str, date: &str, time: &str) -> Result<Self, String> {
        let runs: u32 = runs
            .trim()
            .parse()
            .map_err(|_| "跑步次数应为 1–30 之间的整数")?;
        if !(1..=30).contains(&runs) {
            return Err("跑步次数应在 1–30 之间".into());
        }
        let distance_km: f64 = distance
            .trim()
            .parse()
            .map_err(|_| "距离应为数字，单位 km")?;
        if !(MIN_DISTANCE_KM..=MAX_DISTANCE_KM).contains(&distance_km) {
            return Err("距离应在 1.20–5.00 km 之间".into());
        }
        let date_text = date.trim();
        if date_text.len() != 10 {
            return Err("日期格式应为 YYYY-MM-DD".into());
        }
        let date = NaiveDate::parse_from_str(date_text, "%Y-%m-%d")
            .map_err(|_| "日期无效，应为 YYYY-MM-DD")?;
        if date.format("%Y-%m-%d").to_string() != date_text {
            return Err("日期格式应为 YYYY-MM-DD".into());
        }
        let time_text = time.trim();
        if time_text.len() != 8 {
            return Err("时间格式应为 HH:MM:SS".into());
        }
        let time = NaiveTime::parse_from_str(time_text, "%H:%M:%S")
            .map_err(|_| "时间无效，应为 HH:MM:SS")?;
        if time.format("%H:%M:%S").to_string() != time_text {
            return Err("时间格式应为 HH:MM:SS".into());
        }
        Ok(Self {
            runs,
            distance_km,
            date,
            time,
        })
    }
}

pub fn yesterday() -> String {
    (Local::now().date_naive() - Duration::days(1)).to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn validates_all_input_boundaries() {
        for runs in ["0", "31", "-1", "1.5", ""] {
            assert!(RunConfig::parse(runs, "4", "2026-10-15", "08:00:00").is_err());
        }
        for distance in ["NaN", "inf", "0", "-1", "1", "1.19", "5.01", "5.1", "abc"] {
            assert!(RunConfig::parse("1", distance, "2026-10-15", "08:00:00").is_err());
        }
        for date in ["2026-2-01", "2026/10/15", "2026-02-30", ""] {
            assert!(RunConfig::parse("1", "4", date, "08:00:00").is_err());
        }
        for time in ["8:00", "8:00:00", "24:00:00", "08:60:00"] {
            assert!(RunConfig::parse("1", "4", "2026-10-15", time).is_err());
        }
        for distance in ["1.2", "1.21", "4", "5"] {
            assert!(RunConfig::parse("1", distance, "2026-10-15", "08:00:00").is_ok());
        }
        assert!(RunConfig::parse("30", "5", "2026-10-15", "23:59:59").is_ok());
    }
    #[test]
    fn settings_never_serialize_credentials() {
        let text = serde_json::to_string(&Settings::default()).unwrap();
        for secret in ["password", "cookie", "username", "token"] {
            assert!(!text.contains(secret));
        }
    }

    #[test]
    fn settings_from_older_version_keep_new_defaults() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("settings.json"),
            r#"{"dark":true,"runs":"3","distance":"2.5","time":"07:30:00","route":"old"}"#,
        )
        .unwrap();
        let saved = load(dir.path()).unwrap();
        assert_eq!(saved.runs, "3");
        assert!(saved.skip_existing);
        assert!(!saved.plan_auto);
    }

    #[test]
    fn legacy_distances_are_restored_within_current_limits() {
        let dir = tempfile::tempdir().unwrap();
        for (stored, expected) in [
            ("0.1", "1.2"),
            ("1", "1.2"),
            ("1.19", "1.2"),
            ("1.2", "1.2"),
            ("2.5", "2.5"),
            ("5", "5"),
            ("6", "5"),
            ("NaN", "4"),
            ("inf", "4"),
            ("broken", "4"),
        ] {
            let settings = Settings {
                distance: stored.into(),
                ..Settings::default()
            };
            save(dir.path(), &settings).unwrap();
            assert_eq!(
                load(dir.path()).unwrap().distance,
                expected,
                "stored distance: {stored}"
            );
        }
    }

    #[test]
    fn settings_round_trip_and_corrupt_file_is_preserved() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(load(dir.path()).unwrap().distance, "4");
        let settings = Settings {
            dark: true,
            route: "my-route".into(),
            ..Settings::default()
        };
        save(dir.path(), &settings).unwrap();
        let saved = load(dir.path()).unwrap();
        assert!(saved.dark);
        assert_eq!(saved.route, "my-route");
        std::fs::write(dir.path().join("settings.json"), "broken").unwrap();
        assert!(load(dir.path()).is_err());
        assert!(!dir.path().join("settings.json").exists());
        assert_eq!(
            std::fs::read_to_string(dir.path().join("settings.json.bak")).unwrap(),
            "broken"
        );
        // 备份后必须能继续保存，否则用户的后续改动会一直丢失。
        save(dir.path(), &Settings::default()).unwrap();
        assert!(!load(dir.path()).unwrap().dark);
    }
}
