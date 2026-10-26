/**
 * 上传日期的排期规则：把这一批记录落在哪些日期上。
 * 迁移自 Android: com.sjtu.runner.stats.RunSchedule
 */

import { dayKey, addDays, startOfDay } from './SemesterStats';

/** 跳过已有记录时最多向前翻多少天，避免一路翻到学期之外 */
export const MAX_LOOKBACK_DAYS: number = 120;

export class RunSchedule {
  /** 实际要上传的日期，从「结束日期」向前排列 */
  dates: Date[];
  /** 因为已经有记录而被跳过的日期 */
  skipped: Date[];
  /** 向前翻到上限或学期起点仍未凑够设定的次数 */
  truncated: boolean;

  constructor(dates: Date[], skipped: Date[], truncated: boolean) {
    this.dates = dates;
    this.skipped = skipped;
    this.truncated = truncated;
  }
}

/**
 * 决定这批记录落在哪些日期。
 * 开启「跳过已有记录」后仍然上传设定的次数，只是把已有记录的那几天往后（更早）挪；
 * 关闭时保持原来的连续向前生成。
 *
 * @param endDate 结束日期（含）
 * @param runs 设定次数
 * @param skipExisting 是否跳过已有记录的日期
 * @param occupied 已有记录的日期键集合（YYYY-MM-DD）
 * @param earliest 允许的最早日期（学期起点）；undefined 表示不限制
 */
export function buildSchedule(endDate: Date, runs: number, skipExisting: boolean,
  occupied: Set<string>, earliest: Date | undefined): RunSchedule {
  const dates: Date[] = [];
  const skipped: Date[] = [];
  const end = startOfDay(endDate);

  if (!skipExisting) {
    for (let index = 0; index < runs; index++) {
      dates.push(addDays(end, -index));
    }
    return new RunSchedule(dates, skipped, false);
  }

  const earliestMs = earliest === undefined ? undefined : startOfDay(earliest).getTime();
  let offset = 0;
  let truncated = false;
  while (dates.length < runs) {
    const date = addDays(end, -offset);
    if (offset > MAX_LOOKBACK_DAYS || (earliestMs !== undefined && date.getTime() < earliestMs)) {
      truncated = true;
      break;
    }
    if (occupied.has(dayKey(date))) {
      skipped.push(date);
    } else {
      dates.push(date);
    }
    offset += 1;
  }
  return new RunSchedule(dates, skipped, truncated);
}

/** 日志里那句「跳过已有记录的日期」：最多列出前 5 天，再多只报数量 */
export function formatSkippedDays(skipped: Date[]): string {
  if (skipped.length === 0) {
    return '';
  }
  const shown: string[] = [];
  const limit = Math.min(5, skipped.length);
  for (let i = 0; i < limit; i++) {
    shown.push(dayKey(skipped[i]));
  }
  const joined = shown.join('、');
  if (skipped.length > 5) {
    return `跳过已有记录的日期：${joined} 等 ${skipped.length} 天`;
  }
  return `跳过已有记录的日期：${joined}`;
}
