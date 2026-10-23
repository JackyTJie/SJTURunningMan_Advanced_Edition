import { useEffect, useRef, useState } from 'react';
import type { LoginPreparation } from '../lib/backend';
import { Dialog } from '../components/Dialog';
import { Notice } from '../components/Notice';
import { TextField } from '../components/TextField';

interface LoginDialogProps {
  open: boolean;
  stage: 1 | 2;
  preparation: LoginPreparation | null;
  loading: boolean;
  notice: string;
  noticeKind: 'info' | 'error' | 'success';
  onRefresh: () => void;
  onEdit: () => void;
  onSubmit: (username: string, password: string, captcha: string) => void;
  onCancel: () => void;
}

export function LoginDialog({
  open,
  stage,
  preparation,
  loading,
  notice,
  noticeKind,
  onRefresh,
  onEdit,
  onSubmit,
  onCancel,
}: LoginDialogProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [captcha, setCaptcha] = useState('');
  const [visible, setVisible] = useState(false);
  const composing = useRef(false);
  const submitting = useRef(false);
  const canSubmit = !loading && Boolean(preparation && username.trim() && password && captcha.trim());

  useEffect(() => {
    if (!loading) submitting.current = false;
    if (!open) composing.current = false;
  }, [loading, open]);

  const edit = (setValue: (value: string) => void, value: string) => {
    setValue(value);
    if (notice && noticeKind === 'error') onEdit();
  };

  useEffect(() => {
    if (!open || stage === 2) {
      setPassword('');
      setCaptcha('');
    }
    if (!open) setVisible(false);
  }, [open, stage]);

  useEffect(() => {
    if (open && stage === 1) setCaptcha(preparation?.captchaCode ?? '');
  }, [open, stage, preparation]);

  const submit = () => {
    if (!canSubmit || composing.current || submitting.current) return;
    submitting.current = true;
    onSubmit(username.trim(), password, captcha.trim());
    setPassword('');
  };

  return (
    <Dialog
      open={open && stage === 1}
      onClose={onCancel}
      headline="连接 JAccount"
      icon="person"
      className="login-dialog"
      actions={
        <>
          <md-text-button type="button" onClick={onCancel} disabled={loading}>
            取消
          </md-text-button>
          <md-filled-button type="button" onClick={submit} disabled={!canSubmit}>
            {loading ? '连接中…' : '登录'}
          </md-filled-button>
        </>
      }
    >
      <form
        className="dialog-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        onCompositionStart={() => { composing.current = true; }}
        onCompositionEnd={() => { composing.current = false; }}
        onKeyDown={(event) => {
          if (event.key !== 'Enter') return;
          // 输入法确认（含部分 WebView 的 keyCode 229）不代表提交。
          if (composing.current || event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return;
          // 刷新验证码、显示密码等按钮保留自己的键盘操作。
          if (!event.nativeEvent.composedPath().some((node) => node instanceof HTMLInputElement)) return;
          event.preventDefault();
          submit();
        }}
      >
        <p className="dialog-lead">凭据仅发送给学校认证服务，不保存在本地。</p>
        <TextField
          label="JAccount 账号"
          value={username}
          onValueChange={(value) => edit(setUsername, value)}
          disabled={loading}
          name="username"
        />
        <TextField
          label="密码"
          value={password}
          onValueChange={(value) => edit(setPassword, value)}
          password={!visible}
          disabled={loading}
          name="password"
          trailingIcon={
            <md-icon-button
              type="button"
              disabled={loading}
              aria-label={visible ? '隐藏密码' : '显示密码'}
              title={visible ? '隐藏密码' : '显示密码'}
              onClick={(event) => {
                event.preventDefault();
                setVisible((value) => !value);
              }}
            >
              <md-icon aria-hidden="true">{visible ? 'visibility_off' : 'visibility'}</md-icon>
            </md-icon-button>
          }
        />
        <div className="captcha-row">
          <div className="captcha-copy">
            <TextField
              label="验证码"
              value={captcha}
              onValueChange={(value) => edit(setCaptcha, value)}
              disabled={loading}
              name="captcha"
            />
          </div>
          <div className="captcha-image-box">
            {preparation?.captcha ? (
              <img src={preparation.captcha} alt="图形验证码" />
            ) : (
              <md-circular-progress indeterminate aria-label="正在加载验证码" />
            )}
          </div>
          <md-outlined-icon-button
            type="button"
            aria-label="刷新验证码"
            title="刷新验证码"
            onClick={(event) => {
              event.preventDefault();
              onRefresh();
            }}
            disabled={loading}
          >
            <md-icon aria-hidden="true">refresh</md-icon>
          </md-outlined-icon-button>
        </div>
        {notice ? <Notice message={notice} kind={noticeKind} /> : null}
      </form>
    </Dialog>
  );
}
