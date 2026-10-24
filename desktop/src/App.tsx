import { routeDisplayName } from './lib/routeName';
import { useCallback, useEffect, useRef, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { open as openFileDialog } from '@tauri-apps/plugin-dialog';
import {
  backend,
  errorMessage,
  type Bootstrap,
  type CalendarWeek,
  type LoginPreparation,
  type PreviewMapResult,
  type PreviewRequest,
  type PreviewView,
  type RouteDetail,
  type RouteView,
  type StatsPayload,
} from './lib/backend';
import { useTauriEvent } from './lib/events';
import { LoginDialog } from './dialogs/LoginDialog';
import { TwoFactorDialog } from './dialogs/TwoFactorDialog';
import { ConsentDialog } from './dialogs/ConsentDialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import {
  LoadingScreen,
  PAGE_META,
  Sidebar,
  TaskBar,
  TopBar,
  type Page,
} from './components/AppShell';
import { Notice } from './components/Notice';
import { TaskCelebration } from './components/TaskCelebration';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { RoutesPage } from './pages/RoutesPage';
import { LogsPage, type LogEntry } from './pages/LogsPage';
import { AboutPage } from './pages/AboutPage';

type NoticeKind = 'info' | 'error' | 'success';

interface NoticeState {
  id: number;
  message: string;
  kind: NoticeKind;
}

interface LoginState {
  open: boolean;
  stage: 1 | 2;
  preparation: LoginPreparation | null;
  loading: boolean;
  notice: string;
  noticeKind: NoticeKind;
  account: string;
}

type ConfirmState = { kind: 'start' } | { kind: 'delete'; routeName: string };

const initialLogin: LoginState = {
  open: false,
  stage: 1,
  preparation: null,
  loading: false,
  notice: '',
  noticeKind: 'info',
  account: '',
};

function FatalScreen({ message }: { message: string }) {
  return (
    <div className="loading-screen">
      <md-icon className="fatal-icon" aria-hidden="true">error</md-icon>
      <div className="loading-copy">
        <span className="loading-title">无法启动应用</span>
        <span className="loading-sub">{message}</span>
      </div>
      <md-filled-button onClick={() => window.location.reload()}>重试</md-filled-button>
    </div>
  );
}

export function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [fatal, setFatal] = useState('');
  const [page, setPage] = useState<Page>('workbench');
  const [dark, setDark] = useState(false);
  const [runs, setRuns] = useState('1');
  const [distance, setDistance] = useState('4');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('08:00:00');
  const [skipExisting, setSkipExisting] = useState(true);
  const [routes, setRoutes] = useState<RouteView[]>([]);
  const [routeName, setRouteName] = useState('default');
  const [route, setRoute] = useState<RouteDetail | null>(null);
  const [preview, setPreview] = useState<PreviewView | null>(null);
  const [previewInputs, setPreviewInputs] = useState<PreviewRequest | null>(null);
  const [weeks, setWeeks] = useState<CalendarWeek[]>([]);
  const [semesterKm, setSemesterKm] = useState('--');
  const [semesterPercent, setSemesterPercent] = useState('--');
  const [runDays, setRunDays] = useState(0);
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [networkBusy, setNetworkBusy] = useState(false);
  const [updateStatus, setUpdateStatus] = useState('按需检查更新，启动时不请求网络。');
  const [celebration, setCelebration] = useState(0);
  const celebrationId = useRef(0);
  const clearCelebration = useCallback(() => setCelebration(0), []);
  const [task, setTask] = useState({ busy: false, progress: 0, status: '准备就绪' });
  const [consentOpen, setConsentOpen] = useState(true);
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);
  const [login, setLogin] = useState<LoginState>(initialLogin);

  const logId = useRef(0);
  const noticeId = useRef(0);
  const previewSeq = useRef(0);
  const autoPreviewTimer = useRef<number | null>(null);
  const distanceTouched = useRef(false);
  const lastDistance = useRef(distance);
  const planRef = useRef({ runs, distance, date, time, route: routeName, skipExisting });
  planRef.current = { runs, distance, date, time, route: routeName, skipExisting };
  const routeRef = useRef(route);
  routeRef.current = route;
  const taskBusyRef = useRef(task.busy);
  taskBusyRef.current = task.busy;

  const appendLog = useCallback((message: string) => {
    const entry: LogEntry = {
      id: logId.current++,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      message,
    };
    setLogs((previous) => {
      const next = [...previous, entry];
      return next.length > 250 ? next.slice(next.length - 250) : next;
    });
  }, []);

  const showNotice = useCallback((message: string, kind: NoticeKind = 'info') => {
    setNotice({ id: noticeId.current++, message, kind });
  }, []);

  const notify = useCallback(
    (message: string, kind: NoticeKind = 'info') => {
      appendLog(message);
      showNotice(message, kind);
    },
    [appendLog, showNotice],
  );

  const resetPreview = useCallback(() => {
    previewSeq.current += 1;
    if (autoPreviewTimer.current !== null) {
      window.clearTimeout(autoPreviewTimer.current);
      autoPreviewTimer.current = null;
    }
    setPreview(null);
    setPreviewInputs(null);
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 6000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  }, [dark]);

  useEffect(() => {
    if (!boot) return;
    const nativeWindow = getCurrentWindow();
    const surface = getComputedStyle(document.documentElement)
      .getPropertyValue('--md-sys-color-surface').trim();
    // macOS also paints the title bar with the explicitly configured window background.
    Promise.all([
      nativeWindow.setTheme(dark ? 'dark' : 'light'),
      nativeWindow.setBackgroundColor(surface),
    ]).catch((error) => appendLog(`窗口主题同步失败：${errorMessage(error)}`));
  }, [dark, boot, appendLog]);

  useEffect(() => {
    if (!boot) return;
    const frame = window.requestAnimationFrame(() => {
      getCurrentWindow().show().catch(() => undefined);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [boot]);

  useEffect(() => {
    if (fatal) getCurrentWindow().show().catch(() => undefined);
  }, [fatal]);

  useEffect(() => {
    // 启动数据异常缓慢时也先把窗口显示出来，让用户看到加载或错误界面。
    const timer = window.setTimeout(() => {
      getCurrentWindow().show().catch(() => undefined);
    }, 2500);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    backend
      .bootstrap()
      .then((data) => {
        if (cancelled) return;
        setBoot(data);
        setDark(data.settings.dark);
        setRuns(data.settings.runs);
        setDistance(data.settings.distance);
        setDate(data.date);
        setTime(data.settings.time);
        setSkipExisting(data.settings.skipExisting);
        setRoutes(data.routes);
        setRouteName(data.selected.name);
        setRoute(data.selected);
        setWeeks(data.calendar);
        setSemesterKm(data.semesterKm);
        setSemesterPercent(data.semesterPercent);
        data.logs.forEach((message) => appendLog(message));
        if (data.warning) showNotice(data.warning, 'error');
        backend.uiReady().catch(() => undefined);
      })
      .catch((error) => setFatal(errorMessage(error)));
    return () => {
      cancelled = true;
    };
  }, [appendLog, showNotice]);

  useEffect(() => {
    if (!boot) return;
    const timer = window.setTimeout(() => {
      backend
        .saveSettings({ dark, runs, distance, time, route: routeName, skipExisting })
        .catch((error) => appendLog(`保存设置失败：${errorMessage(error)}`));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [boot, dark, runs, distance, time, skipExisting, routeName, appendLog]);

  const applyStats = useCallback(
    (payload: StatsPayload) => {
      setSemesterKm(payload.km);
      setSemesterPercent(payload.percent);
      setRunDays(payload.runDays);
      if (payload.weeks) setWeeks(payload.weeks);
      payload.logs.forEach((message) => appendLog(message));
      if (payload.plan) {
        setRuns(payload.plan.runs);
        setDistance(payload.plan.distance);
        resetPreview();
      }
      if (payload.notice) showNotice(payload.notice, 'success');
    },
    [appendLog, showNotice, resetPreview],
  );

  const syncStats = useCallback(
    async (runsValue: string, distanceValue: string) => {
      try {
        const payload = await backend.syncStats(runsValue, distanceValue);
        applyStats(payload);
      } catch (error) {
        const message = errorMessage(error);
        if (!message.includes('已忽略过期的学期数据')) appendLog(message);
      }
    },
    [appendLog, applyStats],
  );

  const finishLogin = useCallback(
    (account: string, message: string) => {
      setLoggedIn(true);
      setUser(account);
      setLogin({ ...initialLogin });
      notify(message, 'success');
      const current = planRef.current;
      void syncStats(current.runs, current.distance);
    },
    [notify, syncStats],
  );

  const refreshCaptcha = useCallback(async () => {
    setLogin((previous) => ({ ...previous, loading: true, notice: '' }));
    try {
      const preparation = await backend.prepareLogin();
      setLogin((previous) => ({
        ...previous,
        loading: false,
        preparation,
        notice: preparation.manual ? '请填写图片中的验证码，或刷新重试。' : '',
        noticeKind: preparation.manual ? 'error' : 'info',
      }));
    } catch (error) {
      setLogin((previous) => ({
        ...previous,
        loading: false,
        preparation: null,
        notice: errorMessage(error),
        noticeKind: 'error',
      }));
    }
  }, []);

  const openLogin = useCallback(() => {
    setLogin({
      ...initialLogin,
      open: true,
      loading: true,
      notice: '',
      noticeKind: 'info',
    });
    void refreshCaptcha();
  }, [refreshCaptcha]);

  const handleAccount = useCallback(() => {
    if (task.busy || networkBusy) return;
    if (!loggedIn) {
      openLogin();
      return;
    }
    setNetworkBusy(true);
    backend
      .logout()
      .then((result) => {
        setLoggedIn(false);
        setUser('');
        setWeeks(result.weeks);
        setSemesterKm(result.km);
        setSemesterPercent(result.percent);
        setRunDays(0);
        resetPreview();
        setLogin({ ...initialLogin });
        notify(result.notice, 'info');
      })
      .catch((error) => notify(errorMessage(error), 'error'))
      .finally(() => setNetworkBusy(false));
  }, [task.busy, networkBusy, loggedIn, openLogin, notify, resetPreview]);

  const handleSubmitLogin = useCallback(
    (username: string, password: string, captcha: string) => {
      setLogin((previous) => ({
        ...previous,
        loading: true,
        notice: '',
        account: username,
      }));
      backend
        .submitLogin(username, password, captcha)
        .then((outcome) => {
          if (outcome.stage === 'authenticated') {
            finishLogin(outcome.user, outcome.notice);
          } else {
            setLogin((previous) => ({
              ...previous,
              stage: 2,
              loading: false,
              account: outcome.user,
              notice: outcome.notice,
              noticeKind: 'info',
            }));
          }
        })
        .catch((error) => {
          const message = errorMessage(error);
          setLogin((previous) => ({
            ...previous,
            loading: false,
            notice: message,
            noticeKind: 'error',
          }));
          appendLog(message);
        });
    },
    [appendLog, finishLogin],
  );

  const handleSendCode = useCallback(
    (method: string) => {
      setLogin((previous) => ({ ...previous, loading: true }));
      backend
        .sendCode(method)
        .then((message) => {
          appendLog(message);
          setLogin((previous) => ({
            ...previous,
            loading: false,
            notice: message,
            noticeKind: 'info',
          }));
        })
        .catch((error) => {
          const message = errorMessage(error);
          appendLog(message);
          setLogin((previous) => ({
            ...previous,
            loading: false,
            notice: message,
            noticeKind: 'error',
          }));
        });
    },
    [appendLog],
  );

  const handleVerifyCode = useCallback(
    (code: string) => {
      setLogin((previous) => ({ ...previous, loading: true }));
      backend
        .verifyCode(code)
        .then((outcome) => {
          if (outcome.verified) {
            finishLogin(login.account, outcome.message);
          } else if (outcome.locked) {
            setLogin({ ...initialLogin });
            setLoggedIn(false);
            notify(outcome.message, 'error');
          } else {
            appendLog(outcome.message);
            setLogin((previous) => ({
              ...previous,
              loading: false,
              notice: outcome.message,
              noticeKind: 'error',
            }));
          }
        })
        .catch((error) => {
          const message = errorMessage(error);
          appendLog(message);
          setLogin((previous) => ({
            ...previous,
            loading: false,
            notice: message,
            noticeKind: 'error',
          }));
        });
    },
    [finishLogin, login.account, notify, appendLog],
  );

  const cancelLogin = useCallback(() => {
    setLogin({ ...initialLogin });
    backend.cancelLogin().catch(() => undefined);
  }, []);

  const autoPreview = useCallback(
    async (request: PreviewRequest) => {
      const seq = ++previewSeq.current;
      try {
        const data = await backend.previewRoute(request);
        if (seq !== previewSeq.current) return;
        setPreview(data);
        setPreviewInputs(request);
      } catch (error) {
        if (seq === previewSeq.current) appendLog(`自动同步预览失败：${errorMessage(error)}`);
      }
    },
    [appendLog],
  );

  const handleDistanceChange = useCallback((value: string) => {
    distanceTouched.current = true;
    setDistance(value);
  }, []);

  // 单次距离决定实际轨迹长度。拖动滑块时防抖重算，让右侧预览跟着走；
  // 只在用户动过距离后才触发，避免启动时自动请求。
  useEffect(() => {
    if (lastDistance.current === distance) return;
    lastDistance.current = distance;
    // 先让在途的旧预览失效，避免它晚到后盖掉新轨迹。
    previewSeq.current += 1;
    if (!distanceTouched.current) return;
    if (autoPreviewTimer.current !== null) window.clearTimeout(autoPreviewTimer.current);
    if (!routeRef.current || taskBusyRef.current) return;
    const scheduledRoute = planRef.current.route;
    autoPreviewTimer.current = window.setTimeout(() => {
      autoPreviewTimer.current = null;
      if (!distanceTouched.current || !routeRef.current || taskBusyRef.current) return;
      if (planRef.current.route !== scheduledRoute) return;
      const plan = planRef.current;
      void autoPreview({
        runs: plan.runs,
        distance: plan.distance,
        date: plan.date,
        time: plan.time,
        route: plan.route,
      });
    }, 250);
  }, [distance, autoPreview]);

  useEffect(() => () => {
    if (autoPreviewTimer.current !== null) window.clearTimeout(autoPreviewTimer.current);
  }, []);

  const openMap = useCallback(async (): Promise<PreviewMapResult | null> => {
    const request: PreviewRequest = { runs, distance, date, time, route: routeName };
    setNetworkBusy(true);
    try {
      // 打开地图是普通浏览动作，不弹顶部提示；需要说明的情况由卡片内联显示。
      return await backend.previewMap(request);
    } catch (error) {
      notify(errorMessage(error), 'error');
      return null;
    } finally {
      setNetworkBusy(false);
    }
  }, [runs, distance, date, time, routeName, notify]);

  const openPlanner = useCallback(async () => {
    setNetworkBusy(true);
    try {
      const result = await backend.openPlanner();
      notify(result.notice ?? '规划器已打开', 'info');
    } catch (error) {
      notify(errorMessage(error), 'error');
    } finally {
      setNetworkBusy(false);
    }
  }, [notify]);

  const chooseRoute = useCallback(
    (name: string) => {
      if (task.busy) return;
      if (name === routeName) return;
      backend
        .selectRoute(name)
        .then((detail) => {
          setRouteName(detail.name);
          setRoute(detail);
          resetPreview();
        })
        .catch((error) => notify(errorMessage(error), 'error'));
    },
    [routeName, task.busy, notify, resetPreview],
  );

  const importRoute = useCallback(async () => {
    if (task.busy || networkBusy) return;
    try {
      const selected = await openFileDialog({
        multiple: false,
        directory: false,
        title: '导入 BD09 路线',
        filters: [{ name: '路线文本', extensions: ['txt'] }],
      });
      if (typeof selected !== 'string') return;
      setNetworkBusy(true);
      const result = await backend.importRoute(selected);
      setRoutes(result.routes);
      setRoute(result.selected);
      setRouteName(result.selectedName);
      resetPreview();
      result.logs.forEach((message) => appendLog(message));
      notify('路线已导入，源文件保持原样', 'success');
    } catch (error) {
      notify(errorMessage(error), 'error');
    } finally {
      setNetworkBusy(false);
    }
  }, [task.busy, networkBusy, appendLog, notify, resetPreview]);

  const confirmDelete = useCallback(async () => {
    if (!confirm || confirm.kind !== 'delete') return;
    const name = confirm.routeName;
    setConfirm(null);
    setNetworkBusy(true);
    try {
      const result = await backend.deleteRoute(name);
      setRoutes(result.routes);
      setRoute(result.selected);
      setRouteName(result.selectedName);
      resetPreview();
      result.logs.forEach((message) => appendLog(message));
      notify('已删除导入的路线副本', 'success');
    } catch (error) {
      notify(errorMessage(error), 'error');
    } finally {
      setNetworkBusy(false);
    }
  }, [confirm, appendLog, notify, resetPreview]);

  const startTask = useCallback(async () => {
    setConfirm(null);
    previewSeq.current += 1;
    if (autoPreviewTimer.current !== null) {
      window.clearTimeout(autoPreviewTimer.current);
      autoPreviewTimer.current = null;
    }
    setTask({ busy: true, progress: 0, status: '正在准备任务' });
    try {
      const started = await backend.startTask({ ...planRef.current });
      const skipped = started.skipped > 0 ? `，跳过 ${started.skipped} 天已有记录` : '';
      const truncated = started.truncated ? '（向前查找已到头）' : '';
      appendLog(`任务已开始：计划上传 ${started.count} 条${skipped}${truncated}`);
    } catch (error) {
      setTask({ busy: false, progress: 0, status: '准备就绪' });
      notify(errorMessage(error), 'error');
    }
  }, [appendLog, notify]);

  const requestStart = useCallback(() => {
    if (task.busy || networkBusy) return;
    if (!loggedIn) {
      openLogin();
      return;
    }
    setConfirm({ kind: 'start' });
  }, [task.busy, networkBusy, loggedIn, openLogin]);

  const stopTask = useCallback(() => {
    backend
      .stopTask()
      .catch((error) => notify(errorMessage(error), 'error'));
  }, [notify]);

  const checkUpdate = useCallback(() => {
    if (networkBusy) return;
    setNetworkBusy(true);
    setUpdateStatus('正在检查…');
    backend
      .checkUpdate()
      .then((message) => {
        setUpdateStatus(message);
        appendLog(message);
      })
      .catch((error) => {
        const message = `检查更新失败：${errorMessage(error)}`;
        setUpdateStatus(message);
        appendLog(message);
      })
      .finally(() => setNetworkBusy(false));
  }, [networkBusy, appendLog]);

  const openExternal = useCallback(
    (kind: 'project' | 'shuiyuan') => {
      backend
        .openExternal(kind)
        .catch((error) => notify(errorMessage(error), 'error'));
    },
    [notify],
  );

  useTauriEvent<{ message: string }>('app-log', (payload) => appendLog(payload.message));
  useTauriEvent<{ message: string }>('task-log', (payload) => appendLog(payload.message));
  useTauriEvent<{ value: number; status: string }>('task-progress', (payload) =>
    setTask({ busy: true, progress: payload.value, status: payload.status }),
  );
  useTauriEvent<PreviewView>('task-preview', (payload) => {
    previewSeq.current += 1;
    setPreview(payload);
    setPreviewInputs({ ...planRef.current });
  });
  useTauriEvent<{ success: number; failed: number; stopped: boolean; status: string; progress: number }>(
    'task-finished',
    (payload) => {
      setTask({ busy: false, progress: payload.progress, status: payload.status });
      showNotice(payload.status, payload.stopped ? 'info' : 'success');
      if (payload.success > 0 && payload.failed === 0 && !payload.stopped) {
        setCelebration(++celebrationId.current);
      }
    },
  );
  useTauriEvent<{ message: string; status: string }>('task-error', (payload) => {
    setTask({ busy: false, progress: 0, status: payload.status });
    appendLog(payload.message);
    showNotice(payload.message, 'error');
  });
  useTauriEvent<{ status: string }>('task-status', (payload) =>
    setTask((previous) => ({ ...previous, status: payload.status })),
  );
  useTauriEvent<StatsPayload>('stats-updated', (payload) => applyStats(payload));

  if (!boot) {
    return fatal ? <FatalScreen message={fatal} /> : <LoadingScreen message="正在准备工作台…" />;
  }

  const stale = Boolean(
    preview &&
      previewInputs &&
      (previewInputs.runs !== runs ||
        previewInputs.distance !== distance ||
        previewInputs.date !== date ||
        previewInputs.time !== time ||
        previewInputs.route !== routeName),
  );
  const busy = task.busy || networkBusy || login.loading;
  const modalOpen = consentOpen || login.open || confirm !== null;
  const meta = PAGE_META[page];

  return (
    <div className="app-shell">
      <div className="titlebar-drag" data-tauri-drag-region />
      {celebration > 0 ? (
        <TaskCelebration key={celebration} onComplete={clearCelebration} />
      ) : null}
      <Sidebar
        page={page}
        onNavigate={setPage}
        version={boot.version}
        user={user}
        loggedIn={loggedIn}
      />
      <div className="main-column">
        <TopBar
          page={page}
          dark={dark}
          loggedIn={loggedIn}
          busy={busy}
          onToggleTheme={() => setDark((value) => !value)}
          onAccount={handleAccount}
        />
        <main className={`content content-${page}`} aria-label={meta.title}>
          {notice && !modalOpen ? (
            <div className="notice-host">
              <Notice message={notice.message} kind={notice.kind} />
            </div>
          ) : null}
          <div className={`page page-${page}`}>
            {page === 'workbench' ? (
              <WorkbenchPage
                weeks={weeks}
                runs={runs}
                onRunsChange={setRuns}
                distance={distance}
                onDistanceChange={handleDistanceChange}
                date={date}
                onDateChange={setDate}
                time={time}
                onTimeChange={setTime}
                skipExisting={skipExisting}
                onSkipExistingChange={setSkipExisting}
                routes={routes}
                routeName={routeName}
                onRouteChange={chooseRoute}
                route={route}
                preview={preview}
                stale={Boolean(preview && previewInputs && (
                  previewInputs.runs !== runs || previewInputs.date !== date ||
                  previewInputs.time !== time || previewInputs.route !== routeName
                ))}
                busy={task.busy || networkBusy}
                onOpenMap={openMap}
              />
            ) : null}
            {page === 'routes' ? (
              <RoutesPage
                distanceKm={Number(distance)}
                routes={routes}
                route={route}
                routeName={routeName}
                preview={preview}
                stale={stale}
                busy={task.busy || networkBusy}
                onSelect={chooseRoute}
                onOpenMap={openMap}
                onPlanner={openPlanner}
                onImport={importRoute}
                onDelete={() => {
                  if (route?.canDelete) setConfirm({ kind: 'delete', routeName: route.name });
                }}
              />
            ) : null}
            {page === 'logs' ? (
              <LogsPage
                weeks={weeks}
                loggedIn={loggedIn}
                logs={logs}
                onClear={() => setLogs([])}
              />
            ) : null}
            {page === 'about' ? (
              <AboutPage
                version={boot.version}
                updateStatus={updateStatus}
                networkBusy={networkBusy}
                onCheckUpdate={checkUpdate}
                onOpen={openExternal}
              />
            ) : null}
          </div>
        </main>
        {page === 'workbench' || task.busy ? (
          <TaskBar
            page={page}
            busy={task.busy}
            progress={task.progress}
            status={task.status}
            loggedIn={loggedIn}
            semesterKm={semesterKm}
            semesterPercent={semesterPercent}
            runDays={runDays}
            compact={page !== 'workbench'}
            onStart={requestStart}
            onStop={stopTask}
          />
        ) : null}
      </div>

      <ConsentDialog
        open={consentOpen}
        onAccept={() => setConsentOpen(false)}
        onQuit={() => {
          getCurrentWindow().close().catch(() => undefined);
        }}
      />
      <LoginDialog
        open={login.open && login.stage === 1}
        stage={login.stage}
        preparation={login.preparation}
        loading={login.loading}
        notice={login.notice}
        noticeKind={login.noticeKind}
        onRefresh={() => void refreshCaptcha()}
        onEdit={() => setLogin((previous) => ({ ...previous, notice: '' }))}
        onSubmit={handleSubmitLogin}
        onCancel={cancelLogin}
      />
      <TwoFactorDialog
        open={login.open && login.stage === 2}
        user={login.account}
        loading={login.loading}
        notice={login.notice}
        noticeKind={login.noticeKind}
        onSend={handleSendCode}
        onVerify={handleVerifyCode}
        onCancel={cancelLogin}
      />
      <ConfirmDialog
        open={confirm?.kind === 'start'}
        headline="确认开始任务"
        icon="play_arrow"
        confirmLabel="确认开始"
        busy={task.busy}
        onConfirm={startTask}
        onCancel={() => setConfirm(null)}
      >
        <p>
          即将上传 <strong>{runs}</strong> 条记录，每条 <strong>{distance} km</strong>，路线为
          <strong> {routeDisplayName(routeName)}</strong>。
        </p>
        <p className="dialog-note">请确认已预览实际轨迹，并遵守使用承诺。</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm?.kind === 'delete'}
        headline="删除这条路线？"
        icon="delete"
        confirmLabel="确认删除"
        cancelLabel="保留路线"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setConfirm(null)}
      >
        <p>
          只删除应用中导入的副本，源文件不受影响。
        </p>
        <p className="dialog-note mono">{confirm?.kind === 'delete' ? confirm.routeName : ''}</p>
      </ConfirmDialog>
    </div>
  );
}
