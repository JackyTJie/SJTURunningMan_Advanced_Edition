import { useEffect, useRef, type ReactNode } from 'react';
import { useCustomEvent } from '../lib/foreign';
import type { MdDialog } from '../types/md';

interface DialogProps {
  open: boolean;
  onClose: () => void;
  headline: string;
  icon?: string;
  children: ReactNode;
  actions: ReactNode;
  type?: 'alert';
  preventCancel?: boolean;
  className?: string;
}

/** 官方 md-dialog 的通用布局；headline/content/actions 均使用组件原生插槽。 */
export function Dialog({
  open,
  onClose,
  headline,
  icon,
  children,
  actions,
  type,
  preventCancel = false,
  className,
}: DialogProps) {
  const ref = useRef<MdDialog>(null);
  const programmaticClose = useRef(false);
  useCustomEvent<Event, MdDialog>(ref, 'closed', () => {
    // 由父组件状态驱动的关闭（例如登录 → 二次验证切换）不应再触发取消回调。
    if (programmaticClose.current) return;
    onClose();
  });

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    if (open && !element.open) {
      void element.show();
    } else if (!open && element.open) {
      programmaticClose.current = true;
      void element.close().finally(() => {
        programmaticClose.current = false;
      });
    }
  }, [open]);

  useEffect(() => {
    const element = ref.current;
    if (!element || !preventCancel) return;
    const cancel = (event: Event) => event.preventDefault();
    element.addEventListener('cancel', cancel);
    return () => element.removeEventListener('cancel', cancel);
  }, [preventCancel]);

  return (
    <md-dialog ref={ref} type={type} className={className}>
      {icon ? (
        <md-icon slot="icon" aria-hidden="true">
          {icon}
        </md-icon>
      ) : null}
      <div slot="headline">{headline}</div>
      <div slot="content">{children}</div>
      <div slot="actions">{actions}</div>
    </md-dialog>
  );
}
