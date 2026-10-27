import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { Point } from '../lib/backend';

interface RouteMapProps {
  points: Point[];
  bounds?: Point[];
  height?: number;
  fill?: boolean;
  stale?: boolean;
  jumpSegments?: number[];
  label?: string;
}

interface Projected {
  x: number;
  y: number;
}

interface Size {
  width: number;
  height: number;
}

function project(points: Point[], width: number, height: number, bounds: Point[] = points): Projected[] {
  if (points.length === 0) return [];
  const lon = bounds.map((point) => point.lon);
  const lat = bounds.map((point) => point.lat);
  const minLon = Math.min(...lon);
  const maxLon = Math.max(...lon);
  const minLat = Math.min(...lat);
  const maxLat = Math.max(...lat);
  const midLat = (minLat + maxLat) / 2;
  const aspect = Math.max(Math.cos((midLat * Math.PI) / 180), 0.2);
  const pad = 38;
  const spanX = Math.max((maxLon - minLon) * aspect, 1e-9);
  const spanY = Math.max(maxLat - minLat, 1e-9);
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const offsetX = width / 2 - ((minLon + maxLon) / 2) * aspect * scale;
  const offsetY = height / 2 + ((minLat + maxLat) / 2) * scale;
  return points.map((point) => ({
    x: offsetX + point.lon * aspect * scale,
    y: offsetY - point.lat * scale,
  }));
}

function segments(projected: Projected[], jumpSegments: number[]) {
  const jumpSet = new Set(jumpSegments);
  const normal: string[] = [];
  const jump: string[] = [];
  for (let index = 1; index < projected.length; index += 1) {
    const from = projected[index - 1];
    const to = projected[index];
    const command = `M ${from.x.toFixed(2)} ${from.y.toFixed(2)} L ${to.x.toFixed(2)} ${to.y.toFixed(2)}`;
    if (jumpSet.has(index)) jump.push(command);
    else normal.push(command);
  }
  return { normal: normal.join(' '), jump: jump.join(' ') };
}

/** 轨迹预览：随 MD3 主题着色的本地 SVG，按容器实际尺寸投影，不加载网络瓦片。 */
export function RouteMap({
  points,
  bounds,
  height = 360,
  fill = false,
  stale = false,
  jumpSegments = [],
  label,
}: RouteMapProps) {
  const patternId = useId().replace(/:/g, '');
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<Size>({ width: 760, height });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const update = (width: number, nextHeight: number) => {
      const next = { width: Math.max(Math.round(width), 1), height: Math.max(Math.round(nextHeight), 1) };
      setSize((previous) =>
        previous.width === next.width && previous.height === next.height ? previous : next,
      );
    };
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) update(rect.width, rect.height);
    });
    observer.observe(element);
    const rect = element.getBoundingClientRect();
    update(rect.width, rect.height);
    return () => observer.disconnect();
  }, [height]);

  const projected = useMemo(() => project(points, size.width, size.height, bounds), [points, size, bounds]);
  const path = useMemo(() => segments(projected, jumpSegments), [projected, jumpSegments]);
  const start = projected[0];
  const end = projected[projected.length - 1];

  return (
    <div
      ref={containerRef}
      className={`route-map${fill ? ' is-fill' : ''}${stale ? ' is-stale' : ''}`}
      style={fill ? undefined : { height }}
    >
      <svg
        viewBox={`0 0 ${size.width} ${size.height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label ?? '路线轨迹预览'}
      >
        <defs>
          <pattern id={patternId} width="32" height="32" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" className="map-dot" />
          </pattern>
        </defs>
        <rect width={size.width} height={size.height} fill={`url(#${patternId})`} />
        {projected.length > 1 ? (
          <>
            <path className="map-halo" d={path.normal} />
            <path className="map-jump-halo" d={path.jump} />
            <path className="map-line" d={path.normal} />
            <path className="map-jump" d={path.jump} />
            {start ? (
              <g className="map-start">
                <circle cx={start.x} cy={start.y} r="9" />
                <circle cx={start.x} cy={start.y} r="4.5" />
              </g>
            ) : null}
            {end ? (
              <g className="map-end">
                <circle cx={end.x} cy={end.y} r="9" />
                <circle cx={end.x} cy={end.y} r="4.5" />
              </g>
            ) : null}
          </>
        ) : (
          <g className="map-empty">
            <text x={size.width / 2} y={size.height / 2 - 8} textAnchor="middle">
              暂无轨迹
            </text>
            <text
              x={size.width / 2}
              y={size.height / 2 + 18}
              textAnchor="middle"
              className="map-empty-sub"
            >
              选择路线或生成预览后显示
            </text>
          </g>
        )}
      </svg>
      {stale ? <div className="route-map-stale">参数已修改 · 预览待更新</div> : null}
    </div>
  );
}
