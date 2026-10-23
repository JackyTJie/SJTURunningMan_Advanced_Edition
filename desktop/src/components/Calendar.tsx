import type { CalendarWeek } from '../lib/backend';

interface CalendarProps {
  weeks: CalendarWeek[];
  loggedIn: boolean;
}

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];

/** 学期日历：周一起始，按服务器返回的周行渲染；状态色使用 MD3 角色。 */
export function Calendar({ weeks, loggedIn }: CalendarProps) {
  if (weeks.length === 0) {
    return (
      <div className="calendar-empty">
        <md-icon aria-hidden="true">calendar_month</md-icon>
        <p>暂无可显示的学期区间</p>
      </div>
    );
  }
  return (
    <div className="calendar">
      <div className="calendar-weekdays" aria-hidden="true">
        {WEEKDAYS.map((day) => (
          <span key={day}>{day}</span>
        ))}
      </div>
      <div className="calendar-months">
        {weeks.map((week, index) => (
          <div className="calendar-month-row" key={`${week.title}-${index}`}>
            {week.title ? (
              <div className="calendar-month-title">
                {week.title}
                {index === 0 && !loggedIn ? (
                  <span className="calendar-month-hint">登录后同步</span>
                ) : null}
              </div>
            ) : null}
            <div className="calendar-week">
              {week.days.map((day, dayIndex) => (
                <span
                  key={dayIndex}
                  className={`calendar-day day-${day.state}${day.day === 0 ? ' day-empty' : ''}`}
                  aria-label={day.day ? `${week.title || ''} ${day.day} 日` : undefined}
                >
                  {day.day > 0 ? day.day : ''}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CalendarLegend() {
  return (
    <div className="calendar-legend" aria-hidden="true">
      <span>
        <i className="legend-dot valid" /> 计入成绩
      </span>
      <span>
        <i className="legend-dot invalid" /> 无效记录
      </span>
      <span>
        <i className="legend-dot none" /> 未跑
      </span>
    </div>
  );
}
