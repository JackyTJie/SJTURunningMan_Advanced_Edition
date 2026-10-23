import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { useCustomEvent } from '../lib/foreign';
import type { MdTextField } from '../types/md';

interface TextFieldProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
  password?: boolean;
  readOnly?: boolean;
  placeholder?: string;
  supportingText?: string;
  error?: boolean;
  errorText?: string;
  inputMode?: 'numeric' | 'decimal' | 'text' | 'email' | 'tel' | 'url' | 'search' | 'none';
  min?: string;
  max?: string;
  step?: string;
  autoFocus?: boolean;
  name?: string;
  className?: string;
  trailingIcon?: ReactNode;
}

/** 官方 md-outlined-text-field 的 React 绑定；视觉与交互完全由组件提供。 */
export function TextField({
  label,
  value,
  onValueChange,
  disabled = false,
  password = false,
  readOnly = false,
  placeholder,
  supportingText,
  error,
  errorText,
  inputMode,
  min,
  max,
  step,
  autoFocus,
  name,
  className,
  trailingIcon,
}: TextFieldProps) {
  const ref = useRef<MdTextField>(null);
  useCustomEvent<Event, MdTextField>(ref, 'input', () => {
    onValueChange(ref.current?.value ?? '');
  });
  useLayoutEffect(() => {
    if (ref.current && ref.current.value !== value) ref.current.value = value;
  }, [value]);
  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  return (
    <md-outlined-text-field
      ref={ref}
      className={className}
      label={label}
      type={password ? 'password' : 'text'}
      placeholder={placeholder}
      supportingText={supportingText}
      error={error}
      errorText={errorText}
      inputMode={inputMode}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      readOnly={readOnly}
      autoComplete="off"
      name={name}
    >
      {trailingIcon ? <div slot="trailing-icon">{trailingIcon}</div> : null}
    </md-outlined-text-field>
  );
}
