import { Slider } from 'material/react';
import { MIN_DISTANCE_KM, MAX_DISTANCE_KM } from '../lib/distance';

interface DistanceSliderProps {
  value: string;
  onValueChange: (value: string) => void;
  disabled: boolean;
}

export function DistanceSlider({ value, onValueChange, disabled }: DistanceSliderProps) {
  return (
    <div className="distance-field" onKeyDownCapture={(event) => {
      if (disabled || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      event.stopPropagation();
      const direction = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 1 : -1;
      onValueChange(String(Number(Math.max(MIN_DISTANCE_KM, Math.min(MAX_DISTANCE_KM, Number(value) + direction * (event.shiftKey ? 0.1 : 0.01))).toFixed(2))));
    }}>
      <div className="distance-heading">
        <span>单次距离</span>
        <span className="distance-value">{Number(value).toFixed(2)} km</span>
      </div>
      <Slider
        aria-label="单次距离"
        aria-valuetext={`${Number(value).toFixed(2)} 公里`}
        min={MIN_DISTANCE_KM}
        max={MAX_DISTANCE_KM}
        step={0}
        size="XS"
        showValue={false}
        value={Number(value)}
        onInput={(event) => onValueChange(String(event.detail.value))}
        disabled={disabled}
      />
      <span className="distance-support">1.20–5.00 km · 连续调节</span>
    </div>
  );
}
