/**
 * 学期统计的纯逻辑：日期模型、日历展开与显示格式化。
 * 迁移自 Android: com.sjtu.runner.stats.SemesterStats
 *
 * 这里不碰网络也不碰 UI，方便复用；网络解析在 service/ApiService.ets 的 semesterStats()。
 */

import { formatDate, pad2 } from '../utils/FormatUtil';

/** 北京时间相对 UTC 的偏移（毫秒）。服务器与客户端都按北京时间记账。 */
const CST_OFFSET_MS: number = 8 * 3600 * 1000;
const MS_PER_DAY: number = 24 * 3600 * 1000;

/** 日历单元格状态 */
export enum DayState {
  /** 区间内没有有效记录 */
  NONE = 0,
  /** 计入成绩（服务器 state == "0"） */
  VALID = 1,
  /** 有记录但未计入成绩 */
  INVALID = 2
}

/** 取 +08:00 的「今天」（当天 00:00:00 的本地 Date） */
export function todayCst(): Date {
  const now = new Date();
  // 先把“本地时间”换算成 UTC 时刻，再加 8 小时得到北京时间
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  const cst = new Date(utcMs + CST_OFFSET_MS);
  return new Date(cst.getFullYear(), cst.getMonth(), cst.getDate());
}

/** Date -> YYYY-MM-DD，用作 Map/Set 的键 */
export function dayKey(date: Date): string {
  return formatDate(date);
}

/** 去掉时分秒，得到当天 00:00:00（本地时区） */
export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** 日期加减天数（不修改入参） */
export function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

/**
 * 学期区间。服务器给出的日期不可信：起终点颠倒或跨度过大时按「没有区间」处理，
 * 免得异常响应撑爆日历模型。
 */
export class SemesterRange {
  start: Date;
  end: Date;

  constructor(start: Date, end: Date) {
    this.start = start;
    this.end = end;
  }

  static of(start: Date, end: Date): SemesterRange | undefined {
    const span = Math.round((startOfDay(end).getTime() - startOfDay(start).getTime()) / MS_PER_DAY);
    if (span < 0 || span > 400) {
      return undefined;
    }
    return new SemesterRange(startOfDay(start), startOfDay(end));
  }
}

/** CalendarDay.day 为 0 表示空白格（月首月尾补齐、或落在学期区间之外） */
export class CalendarDay {
  day: number;
  state: DayState;

  constructor(day: number, state: DayState) {
    this.day = day;
    this.state = state;
  }
}

export class CalendarWeek {
  title: string;
  days: CalendarDay[];

  constructor(title: string, days: CalendarDay[]) {
    this.title = title;
    this.days = days;
  }
}

/** 一次学期统计的结果。未拿到的数值保持 undefined（界面显示 `--`）。 */
export class SemesterStats {
  resultKm: number | undefined = undefined;
  totalKm: number | undefined = undefined;
  percent: number | undefined = undefined;
  targetKm: number | undefined = undefined;
  semesterName: string = '本学期';
  range: SemesterRange | undefined = undefined;
  /** 有记录的日期 -> 当天状态（键为 YYYY-MM-DD） */
  runDays: Map<string, DayState> = new Map<string, DayState>();

  /** 距离本学期目标还差多少公里；目标或已完成值缺失时返回 undefined */
  remainingKm(): number | undefined {
    const target = this.targetKm;
    const done = this.resultKm;
    if (target === undefined || !Number.isFinite(target)) {
      return undefined;
    }
    if (done === undefined || !Number.isFinite(done)) {
      return undefined;
    }
    return target - done;
  }
}

/** 同一天可能有多条记录：有效记录优先，无效记录不能把它盖掉 */
export function recordDay(runDays: Map<string, DayState>, date: Date, state: DayState): void {
  const key = dayKey(date);
  if (runDays.get(key) === DayState.VALID) {
    return;
  }
  runDays.set(key, state);
}

/** 未登录时的占位日历：按月份猜一个学期区间，全部为「未跑」 */
export function placeholderWeeks(today: Date): CalendarWeek[] {
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  let range: SemesterRange | undefined;
  if (month === 1 || month === 2) {
    range = SemesterRange.of(new Date(year - 1, 8, 1), new Date(year, 0, 31));
  } else if (month >= 3 && month <= 7) {
    range = SemesterRange.of(new Date(year, 2, 1), new Date(year, 6, 31));
  } else {
    range = SemesterRange.of(new Date(year, 8, 1), new Date(year + 1, 0, 31));
  }
  if (range === undefined) {
    return [];
  }
  return calendarWeeks(range, new Map<string, DayState>());
}

/**
 * 按月份逐月展开成「周行」，周一起始，每月第一行带月份标题。
 * 行内固定 7 格，月首/月尾与学期区间之外补空白格（day = 0）。
 */
export function calendarWeeks(range: SemesterRange, runDays: Map<string, DayState>): CalendarWeek[] {
  const weeks: CalendarWeek[] = [];
  let year = range.start.getFullYear();
  let month = range.start.getMonth();
  const lastYear = range.end.getFullYear();
  const lastMonth = range.end.getMonth();
  const startMs = range.start.getTime();
  const endMs = range.end.getTime();

  while (year < lastYear || (year === lastYear && month <= lastMonth)) {
    const first = new Date(year, month, 1);
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    // Date.getDay(): 周日 = 0；换成周一起始的列偏移
    const leading = (first.getDay() + 6) % 7;
    const rows = Math.floor((leading + daysInMonth + 6) / 7);
    for (let row = 0; row < rows; row++) {
      const days: CalendarDay[] = [];
      for (let slot = 0; slot < 7; slot++) {
        const dayNumber = row * 7 + slot - leading;
        if (dayNumber < 0 || dayNumber >= daysInMonth) {
          days.push(new CalendarDay(0, DayState.NONE));
          continue;
        }
        const date = new Date(year, month, dayNumber + 1);
        const ms = date.getTime();
        if (ms < startMs || ms > endMs) {
          days.push(new CalendarDay(0, DayState.NONE));
          continue;
        }
        const state = runDays.get(dayKey(date));
        days.push(new CalendarDay(dayNumber + 1, state === undefined ? DayState.NONE : state));
      }
      const title = row === 0 ? `${year}年${month + 1}月` : '';
      weeks.push(new CalendarWeek(title, days));
    }
    if (month === 11) {
      year += 1;
      month = 0;
    } else {
      month += 1;
    }
  }
  return weeks;
}

/** 公里数显示：缺失或非法值显示 `--` */
export function formatKm(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) {
    return '--';
  }
  return `${value.toFixed(2)} km`;
}

/** 服务器的 percent 已经是百分数（"100.00"），不要再乘 100 */
export function formatPercent(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) {
    return '--';
  }
  return `${value.toFixed(1)}%`;
}

/** 服务器没给 percent 时的兜底：达标 / 总公里。分母为 0 时不算 */
export function percentFromRatio(numerator: number | undefined, denominator: number | undefined): number | undefined {
  if (numerator === undefined || !Number.isFinite(numerator)) {
    return undefined;
  }
  if (denominator === undefined || !Number.isFinite(denominator) || denominator <= 0) {
    return undefined;
  }
  return numerator / denominator * 100.0;
}

/** 自动排计划的边界：单次距离取服务器允许的 1–5 km，次数取客户端上限 30 */
export const PLAN_MIN_KM: number = 1.0;
export const PLAN_MAX_KM: number = 5.0;
export const PLAN_MAX_RUNS: number = 30;

export class AutoPlan {
  runs: number;
  distanceKm: number;

  constructor(runs: number, distanceKm: number) {
    this.runs = runs;
    this.distanceKm = distanceKm;
  }
}

/**
 * 按本学期未完成公里数反推「次数 × 单次距离」：先用单次上限摊出次数，再把缺口
 * 平摊到每次并向上取整到 0.01 km，保证这批记录足以补上缺口。
 *
 * 公里数换算成整百分公里再取整，避免 21 / 5 这类浮点误差把 4.2 变成 4.21。
 */
export function autoPlan(remainingKm: number): AutoPlan | undefined {
  if (!Number.isFinite(remainingKm) || remainingKm <= 0) {
    return undefined;
  }
  const centis = Math.round(remainingKm * 100.0);
  let runs = Math.ceil(centis / (PLAN_MAX_KM * 100.0));
  runs = Math.min(PLAN_MAX_RUNS, Math.max(1, runs));
  const distance = Math.ceil(centis / runs) / 100.0;
  return new AutoPlan(runs, Math.min(PLAN_MAX_KM, Math.max(PLAN_MIN_KM, distance)));
}

/** 填进输入框的距离：去掉多余的零，4.00 → "4"、4.50 → "4.5"、4.25 → "4.25" */
export function formatPlanKm(value: number): string {
  let text = value.toFixed(2);
  while (text.endsWith('0')) {
    text = text.substring(0, text.length - 1);
  }
  if (text.endsWith('.')) {
    text = text.substring(0, text.length - 1);
  }
  return text;
}

/** 两位补零的时分秒文本（日历页与进度卡不需要，供调用方复用时保持一致） */
export function hhmmss(hour: number, minute: number, second: number): string {
  return `${pad2(hour)}:${pad2(minute)}:${pad2(second)}`;
}
