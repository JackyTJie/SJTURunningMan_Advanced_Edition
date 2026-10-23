import { useEffect, useRef, type ReactNode } from 'react';
import type { MdNavigationDrawer } from '../types/md';
import { SemesterProgress } from './SemesterProgress';

export type Page = 'workbench' | 'routes' | 'logs' | 'about';

export const PAGE_META: Record<Page, { title: string; subtitle: string; icon: string }> = {
  workbench: {
    title: '跑步工作台',
    subtitle: '配置本次计划，预览轨迹后开始上传。',
    icon: 'dashboard',
  },
  routes: {
    title: '路线管理',
    subtitle: '整理 BD09 路线，导入后保留独立副本。',
    icon: 'route',
  },
  logs: {
    title: '任务日志',
    subtitle: '查看学期打卡与本次会话的运行记录。',
    icon: 'history',
  },
  about: {
    title: '关于软件',
    subtitle: '版本、更新与使用说明。',
    icon: 'info',
  },
};

const NAV: { id: Page; label: string; icon: string }[] = [
  { id: 'workbench', label: '跑步工作台', icon: 'dashboard' },
  { id: 'routes', label: '路线管理', icon: 'route' },
  { id: 'logs', label: '任务日志', icon: 'history' },
  { id: 'about', label: '关于软件', icon: 'info' },
];

interface SidebarProps {
  page: Page;
  onNavigate: (page: Page) => void;
  version: string;
  user: string;
  loggedIn: boolean;
}

/** Keep the domain for recognition, but never expose the complete account name. */
function maskAccount(user: string): string {
  const account = user.trim();
  if (!account) return '***';
  const at = account.lastIndexOf('@');
  const name = Array.from(at >= 0 ? account.slice(0, at) : account);
  const prefix = name.slice(0, Math.min(2, Math.max(0, name.length - 1))).join('');
  return `${prefix}***${at >= 0 ? account.slice(at) : ''}`;
}

export function Sidebar({ page, onNavigate, version, user, loggedIn }: SidebarProps) {
  const ref = useRef<MdNavigationDrawer>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    element.opened = true;
  }, []);
  return (
    <md-navigation-drawer ref={ref} className="app-drawer" aria-label="主导航">
      <div className="drawer-inner">
        <div className="brand">
          <img src="/app-icon.png" alt="" className="brand-icon" />
          <div className="brand-copy">
            <span className="brand-name">RunningMan</span>
            <span className="brand-sub">SJTU · 交我润</span>
          </div>
        </div>
        <md-list className="nav-list" type="button">
          {NAV.map((item) => (
            <md-list-item
              key={item.id}
              type="button"
              className={`nav-item${page === item.id ? ' is-active' : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={page === item.id ? 'page' : undefined}
            >
              <md-icon slot="start" aria-hidden="true">
                {item.icon}
              </md-icon>
              {item.label}
            </md-list-item>
          ))}
        </md-list>
        <div className="drawer-spacer" />
        <div className="drawer-status">
          <span className={`status-dot${loggedIn ? ' is-online' : ''}`} />
          <span>{loggedIn ? `已连接 · ${maskAccount(user)}` : '未登录 · 可离线预览'}</span>
        </div>
        <div className="drawer-foot">
          <span>Material Design 3</span>
          <span className="mono">{version}</span>
        </div>
      </div>
    </md-navigation-drawer>
  );
}

interface TopBarProps {
  page: Page;
  dark: boolean;
  loggedIn: boolean;
  busy: boolean;
  onToggleTheme: () => void;
  onAccount: () => void;
}

export function TopBar({ page, dark, loggedIn, busy, onToggleTheme, onAccount }: TopBarProps) {
  const meta = PAGE_META[page];
  return (
    <header className="top-bar">
      <div className="top-bar-copy">
        <h1>{meta.title}</h1>
        <p>{meta.subtitle}</p>
      </div>
      <div className="top-bar-actions">
        <md-icon-button
          aria-label={dark ? '切换到浅色外观' : '切换到深色外观'}
          title={dark ? '切换到浅色外观' : '切换到深色外观'}
          onClick={onToggleTheme}
        >
          <md-icon aria-hidden="true">{dark ? 'light_mode' : 'dark_mode'}</md-icon>
        </md-icon-button>
        <md-filled-tonal-button onClick={onAccount} disabled={busy}>
          <md-icon slot="icon" aria-hidden="true">
            {loggedIn ? 'logout' : 'login'}
          </md-icon>
          {loggedIn ? '退出账号' : '登录账号'}
        </md-filled-tonal-button>
      </div>
    </header>
  );
}

interface TaskBarProps {
  page: Page;
  busy: boolean;
  progress: number;
  status: string;
  loggedIn: boolean;
  semesterKm: string;
  semesterPercent: string;
  runDays: number;
  compact: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function TaskBar({ page, busy, progress, status, loggedIn, semesterKm, semesterPercent, runDays, compact, onStart, onStop }: TaskBarProps) {
  const percent = Number.parseFloat(semesterPercent);
  const hasSemester = loggedIn && Number.isFinite(percent);
  if (compact) {
    return (
      <div className="task-bar task-bar-compact">
        <div className="task-bar-status">
          <span className="live-dot" />
          <span>{status}</span>
        </div>
        <md-linear-progress value={progress} max={100} aria-label="任务进度" />
        <md-text-button onClick={onStop}>停止任务</md-text-button>
      </div>
    );
  }
  return (
    <div className={`task-bar${busy ? ' is-busy' : ''}`}>
      <div className="task-bar-status">
        {busy ? (
          <div className="task-bar-line">
            <span className="live-dot" />
            <span className="task-status-text">{status}</span>
            {busy ? (
              <span className="task-progress-text">{Math.round(progress)}%</span>
            ) : null}
          </div>
        ) : null}
        {busy ? <md-linear-progress value={progress} max={100} aria-label="任务进度" /> : null}
        <div className="semester-summary">
          <strong>本学期进度</strong>
          <span>达标公里 <span className="semester-value">{loggedIn ? semesterKm : '--'}</span></span>
          <span>完成率 <span className="semester-value">{hasSemester ? semesterPercent : '--'}</span></span>
          <span className="semester-sync">{loggedIn
            ? runDays > 0 ? `已同步 ${runDays} 天打卡记录` : '登录状态下自动同步，只读展示当前学期。'
            : '登录账号后自动同步本学期数据。'}</span>
        </div>
        <SemesterProgress value={hasSemester ? percent : null} label={hasSemester ? `本学期完成率 ${semesterPercent}` : '本学期完成率暂无数据'} />
      </div>
      {busy ? (
        <md-filled-button className="danger-button" onClick={onStop}>
          <md-icon slot="icon" aria-hidden="true">stop</md-icon>
          停止任务
        </md-filled-button>
      ) : (
        <md-filled-button onClick={onStart} disabled={page !== 'workbench'}>
          <md-icon slot="icon" aria-hidden="true">play_arrow</md-icon>
          开始任务
        </md-filled-button>
      )}
    </div>
  );
}

export function LoadingScreen({ message }: { message: string }) {
  return (
    <div className="loading-screen">
      <img src="/app-icon.png" alt="" className="loading-icon" />
      <div className="loading-copy">
        <span className="loading-title">SJTU RunningMan</span>
        <span className="loading-sub">{message}</span>
      </div>
      <md-circular-progress indeterminate aria-label="正在启动" />
    </div>
  );
}

export function PageSection({ children }: { children: ReactNode }) {
  return <div className="page">{children}</div>;
}
