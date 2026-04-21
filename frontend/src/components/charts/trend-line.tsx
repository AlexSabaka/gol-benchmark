import { regressionLinear, regressionLoess } from "d3-regression"

export interface TrendPoint {
  x: number
  y: number
}

/**
 * Compute trend-line points for a scatter series.
 *
 * Uses LOESS (locally-weighted regression) when there are enough data points to
 * extract a meaningful local trend (default `8+`), and falls back to a simple
 * linear fit for small samples where LOESS bandwidth would collapse.
 *
 * Returns an empty array when there are fewer than 2 distinct x-values — a
 * single point can't form a trend.
 */
export function trendPoints(
  data: Array<{ x: number; y: number }>,
  options: { method?: "loess" | "linear" | "auto"; bandwidth?: number } = {},
): TrendPoint[] {
  if (data.length < 2) return []
  const distinctX = new Set(data.map((d) => d.x)).size
  if (distinctX < 2) return []

  const method = options.method ?? "auto"
  const effectiveMethod = method === "auto" ? (data.length >= 8 ? "loess" : "linear") : method

  const accessor = { x: (d: unknown) => (d as { x: number }).x, y: (d: unknown) => (d as { y: number }).y }

  if (effectiveMethod === "loess") {
    const fit = regressionLoess()
      .x(accessor.x)
      .y(accessor.y)
      .bandwidth(options.bandwidth ?? 0.75)
    const points = fit(data)
    return points.map(([x, y]) => ({ x, y }))
  }

  const fit = regressionLinear().x(accessor.x).y(accessor.y)
  const points = fit(data)
  return points.map(([x, y]) => ({ x, y }))
}
