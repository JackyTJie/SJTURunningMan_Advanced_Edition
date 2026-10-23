import { useLayoutEffect, useRef } from 'react';
import { useCustomEvent } from '../lib/foreign';
import type { MdSelect } from '../types/md';

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: SelectOption[];
  onValueChange: (value: string) => void;
  disabled?: boolean;
  supportingText?: string;
  className?: string;
  menuPositioning?: 'absolute' | 'fixed' | 'popover';
}

/** 官方 md-outlined-select 的 React 绑定。 */
export function SelectField({
  label,
  value,
  options,
  onValueChange,
  disabled = false,
  supportingText,
  className,
  menuPositioning = 'fixed',
}: SelectFieldProps) {
  const ref = useRef<MdSelect>(null);
  useCustomEvent<Event, MdSelect>(ref, 'change', () => {
    onValueChange(ref.current?.value ?? '');
  });
  useLayoutEffect(() => {
    if (ref.current && ref.current.value !== value) ref.current.value = value;
  }, [value, options]);

  return (
    <md-outlined-select
      ref={ref}
      className={className}
      label={label}
      supportingText={supportingText}
      disabled={disabled}
      menuPositioning={menuPositioning}
    >
      {options.map((option) => (
        <md-select-option key={option.value} value={option.value}>
          <div slot="headline">{option.label}</div>
        </md-select-option>
      ))}
    </md-outlined-select>
  );
}
