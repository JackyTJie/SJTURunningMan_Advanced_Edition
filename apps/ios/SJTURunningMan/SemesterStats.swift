//
//  SemesterStats.swift
//  SJTURunningMan
//
//  学期统计的纯逻辑：日期模型、日历展开与显示格式化。
//  行为对齐安卓版 stats/SemesterStats.kt，与电脑版 stats.rs 同构。
//  这里不碰网络也不碰 UI，方便单独验证；网络解析在 ApiService.semesterStats。
//

import Foundation

// MARK: - 日期模型

/// 服务器与客户端都按北京时间记账，日历展开与「今天」都用这个时区。
enum CST {
    static let calendar: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Asia/Shanghai") ?? .current
        return calendar
    }()
}

/// 有记录时 +08:00 的「今天」。
func todayCST() -> Date {
    CST.calendar.startOfDay(for: Date())
}

/// 日期选择器给出的是本地时区的「日历日期」，按年月日重建北京时间的那一天，
/// 这样日历格与已有记录才能按同一天对上。
func cstDay(fromLocal date: Date) -> Date {
    let local = Calendar.current.dateComponents([.year, .month, .day], from: date)
    return CST.calendar.date(from: DateComponents(year: local.year, month: local.month, day: local.day))
        ?? CST.calendar.startOfDay(for: date)
}

func addDays(_ date: Date, _ delta: Int) -> Date {
    CST.calendar.date(byAdding: .day, value: delta, to: date) ?? date
}

enum DayState {
    /// 区间内没有有效记录。
    case none
    /// 计入成绩（服务器 `state == "0"`）。
    case valid
    /// 有记录但未计入成绩。
    case invalid
}

struct SemesterRange {
    let start: Date
    let end: Date

    /// 服务器给出的日期不可信：起终点颠倒或跨度过大时按「没有区间」处理，
    /// 免得异常响应撑爆日历模型。
    static func of(start: Date, end: Date) -> SemesterRange? {
        let span = CST.calendar.dateComponents([.day], from: start, to: end).day ?? 0
        if span < 0 || span > 400 {
            return nil
        }
        return SemesterRange(start: start, end: end)
    }
}

/// `day == 0` 表示空白格（月首月尾补齐、或落在学期区间之外）。
struct CalendarDay {
    let day: Int
    let state: DayState
}

struct CalendarWeek {
    /// 每月第一行给出「2026年9月」，其余行为空字符串。
    let title: String
    let days: [CalendarDay]
}

struct SemesterStats {
    var resultKm: Double?
    var totalKm: Double?
    var percent: Double?
    var targetKm: Double?
    var semesterName = ""
    var range: SemesterRange?
    var runDays: [Date: DayState] = [:]

    var remainingKm: Double? {
        guard let target = finiteKm(targetKm), let done = finiteKm(resultKm) else { return nil }
        return target - done
    }
}

/// 服务器偶尔给出 NaN / 无穷，取不出来就当没有这个数。
private func finiteKm(_ value: Double?) -> Double? {
    guard let value, value.isFinite else { return nil }
    return value
}

/// 同一天可能有多条记录：有效记录优先，无效记录不能把它盖掉。
func recordDay(_ runDays: inout [Date: DayState], _ date: Date, _ state: DayState) {
    if runDays[date] == .valid {
        return
    }
    runDays[date] = state
}

// MARK: - 日历展开

/// 未登录时的占位日历：按月份猜一个学期区间，全部为「未跑」。
func placeholderWeeks(_ today: Date) -> [CalendarWeek] {
    let year = CST.calendar.component(.year, from: today)
    let month = CST.calendar.component(.month, from: today)
    let range: SemesterRange?
    switch month {
    case 1, 2:
        range = semesterRange(year - 1, 9, 1, year, 1, 31)
    case 3...7:
        range = semesterRange(year, 3, 1, year, 7, 31)
    default:
        range = semesterRange(year, 9, 1, year + 1, 1, 31)
    }
    guard let range else { return [] }
    return calendarWeeks(range: range, runDays: [:])
}

private func semesterRange(
    _ startYear: Int, _ startMonth: Int, _ startDay: Int,
    _ endYear: Int, _ endMonth: Int, _ endDay: Int
) -> SemesterRange? {
    guard let start = CST.calendar.date(from: DateComponents(year: startYear, month: startMonth, day: startDay)),
          let end = CST.calendar.date(from: DateComponents(year: endYear, month: endMonth, day: endDay)) else {
        return nil
    }
    return SemesterRange.of(start: start, end: end)
}

/// 按月份逐月展开成「周行」，周一起始，每月第一行带月份标题。
func calendarWeeks(range: SemesterRange, runDays: [Date: DayState]) -> [CalendarWeek] {
    var weeks: [CalendarWeek] = []
    var year = CST.calendar.component(.year, from: range.start)
    var month = CST.calendar.component(.month, from: range.start)
    let lastYear = CST.calendar.component(.year, from: range.end)
    let lastMonth = CST.calendar.component(.month, from: range.end)

    while year < lastYear || (year == lastYear && month <= lastMonth) {
        guard let first = CST.calendar.date(from: DateComponents(year: year, month: month, day: 1)) else { break }
        let daysInMonth = CST.calendar.range(of: .day, in: .month, for: first)?.count ?? 30
        // 周一起始：周一偏移 0，周日偏移 6。
        let leading = (CST.calendar.component(.weekday, from: first) + 5) % 7
        let rows = (leading + daysInMonth + 6) / 7

        for row in 0..<rows {
            var days: [CalendarDay] = []
            for slot in 0..<7 {
                let dayNumber = row * 7 + slot - leading
                if dayNumber < 0 || dayNumber >= daysInMonth {
                    days.append(CalendarDay(day: 0, state: .none))
                    continue
                }
                guard let date = CST.calendar.date(
                    from: DateComponents(year: year, month: month, day: dayNumber + 1)
                ) else {
                    days.append(CalendarDay(day: 0, state: .none))
                    continue
                }
                if date < range.start || date > range.end {
                    days.append(CalendarDay(day: 0, state: .none))
                    continue
                }
                days.append(CalendarDay(day: dayNumber + 1, state: runDays[date] ?? .none))
            }
            let title = row == 0 ? "\(year)年\(month)月" : ""
            weeks.append(CalendarWeek(title: title, days: days))
        }

        if month == 12 {
            year += 1
            month = 1
        } else {
            month += 1
        }
    }
    return weeks
}

// MARK: - 显示格式化

func formatKm(_ value: Double?) -> String {
    guard let value = finiteKm(value) else { return "--" }
    return String(format: "%.2f km", value)
}

/// 服务器的 `percent` 已经是百分数（`"100.00"`），不要再乘 100。
func formatPercent(_ value: Double?) -> String {
    guard let value = finiteKm(value) else { return "--" }
    return String(format: "%.1f%%", value)
}

/// 服务器没给 `percent` 时的兜底：达标 / 总公里。分母为 0 时不算。
func percentFromRatio(_ numerator: Double?, _ denominator: Double?) -> Double? {
    guard let num = finiteKm(numerator), let den = finiteKm(denominator), den > 0 else { return nil }
    return num / den * 100.0
}

// MARK: - 自动排计划

/// 边界：单次距离取服务器允许的 1–5 km，次数取客户端上限 30。
let planMinKm = 1.0
let planMaxKm = 5.0
let planMaxRuns = 30

struct AutoPlan: Equatable {
    let runs: Int
    let distanceKm: Double
}

/// 按本学期未完成公里数反推「次数 × 单次距离」：先用单次上限摊出次数，再把缺口
/// 平摊到每次并向上取整到 0.01 km，保证这批记录足以补上缺口。
///
/// 公里数换算成整百分公里再取整，避免 `21 / 5` 这类浮点误差把 4.2 变成 4.21。
func autoPlan(_ remainingKm: Double) -> AutoPlan? {
    guard let remaining = finiteKm(remainingKm), remaining > 0 else { return nil }

    let centis = (remaining * 100.0).rounded()
    let runs = min(max(Int(ceil(centis / (planMaxKm * 100.0))), 1), planMaxRuns)
    let distance = ceil(centis / Double(runs)) / 100.0
    return AutoPlan(runs: runs, distanceKm: min(max(distance, planMinKm), planMaxKm))
}

/// 填进输入框的距离：去掉多余的零，`4.00 → "4"`、`4.50 → "4.5"`、`4.25 → "4.25"`。
func formatPlanKm(_ value: Double) -> String {
    var text = String(format: "%.2f", value)
    while text.hasSuffix("0") { text.removeLast() }
    if text.hasSuffix(".") { text.removeLast() }
    return text
}
