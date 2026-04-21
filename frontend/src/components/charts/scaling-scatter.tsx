import { useMemo } from "react"
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label,
  ErrorBar,
} from "recharts"
import {
  formatModelSize,
  formatParamCount,
  getFamilyColor,
  getModelFamilyColor,
  getModelInfo,
} from "@/lib/model-sizes"
import { wilsonCI, LOW_SAMPLE_THRESHOLD } from "@/lib/stats"
import type { ScatterPoint } from "@/types"
import { ModelBadge } from "./model-badge"
import { trendPoints } from "./trend-line"
import { familyOf, isFamilyActive } from "./family-legend"
import { CI_STROKE_COLOR, LEADER_LINE_COLOR, getThemeColors } from "./chart-theme"

interface ScalingScatterProps {
  data: ScatterPoint[]
  logScale?: boolean
  labelMode?: "hover" | "smart" | "all"
  highlightedFamilies?: Set<string>
}

type ScatterDatum = {
  model: string
  family: string
  x: number
  y: number
  total: number
  errorY: [number, number]
  ciLow: number
  ciHigh: number
  isActive: boolean
  aliases?: string[]
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ScatterDatum | { x: number; y: number } }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  // Trend-line points pass through the same Tooltip — skip if this isn't a scatter datum.
  if (!d || !("model" in d) || typeof (d as ScatterDatum).total !== "number") return null
  const sd = d as ScatterDatum
  const lowN = sd.total < LOW_SAMPLE_THRESHOLD
  return (
    <div className="space-y-2 rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <ModelBadge model={sd.model} layout="inline" mergedCount={sd.aliases?.length} />
      <div className="space-y-0.5 text-xs">
        <p>Parameters: {formatParamCount(sd.x)}</p>
        <p>
          Accuracy: {(sd.y * 100).toFixed(1)}% <span className="text-muted-foreground">(n={sd.total.toLocaleString()})</span>
        </p>
        <p className="text-muted-foreground">
          95% CI [{(sd.ciLow * 100).toFixed(1)}%, {(sd.ciHigh * 100).toFixed(1)}%]
        </p>
        {lowN && (
          <p className="text-amber-600 dark:text-amber-400">Low sample size — CI is wide.</p>
        )}
        {sd.aliases && sd.aliases.length > 1 && (
          <p className="text-muted-foreground">Merged from: {sd.aliases.join(", ")}</p>
        )}
      </div>
    </div>
  )
}

function buildSmartLabelSet(data: ScatterDatum[]): Set<string> {
  if (data.length <= 12) return new Set(data.map((entry) => entry.model))

  const selected = new Set<string>()
  const byAccuracyDesc = [...data].sort((left, right) => right.y - left.y)
  const byAccuracyAsc = [...data].sort((left, right) => left.y - right.y)
  const byParams = [...data].sort((left, right) => left.x - right.x)

  byAccuracyDesc.slice(0, 4).forEach((entry) => selected.add(entry.model))
  byAccuracyAsc.slice(0, 2).forEach((entry) => selected.add(entry.model))
  byParams.slice(0, 1).forEach((entry) => selected.add(entry.model))
  byParams.slice(-1).forEach((entry) => selected.add(entry.model))

  const stride = Math.max(Math.floor(data.length / 6), 1)
  byParams.forEach((entry, index) => {
    if (index % stride === 0 && selected.size < 12) selected.add(entry.model)
  })

  return selected
}

/**
 * Build per-model label placement offsets. Walks points sorted by screen x, and
 * when two labels land in the same x bucket within vertical reach, it flips
 * every-other one above/below the dot. A short leader line connects displaced
 * labels back to their dot so the association stays readable.
 */
function buildLabelPlacement(
  points: Array<{ model: string; x: number; y: number }>,
  xDomain: [number, number],
  logScale: boolean,
): Map<string, { anchor: "start" | "end"; dy: number; leader: boolean }> {
  const sorted = [...points].sort((a, b) => a.x - b.x)
  const result = new Map<string, { anchor: "start" | "end"; dy: number; leader: boolean }>()

  const xBuckets: Array<Array<{ model: string; x: number; y: number }>> = []
  const bucketCount = 8
  const xRange = logScale
    ? [Math.log10(xDomain[0]), Math.log10(xDomain[1])]
    : xDomain
  const toBucket = (x: number) => {
    const v = logScale ? Math.log10(x) : x
    const t = (v - xRange[0]) / (xRange[1] - xRange[0])
    return Math.min(bucketCount - 1, Math.max(0, Math.floor(t * bucketCount)))
  }

  for (const pt of sorted) {
    const idx = toBucket(pt.x)
    ;(xBuckets[idx] ??= []).push(pt)
  }

  for (const bucket of xBuckets) {
    if (!bucket) continue
    // Sort by y so we can alternate displacement in a stable way
    bucket.sort((a, b) => b.y - a.y)
    bucket.forEach((pt, i) => {
      const above = i % 2 === 0
      result.set(pt.model, {
        anchor: i >= 2 ? "end" : "start",
        dy: above ? -10 : 16,
        leader: bucket.length > 2,
      })
    })
  }

  return result
}

/** Custom dot + label renderer. Applies family fade via opacity. */
function CustomDot(props: {
  cx?: number
  cy?: number
  payload?: ScatterDatum
  showLabel?: boolean
  placement?: { anchor: "start" | "end"; dy: number; leader: boolean }
}) {
  const { cx, cy, payload, showLabel, placement } = props
  if (cx == null || cy == null || !payload || !payload.model) return null

  const color = getModelFamilyColor(payload.model)
  const info = getModelInfo(payload.model)
  const nameLabel = info ? (info.variant ? `${info.family} ${info.variant}` : info.family) : payload.model
  const truncated = nameLabel.length > 22 ? nameLabel.slice(0, 20) + "\u2026" : nameLabel
  const sizeLabel = info ? formatModelSize(info) : null
  const opacity = payload.isActive ? 0.9 : 0.25
  const theme = getThemeColors()

  const labelX = cx + (placement?.anchor === "end" ? -10 : 10)
  const labelY = cy + (placement?.dy ?? -10)

  return (
    <g opacity={opacity}>
      <circle cx={cx} cy={cy} r={6} fill={color} stroke="#fff" strokeWidth={1.5} />
      {showLabel ? (
        <g>
          {placement?.leader && (
            <line
              x1={cx}
              y1={cy}
              x2={labelX + (placement.anchor === "end" ? 2 : -2)}
              y2={labelY - 3}
              stroke={LEADER_LINE_COLOR}
              strokeWidth={0.5}
              opacity={0.45}
            />
          )}
          <text
            x={labelX}
            y={labelY}
            textAnchor={placement?.anchor ?? "start"}
            fontSize={11}
            fill={theme.foreground}
            fillOpacity={0.85}
          >
            {truncated}
            {sizeLabel ? (
              <tspan fontFamily="ui-monospace, SFMono-Regular, monospace" fill={theme.mutedForeground} dx={6}>
                {sizeLabel}
              </tspan>
            ) : null}
          </text>
        </g>
      ) : null}
    </g>
  )
}

export function ScalingScatter({
  data,
  logScale = true,
  labelMode = "smart",
  highlightedFamilies,
}: ScalingScatterProps) {
  const highlighted = highlightedFamilies ?? new Set<string>()
  const known = data.filter((d) => d.paramCount !== null)
  const unknown = data.filter((d) => d.paramCount === null)

  const chartData: ScatterDatum[] = useMemo(
    () =>
      known.map((d) => {
        const family = familyOf(d.model)
        const { low, high } = wilsonCI(Math.round(d.accuracy * d.total), d.total)
        return {
          model: d.model,
          family,
          x: d.paramCount!,
          y: d.accuracy,
          total: d.total,
          ciLow: low,
          ciHigh: high,
          errorY: [d.accuracy - low, high - d.accuracy],
          isActive: isFamilyActive(family, highlighted),
          aliases: d.aliases,
        }
      }),
    [known, highlighted],
  )

  const labeledModels = useMemo(() => {
    if (labelMode === "all") return new Set(chartData.map((entry) => entry.model))
    if (labelMode === "hover") return new Set<string>()
    return buildSmartLabelSet(chartData)
  }, [chartData, labelMode])

  const xDomain = useMemo<[number, number]>(() => {
    if (!chartData.length) return [1, 1e12]
    const xs = chartData.map((d) => d.x)
    return [Math.min(...xs), Math.max(...xs)]
  }, [chartData])

  const labelPlacement = useMemo(
    () =>
      buildLabelPlacement(
        chartData.filter((d) => labeledModels.has(d.model)),
        xDomain,
        logScale,
      ),
    [chartData, labeledModels, xDomain, logScale],
  )

  /** Trend lines: overall when nothing is soloed; per-family otherwise. */
  const trendSeries = useMemo(() => {
    if (chartData.length < 2) return []
    // Work in log space for x when logScale is on so LOESS bandwidth behaves
    const toFit = (pts: ScatterDatum[]) =>
      pts.map((d) => ({ x: logScale ? Math.log10(d.x) : d.x, y: d.y, rawX: d.x }))
    const fromFit = (pts: Array<{ x: number; y: number }>) =>
      pts.map((p) => ({ x: logScale ? Math.pow(10, p.x) : p.x, y: p.y }))

    if (highlighted.size === 0) {
      const fit = trendPoints(toFit(chartData))
      return fit.length
        ? [{ family: "__overall__", color: "currentColor", points: fromFit(fit), dashed: true }]
        : []
    }

    return [...highlighted]
      .map((family) => {
        const fam = chartData.filter((d) => d.family === family)
        if (fam.length < 2) return null
        const fit = trendPoints(toFit(fam))
        if (!fit.length) return null
        return {
          family,
          color: getFamilyColor(family),
          points: fromFit(fit),
          dashed: false,
        }
      })
      .filter((s): s is NonNullable<typeof s> => s !== null)
  }, [chartData, highlighted, logScale])

  if (!known.length) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
        <p>No models with known parameter counts.</p>
        <p className="text-xs">
          Model sizes are inferred from names (e.g. &quot;7b&quot;, &quot;27b&quot;).
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {unknown.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {unknown.length} model{unknown.length > 1 ? "s" : ""} not shown (unknown parameter count):{" "}
          {unknown.map((d) => d.model).join(", ")}
        </p>
      )}
      <ResponsiveContainer width="100%" height={440}>
        <ComposedChart margin={{ top: 24, right: 80, bottom: 40, left: 56 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            type="number"
            dataKey="x"
            scale={logScale ? "log" : "linear"}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => formatParamCount(v)}
            allowDuplicatedCategory={false}
          >
            <Label value="Parameters" position="bottom" offset={14} className="fill-muted-foreground text-sm" />
          </XAxis>
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          >
            <Label value="Accuracy" angle={-90} position="left" offset={10} className="fill-muted-foreground text-sm" />
          </YAxis>
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={chartData}
            isAnimationActive={false}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            shape={(props: any) => (
              <CustomDot
                {...props}
                showLabel={props.payload.isActive && labeledModels.has(props.payload.model)}
                placement={labelPlacement.get(props.payload.model)}
              />
            )}
          >
            <ErrorBar dataKey="errorY" direction="y" width={4} stroke={CI_STROKE_COLOR} strokeOpacity={0.7} />
          </Scatter>
          {trendSeries.map((series) => (
            <Line
              key={series.family}
              data={series.points}
              dataKey="y"
              type="monotone"
              stroke={series.color}
              strokeWidth={1.75}
              strokeDasharray={series.dashed ? "4 3" : undefined}
              dot={false}
              isAnimationActive={false}
              legendType="none"
              activeDot={false}
              connectNulls
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-xs text-muted-foreground">
        {labelMode === "hover"
          ? "Labels are hidden until hover for maximum clarity."
          : labelMode === "smart"
            ? "Smart labels highlight a representative subset. Hover for exact values."
            : "All model labels are shown. Hover shows exact values and CI."}
      </p>
    </div>
  )
}
