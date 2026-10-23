import { useEffect, useState } from 'react';
import { Dialog } from '../components/Dialog';
import { Notice } from '../components/Notice';
import { SelectField } from '../components/SelectField';
import { TextField } from '../components/TextField';

interface TwoFactorDialogProps {
  open: boolean;
  user: string;
  loading: boolean;
  notice: string;
  noticeKind: 'info' | 'error' | 'success';
  onSend: (method: string) => void;
  onVerify: (code: string) => void;
  onCancel: () => void;
}

const METHODS = [
  { value: 'app', label: '交我办' },
  { value: 'email', label: '邮箱' },
  { value: 'sms', label: '短信' },
];

export function TwoFactorDialog({
  open,
  user,
  loading,
  notice,
  noticeKind,
  onSend,
  onVerify,
  onCancel,
}: TwoFactorDialogProps) {
  const [method, setMethod] = useState('app');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!open) {
      setCode('');
      setSent(false);
    }
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      headline="完成二次验证"
      icon="lock"
      className="login-dialog"
      actions={
        <>
          <md-text-button onClick={onCancel} disabled={loading}>
            取消
          </md-text-button>
          <md-filled-button onClick={() => onVerify(code)} disabled={loading || code.trim().length === 0}>
            验证并继续
          </md-filled-button>
        </>
      }
    >
      <div
        className="dialog-form"
        onKeyDown={(event) => {
          if (event.key === 'Enter' && code.trim().length > 0 && !loading) {
            event.preventDefault();
            onVerify(code);
          }
        }}
      >
        <p className="dialog-lead">
          账号 <strong>{user}</strong> 需要二次验证。选择接收方式，发送并填写验证码。
          验证码有时效，重新发送会使旧验证码失效。
        </p>
        <div className="two-factor-row">
          <SelectField
            label="验证方式"
            value={method}
            options={METHODS}
            onValueChange={(value) => {
              setMethod(value);
              setSent(false);
            }}
            disabled={loading}
          />
          <md-outlined-button
            onClick={() => {
              onSend(method);
              setSent(true);
            }}
            disabled={loading}
          >
            <md-icon slot="icon" aria-hidden="true">send</md-icon>
            {sent ? '重新发送' : '发送验证码'}
          </md-outlined-button>
        </div>
        <TextField
          label="6 位验证码"
          value={code}
          onValueChange={setCode}
          disabled={loading}
          inputMode="numeric"
          supportingText={sent ? '重新发送会使旧验证码失效；验证失败 5 次后需要重新登录' : '验证失败 5 次后需要重新登录'}
        />
        {notice ? <Notice message={notice} kind={noticeKind} /> : null}
      </div>
    </Dialog>
  );
}
