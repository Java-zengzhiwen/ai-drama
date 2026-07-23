export type PaneRatios = Readonly<{ left: number; right: number }>;
export type WorkspaceDivider = "left" | "right";

type StoredPaneRatios = PaneRatios & { version: 1 };

export const WORKSPACE_RATIO_STORAGE_KEY = "ai-drama:workspace-pane-ratios:v1";
export const MIN_CENTER_RATIO = 55;
export const MIN_LEFT_RATIO = 8;
export const MAX_LEFT_RATIO = 20;
export const MIN_RIGHT_RATIO = 12;
export const MAX_RIGHT_RATIO = 28;

export function defaultPaneRatios(viewportWidth: number): PaneRatios {
  if (viewportWidth < 1024) return { left: 0, right: 0 };
  if (viewportWidth < 1440) return { left: 14, right: 20 };
  return { left: 11, right: 16 };
}

export function centerRatio(ratios: PaneRatios): number {
  return roundRatio(100 - ratios.left - ratios.right);
}

export function clampPaneRatios(input: PaneRatios, viewportWidth: number): PaneRatios {
  if (viewportWidth < 1024) return { left: 0, right: 0 };

  let left = clamp(finiteOr(input.left, MIN_LEFT_RATIO), MIN_LEFT_RATIO, MAX_LEFT_RATIO);
  let right = clamp(finiteOr(input.right, MIN_RIGHT_RATIO), MIN_RIGHT_RATIO, MAX_RIGHT_RATIO);
  let overflow = left + right - (100 - MIN_CENTER_RATIO);

  if (overflow > 0) {
    const rightReduction = Math.min(overflow, right - MIN_RIGHT_RATIO);
    right -= rightReduction;
    overflow -= rightReduction;
  }
  if (overflow > 0) {
    left -= Math.min(overflow, left - MIN_LEFT_RATIO);
  }

  return { left: roundRatio(left), right: roundRatio(right) };
}

export function moveDivider(
  current: PaneRatios,
  divider: WorkspaceDivider,
  delta: number,
  viewportWidth: number,
): PaneRatios {
  const candidate = divider === "left"
    ? { left: current.left + delta, right: current.right }
    : { left: current.left, right: current.right - delta };
  return clampPaneRatios(candidate, viewportWidth);
}

export function parseStoredPaneRatios(raw: string | null): PaneRatios | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<StoredPaneRatios>;
    if (value.version !== 1 || !Number.isFinite(value.left) || !Number.isFinite(value.right)) {
      return null;
    }
    const left = Number(value.left);
    const right = Number(value.right);
    if (
      left < MIN_LEFT_RATIO
      || left > MAX_LEFT_RATIO
      || right < MIN_RIGHT_RATIO
      || right > MAX_RIGHT_RATIO
      || left + right > 100 - MIN_CENTER_RATIO
    ) {
      return null;
    }
    return { left, right };
  } catch {
    return null;
  }
}

export function serializePaneRatios(ratios: PaneRatios): string {
  return JSON.stringify({ version: 1, left: ratios.left, right: ratios.right } satisfies StoredPaneRatios);
}

function finiteOr(value: number, fallback: number): number {
  return Number.isFinite(value) ? value : fallback;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function roundRatio(value: number): number {
  return Math.round(value * 100) / 100;
}
