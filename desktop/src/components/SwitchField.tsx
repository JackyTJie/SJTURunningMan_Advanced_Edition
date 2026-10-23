import { useLayoutEffect, useRef, type MouseEvent } from 'react';
import { useCustomEvent } from '../lib/foreign';
import type { MdSwitch } from '../types/md';

interface SwitchFieldProps {
  label: string;
  supportingText?: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}

/** 官方 md-switch 的 React 绑定；说明在左、控件在右，整行可点。 */
export function SwitchField({
  label,
  supportingText,
  checked,
  onCheckedChange,
  disabled = false,
}: SwitchFieldProps) {
  const ref = useRef<MdSwitch>(null);
  useCustomEvent<Event, MdSwitch>(ref, 'change', () => {
    onCheckedChange(ref.current?.selected ?? false);
  });
  useLayoutEffect(() => {
    if (ref.current && ref.current.selected !== checked) ref.current.selected = checked;
  }, [checked]);

  const toggle = (event: MouseEvent<HTMLDivElement>) => {
    if (disabled) return;
    const target = event.target as HTMLElement;
    if (target.closest('md-switch')) return;
    onCheckedChange(!checked);
  };

  return (
    <div className={`switch-field${disabled ? ' is-disabled' : ''}`} onClick={toggle}>
      <span className="switch-copy">
        <span className="switch-label">{label}</span>
        {supportingText ? <span className="switch-support">{supportingText}</span> : null}
      </span>
      <md-switch ref={ref} disabled={disabled} aria-label={label} />
    </div>
  );
}
