import { memo, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
  ErrorBar,
  LabelList,
} from "recharts"
import { accuracyColor, accuracyTextColor } from "@/lib/chart-colors"
import { wilsonCI, LOW_SAMPLE_THRESHOLD } from "@/lib/stats"
import type { BarDataPoint } from "@/hooks/use-chart-data"
import { ModelBadge } from "./model-badge"
import { SvgModelTick } from "./svg-model-tick"
import { familyOf, isFamilyActive } from "./family-legend"
import { CI_STROKE_COLOR } from "./chart-theme"

interface ModelBarChartProps {
  data: BarDataPoint[]
  highlightedFamilies?: Set<string>
}

interface EnrichedPoint extends BarDataPoint {
  ciLow: number
  ciHigh: number
  errorX: [number, number]
  isActive: boolean
  family: string
  lowSample: boolean
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: EnrichedPoint }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="space-y-2 rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <ModelBadge model={d.model} layout="inline" mergedCount={d.aliases?.length} />
      <div className="space-y-0.5 text-xs">
        <p>
          Accuracy: {(d.accuracy * 100).toFixed(1)}% <span className="text-muted-foreground">(n={d.total.toLocaleString()})</span>
        </p>
        <p className="text-muted-foreground">
          95% CI [{(d.ciLow * 100).toFixed(1)}%, {(d.ciHigh * 100).toFixed(1)}%]
        </p>
        <p className="text-muted-foreground">
          {d.correct} / {d.total} correct
        </p>
        {d.lowSample && (
          <p className="text-amber-600 dark:text-amber-400">Low sample size — CI is wide.</p>
        )}
        {d.aliases && d.aliases.length > 1 && (
          <p className="text-muted-foreground">
            Merged from: {d.aliases.join(", ")}
          </p>
        )}
      </div>
    </div>
  )
}

function BadgeTick({
  x,
  y,
  payload,
  activeModels,
}: {
  x?: number
  y?: number
  payload?: { value: string }
  activeModels?: Set<string>
}) {
  if (x == null || y == null || !payload) return null
  const active = activeModels?.has(payload.value) ?? true
  const rightEdge = Math.max(x - 4, 0)
  return (
    <SvgModelTick
      model={payload.value}
      rightEdge={rightEdge}
      y={y}
      width={rightEdge}
      active={active}
    />
  )
}

/** Print exact accuracy % at the bar's end; flips inside for long bars. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function AccuracyLabel(props: any) {
  const { x, y, width, height, value, payload } = props
  if (width == null || y == null || x == null || value == null) return null
  const barWidth = width as number
  const insideBar = barWidth > 60
  const labelX = insideBar ? (x as number) + barWidth - 6 : (x as number) + barWidth + 6
  const anchor = insideBar ? "end" : "start"
  // Inside bar: contrast against the filled color (accuracyTextColor picks dark for sandy mids, white elsewhere)
  // Outside bar: use the foreground CSS variable so dark/light mode both render
  const fill = insideBar ? accuracyTextColor(value as number) : "currentColor"
  const isActive = (payload as EnrichedPoint | undefined)?.isActive ?? true
  return (
    <text
      x={labelX}
      y={(y as number) + (height as number) / 2}
      fill={fill}
      textAnchor={anchor}
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
      opacity={isActive ? 1 : 0.4}
    >
      {((value as number) * 100).toFixed(1)}%
    </text>
  )
}

export const ModelBarChart = memo(function ModelBarChart({
  data,
  highlightedFamilies,
}: ModelBarChartProps) {
  const highlighted = highlightedFamilies ?? new Set<string>()

  const enriched = useMemo<EnrichedPoint[]>(() => {
    return data.map((d) => {
      const { low, high } = wilsonCI(d.correct, d.total)
      const family = familyOf(d.model)
      return {
        ...d,
        ciLow: low,
        ciHigh: high,
        errorX: [d.accuracy - low, high - d.accuracy],
        family,
        isActive: isFamilyActive(family, highlighted),
        lowSample: d.total < LOW_SAMPLE_THRESHOLD,
      }
    })
  }, [data, highlighted])

  const activeModels = useMemo(
    () => new Set(enriched.filter((d) => d.isActive).map((d) => d.model)),
    [enriched],
  )

  if (!enriched.length) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">No data available</div>
  }

  const barHeight = 42
  const chartHeight = Math.max(300, enriched.length * barHeight + 60)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={enriched} layout="vertical" margin={{ top: 5, right: 70, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis
          type="category"
          dataKey="model"
          width={220}
          interval={0}
          tick={<BadgeTick activeModels={activeModels} />}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} maxBarSize={28} isAnimationActive={false}>
          {enriched.map((entry, i) => (
            <Cell
              key={i}
              fill={accuracyColor(entry.accuracy)}
              fillOpacity={entry.isActive ? 1 : 0.25}
            />
          ))}
          <ErrorBar
            dataKey="errorX"
            direction="x"
            width={3}
            stroke={CI_STROKE_COLOR}
            strokeOpacity={0.7}
          />
          <LabelList dataKey="accuracy" content={<AccuracyLabel />} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
})
