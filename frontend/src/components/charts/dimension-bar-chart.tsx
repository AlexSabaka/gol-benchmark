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
import { CI_STROKE_COLOR } from "./chart-theme"
import type { DimensionBucket } from "@/types"

interface DimensionBarChartProps {
  data: Record<string, DimensionBucket>
  label: string
}

interface DimensionDataPoint {
  name: string
  accuracy: number
  correct: number
  total: number
  ciLow: number
  ciHigh: number
  errorX: [number, number]
  lowSample: boolean
}

/** Print exact accuracy % at the bar's end; flips inside for long bars. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function AccuracyLabel(props: any) {
  const { x, y, width, height, value } = props
  if (width == null || y == null || x == null || value == null) return null
  const barWidth = width as number
  const insideBar = barWidth > 60
  const labelX = insideBar ? (x as number) + barWidth - 6 : (x as number) + barWidth + 6
  const anchor = insideBar ? "end" : "start"
  const fill = insideBar ? accuracyTextColor(value as number) : "currentColor"
  return (
    <text
      x={labelX}
      y={(y as number) + (height as number) / 2}
      fill={fill}
      textAnchor={anchor}
      dominantBaseline="central"
      fontSize={11}
      fontWeight={600}
    >
      {((value as number) * 100).toFixed(1)}%
    </text>
  )
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: DimensionDataPoint }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{d.name}</p>
      <p className="text-xs">
        Accuracy: {(d.accuracy * 100).toFixed(1)}% <span className="text-muted-foreground">(n={d.total.toLocaleString()})</span>
      </p>
      <p className="text-xs text-muted-foreground">
        95% CI [{(d.ciLow * 100).toFixed(1)}%, {(d.ciHigh * 100).toFixed(1)}%]
      </p>
      <p className="text-xs text-muted-foreground">{d.correct} / {d.total} correct</p>
      {d.lowSample && (
        <p className="text-xs text-amber-600 dark:text-amber-400">Low sample size — CI is wide.</p>
      )}
    </div>
  )
}

export const DimensionBarChart = memo(function DimensionBarChart({ data, label }: DimensionBarChartProps) {
  const points = useMemo<DimensionDataPoint[]>(() => {
    return Object.entries(data)
      .map(([name, bucket]) => {
        const { low, high } = wilsonCI(bucket.correct, bucket.total)
        return {
          name,
          accuracy: bucket.accuracy,
          correct: bucket.correct,
          total: bucket.total,
          ciLow: low,
          ciHigh: high,
          errorX: [bucket.accuracy - low, high - bucket.accuracy] as [number, number],
          lowSample: bucket.total < LOW_SAMPLE_THRESHOLD,
        }
      })
      .sort((a, b) => b.accuracy - a.accuracy)
  }, [data])

  if (!points.length) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
        No {label.toLowerCase()} breakdown available. Run new benchmarks to see this data.
      </div>
    )
  }

  const barHeight = 40
  const chartHeight = Math.max(200, points.length * barHeight + 60)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={points} layout="vertical" margin={{ top: 5, right: 70, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} maxBarSize={28} isAnimationActive={false}>
          {points.map((entry, i) => (
            <Cell key={i} fill={accuracyColor(entry.accuracy)} />
          ))}
          <ErrorBar dataKey="errorX" direction="x" width={3} stroke={CI_STROKE_COLOR} strokeOpacity={0.7} />
          <LabelList dataKey="accuracy" content={<AccuracyLabel />} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
})
