import { memo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts"
import { accuracyColor } from "@/lib/chart-colors"
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
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: DimensionDataPoint }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{d.name}</p>
      <p>Accuracy: {(d.accuracy * 100).toFixed(1)}%</p>
      <p>{d.correct} / {d.total} correct</p>
    </div>
  )
}

export const DimensionBarChart = memo(function DimensionBarChart({ data, label }: DimensionBarChartProps) {
  const points: DimensionDataPoint[] = Object.entries(data)
    .map(([name, bucket]) => ({
      name,
      accuracy: bucket.accuracy,
      correct: bucket.correct,
      total: bucket.total,
    }))
    .sort((a, b) => b.accuracy - a.accuracy)

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
      <BarChart data={points} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {points.map((entry, i) => (
            <Cell key={i} fill={accuracyColor(entry.accuracy)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
})
