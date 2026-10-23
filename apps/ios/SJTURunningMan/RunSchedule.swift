//
//  RunSchedule.swift
//  SJTURunningMan
//
//  决定这批记录落在哪些日期，行为对齐安卓版 stats/RunSchedule.kt。
//

import Foundation

/// 跳过已有记录时最多向前翻多少天，避免一路翻到学期之外。
let maxLookbackDays = 120

struct RunSchedule {
    /// 实际要上传的日期，从「结束日期」向前排列。
    let dates: [Date]
    /// 因为已经有记录而被跳过的日期。
    let skipped: [Date]
    /// 向前翻到上限或学期起点仍未凑够设定的次数。
    let truncated: Bool
}

/// 开启「跳过已有记录」后仍然上传设定的次数，只是把已有记录的那几天往后（更早）挪；
/// 关闭时保持原来的连续向前生成。
func buildSchedule(
    endDate: Date,
    runs: Int,
    skipExisting: Bool,
    occupied: Set<Date>,
    earliest: Date?
) -> RunSchedule {
    var dates: [Date] = []
    var skipped: [Date] = []

    if !skipExisting {
        for index in 0..<runs {
            dates.append(addDays(endDate, -index))
        }
        return RunSchedule(dates: dates, skipped: skipped, truncated: false)
    }

    var offset = 0
    var truncated = false
    while dates.count < runs {
        let date = addDays(endDate, -offset)
        if offset > maxLookbackDays || (earliest != nil && date < earliest!) {
            truncated = true
            break
        }
        if occupied.contains(date) {
            skipped.append(date)
        } else {
            dates.append(date)
        }
        offset += 1
    }
    return RunSchedule(dates: dates, skipped: skipped, truncated: truncated)
}

/// 日志里那句「跳过已有记录的日期」：最多列出前 5 天，再多只报数量。
func formatSkippedDays(_ skipped: [Date]) -> String {
    if skipped.isEmpty {
        return ""
    }
    let shown = skipped.prefix(5).map { isoDay($0) }.joined(separator: "、")
    if skipped.count > 5 {
        return "跳过已有记录的日期：\(shown) 等 \(skipped.count) 天"
    }
    return "跳过已有记录的日期：\(shown)"
}

/// 北京时间那一天的 `yyyy-MM-dd`。
func isoDay(_ date: Date) -> String {
    let comps = CST.calendar.dateComponents([.year, .month, .day], from: date)
    return String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, comps.day ?? 0)
}
