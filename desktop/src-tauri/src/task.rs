use crate::{
    api::Session,
    route::{self, Point},
    settings::RunConfig,
};
use chrono::{Duration, Local, NaiveDate, TimeZone};
use rand::Rng;
use serde_json::{json, Value};
use std::collections::HashSet;
use std::sync::atomic::{AtomicBool, Ordering};
use uuid::Uuid;

#[derive(Clone, Debug)]
pub struct Preview {
    pub points: Vec<Point>,
    pub payload: Value,
    pub distance_m: f64,
    pub duration_s: i64,
}

#[derive(Clone, Debug)]
pub enum Event {
    Log(String),
    Progress(i32, String),
    Preview(Preview),
    Finished {
        success: u32,
        failed: u32,
        stopped: bool,
    },
}

/// 跳过已有记录时最多向前翻多少天，避免一路翻到学期之外。
pub const MAX_LOOKBACK_DAYS: i64 = 120;

#[derive(Clone, Debug, PartialEq)]
pub struct Schedule {
    /// 实际要上传的日期，从「结束日期」向前排列。
    pub dates: Vec<NaiveDate>,
    /// 因为已经有记录而被跳过的日期。
    pub skipped: Vec<NaiveDate>,
    /// 向前翻到上限或学期起点仍未凑够设定的次数。
    pub truncated: bool,
}

/// 决定这批记录落在哪些日期。开启「跳过已有记录」后仍然上传设定的次数，
/// 只是把已有记录的那几天往后（更早）挪；关闭时保持原来的连续向前生成。
pub fn schedule(
    config: &RunConfig,
    skip_existing: bool,
    occupied: &HashSet<NaiveDate>,
    earliest: Option<NaiveDate>,
) -> Result<Schedule, String> {
    let mut plan = Schedule {
        dates: Vec::new(),
        skipped: Vec::new(),
        truncated: false,
    };
    if !skip_existing {
        for index in 0..config.runs {
            plan.dates.push(day_before(config.date, index as i64)?);
        }
        return Ok(plan);
    }
    let mut offset = 0i64;
    while plan.dates.len() < config.runs as usize {
        let date = day_before(config.date, offset)?;
        if offset > MAX_LOOKBACK_DAYS || earliest.is_some_and(|start| date < start) {
            plan.truncated = true;
            break;
        }
        if occupied.contains(&date) {
            plan.skipped.push(date);
        } else {
            plan.dates.push(date);
        }
        offset += 1;
    }
    Ok(plan)
}

fn day_before(date: NaiveDate, days: i64) -> Result<NaiveDate, String> {
    date.checked_sub_signed(Duration::days(days))
        .ok_or_else(|| "日期超出范围".into())
}

pub fn generate(
    points: &[Point],
    config: &RunConfig,
    user: &str,
    start_ms: i64,
    rules: &Value,
) -> Result<Preview, String> {
    let mut rng = rand::rng();
    let pace: f64 = rng.random_range(240.0..=360.0);
    let speed = 1_000.0 / pace;
    let points = route::resample(
        &route::corrected(points),
        config.distance_km * 1_000.0,
        speed * 3.0,
    )?;
    let mut traveled = 0.0;
    let timed: Vec<Value>=points.iter().enumerate().map(|(i,p)| {
        if i>0 { traveled+=route::haversine(points[i-1],*p); }
        json!({"latLng":{"latitude":p.lat,"longitude":p.lon},"location":format!("{:.14},{:.14}",p.lon,p.lat),"step":0,"locatetime":start_ms+(traveled/speed*1_000.0) as i64})
    }).collect();
    let duration_s = (traveled / speed).floor().max(1.0) as i64;
    let mut tracks = Vec::new();
    let mut offset = 0;
    while offset < timed.len() {
        let remaining = timed.len() - offset;
        let length = if remaining <= 5 {
            remaining
        } else {
            rng.random_range(5..=(remaining / 3).max(5)).min(remaining)
        };
        let slice = &timed[offset..offset + length];
        let segment = &points[offset..offset + length];
        let start = slice[0]["locatetime"].as_i64().ok_or("轨迹时间无效")?;
        let end = slice[length - 1]["locatetime"]
            .as_i64()
            .ok_or("轨迹时间无效")?;
        let choice: f64 = rng.random();
        let status = if choice < 0.8 {
            "normal"
        } else if choice < 0.9 {
            "invalid"
        } else {
            "stop"
        };
        tracks.push(json!({"counts":length,"distance":route::distance(segment),"duration":((end-start) as f64/1_000.0).ceil() as i64,
            "points":slice,"status":status,"trid":Uuid::new_v4().to_string(),"tstate":if status=="invalid" {"2"} else {"0"},"stime":start/1_000,"etime":end/1_000}));
        offset += length;
    }
    let mut id = rules["rules"]["id"].as_i64().unwrap_or(6);
    if id == 6 {
        id = 9;
    }
    let min = rules["rules"]["spmin"].as_f64().unwrap_or(180.0) / 60.0;
    let max = rules["rules"]["spmax"].as_f64().unwrap_or(540.0) / 60.0;
    if !min.is_finite() || !max.is_finite() || min > max {
        return Err("服务器配速规则无效".into());
    }
    let spavg = (duration_s as f64 / (traveled / 1_000.0) / 60.0)
        .round()
        .max(min.ceil())
        .min(max.floor());
    let payload = json!([{"fravg":0,"id":id,"sid":Uuid::new_v4().to_string(),"signpoints":[],"spavg":spavg,"state":"0","tracks":tracks,"userId":user}]);
    Ok(Preview {
        points,
        payload,
        distance_m: traveled,
        duration_s,
    })
}

pub fn run(
    session: &Session,
    points: &[Point],
    config: &RunConfig,
    plan: &Schedule,
    user: &str,
    cancel: &AtomicBool,
    emit: impl Fn(Event),
) -> Result<(), String> {
    let stopped = || cancel.load(Ordering::Relaxed);
    if stopped() {
        emit(Event::Finished {
            success: 0,
            failed: 0,
            stopped: true,
        });
        return Ok(());
    }
    emit(Event::Progress(3, "正在获取认证与跑步规则".into()));
    let (token, rules) = match session.authorize(cancel) {
        Ok(result) => result,
        Err(_) if stopped() => {
            emit(Event::Finished {
                success: 0,
                failed: 0,
                stopped: true,
            });
            return Ok(());
        }
        Err(error) => return Err(error),
    };
    if plan.dates.is_empty() {
        emit(Event::Log("没有可上传的日期，任务结束".into()));
        emit(Event::Finished {
            success: 0,
            failed: 0,
            stopped: false,
        });
        return Ok(());
    }
    let total = plan.dates.len();
    if !plan.skipped.is_empty() {
        let shown = plan
            .skipped
            .iter()
            .take(5)
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join("、");
        let more = if plan.skipped.len() > 5 {
            format!(" 等 {} 天", plan.skipped.len())
        } else {
            String::new()
        };
        emit(Event::Log(format!("跳过已有记录的日期：{shown}{more}")));
    }
    if plan.truncated {
        emit(Event::Log(format!(
            "向前查找已到头，只找到 {total} 个可上传的日期（设定 {runs} 次）",
            runs = config.runs
        )));
    }
    let mut success = 0;
    let mut failed = 0;
    for (index, date) in plan.dates.iter().enumerate() {
        if stopped() {
            break;
        }
        let date = *date;
        let offset = rand::rng().random_range(-10..=10) * 60 + rand::rng().random_range(-30..=30);
        let start = Local
            .from_local_datetime(&(date.and_time(config.time) + Duration::seconds(offset)))
            .single()
            .ok_or("该本地时间无效或处于夏令时切换区间")?
            .timestamp_millis();
        emit(Event::Log(format!(
            "生成第 {}/{} 条记录 · {}",
            index + 1,
            total,
            date
        )));
        let preview = generate(points, config, user, start, &rules)?;
        let payload = preview.payload.clone();
        emit(Event::Preview(preview));
        if stopped() {
            break;
        }
        emit(Event::Progress(
            ((index * 100 + 50) / total) as i32,
            format!("正在上传第 {}/{} 条", index + 1, total),
        ));
        // POST 只发送一次，网络结果不确定时不自动重试，以免生成重复记录。
        match session.upload(&token, &payload) {
            Ok(()) => {
                success += 1;
                emit(Event::Log(format!("第 {} 条上传成功", index + 1)));
            }
            Err(error) => {
                failed += 1;
                emit(Event::Log(format!("第 {} 条失败：{error}", index + 1)));
            }
        }
        emit(Event::Progress(
            ((index + 1) * 100 / total) as i32,
            format!("已处理 {}/{} 条", index + 1, total),
        ));
    }
    emit(Event::Finished {
        success,
        failed,
        stopped: stopped(),
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn generated_payload_preserves_contract_and_monotonic_time() {
        let points = route::parse(route::DEFAULT_ROUTE).unwrap();
        let config = RunConfig::parse("1", "4", "2026-10-15", "08:00:00").unwrap();
        let preview = generate(
            &points,
            &config,
            "offline-test",
            1_700_000_000_000,
            &json!({"rules":{"id":6,"spmin":180,"spmax":540}}),
        )
        .unwrap();
        assert!((preview.distance_m - 4_000.0).abs() < 0.1);
        assert!((900..=1_600).contains(&preview.duration_s));
        assert_eq!(preview.payload[0]["id"], 9);
        let tracks = preview.payload[0]["tracks"].as_array().unwrap();
        let mut previous = 0;
        let mut count = 0;
        for track in tracks {
            let ps = track["points"].as_array().unwrap();
            assert_eq!(track["counts"], ps.len());
            for point in ps {
                let time = point["locatetime"].as_i64().unwrap();
                assert!(time >= previous);
                previous = time;
                count += 1;
            }
        }
        assert_eq!(count, preview.points.len());
        assert!(route::jumps(&preview.points) == 0);
    }
    #[test]
    fn generated_distance_matches_target_without_fixed_allowance() {
        let points = route::parse(route::DEFAULT_ROUTE).unwrap();
        for distance in ["1.2", "1.21", "4", "5"] {
            let config = RunConfig::parse("1", distance, "2026-10-15", "08:00:00").unwrap();
            let preview = generate(
                &points,
                &config,
                "offline-test",
                1_700_000_000_000,
                &json!({"rules":{"id":6,"spmin":180,"spmax":540}}),
            )
            .unwrap();
            assert!(
                (preview.distance_m - config.distance_km * 1_000.0).abs() < 0.1,
                "target {distance} km, generated {} m",
                preview.distance_m
            );
        }
    }

    #[test]
    fn cancelled_task_never_makes_network_request() {
        let session = Session::new().unwrap();
        let config = RunConfig::parse("1", "4", "2026-10-15", "08:00:00").unwrap();
        let plan = schedule(&config, true, &HashSet::new(), None).unwrap();
        run(
            &session,
            &[],
            &config,
            &plan,
            "",
            &AtomicBool::new(true),
            |event| assert!(matches!(event, Event::Finished { stopped: true, .. })),
        )
        .unwrap();
    }

    fn day(text: &str) -> NaiveDate {
        NaiveDate::parse_from_str(text, "%Y-%m-%d").unwrap()
    }

    fn days(spec: &[&str]) -> Vec<NaiveDate> {
        spec.iter().map(|text| day(text)).collect()
    }

    fn occupied(spec: &[&str]) -> HashSet<NaiveDate> {
        days(spec).into_iter().collect()
    }

    #[test]
    fn schedule_keeps_the_plain_backfill_when_skip_is_off() {
        let config = RunConfig::parse("3", "4", "2026-10-15", "08:00:00").unwrap();
        let plan = schedule(&config, false, &occupied(&["2026-10-15"]), None).unwrap();
        assert_eq!(
            plan.dates,
            days(&["2026-10-15", "2026-10-14", "2026-10-13"])
        );
        assert!(plan.skipped.is_empty());
        assert!(!plan.truncated);
    }

    #[test]
    fn schedule_still_uploads_the_requested_count_by_moving_earlier() {
        let config = RunConfig::parse("3", "4", "2026-10-15", "08:00:00").unwrap();
        let plan = schedule(
            &config,
            true,
            &occupied(&["2026-10-15", "2026-10-13"]),
            None,
        )
        .unwrap();
        assert_eq!(
            plan.dates,
            days(&["2026-10-14", "2026-10-12", "2026-10-11"])
        );
        assert_eq!(plan.skipped, days(&["2026-10-15", "2026-10-13"]));
        assert!(!plan.truncated);
    }

    #[test]
    fn schedule_stops_at_the_semester_start() {
        let config = RunConfig::parse("3", "4", "2026-10-02", "08:00:00").unwrap();
        let taken = occupied(&["2026-10-02", "2026-10-01"]);
        let plan = schedule(&config, true, &taken, Some(day("2026-09-25"))).unwrap();
        assert_eq!(
            plan.dates,
            days(&["2026-09-30", "2026-09-29", "2026-09-28"])
        );
        assert!(!plan.truncated);
        // 学期只剩两天可跑时如实报告不足，不会跑到学期之外。
        let plan = schedule(&config, true, &taken, Some(day("2026-09-29"))).unwrap();
        assert_eq!(plan.dates, days(&["2026-09-30", "2026-09-29"]));
        assert!(plan.truncated);
    }

    #[test]
    fn schedule_bounds_the_lookback() {
        let config = RunConfig::parse("3", "4", "2026-10-15", "08:00:00").unwrap();
        let taken: HashSet<NaiveDate> = (0..=200)
            .map(|offset| day_before(config.date, offset).unwrap())
            .collect();
        let plan = schedule(&config, true, &taken, None).unwrap();
        assert!(plan.dates.is_empty());
        assert!(plan.truncated);
        assert_eq!(plan.skipped.len(), (MAX_LOOKBACK_DAYS + 1) as usize);
    }
}
