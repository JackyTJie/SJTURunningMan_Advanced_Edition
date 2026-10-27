import { routeDisplayName } from '../lib/routeName';
import { useEffect, useRef, useState } from 'react';
import type { PreviewMapResult, PreviewView, RouteDetail } from '../lib/backend';
import { useLiveRoute, meters } from '../lib/liveRoute';
import { RouteMap } from './RouteMap';

const EMPTY_POINTS: RouteDetail["points"] = [];

interface RoutePreviewCardProps {
  distanceKm?: number;
  route: RouteDetail | null;
  preview: PreviewView | null;
  stale: boolean;
  busy: boolean;
  mode: 'workbench' | 'routes';
  onOpenMap: () => Promise<PreviewMapResult | null>;
  onPlanner?: () => void;
  onDelete?: () => void;
}

export function RoutePreviewCard({
  route,
  distanceKm,
  preview,
  stale,
  busy,
  mode,
  onOpenMap,
  onPlanner,
  onDelete,
}: RoutePreviewCardProps) {
  const live = useLiveRoute(route?.points ?? EMPTY_POINTS, distanceKm);
  const points = distanceKm !== undefined ? live.points : preview?.points ?? route?.points ?? EMPTY_POINTS;
  const frameRef = useRef<HTMLIFrameElement>(null);
  const syncMap = () => {
    if (!mapUrl) return;
    frameRef.current?.contentWindow?.postMessage({ type: 'sjturm-route-update', points, bounds: distanceKm !== undefined ? live.bounds : undefined }, new URL(mapUrl).origin);
  };
  const distance = distanceKm !== undefined ? distanceKm : preview ? preview.distanceM / 1000 : route?.distanceKm ?? 0;
  const pointCount = points.length;
  const jumpSegments = distanceKm !== undefined
    ? points.flatMap((p, i) => i > 0 && meters(points[i - 1], p) > 150 ? [i] : [])
    : preview?.jumpSegments ?? route?.jumpSegments ?? [];
  const jumpCount = jumpSegments.length;
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [mapNotice, setMapNotice] = useState<string | null>(null);
  const [mapLoading, setMapLoading] = useState(false);

  const [mapExpanded, setMapExpanded] = useState(true);
  const openMapRef = useRef(onOpenMap);
  openMapRef.current = onOpenMap;

  // 默认加载在线底图；仅路线或展开状态变化时请求，参数变化原位同步。
  useEffect(() => {
    let cancelled = false;
    setMapUrl(null);
    setMapNotice(null);
    setMapLoading(false);
    if (!route?.name || !mapExpanded) return;

    setMapLoading(true);
    void (async () => {
      try {
        const result = await openMapRef.current();
        if (cancelled) return;
        if (result) {
          setMapUrl(result.url);
          setMapNotice(result.notice);
        } else {
          setMapExpanded(false);
        }
      } catch {
        // 具体错误已由 App 的状态条提示，保留本地预览并允许重试。
        if (!cancelled) setMapExpanded(false);
      } finally {
        if (!cancelled) setMapLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [route?.name, mapExpanded]);

  useEffect(syncMap, [points, mapUrl]);

  const toggleMap = () => setMapExpanded((expanded) => !expanded);

  return (
    <md-outlined-card className="surface-card preview-card">
      <div className="card-body">
        {mode === 'routes' ? (
          <div className="card-header">
            <div>
              <div className="card-eyebrow">路线预览</div>
              <h2 className="card-title">{route ? routeDisplayName(route.name) : '未选择路线'}</h2>
              <p className="card-sub">
                {distanceKm !== undefined && route
                  ? `按当前单次距离 ${distanceKm.toFixed(2)} km 自动预览 · 原始路线 ${route.distanceKm.toFixed(2)} km`
                  : preview
                  ? preview.summary
                  : route
                    ? `原始路线 ${route.distanceKm.toFixed(2)} km · ${route.pointCount} 个坐标点`
                    : '请先选择一条路线'}
              </p>
            </div>
            {route ? (
              <div className="preview-head-actions">
                <span className={`route-badge${route.imported ? ' is-imported' : ''}`}>
                  {route.imported ? '已导入 · BD09' : '内置 · BD09'}
                </span>
                {mode === 'routes' && route.canDelete ? (
                  <md-icon-button
                    className="delete-icon"
                    aria-label="删除路线"
                    title="删除路线"
                    onClick={onDelete}
                    disabled={busy}
                  >
                    <md-icon aria-hidden="true">delete</md-icon>
                  </md-icon-button>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
        {mapUrl ? (
          <div
            className={`route-map route-map-live${mode === 'workbench' ? ' is-fill' : ''}`}
            style={mode === 'routes' ? { height: 380 } : undefined}
          >
            <iframe
              ref={frameRef}
              onLoad={syncMap}
              className="route-map-frame"
              src={mapUrl}
              title={`${route ? routeDisplayName(route.name) : '路线'} 地图`}
            />
          </div>
        ) : (
          <RouteMap
            points={points}
            bounds={distanceKm !== undefined ? live.bounds : undefined}
            height={380}
            fill={mode === 'workbench'}
            stale={distanceKm === undefined && stale}
            jumpSegments={jumpSegments}
            label={`${route ? routeDisplayName(route.name) : ''} 轨迹预览`}
          />
        )}
        {mode === 'routes' && mapUrl && mapNotice ? (
          <div className="inline-alert">
            <md-icon aria-hidden="true">info</md-icon>
            <span>{mapNotice}</span>
          </div>
        ) : null}
        <div className="metric-row">
          <div className="metric">
            <span className="metric-label">距离</span>
            <span className="metric-value">{distance.toFixed(2)}<small> km</small></span>
          </div>
          <div className="metric">
            <span className="metric-label">坐标点</span>
            <span className="metric-value">{pointCount.toLocaleString()}</span>
          </div>
          <div className="metric">
            <span className="metric-label">跳段</span>
            <span className={`metric-value${jumpCount > 0 ? ' is-warning' : ''}`}>{jumpCount}</span>
          </div>
          <div className="metric metric-legend">
            <span className="legend-item"><i className="marker start" />起点</span>
            <span className="legend-item"><i className="marker end" />终点</span>
          </div>
        </div>
        {route?.warning ? (
          <div className="inline-alert">
            <md-icon aria-hidden="true">warning</md-icon>
            <span>{route.warning}</span>
          </div>
        ) : null}
        {mode === 'routes' || !mapUrl ? <div className="card-actions">
          <md-outlined-button onClick={toggleMap} disabled={busy || !route || mapLoading}>
            <md-icon slot="icon" aria-hidden="true">map</md-icon>
            {mapLoading ? '正在加载地图…' : mapUrl ? '收起地图' : '在地图中打开'}
          </md-outlined-button>
          {mode === 'routes' && onPlanner ? (
            <md-text-button onClick={onPlanner} disabled={busy}>
              <md-icon slot="icon" aria-hidden="true">open_in_new</md-icon>
              设计路线
            </md-text-button>
          ) : null}
        </div> : null}
      </div>
    </md-outlined-card>
  );
}
