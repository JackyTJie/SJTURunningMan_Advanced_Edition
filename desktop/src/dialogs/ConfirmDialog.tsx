import type { ReactNode } from 'react';
import { Dialog } from '../components/Dialog';

interface ConfirmDialogProps {
  open: boolean;
  headline: string;
  icon: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  headline,
  icon,
  children,
  confirmLabel,
  cancelLabel = '返回检查',
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      headline={headline}
      icon={icon}
      className="confirm-dialog"
      actions={
        <>
          <md-text-button onClick={onCancel}>{cancelLabel}</md-text-button>
          <md-filled-button
            className={danger ? 'danger-button' : undefined}
            onClick={onConfirm}
            disabled={busy}
          >
            {confirmLabel}
          </md-filled-button>
        </>
      }
    >
      {children}
    </Dialog>
  );
}
