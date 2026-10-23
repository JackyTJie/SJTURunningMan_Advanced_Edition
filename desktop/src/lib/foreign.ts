import { useEffect, useRef, type RefObject } from 'react';

/**
 * 给 @material/web 自定义元素绑定其自定义事件。
 *
 * 这些组件的事件（input/change/closed 等）不是 React 的合成事件，直接写
 * onChange 不可靠；这里只做 addEventListener 适配，不包装或仿制组件本身。
 */
export function useCustomEvent<T extends Event, E extends HTMLElement>(
  ref: RefObject<E | null>,
  event: string,
  handler: (event: T) => void,
) {
  const saved = useRef(handler);
  saved.current = handler;
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const listener = (event: Event) => saved.current(event as T);
    element.addEventListener(event, listener);
    return () => element.removeEventListener(event, listener);
  }, [ref, event]);
}
