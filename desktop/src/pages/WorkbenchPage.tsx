import { MIN_DISTANCE_KM, MAX_DISTANCE_KM } from '../lib/distance';
import { routeDisplayName } from '../lib/routeName';
import type { CalendarWeek, PreviewMapResult, PreviewView, RouteDetail, RouteView } from '../lib/backend';
import { RoutePreviewCard } from '../components/RoutePreviewCard';
import { SelectField, type SelectOption } from '../components/SelectField';
import { SwitchField } from '../components/SwitchField';
import { TextField } from '../components/TextField';
import { TimeField } from '../components/TimeField';
import { DistanceSlider } from '../components/DistanceSlider';
import { DateField } from '../components/DateField';
import { formatClock12 } from '../lib/time';

export interface WorkbenchProps {
  runs: string;
  onRunsChange: (value: string) => void;
  distance: string;
  onDistanceChange: (value: string) => void;
  date: string;
  weeks: CalendarWeek[];
  onDateChange: (value: string) => void;
  time: string;
  onTimeChange: (value: string) => void;
  skipExisting: boolean;
  onSkipExistingChange: (value: boolean) => void;
  routes: RouteView[];
  routeName: string;
  onRouteChange: (name: string) => void;
  route: RouteDetail | null;
  preview: PreviewView | null;
  stale: boolean;
  busy: boolean;
  onOpenMap: () => Promise<PreviewMapResult | null>;
}

function endDateLabel(value: string): string | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return `${Number(match[2])}月${Number(match[3])}日`;
}

/** 把当前四项参数翻译成一句人话，让用户在开始前就能确认这次计划。 */
function planSummary(runs: string, distance: string, date: string, time: string) {
  const count = Number(runs);
  const km = Number(distance);
  const countOk = Number.isInteger(count) && count >= 1 && count <= 30;
  const distanceOk = Number.isFinite(km) && km >= MIN_DISTANCE_KM && km <= MAX_DISTANCE_KM;

  const title =
    countOk && distanceOk
      ? `${count} 次 · 合计 ${(count * km).toFixed(1)} km`
      : '填写完整后显示合计';

  const end = endDateLabel(date);
  const clock = formatClock12(time);
  const parts: string[] = [];
  if (end) parts.push(`${end}截止`);
  if (clock) parts.push(`${clock} 前后起跑`);

  return {
    title,
    detail: parts.length ? parts.join(' · ') : '选择结束日期并填写开始时间',
  };
}

export function WorkbenchPage(props: WorkbenchProps) {
  const options: SelectOption[] = props.routes.map((route) => ({
    value: route.name,
    label: `${routeDisplayName(route.name)} · ${route.distanceKm.toFixed(2)} km`,
  }));
  const summary = planSummary(props.runs, props.distance, props.date, props.time);

  return (
    <div className="workbench-grid">
      <div className="workbench-left">
        <md-outlined-card className="surface-card plan-card">
          <div className="card-body">
            <div className="plan-section-head">
              <md-icon aria-hidden="true">speed</md-icon>
              <h2 className="plan-section-title">跑步参数</h2>
            </div>

            <div className="plan-summary">
              <md-icon aria-hidden="true">calendar_month</md-icon>
              <div className="plan-summary-copy">
                <span className="plan-summary-title">{summary.title}</span>
                <span className="plan-summary-detail">{summary.detail}</span>
              </div>
            </div>

            <div className="field-grid">
              <TextField
                label="跑步次数"
                value={props.runs}
                onValueChange={props.onRunsChange}
                disabled={props.busy}
                inputMode="numeric"
                supportingText="1–30 次"
                className="runs-field"
              />
              <DistanceSlider
                value={props.distance}
                onValueChange={props.onDistanceChange}
                disabled={props.busy}
              />
              <DateField
                weeks={props.weeks}
                value={props.date}
                onValueChange={props.onDateChange}
                disabled={props.busy}
              />
              <TimeField
                value={props.time}
                onValueChange={props.onTimeChange}
                disabled={props.busy}
              />
            </div>

            <SwitchField
              label="跳过已有记录的日期"
              supportingText="已有记录的日期会前移，条数不变"
              checked={props.skipExisting}
              onCheckedChange={props.onSkipExistingChange}
              disabled={props.busy}
            />

            <div className="plan-section-head">
              <md-icon aria-hidden="true">route</md-icon>
              <h3 className="plan-section-title">路线</h3>
            </div>

            <SelectField
              label="当前路线"
              value={props.routeName}
              options={options}
              onValueChange={props.onRouteChange}
              disabled={props.busy}
              className="route-select"
            />
          </div>
        </md-outlined-card>
      </div>

      <RoutePreviewCard
        route={props.route}
        preview={props.preview}
        stale={props.stale}
        busy={props.busy}
        mode="workbench"
        distanceKm={Number(props.distance)}
        onOpenMap={props.onOpenMap}
      />
    </div>
  );
}
