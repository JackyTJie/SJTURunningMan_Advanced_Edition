import { routeDisplayName } from '../lib/routeName';
import type { PreviewMapResult, PreviewView, RouteDetail, RouteView } from '../lib/backend';
import { RoutePreviewCard } from '../components/RoutePreviewCard';

interface RoutesPageProps {
  routes: RouteView[];
  route: RouteDetail | null;
  routeName: string;
  preview: PreviewView | null;
  stale: boolean;
  busy: boolean;
  onSelect: (name: string) => void;
  distanceKm: number;
  onOpenMap: () => Promise<PreviewMapResult | null>;
  onPlanner: () => void;
  onImport: () => void;
  onDelete: () => void;
}

export function RoutesPage({
  routes,
  route,
  routeName,
  preview,
  stale,
  busy,
  onSelect,
  distanceKm,
  onOpenMap,
  onPlanner,
  onImport,
  onDelete,
}: RoutesPageProps) {
  return (
    <div className="routes-grid">
      <md-outlined-card className="surface-card route-list-card">
        <div className="card-body">
          <div className="card-header compact-header">
            <div>
              <div className="card-eyebrow">资料库</div>
              <h2 className="card-title">路线列表</h2>
              <p className="card-sub">{routes.length} 条可用路线 · 内置 1 条</p>
            </div>
            <md-outlined-button onClick={onImport} disabled={busy}>
              <md-icon slot="icon" aria-hidden="true">upload_file</md-icon>
              导入
            </md-outlined-button>
          </div>
          <md-list className="route-list" type="button">
            {routes.map((item) => (
              <md-list-item
                key={item.name}
                type="button"
                disabled={busy}
                className={`route-list-item${routeName === item.name ? ' is-active' : ''}`}
                onClick={() => onSelect(item.name)}
                aria-current={routeName === item.name ? 'true' : undefined}
              >
                <md-icon slot="start" aria-hidden="true">
                  {item.imported ? 'edit_location_alt' : 'flag'}
                </md-icon>
                <div className="route-item-name">{routeDisplayName(item.name)}</div>
                <div slot="supporting-text">
                  {item.distanceKm.toFixed(2)} km · {item.pointCount.toLocaleString()} 个点
                </div>
                <span slot="end" className={`route-badge${item.imported ? ' is-imported' : ''}`}>
                  {item.imported ? '导入' : '内置'}
                </span>
              </md-list-item>
            ))}
          </md-list>
          <div className="route-list-foot">
            <md-icon aria-hidden="true">info</md-icon>
            <span>导入会保留独立副本；内置路线不可删除。</span>
          </div>
        </div>
      </md-outlined-card>

      <RoutePreviewCard
        route={route}
        preview={preview}
        stale={stale}
        busy={busy}
        mode="routes"
        distanceKm={distanceKm}
        onOpenMap={onOpenMap}
        onPlanner={onPlanner}
        onDelete={onDelete}
      />
    </div>
  );
}
