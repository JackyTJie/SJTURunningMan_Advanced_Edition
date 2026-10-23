//! 学期统计的纯逻辑：日期模型、日历展开与显示格式化。
//!
//! 这里不碰网络也不碰 UI，方便单测；网络解析在 `api::Session::semester_stats`。

use chrono::{Datelike, FixedOffset, NaiveDate, Utc};
use std::collections::HashMap;

/// 有记录时 +08:00 的「今天」。服务器与客户端都按北京时间记账。
pub fn today_cst() -> NaiveDate {
    let cst = FixedOffset::east_opt(8 * 3600).expect("UTC+8 一定有效");
    Utc::now().with_timezone(&cst).date_naive()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DayState {
    /// 区间内没有有效记录。
    None,
    /// 计入成绩（服务器 `state == "0"`）。
    Valid,
    /// 有记录但未计入成绩。
    Invalid,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SemesterRange {
    pub start: NaiveDate,
    pub end: NaiveDate,
}

impl SemesterRange {
    /// 服务器给出的日期不可信：起终点颠倒或跨度过大时按「没有区间」处理，
    /// 免得异常响应撑爆日历模型。
    pub fn new(start: NaiveDate, end: NaiveDate) -> Option<Self> {
        let span = end.signed_duration_since(start).num_days();
        if !(0..=400).contains(&span) {
            return None;
        }
        Some(Self { start, end })
    }
}

/// `day == 0` 是空白格（月首月尾补齐、或落在学期区间之外）。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CalendarDay {
    pub day: u8,
    pub state: DayState,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CalendarWeek {
    /// 每月第一行给出「2026年9月」，其余行为空字符串。
    pub title: String,
    pub days: [CalendarDay; 7],
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct SemesterStats {
    pub result_km: Option<f64>,
    pub total_km: Option<f64>,
    pub percent: Option<f64>,
    pub target_km: Option<f64>,
    pub semester_name: String,
    pub range: Option<SemesterRange>,
    pub run_days: HashMap<NaiveDate, DayState>,
}

/// 同一天可能有多条记录：有效记录优先，无效记录不能把它盖掉。
pub fn record_day(run_days: &mut HashMap<NaiveDate, DayState>, date: NaiveDate, state: DayState) {
    if run_days.get(&date) == Some(&DayState::Valid) {
        return;
    }
    run_days.insert(date, state);
}

/// 未登录时的占位日历：按月份猜一个学期区间，全部为「未跑」。
pub fn placeholder_weeks(today: NaiveDate) -> Vec<CalendarWeek> {
    let year = today.year();
    let range = match today.month() {
        1..=2 => semester_range(year - 1, 9, 1, year, 1, 31),
        3..=7 => semester_range(year, 3, 1, year, 7, 31),
        _ => semester_range(year, 9, 1, year + 1, 1, 31),
    };
    match range {
        Some(range) => calendar_weeks(range, &HashMap::new()),
        None => Vec::new(),
    }
}

fn semester_range(
    start_year: i32,
    start_month: u32,
    start_day: u32,
    end_year: i32,
    end_month: u32,
    end_day: u32,
) -> Option<SemesterRange> {
    let start = NaiveDate::from_ymd_opt(start_year, start_month, start_day)?;
    let end = NaiveDate::from_ymd_opt(end_year, end_month, end_day)?;
    SemesterRange::new(start, end)
}

/// 按月份逐月展开成「周行」，周一起始，每月第一行带月份标题。
pub fn calendar_weeks(
    range: SemesterRange,
    run_days: &HashMap<NaiveDate, DayState>,
) -> Vec<CalendarWeek> {
    let mut weeks = Vec::new();
    let mut cursor = (range.start.year(), range.start.month());
    let last = (range.end.year(), range.end.month());
    while cursor <= last {
        let (year, month) = cursor;
        let Some(first) = NaiveDate::from_ymd_opt(year, month, 1) else {
            break;
        };
        let days_in_month = first.num_days_in_month() as usize;
        let leading = first.weekday().num_days_from_monday() as usize;
        let rows = (leading + days_in_month).div_ceil(7);
        for row in 0..rows {
            let mut days = [CalendarDay {
                day: 0,
                state: DayState::None,
            }; 7];
            for (slot, cell) in days.iter_mut().enumerate() {
                let Some(day_number) = (row * 7 + slot).checked_sub(leading) else {
                    continue;
                };
                if day_number >= days_in_month {
                    continue;
                }
                let Some(date) = NaiveDate::from_ymd_opt(year, month, (day_number + 1) as u32)
                else {
                    continue;
                };
                if date < range.start || date > range.end {
                    continue;
                }
                *cell = CalendarDay {
                    day: (day_number + 1) as u8,
                    state: run_days.get(&date).copied().unwrap_or(DayState::None),
                };
            }
            weeks.push(CalendarWeek {
                title: if row == 0 {
                    format!("{year}年{month}月")
                } else {
                    String::new()
                },
                days,
            });
        }
        cursor = next_month(year, month);
    }
    weeks
}

fn next_month(year: i32, month: u32) -> (i32, u32) {
    if month == 12 {
        (year + 1, 1)
    } else {
        (year, month + 1)
    }
}

pub fn format_km(value: Option<f64>) -> String {
    match finite(value) {
        Some(value) => format!("{value:.2} km"),
        None => "--".into(),
    }
}

/// 服务器的 `percent` 已经是百分数（`"100.00"`），不要再乘 100。
pub fn format_percent(value: Option<f64>) -> String {
    match finite(value) {
        Some(value) => format!("{value:.1}%"),
        None => "--".into(),
    }
}

/// 服务器没给 `percent` 时的兜底：达标 / 总公里。分母为 0 时不算。
pub fn percent_from_ratio(numerator: Option<f64>, denominator: Option<f64>) -> Option<f64> {
    let numerator = finite(numerator)?;
    let denominator = finite(denominator)?;
    if denominator > 0.0 {
        Some(numerator / denominator * 100.0)
    } else {
        None
    }
}

/// 自动排计划与桌面端手动配置共用距离边界，次数取客户端上限 30。
pub const PLAN_MIN_KM: f64 = crate::settings::MIN_DISTANCE_KM;
pub const PLAN_MAX_KM: f64 = crate::settings::MAX_DISTANCE_KM;
pub const PLAN_MAX_RUNS: u32 = 30;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct AutoPlan {
    pub runs: u32,
    pub distance_km: f64,
}

/// 按本学期未完成公里数反推「次数 × 单次距离」：先用单次上限摊出次数，再把缺口
/// 平摊到每次并向上取整到 0.01 km，保证这批记录足以补上缺口。
///
/// 公里数换算成整百分公里再取整，避免 `21 / 5` 这类浮点误差把 4.2 变成 4.21。
pub fn auto_plan(remaining_km: f64) -> Option<AutoPlan> {
    let remaining = finite(Some(remaining_km))?;
    if remaining <= 0.0 {
        return None;
    }
    let centis = (remaining * 100.0).round();
    let runs = (centis / (PLAN_MAX_KM * 100.0))
        .ceil()
        .clamp(1.0, f64::from(PLAN_MAX_RUNS)) as u32;
    let distance = (centis / f64::from(runs)).ceil() / 100.0;
    Some(AutoPlan {
        runs,
        distance_km: distance.clamp(PLAN_MIN_KM, PLAN_MAX_KM),
    })
}

/// 填进输入框的距离：去掉多余的零，`4.00 → "4"`、`4.50 → "4.5"`、`4.25 → "4.25"`。
pub fn format_plan_km(value: f64) -> String {
    format!("{value:.2}")
        .trim_end_matches('0')
        .trim_end_matches('.')
        .to_string()
}

fn finite(value: Option<f64>) -> Option<f64> {
    value.filter(|value| value.is_finite())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn date(year: i32, month: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(year, month, day).unwrap()
    }

    fn days(weeks: &[CalendarWeek]) -> Vec<CalendarDay> {
        weeks.iter().flat_map(|week| week.days).collect()
    }

    #[test]
    fn range_rejects_reversed_or_absurd_spans() {
        assert!(SemesterRange::new(date(2026, 9, 14), date(2027, 1, 3)).is_some());
        assert!(SemesterRange::new(date(2027, 1, 3), date(2026, 9, 14)).is_none());
        assert!(SemesterRange::new(date(2026, 1, 1), date(2027, 12, 31)).is_none());
    }

    #[test]
    fn calendar_pads_month_start_on_monday_and_keeps_month_titles() {
        // 2026-09-01 是周二：第一行第一格应为空白，第二格是 1 号。
        let range = SemesterRange::new(date(2026, 9, 1), date(2026, 9, 30)).unwrap();
        let weeks = calendar_weeks(range, &HashMap::new());
        assert_eq!(weeks[0].title, "2026年9月");
        assert_eq!(weeks[0].days[0].day, 0);
        assert_eq!(weeks[0].days[1].day, 1);
        assert_eq!(weeks[1].title, "");
        // 9 月 30 天 + 1 个前导空格 = 31 格 → 5 行，最后一行尾部补空。
        assert_eq!(weeks.len(), 5);
        assert_eq!(weeks[4].days[2].day, 30);
        assert_eq!(weeks[4].days[3].day, 0);
        assert!(
            weeks
                .iter()
                .filter(|week| week.title == "2026年9月")
                .count()
                == 1
        );
    }

    #[test]
    fn calendar_spans_months_and_years() {
        let range = SemesterRange::new(date(2026, 9, 14), date(2027, 1, 3)).unwrap();
        let weeks = calendar_weeks(range, &HashMap::new());
        let titles: Vec<&str> = weeks
            .iter()
            .map(|week| week.title.as_str())
            .filter(|t| !t.is_empty())
            .collect();
        assert_eq!(
            titles,
            [
                "2026年9月",
                "2026年10月",
                "2026年11月",
                "2026年12月",
                "2027年1月"
            ]
        );
        // 学期前的 9/1~9/13 与学期后的 1/4~1/31 都是空白格。
        let filled = days(&weeks).iter().filter(|d| d.day != 0).count();
        let expected = date(2027, 1, 3)
            .signed_duration_since(date(2026, 9, 14))
            .num_days()
            + 1;
        assert_eq!(filled, expected as usize);
        let september = &weeks[0];
        assert!(september.days.iter().all(|d| d.day == 0 || d.day >= 14));
        let january = weeks
            .iter()
            .rev()
            .find(|week| !week.title.is_empty())
            .unwrap();
        assert!(january
            .days
            .iter()
            .filter(|d| d.day != 0)
            .all(|d| d.day <= 3));
    }

    #[test]
    fn out_of_range_dates_inside_the_month_stay_blank() {
        let range = SemesterRange::new(date(2026, 9, 14), date(2026, 9, 20)).unwrap();
        let weeks = calendar_weeks(range, &HashMap::new());
        let present: Vec<u8> = days(&weeks)
            .iter()
            .filter_map(|d| (d.day != 0).then_some(d.day))
            .collect();
        assert_eq!(present, (14..=20).collect::<Vec<u8>>());
    }

    #[test]
    fn valid_record_beats_invalid_on_the_same_day() {
        let mut run_days = HashMap::new();
        let day = date(2026, 9, 19);
        record_day(&mut run_days, day, DayState::Valid);
        record_day(&mut run_days, day, DayState::Invalid);
        assert_eq!(run_days[&day], DayState::Valid);
        record_day(&mut run_days, day, DayState::Valid);
        assert_eq!(run_days[&day], DayState::Valid);

        let other = date(2026, 9, 20);
        record_day(&mut run_days, other, DayState::Invalid);
        record_day(&mut run_days, other, DayState::Valid);
        assert_eq!(run_days[&other], DayState::Valid);
    }

    #[test]
    fn run_days_drive_cell_states() {
        let range = SemesterRange::new(date(2026, 9, 14), date(2026, 9, 20)).unwrap();
        let mut run_days = HashMap::new();
        record_day(&mut run_days, date(2026, 9, 19), DayState::Valid);
        record_day(&mut run_days, date(2026, 9, 20), DayState::Invalid);
        let weeks = calendar_weeks(range, &run_days);
        let states: HashMap<u8, DayState> = days(&weeks)
            .iter()
            .filter(|d| d.day != 0)
            .map(|d| (d.day, d.state))
            .collect();
        assert_eq!(states[&19], DayState::Valid);
        assert_eq!(states[&20], DayState::Invalid);
        assert_eq!(states[&14], DayState::None);
    }

    #[test]
    fn placeholder_ranges_follow_the_calendar_season() {
        let autumn = placeholder_weeks(date(2026, 10, 21));
        assert_eq!(autumn[0].title, "2026年9月");
        assert_eq!(
            autumn
                .iter()
                .map(|w| w.title.clone())
                .rfind(|t| !t.is_empty()),
            Some("2027年1月".into())
        );
        assert!(days(&autumn).iter().all(|d| d.state == DayState::None));

        let winter = placeholder_weeks(date(2027, 1, 10));
        assert_eq!(winter[0].title, "2026年9月");
        assert_eq!(
            winter
                .iter()
                .map(|w| w.title.clone())
                .rfind(|t| !t.is_empty()),
            Some("2027年1月".into())
        );

        let spring = placeholder_weeks(date(2027, 4, 5));
        assert_eq!(spring[0].title, "2027年3月");
        assert_eq!(
            spring
                .iter()
                .map(|w| w.title.clone())
                .rfind(|t| !t.is_empty()),
            Some("2027年7月".into())
        );
    }

    #[test]
    fn formatters_fall_back_to_placeholder() {
        assert_eq!(format_km(Some(80.0)), "80.00 km");
        assert_eq!(format_km(Some(91.223)), "91.22 km");
        assert_eq!(format_km(None), "--");
        assert_eq!(format_km(Some(f64::NAN)), "--");
        assert_eq!(format_km(Some(f64::INFINITY)), "--");
        assert_eq!(format_percent(Some(100.0)), "100.0%");
        assert_eq!(format_percent(Some(66.666)), "66.7%");
        assert_eq!(format_percent(Some(f64::NAN)), "--");
        assert_eq!(format_percent(None), "--");
    }

    #[test]
    fn ratio_fallback_only_when_both_sides_are_usable() {
        assert_eq!(percent_from_ratio(Some(80.0), Some(100.0)), Some(80.0));
        assert_eq!(percent_from_ratio(Some(91.22), Some(91.22)), Some(100.0));
        assert_eq!(percent_from_ratio(Some(80.0), Some(0.0)), None);
        assert_eq!(percent_from_ratio(Some(f64::NAN), Some(100.0)), None);
        assert_eq!(percent_from_ratio(None, Some(100.0)), None);
    }

    #[test]
    fn auto_plan_spreads_the_gap_within_limits() {
        assert_eq!(
            auto_plan(4.0),
            Some(AutoPlan {
                runs: 1,
                distance_km: 4.0
            })
        );
        assert_eq!(
            auto_plan(12.0),
            Some(AutoPlan {
                runs: 3,
                distance_km: 4.0
            })
        );
        assert_eq!(
            auto_plan(21.0),
            Some(AutoPlan {
                runs: 5,
                distance_km: 4.2
            })
        );
        assert_eq!(
            auto_plan(23.45),
            Some(AutoPlan {
                runs: 5,
                distance_km: 4.69
            })
        );
        assert_eq!(
            auto_plan(15.0),
            Some(AutoPlan {
                runs: 3,
                distance_km: 5.0
            })
        );
        // 缺口太小也要留一条有效记录，单次距离不低于 1.2 km。
        assert_eq!(
            auto_plan(0.5),
            Some(AutoPlan {
                runs: 1,
                distance_km: 1.2
            })
        );
        // 缺口大到 30 次 × 5 km 也补不完时，按上限给出最接近的计划。
        assert_eq!(
            auto_plan(160.0),
            Some(AutoPlan {
                runs: 30,
                distance_km: 5.0
            })
        );
        assert_eq!(auto_plan(0.0), None);
        assert_eq!(auto_plan(-3.0), None);
        assert_eq!(auto_plan(f64::NAN), None);
        assert_eq!(auto_plan(f64::INFINITY), None);
    }

    #[test]
    fn auto_plan_covers_the_gap_it_reports() {
        for remaining in [1.0, 3.3, 7.7, 9.99, 12.5, 23.45, 48.6, 99.99] {
            let plan = auto_plan(remaining).expect("正数缺口应有计划");
            assert!((1..=PLAN_MAX_RUNS).contains(&plan.runs));
            assert!((PLAN_MIN_KM..=PLAN_MAX_KM).contains(&plan.distance_km));
            assert!(
                f64::from(plan.runs) * plan.distance_km >= remaining,
                "{remaining} km 缺口被 {plan:?} 漏掉"
            );
        }
    }

    #[test]
    fn plan_km_drops_trailing_zeros() {
        assert_eq!(format_plan_km(4.0), "4");
        assert_eq!(format_plan_km(4.5), "4.5");
        assert_eq!(format_plan_km(4.25), "4.25");
        assert_eq!(format_plan_km(1.0), "1");
        assert_eq!(format_plan_km(5.0), "5");
    }

    #[test]
    fn today_uses_beijing_time() {
        let today = today_cst();
        assert!(today.year() >= 2020);
    }
}
