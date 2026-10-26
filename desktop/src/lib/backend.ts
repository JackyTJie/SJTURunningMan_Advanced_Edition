import { invoke } from '@tauri-apps/api/core';

export type DayState = 'none' | 'valid' | 'invalid';

export interface Point {
  lon: number;
  lat: number;
}

export interface CalendarDay {
  day: number;
  state: DayState;
}

export interface CalendarWeek {
  title: string;
  days: CalendarDay[];
}

export interface SettingsView {
  dark: boolean;
  runs: string;
  distance: string;
  time: string;
  route: string;
  skipExisting: boolean;
}

export interface RouteView {
  name: string;
  imported: boolean;
  canDelete: boolean;
  distanceKm: number;
  pointCount: number;
}

export interface RouteDetail {
  name: string;
  imported: boolean;
  canDelete: boolean;
  points: Point[];
  distanceKm: number;
  pointCount: number;
  jumps: number;
  jumpSegments: number[];
  warning: string | null;
}

export interface Bootstrap {
  version: string;
  date: string;
  settings: SettingsView;
  routes: RouteView[];
  selected: RouteDetail;
  calendar: CalendarWeek[];
  semesterKm: string;
  semesterPercent: string;
  warning: string | null;
  logs: string[];
}

export interface PreviewView {
  summary: string;
  distanceM: number;
  durationS: number;
  points: Point[];
  jumpSegments: number[];
}

export interface RouteListResult {
  routes: RouteView[];
  selected: RouteDetail;
  selectedName: string;
  logs: string[];
}

export interface LoginPreparation {
  captcha: string;
  captchaCode: string | null;
  manual: boolean;
  notice: string;
}

export interface AuthOutcome {
  stage: 'authenticated' | 'two_factor';
  user: string;
  notice: string;
}

export type LoginMode = 'password' | 'qr';

export interface QrPreparation {
  /** 本轮扫码的序号；界面只处理序号相同的事件。 */
  generation: number;
  /** 二维码图片的 data URL。 */
  qr: string;
  notice: string;
}

/** 扫码订阅线程推给界面的事件。 */
export type QrEvent =
  | { kind: 'image'; generation: number; qr: string }
  | { kind: 'authenticated'; generation: number; user: string; notice: string }
  | { kind: 'twoFactor'; generation: number; user: string; notice: string }
  | { kind: 'failed'; generation: number; message: string };

export interface VerifyOutcome {
  verified: boolean;
  locked: boolean;
  message: string;
}

export interface PlanView {
  runs: string;
  distance: string;
}

export interface StatsPayload {
  km: string;
  percent: string;
  weeks: CalendarWeek[] | null;
  runDays: number;
  plan: PlanView | null;
  logs: string[];
  notice: string | null;
}

export interface LogoutResult {
  weeks: CalendarWeek[];
  km: string;
  percent: string;
  notice: string;
}

export interface TaskStarted {
  count: number;
  skipped: number;
  truncated: boolean;
}

export interface MapOpenResult {
  notice: string | null;
}

export interface PreviewMapResult {
  url: string;
  notice: string | null;
}

export interface PreviewRequest {
  runs: string;
  distance: string;
  date: string;
  time: string;
  route: string;
}

export interface SettingsInput {
  dark: boolean;
  runs: string;
  distance: string;
  time: string;
  route: string;
  skipExisting: boolean;
}

export interface TaskRequest extends PreviewRequest {
  skipExisting: boolean;
}

export function errorMessage(error: unknown): string {
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return '操作失败，请重试';
}

const call = <T>(command: string, args?: Record<string, unknown>) => invoke<T>(command, args);

export const backend = {
  bootstrap: () => call<Bootstrap>('bootstrap'),
  selectRoute: (name: string) => call<RouteDetail>('select_route', { name }),
  previewRoute: (request: PreviewRequest) => call<PreviewView>('preview_route', { request }),
  importRoute: (path: string) => call<RouteListResult>('import_route', { path }),
  deleteRoute: (name: string) => call<RouteListResult>('delete_route', { name }),
  saveSettings: (settings: SettingsInput) => call<void>('save_settings', { settings }),
  previewMap: (request: PreviewRequest) => call<PreviewMapResult>('preview_map', { request }),
  openPlanner: () => call<MapOpenResult>('open_planner'),
  openExternal: (kind: 'shuiyuan' | 'project') => call<void>('open_external', { kind }),
  prepareLogin: () => call<LoginPreparation>('prepare_login'),
  prepareQrLogin: () => call<QrPreparation>('prepare_qr_login'),
  submitLogin: (username: string, password: string, captcha: string) =>
    call<AuthOutcome>('submit_login', { username, password, captcha }),
  sendCode: (method: string) => call<string>('send_code', { method }),
  verifyCode: (code: string) => call<VerifyOutcome>('verify_code', { code }),
  cancelLogin: () => call<void>('cancel_login'),
  logout: () => call<LogoutResult>('logout'),
  syncStats: (runs: string, distance: string) =>
    call<StatsPayload>('sync_stats', { runs, distance }),
  checkUpdate: () => call<string>('check_update'),
  startTask: (request: TaskRequest) => call<TaskStarted>('start_task', { request }),
  stopTask: () => call<void>('stop_task'),
  uiReady: () => call<void>('ui_ready'),
};

export interface AppLogEvent {
  message: string;
}
export interface TaskProgressEvent {
  value: number;
  status: string;
}
export interface TaskStatusEvent {
  status: string;
}
export interface TaskPreviewEvent extends PreviewView {}
export interface TaskFinishedEvent {
  success: number;
  failed: number;
  stopped: boolean;
  status: string;
  progress: number;
}
export interface TaskErrorEvent {
  message: string;
  status: string;
}
