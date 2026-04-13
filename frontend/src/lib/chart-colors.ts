/**
 * Color utilities for chart components.
 */

function clampAccuracy(value: number): number {
  return Math.max(0, Math.min(1, value))
}

function mixChannel(start: number, end: number, t: number): number {
  return Math.round(start + (end - start) * t)
}

function mixRgb(start: [number, number, number], end: [number, number, number], t: number): string {
  return `rgb(${mixChannel(start[0], end[0], t)}, ${mixChannel(start[1], end[1], t)}, ${mixChannel(start[2], end[2], t)})`
}

export function accuracyBucket(value: number): "low" | "mid" | "high" {
  const v = clampAccuracy(value)
  if (v < 0.34) return "low"
  if (v < 0.67) return "mid"
  return "high"
}

/** Returns an interpolated color for accuracy values 0-1: orange → sand → teal */
export function accuracyColor(value: number): string {
  const v = clampAccuracy(value)
  const low: [number, number, number] = [178, 95, 46]
  const mid: [number, number, number] = [221, 208, 144]
  const high: [number, number, number] = [36, 132, 124]

  if (v <= 0.5) {
    const t = v / 0.5
    return mixRgb(low, mid, t)
  }

  const t = (v - 0.5) / 0.5
  return mixRgb(mid, high, t)
}

export function accuracyTextColor(value: number): string {
  const bucket = accuracyBucket(value)
  return bucket === "mid" ? "#1f2937" : "#ffffff"
}

/** CSS variable-based chart colors for distinct model series */
const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
]

/** Fallback hex colors when CSS vars aren't available (e.g. recharts tooltips) */
const CHART_COLORS_HEX = [
  "#e76e50",
  "#2a9d8f",
  "#264653",
  "#e9c46a",
  "#f4a261",
  "#6a4c93",
  "#1982c4",
  "#8ac926",
  "#ff595e",
  "#ffca3a",
]

export function modelColorScale(models: string[]): Record<string, string> {
  const map: Record<string, string> = {}
  models.forEach((m, i) => {
    map[m] = CHART_COLORS_HEX[i % CHART_COLORS_HEX.length]
  })
  return map
}

export { CHART_COLORS, CHART_COLORS_HEX }
