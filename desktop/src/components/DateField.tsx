import { useEffect, useRef } from 'react';
import { Datepicker } from 'material/react';
import type { DatepickerElement } from 'material/elements';
import type { CalendarWeek, DayState } from '../lib/backend';

interface DateFieldProps {
  value: string;
  onValueChange: (value: string) => void;
  disabled: boolean;
  weeks: CalendarWeek[];
}

const months = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];
const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const labels: Record<string, string> = {
  'Enter a valid date (YYYY-MM-DD).': '请输入有效日期（YYYY-MM-DD）。',
  'Enter a selectable date (YYYY-MM-DD).': '请输入可选择的日期（YYYY-MM-DD）。',
  'Date is not selectable.': '该日期不可选择。',
  'Select a date.': '请选择日期。',
  'Save': '确定', 'OK': '确定', 'Cancel': '取消', 'Date': '日期', 'Select date': '选择日期',
  'Select month': '选择月份', 'Select year': '选择年份',
  'Choose month': '选择月份', 'Choose year': '选择年份',
  'Previous month': '上个月', 'Next month': '下个月',
  'Previous year': '上一年', 'Next year': '下一年',
  'Switch to calendar': '切换到日历', 'Switch to date input': '切换到日期输入',
  'Use arrow keys for days, Home and End for the week, Page Up and Page Down for months, with Shift for years.':
    '方向键切换日期，Home 和 End 移至周首尾，Page Up 和 Page Down 切换月份，配合 Shift 切换年份。',
};
months.forEach((month, index) => {
  labels[month] = `${index + 1}月`;
  labels[month.slice(0, 3)] = `${index + 1}月`;
});
weekdays.forEach((day, index) => { labels[day] = `星期${'日一二三四五六'[index]}`; });

/** material 3.2.4 has no locale option. Translate presentation only;
 * all date validation, selection, navigation and focus remain upstream. */
function localize(root: ShadowRoot, records: Map<string, DayState>) {
  const translate = (text: string) => {
    if (labels[text]) return labels[text];
    const headline = text.match(/^([A-Za-z]+) (\d{1,2}), (\d{4})$/);
    if (headline && labels[headline[1]]) return `${headline[3]}年${labels[headline[1]]}${headline[2]}日`;
    const monthYear = text.match(/^([A-Za-z]+) (\d{4})$/);
    if (monthYear && labels[monthYear[1]]) return `${monthYear[2]}年${labels[monthYear[1]]}`;
    return text;
  };
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement?.closest('style, script')) continue;
    const translated = translate(node.textContent ?? '');
    if (translated !== node.textContent) node.textContent = translated;
  }
  root.querySelectorAll<HTMLElement>('[aria-label]').forEach((element) => {
    const label = element.getAttribute('aria-label') ?? '';
    const date = element.dataset.date;
    const state = date ? records.get(date) : undefined;
    const status = state === 'valid' ? '已打卡，计入成绩' : state === 'invalid' ? '已打卡，无效记录' : '';
    if (date) {
      element.part.toggle('record-valid', state === 'valid');
      element.part.toggle('record-invalid', state === 'invalid');
      if (element.title !== status) element.title = status;
    }
    const translated = date
      ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' }).format(new Date(`${date}T12:00:00`)) + (status ? `，${status}` : '')
      : translate(label);
    if (label !== translated) element.setAttribute('aria-label', translated);
  });
  root.querySelectorAll<HTMLElement>('.mtrl-datepicker__weekday').forEach((element, index) => {
    const text = '日一二三四五六'[index % 7];
    if (element.textContent !== text) element.textContent = text;
  });
}

export function DateField({ value, onValueChange, disabled, weeks }: DateFieldProps) {
  const ref = useRef<DatepickerElement>(null);
  useEffect(() => {
    const root = ref.current?.shadowRoot;
    if (!root) return;
    // Month headings are carried only by the first week of each month.
    const records = new Map<string, DayState>();
    let month = '';
    for (const week of weeks) {
      if (week.title) {
        const match = /^(\d{4})年(\d{1,2})月$/.exec(week.title);
        month = match ? `${match[1]}-${match[2].padStart(2, '0')}` : '';
      }
      if (!month) continue;
      for (const day of week.days) {
        if (day.day > 0 && day.state !== 'none') {
          records.set(`${month}-${String(day.day).padStart(2, '0')}`, day.state);
        }
      }
    }
    const update = () => localize(root, records);
    const observer = new MutationObserver(update);
    observer.observe(root, { childList: true, characterData: true, subtree: true });
    update();
    return () => observer.disconnect();
  }, [weeks]);

  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    let animation: Animation | undefined;
    const stop = () => animation?.cancel();
    const open = () => {
      stop();
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const panel = host.shadowRoot?.querySelector('dialog');
      if (!panel) return;
      const tokens = getComputedStyle(host);
      // Match the upstream time picker without relying on cross-shadow keyframes.
      animation = panel.animate([
        { opacity: 0, transform: tokens.getPropertyValue('--app-picker-enter-transform').trim() },
        { opacity: 1, transform: 'none' },
      ], {
        duration: parseFloat(tokens.getPropertyValue('--app-motion-duration-medium')),
        easing: tokens.getPropertyValue('--app-picker-enter-easing').trim(),
      });
    };
    host.addEventListener('open', open);
    host.addEventListener('close', stop);
    return () => {
      stop();
      host.removeEventListener('open', open);
      host.removeEventListener('close', stop);
    };
  }, []);

  return (
    <Datepicker
      ref={ref}
      className="md3-date-field"
      label="结束日期"
      variant="modal"
      dateFormat="YYYY-MM-DD"
      supportingText="YYYY-MM-DD"
      value={value}
      disabled={disabled}
      required
      onChange={(event) => onValueChange(event.detail.value)}
    />
  );
}
