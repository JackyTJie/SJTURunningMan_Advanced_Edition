import { useEffect, useRef } from 'react';
import type { CalendarWeek } from '../lib/backend';
import { Calendar, CalendarLegend } from '../components/Calendar';

export interface LogEntry {
  id: number;
  time: string;
  message: string;
}

interface LogsPageProps {
  weeks: CalendarWeek[];
  loggedIn: boolean;
  logs: LogEntry[];
  onClear: () => void;
}

export function LogsPage({ weeks, loggedIn, logs, onClear }: LogsPageProps) {
  const listRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = listRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [logs]);

  return (
    <div className="logs-grid">
      <md-outlined-card className="surface-card calendar-card">
        <div className="card-body">
          <div className="card-header compact-header">
            <div>
              <div className="card-eyebrow">学期</div>
              <h2 className="card-title">学期日历</h2>
              <p className="card-sub">
                {loggedIn ? '按北京时间统计本学期的打卡状态。' : '登录后显示本学期打卡记录。'}
              </p>
            </div>
            <md-icon className="header-icon" aria-hidden="true">calendar_month</md-icon>
          </div>
          <CalendarLegend />
          <div className="calendar-scroll">
            <Calendar weeks={weeks} loggedIn={loggedIn} />
          </div>
        </div>
      </md-outlined-card>

      <md-outlined-card className="surface-card log-card">
        <div className="card-body">
          <div className="card-header compact-header">
            <div>
              <div className="card-eyebrow">本次会话</div>
              <h2 className="card-title">运行记录</h2>
              <p className="card-sub">仅保留最近 250 行，退出程序后清空。</p>
            </div>
            <md-text-button onClick={onClear} disabled={logs.length === 0}>
              <md-icon slot="icon" aria-hidden="true">delete</md-icon>
              清空日志
            </md-text-button>
          </div>
          <div className="log-list" ref={listRef} role="log" aria-live="polite">
            {logs.length === 0 ? (
              <div className="log-empty">
                <md-icon aria-hidden="true">history</md-icon>
                <span>暂无任务日志</span>
                <small>登录、预览与上传的结果会记录在这里。</small>
              </div>
            ) : (
              logs.map((entry) => (
                <div className="log-line" key={entry.id}>
                  <span className="log-time">{entry.time}</span>
                  <span className="log-message">{entry.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </md-outlined-card>
    </div>
  );
}
