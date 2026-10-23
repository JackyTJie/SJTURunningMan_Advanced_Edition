import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Timepicker } from 'material/react';
import type { TimepickerElement } from 'material/elements';
import { formatClock12 } from '../lib/time';
import { TextField } from './TextField';

interface TimeFieldProps {
  value: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
}

/** md3.io 的时间选择器只渲染对话框，字段本身由项目输入框展示。 */
const labels: Record<string, string> = {
  Cancel: '取消',
  OK: '确定',
  Hour: '时',
  Minute: '分',
  Second: '秒',
  Time: '时间',
  'Toggle input picker': '切换到输入',
  'Toggle dial picker': '切换到表盘',
};

function localize(root: ShadowRoot) {
  const translate = (text: string) => labels[text] ?? text;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement?.closest('style, script')) continue;
    const translated = translate(node.textContent ?? '');
    if (translated !== node.textContent) node.textContent = translated;
  }
  root.querySelectorAll<HTMLElement>('[aria-label]').forEach((element) => {
    const label = element.getAttribute('aria-label') ?? '';
    const translated = translate(label);
    if (translated !== label) element.setAttribute('aria-label', translated);
  });
}

/** 开始时间用现成的 md3.io 时间选择器：紧凑的输入式对话框，可直接改时/分/秒。 */
export function TimeField({ value, onValueChange, disabled = false }: TimeFieldProps) {
  const picker = useRef<TimepickerElement>(null);

  useEffect(() => {
    const root = picker.current?.shadowRoot;
    if (!root) return;
    const observer = new MutationObserver(() => localize(root));
    observer.observe(root, { childList: true, characterData: true, subtree: true });
    localize(root);
    return () => observer.disconnect();
  }, []);

  const value24 = value.slice(0, 5);
  const display = formatClock12(value24) ?? value24;

  const openPicker = () => {
    if (disabled) return;
    picker.current?.show();
  };

  return (
    <>
      <div
        className="time-field"
        onClick={openPicker}
        onKeyDown={(event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          openPicker();
        }}
      >
        <TextField
          label="开始时间"
          value={display}
          onValueChange={() => undefined}
          disabled={disabled}
          readOnly
          supportingText="12 小时制"
          trailingIcon={
            <md-icon-button
              aria-label="选择开始时间"
              title="选择开始时间"
              disabled={disabled}
              onClick={(event) => {
                event.stopPropagation();
                openPicker();
              }}
            >
              <md-icon aria-hidden="true">schedule</md-icon>
            </md-icon-button>
          }
        />
      </div>

      {createPortal(
        <Timepicker
          ref={picker}
          className="time-picker"
          label="开始时间"
          type="input"
          format="12h"
          value={value24}
          onChange={(event) => onValueChange(`${event.detail.value}:00`)}
        />,
        document.body,
      )}
    </>
  );
}
