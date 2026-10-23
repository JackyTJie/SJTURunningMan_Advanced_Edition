import { useEffect, useRef } from 'react';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

/** 订阅 Tauri 后端事件；回调变化不会重复注册监听。 */
export function useTauriEvent<T>(name: string, handler: (payload: T) => void) {
  const saved = useRef(handler);
  saved.current = handler;
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    let cancelled = false;
    listen<T>(name, (event) => saved.current(event.payload))
      .then((dispose) => {
        if (cancelled) dispose();
        else unlisten = dispose;
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [name]);
}
