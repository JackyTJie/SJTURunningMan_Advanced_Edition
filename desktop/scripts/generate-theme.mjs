// 生成 MD3 设计令牌（颜色、排版、形状、层级、动效）。
// 颜色来自 Google 官方 material-color-utilities 的 tonal-spot 方案；
// 生成结果提交到 src/styles/tokens.css，构建时不依赖此脚本。
import { argbFromHex, hexFromArgb, themeFromSourceColor } from '@material/material-color-utilities';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const SEED = '#335C9C';
const theme = themeFromSourceColor(argbFromHex(SEED));
const { light, dark } = theme.schemes;
const neutral = theme.palettes.neutral;
const primary = theme.palettes.primary;
const secondary = theme.palettes.secondary;
const tertiary = theme.palettes.tertiary;
const error = theme.palettes.error;

const kebab = (value) => value.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);
const hex = (argb) => hexFromArgb(argb);
const tone = (palette, value) => hex(palette.tone(value));

function scheme(scheme, toneMap) {
  const roles = scheme.toJSON();
  const lines = [];
  for (const [key, value] of Object.entries(roles)) {
    if (key === 'background' || key === 'onBackground') continue; // MD3 2021 已弃用，保留 surface。
    lines.push(`  --md-sys-color-${kebab(key)}: ${hexFromArgb(value)};`);
  }
  for (const [key, value] of Object.entries(toneMap)) {
    lines.push(`  --md-sys-color-${key}: ${value};`);
  }
  return lines.join('\n');
}

const lightTones = {
  'surface-dim': tone(neutral, 87),
  'surface-bright': tone(neutral, 98),
  'surface-container-lowest': tone(neutral, 100),
  'surface-container-low': tone(neutral, 96),
  'surface-container': tone(neutral, 94),
  'surface-container-high': tone(neutral, 92),
  'surface-container-highest': tone(neutral, 90),
  'surface-tint': hex(light.primary),
  'primary-fixed': tone(primary, 90),
  'primary-fixed-dim': tone(primary, 80),
  'on-primary-fixed': tone(primary, 10),
  'on-primary-fixed-variant': tone(primary, 30),
  'secondary-fixed': tone(secondary, 90),
  'secondary-fixed-dim': tone(secondary, 80),
  'on-secondary-fixed': tone(secondary, 10),
  'on-secondary-fixed-variant': tone(secondary, 30),
  'tertiary-fixed': tone(tertiary, 90),
  'tertiary-fixed-dim': tone(tertiary, 80),
  'on-tertiary-fixed': tone(tertiary, 10),
  'on-tertiary-fixed-variant': tone(tertiary, 30),
  'error-fixed': tone(error, 90),
  'error-fixed-dim': tone(error, 80),
  'on-error-fixed': tone(error, 10),
  'on-error-fixed-variant': tone(error, 30),
};

const darkTones = {
  ...lightTones,
  'surface-dim': tone(neutral, 6),
  'surface-bright': tone(neutral, 24),
  'surface-container-lowest': tone(neutral, 4),
  'surface-container-low': tone(neutral, 10),
  'surface-container': tone(neutral, 12),
  'surface-container-high': tone(neutral, 17),
  'surface-container-highest': tone(neutral, 22),
  'surface-tint': hex(dark.primary),
};

const css = `/*
 * SJTU RunningMan — Material Design 3 design tokens.
 * 由 scripts/generate-theme.mjs 从 seed ${SEED} 生成，请勿手改颜色值。
 */
:root {
  color-scheme: light;
${scheme(light, lightTones)}

  /* 排版：MD3 type scale（Roboto + 系统 CJK 回退） */
  --md-ref-typeface-plain: 'Roboto', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei UI', 'Noto Sans CJK SC', system-ui, sans-serif;
  --md-ref-typeface-brand: var(--md-ref-typeface-plain);
  --app-font-mono: 'SF Mono', 'Cascadia Mono', 'Consolas', 'Roboto Mono', monospace;

  --md-sys-typescale-display-large-size: 3.5625rem;
  --md-sys-typescale-display-large-line-height: 4rem;
  --md-sys-typescale-display-large-weight: 400;
  --md-sys-typescale-display-large-tracking: -0.015625rem;
  --md-sys-typescale-display-medium-size: 2.8125rem;
  --md-sys-typescale-display-medium-line-height: 3.25rem;
  --md-sys-typescale-display-medium-weight: 400;
  --md-sys-typescale-display-medium-tracking: 0;
  --md-sys-typescale-display-small-size: 2.25rem;
  --md-sys-typescale-display-small-line-height: 2.75rem;
  --md-sys-typescale-display-small-weight: 400;
  --md-sys-typescale-display-small-tracking: 0;
  --md-sys-typescale-headline-large-size: 2rem;
  --md-sys-typescale-headline-large-line-height: 2.5rem;
  --md-sys-typescale-headline-large-weight: 400;
  --md-sys-typescale-headline-large-tracking: 0;
  --md-sys-typescale-headline-medium-size: 1.75rem;
  --md-sys-typescale-headline-medium-line-height: 2.25rem;
  --md-sys-typescale-headline-medium-weight: 400;
  --md-sys-typescale-headline-medium-tracking: 0;
  --md-sys-typescale-headline-small-size: 1.5rem;
  --md-sys-typescale-headline-small-line-height: 2rem;
  --md-sys-typescale-headline-small-weight: 400;
  --md-sys-typescale-headline-small-tracking: 0;
  --md-sys-typescale-title-large-size: 1.375rem;
  --md-sys-typescale-title-large-line-height: 1.75rem;
  --md-sys-typescale-title-large-weight: 500;
  --md-sys-typescale-title-large-tracking: 0;
  --md-sys-typescale-title-medium-size: 1rem;
  --md-sys-typescale-title-medium-line-height: 1.5rem;
  --md-sys-typescale-title-medium-weight: 500;
  --md-sys-typescale-title-medium-tracking: 0.009375rem;
  --md-sys-typescale-title-small-size: 0.875rem;
  --md-sys-typescale-title-small-line-height: 1.25rem;
  --md-sys-typescale-title-small-weight: 500;
  --md-sys-typescale-title-small-tracking: 0.00625rem;
  --md-sys-typescale-body-large-size: 1rem;
  --md-sys-typescale-body-large-line-height: 1.5rem;
  --md-sys-typescale-body-large-weight: 400;
  --md-sys-typescale-body-large-tracking: 0.03125rem;
  --md-sys-typescale-body-medium-size: 0.875rem;
  --md-sys-typescale-body-medium-line-height: 1.25rem;
  --md-sys-typescale-body-medium-weight: 400;
  --md-sys-typescale-body-medium-tracking: 0.015625rem;
  --md-sys-typescale-body-small-size: 0.75rem;
  --md-sys-typescale-body-small-line-height: 1rem;
  --md-sys-typescale-body-small-weight: 400;
  --md-sys-typescale-body-small-tracking: 0.025rem;
  --md-sys-typescale-label-large-size: 0.875rem;
  --md-sys-typescale-label-large-line-height: 1.25rem;
  --md-sys-typescale-label-large-weight: 500;
  --md-sys-typescale-label-large-tracking: 0.00625rem;
  --md-sys-typescale-label-medium-size: 0.75rem;
  --md-sys-typescale-label-medium-line-height: 1rem;
  --md-sys-typescale-label-medium-weight: 500;
  --md-sys-typescale-label-medium-tracking: 0.03125rem;
  --md-sys-typescale-label-small-size: 0.6875rem;
  --md-sys-typescale-label-small-line-height: 1rem;
  --md-sys-typescale-label-small-weight: 500;
  --md-sys-typescale-label-small-tracking: 0.03125rem;

  /* 形状 */
  --md-sys-shape-corner-none: 0;
  --md-sys-shape-corner-extra-small: 4px;
  --md-sys-shape-corner-small: 8px;
  --md-sys-shape-corner-medium: 12px;
  --md-sys-shape-corner-large: 16px;
  --md-sys-shape-corner-extra-large: 28px;
  --md-sys-shape-corner-full: 9999px;

  /* 层级 */
  --md-sys-elevation-shadow-color: var(--md-sys-color-shadow);
  --app-elevation-0: none;
  --app-elevation-1: 0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 3px 1px rgba(0, 0, 0, 0.15);
  --app-elevation-2: 0 1px 2px rgba(0, 0, 0, 0.3), 0 2px 6px 2px rgba(0, 0, 0, 0.15);
  --app-elevation-3: 0 1px 3px rgba(0, 0, 0, 0.3), 0 4px 8px 3px rgba(0, 0, 0, 0.15);

  /* 状态层与动效 */
  --md-sys-state-hover-state-layer-opacity: 0.08;
  --md-sys-state-focus-state-layer-opacity: 0.1;
  --md-sys-state-pressed-state-layer-opacity: 0.1;
  --md-sys-state-dragged-state-layer-opacity: 0.16;
  --app-motion-standard: cubic-bezier(0.2, 0, 0, 1);
  --app-motion-emphasized: cubic-bezier(0.2, 0, 0, 1);
  --app-motion-duration-short: 150ms;
  --app-motion-duration-medium: 250ms;
  --app-motion-duration-long: 400ms;

  /* Material Components Android progress tokens; dp mapped to CSS px. */
  --app-semester-progress-thickness: 4px;
  --app-semester-progress-amplitude: 3px;
  --app-semester-progress-wavelength: 40px;
  /* Explicit nonzero waveSpeed: one 40px wave per second. Upstream default is 0. */
  --app-semester-progress-speed: 40;
  --app-semester-progress-gap: 4px;
  --app-semester-progress-stop-size: 4px;
  --app-semester-progress-active-color: var(--md-sys-color-primary);
  --app-semester-progress-track-color: var(--md-sys-color-secondary-container);

  /* Task completion celebration: shared palette and particle motion. */
  --app-confetti-colors: #2979ff, #a142f4, #ffca28, #00c853, #ff4081;
  --app-confetti-particles-per-side: 90;
  --app-confetti-scalar: 1.4;
  --app-confetti-emoji-per-side: 8;
  --app-confetti-emoji-scalar: 2.8;
  --app-confetti-spread: 65;
  --app-confetti-velocity: 48;
  --app-confetti-gravity: 1;
  --app-confetti-ticks: 180;
  --app-confetti-layer: 100;

  /* 图标字体 */
  --md-icon-font: 'Material Symbols Rounded';
  --app-sidebar-width: 248px;
}

:root[data-theme='dark'] {
  color-scheme: dark;
${scheme(dark, darkTones)}
}

/* md3.io date picker and distance slider: reuse project tokens. */
.md3-date-field,
.distance-field {
  --mtrl-sys-color-primary: var(--md-sys-color-primary);
  --mtrl-sys-color-on-primary: var(--md-sys-color-on-primary);
  --mtrl-sys-color-secondary: var(--md-sys-color-secondary);
  --mtrl-sys-color-on-secondary: var(--md-sys-color-on-secondary);
  --mtrl-sys-color-secondary-container: var(--md-sys-color-secondary-container);
  --mtrl-sys-color-on-secondary-container: var(--md-sys-color-on-secondary-container);
  --mtrl-sys-color-surface: var(--md-sys-color-surface);
  --mtrl-sys-color-on-surface: var(--md-sys-color-on-surface);
  --mtrl-sys-color-on-surface-variant: var(--md-sys-color-on-surface-variant);
  --mtrl-sys-color-surface-container-high: var(--md-sys-color-surface-container-high);
  --mtrl-sys-color-outline: var(--md-sys-color-outline);
  --mtrl-sys-color-outline-variant: var(--md-sys-color-outline-variant);
  --mtrl-sys-color-error: var(--md-sys-color-error);
  --mtrl-sys-color-scrim: var(--md-sys-color-scrim);
  --mtrl-ref-typeface-plain: var(--md-ref-typeface-plain);
  --mtrl-ref-typeface-brand: var(--md-ref-typeface-brand);
  --mtrl-sys-shape-corner-extra-large: var(--md-sys-shape-corner-extra-large);
  --mtrl-sys-shape-corner-full: var(--md-sys-shape-corner-full);
}
`;

const target = resolve(dirname(fileURLToPath(import.meta.url)), '../src/styles/tokens.css');
writeFileSync(target, css);
console.log(`wrote ${target} (${css.length} bytes)`);
