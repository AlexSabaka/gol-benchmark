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
import type { BarDataPoint } from "@/hooks/use-chart-data"
import { ModelBadge } from "./model-badge"

interface ModelBarChartProps {
  data: BarDataPoint[]
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: BarDataPoint }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="space-y-2 rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <ModelBadge model={d.model} layout="inline" mergedCount={d.aliases?.length} />
      <div className="space-y-0.5 text-xs">
        <p>Accuracy: {(d.accuracy * 100).toFixed(1)}%</p>
        <p className="text-muted-foreground">
          {d.correct} / {d.total} correct
        </p>
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
}: {
  x?: number
  y?: number
  payload?: { value: string }
}) {
  if (x == null || y == null || !payload) return null
  return (
    <foreignObject x={0} y={y - 18} width={Math.max((x ?? 0) - 4, 0)} height={36}>
      <div className="flex h-full items-center justify-end pr-1">
        <ModelBadge model={payload.value} layout="stacked" />
      </div>
    </foreignObject>
  )
}

export const ModelBarChart = memo(function ModelBarChart({ data }: ModelBarChartProps) {
  if (!data.length) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">No data available</div>
  }

  const barHeight = 42
  const chartHeight = Math.max(300, data.length * barHeight + 60)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis
          type="category"
          dataKey="model"
          width={220}
          interval={0}
          tick={<BadgeTick />}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {data.map((entry, i) => (
            <Cell key={i} fill={accuracyColor(entry.accuracy)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
})
