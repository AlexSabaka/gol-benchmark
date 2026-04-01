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

interface ModelBarChartProps {
  data: BarDataPoint[]
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: BarDataPoint }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{d.model}</p>
      <p>Accuracy: {(d.accuracy * 100).toFixed(1)}%</p>
      <p>
        {d.correct} / {d.total} correct
      </p>
    </div>
  )
}

export const ModelBarChart = memo(function ModelBarChart({ data }: ModelBarChartProps) {
  if (!data.length) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">No data available</div>
  }

  const barHeight = 36
  const chartHeight = Math.max(300, data.length * barHeight + 60)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="model" width={180} tick={{ fontSize: 12 }} />
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
