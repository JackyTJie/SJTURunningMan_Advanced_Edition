interface NoticeProps {
  message: string;
  kind: 'info' | 'error' | 'success';
}

/** MD3 snackbar 样式的工作区浮层：不参与布局，避免推动下方内容。 */
export function Notice({ message, kind }: NoticeProps) {
  return (
    <div className={`notice notice-${kind}`} role="status" aria-live="polite">
      <md-icon aria-hidden="true">
        {kind === 'error' ? 'error' : kind === 'success' ? 'check_circle' : 'info'}
      </md-icon>
      <span>{message}</span>
    </div>
  );
}
