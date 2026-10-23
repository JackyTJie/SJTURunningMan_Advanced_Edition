import type * as React from 'react';

/** @material/web 的自定义元素在 React 里需要显式的属性/事件类型。 */
export interface MdTextField extends HTMLElement {
  value: string;
  label: string;
  type: string;
  disabled: boolean;
  error: boolean;
  errorText: string;
  supportingText: string;
  placeholder: string;
  min: string;
  max: string;
  step: string;
  inputMode: string;
  readOnly: boolean;
  focus(): void;
  select(): void;
}

export interface MdSelect extends HTMLElement {
  value: string;
  selectedIndex: number;
  disabled: boolean;
  label: string;
  error: boolean;
  errorText: string;
  supportingText: string;
}

export interface MdDialog extends HTMLElement {
  open: boolean;
  type: string;
  show(): Promise<void>;
  close(returnValue?: string): Promise<void>;
}

export interface MdSwitch extends HTMLElement {
  selected: boolean;
  disabled: boolean;
}

export interface MdCheckbox extends HTMLElement {
  checked: boolean;
  disabled: boolean;
}

export interface MdLinearProgress extends HTMLElement {
  value: number;
  max: number;
  indeterminate: boolean;
}

export interface MdNavigationDrawer extends HTMLElement {
  opened: boolean;
  pivot: 'start' | 'end';
}

type ElementProps = React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
  ref?: React.Ref<HTMLElement>;
  slot?: string;
};

type TextFieldProps = ElementProps & {
  value?: string;
  label?: string;
  type?: string;
  disabled?: boolean;
  error?: boolean;
  errorText?: string;
  supportingText?: string;
  placeholder?: string;
  min?: string;
  max?: string;
  step?: string;
  inputMode?: string;
  readOnly?: boolean;
  required?: boolean;
  name?: string;
  autocomplete?: string;
  autoComplete?: string;
  rows?: number;
};

type SelectProps = ElementProps & {
  value?: string;
  selectedIndex?: number;
  disabled?: boolean;
  label?: string;
  error?: boolean;
  errorText?: string;
  supportingText?: string;
  required?: boolean;
  name?: string;
  quick?: boolean;
  menuPositioning?: string;
};

type ButtonProps = ElementProps & {
  disabled?: boolean;
  href?: string;
  target?: string;
  type?: 'submit' | 'reset' | 'button';
  value?: string;
  name?: string;
  trailingIcon?: boolean;
  hasIcon?: boolean;
};

type IconButtonProps = ElementProps & {
  type?: 'submit' | 'reset' | 'button';
  disabled?: boolean;
  href?: string;
  target?: string;
  selected?: boolean;
  toggle?: boolean;
  ariaLabelSelected?: string;
  ariaLabel?: string;
};

type DialogProps = ElementProps & {
  open?: boolean;
  quick?: boolean;
  type?: 'alert';
  returnValue?: string;
};

type SwitchProps = ElementProps & {
  selected?: boolean;
  disabled?: boolean;
  icons?: boolean;
  showOnlySelectedIcon?: boolean;
  value?: string;
  name?: string;
};

type CheckboxProps = ElementProps & {
  checked?: boolean;
  disabled?: boolean;
  indeterminate?: boolean;
  required?: boolean;
  value?: string;
  name?: string;
};

type ProgressProps = ElementProps & {
  value?: number;
  max?: number;
  indeterminate?: boolean;
  fourColor?: boolean;
  buffer?: number;
};

type ListItemProps = ElementProps & {
  type?: 'text' | 'button' | 'link';
  disabled?: boolean;
  href?: string;
  target?: string;
  selected?: boolean;
};

type SelectOptionProps = ElementProps & {
  value?: string;
  selected?: boolean;
  disabled?: boolean;
  type?: string;
};

type NavigationDrawerProps = ElementProps & {
  opened?: boolean;
  pivot?: 'start' | 'end';
  ariaLabel?: string;
};

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'md-outlined-text-field': TextFieldProps;
      'md-filled-text-field': TextFieldProps;
      'md-outlined-select': SelectProps;
      'md-filled-select': SelectProps;
      'md-select-option': SelectOptionProps;
      'md-filled-button': ButtonProps;
      'md-filled-tonal-button': ButtonProps;
      'md-outlined-button': ButtonProps;
      'md-text-button': ButtonProps;
      'md-elevated-button': ButtonProps;
      'md-icon-button': IconButtonProps;
      'md-filled-icon-button': IconButtonProps;
      'md-filled-tonal-icon-button': IconButtonProps;
      'md-outlined-icon-button': IconButtonProps;
      'md-dialog': DialogProps;
      'md-switch': SwitchProps;
      'md-checkbox': CheckboxProps;
      'md-linear-progress': ProgressProps;
      'md-circular-progress': ProgressProps;
      'md-icon': ElementProps & { filled?: boolean; ariaLabel?: string };
      'md-outlined-card': ElementProps;
      'md-elevated-card': ElementProps;
      'md-filled-card': ElementProps;
      'md-list': ElementProps & { type?: 'text' | 'button' | 'link' };
      'md-list-item': ListItemProps;
      'md-divider': ElementProps;
      'md-navigation-drawer': NavigationDrawerProps;
      'md-outlined-segmented-button-set': ElementProps & { multiselect?: boolean };
      'md-outlined-segmented-button': ElementProps & {
        label?: string;
        selected?: boolean;
        disabled?: boolean;
        noCheckmark?: boolean;
      };
      'md-ripple': ElementProps;
      'md-elevation': ElementProps & { level?: number };
    }
  }
}
