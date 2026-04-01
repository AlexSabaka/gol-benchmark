/**
 * Color utilities for chart components.
 */

/** Returns an interpolated color for accuracy values 0-1: red → yellow → green */
export function accuracyColor(value: number): string {
  const v = Math.max(0, Math.min(1, value))
  // Red (0%) → Yellow (50%) → Green (100%)
  if (v <= 0.5) {
    const t = v / 0.5
    const r = 220
    const g = Math.round(50 + t * 170)
    const b = Math.round(50 - t * 20)
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (v - 0.5) / 0.5
    const r = Math.round(220 - t * 150)
    const g = Math.round(220 - t * 30)
    const b = Math.round(30 + t * 70)
    return `rgb(${r}, ${g}, ${b})`
  }
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
