import { useEffect, useRef, useState } from 'react';
import type { LoginMode, LoginPreparation } from '../lib/backend';
import { Dialog } from '../components/Dialog';
import { Notice } from '../components/Notice';
import { TextField } from '../components/TextField';

export type QrStatus = 'idle' | 'loading' | 'waiting' | 'error';

interface LoginDialogProps {
  open: boolean;
  stage: 1 | 2;
  mode: LoginMode;
  preparation: LoginPreparation | null;
  loading: boolean;
  qrImage: string;
  qrStatus: QrStatus;
  notice: string;
  noticeKind: 'info' | 'error' | 'success';
  onModeChange: (mode: LoginMode) => void;
  onRefreshCaptcha: () => void;
  onRefreshQr: () => void;
  onEdit: () => void;
  onSubmit: (username: string, password: string, captcha: string) => void;
  onCancel: () => void;
}

export function LoginDialog({
  open,
  stage,
  mode,
  preparation,
  loading,
  qrImage,
  qrStatus,
  notice,
  noticeKind,
  onModeChange,
  onRefreshCaptcha,
  onRefreshQr,
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

  const qrStatusText =
    qrStatus === 'error'
      ? '刷新二维码后即可重新扫码'
      : qrStatus === 'loading'
        ? '正在获取二维码…'
        : '等待扫码确认…';

  return (
    <Dialog
      open={open && stage === 1}
      onClose={onCancel}
      headline="连接 JAccount"
      icon="person"
      className="login-dialog"
      actions={
        mode === 'password' ? (
          <>
            <md-text-button type="button" onClick={onCancel} disabled={loading}>
              取消
            </md-text-button>
            <md-filled-button type="button" onClick={submit} disabled={!canSubmit}>
              {loading ? '连接中…' : '登录'}
            </md-filled-button>
          </>
        ) : (
          <>
            <md-text-button type="button" onClick={onCancel}>
              取消
            </md-text-button>
            <md-outlined-button
              type="button"
              onClick={onRefreshQr}
              disabled={qrStatus === 'loading'}
            >
              <md-icon slot="icon" aria-hidden="true">refresh</md-icon>
              刷新二维码
            </md-outlined-button>
          </>
        )
      }
    >
      <div className="dialog-form">
        <md-outlined-segmented-button-set className="login-modes" aria-label="登录方式">
          <md-outlined-segmented-button
            label="账号密码"
            selected={mode === 'password'}
            disabled={loading}
            onClick={() => onModeChange('password')}
          />
          <md-outlined-segmented-button
            label="扫码登录"
            selected={mode === 'qr'}
            disabled={loading}
            onClick={() => onModeChange('qr')}
          />
        </md-outlined-segmented-button-set>
        {mode === 'password' ? (
          <form
            className="login-fields"
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
                  onRefreshCaptcha();
                }}
                disabled={loading}
              >
                <md-icon aria-hidden="true">refresh</md-icon>
              </md-outlined-icon-button>
            </div>
            {notice ? <Notice message={notice} kind={noticeKind} /> : null}
          </form>
        ) : (
          <div className="qr-panel">
            <div className="qr-layout">
              <div className={`qr-frame${qrImage ? '' : ' empty'}`}>
                {qrImage ? (
                  <img src={qrImage} alt="JAccount 登录二维码" />
                ) : qrStatus === 'error' ? (
                  <md-icon className="qr-placeholder-icon" aria-hidden="true">
                    refresh
                  </md-icon>
                ) : (
                  <md-circular-progress indeterminate aria-label="正在获取二维码" />
                )}
              </div>
              <div className="qr-guide">
                <p className="qr-heading">
                  {qrStatus === 'error' ? '二维码已失效' : '手机扫码登录'}
                </p>
                <ol className="qr-steps">
                  <li>
                    <span className="qr-step-index">1</span>
                    打开「交我办」App
                  </li>
                  <li>
                    <span className="qr-step-index">2</span>
                    扫描左侧二维码
                  </li>
                  <li>
                    <span className="qr-step-index">3</span>
                    在手机上确认登录
                  </li>
                </ol>
                <p className={`qr-status ${qrStatus}`}>
                  {qrStatus === 'waiting' ? (
                    <span className="live-dot" aria-hidden="true" />
                  ) : (
                    <span className="idle-dot" aria-hidden="true" />
                  )}
                  {qrStatusText}
                </p>
              </div>
            </div>
            <p className="dialog-note qr-hint">
              二维码约 1 分钟自动更新，也可用相机或微信扫码。密码与 Cookie 只保留在本次进程内。
            </p>
            {notice ? <Notice message={notice} kind={noticeKind} /> : null}
          </div>
        )}
      </div>
    </Dialog>
  );
}
