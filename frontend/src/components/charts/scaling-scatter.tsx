import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label,
} from "recharts"
import { CHART_COLORS_HEX } from "@/lib/chart-colors"
import { formatParamCount } from "@/lib/model-sizes"
import type { ScatterPoint } from "@/types"

interface ScalingScatterProps {
  data: ScatterPoint[]
}

type ScatterPayload = {
  payload: { model: string; x: number; y: number }
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: ScatterPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{d.model}</p>
      <p>Parameters: {formatParamCount(d.x)}</p>
      <p>Accuracy: {(d.y * 100).toFixed(1)}%</p>
    </div>
  )
}

// Custom dot with model name label
function CustomDot(props: {
  cx?: number
  cy?: number
  payload?: { model: string; x: number; y: number }
  index?: number
}) {
  const { cx, cy, payload, index } = props
  if (cx == null || cy == null || !payload) return null
  const color = CHART_COLORS_HEX[(index ?? 0) % CHART_COLORS_HEX.length]
  return (
    <g>
      <circle cx={cx} cy={cy} r={6} fill={color} stroke="#fff" strokeWidth={1.5} opacity={0.85} />
      <text
        x={cx + 10}
        y={cy - 10}
        className="text-xs"
        fill="currentColor"
        opacity={0.8}
      >
        {payload.model.length > 20 ? payload.model.slice(0, 18) + "\u2026" : payload.model}
      </text>
    </g>
  )
}

export function ScalingScatter({ data }: ScalingScatterProps) {
  const known = data.filter((d) => d.paramCount !== null)
  const unknown = data.filter((d) => d.paramCount === null)

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

  const chartData = known.map((d) => ({
    model: d.model,
    x: d.paramCount!,
    y: d.accuracy,
  }))

  return (
    <div className="space-y-2">
      {unknown.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {unknown.length} model{unknown.length > 1 ? "s" : ""} not shown (unknown parameter count):{" "}
          {unknown.map((d) => d.model).join(", ")}
        </p>
      )}
      <ResponsiveContainer width="100%" height={420}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 30, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            type="number"
            dataKey="x"
            scale="log"
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => formatParamCount(v)}
          >
            <Label value="Parameters" position="bottom" offset={10} className="fill-muted-foreground text-sm" />
          </XAxis>
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          >
            <Label value="Accuracy" angle={-90} position="left" offset={0} className="fill-muted-foreground text-sm" />
          </YAxis>
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={chartData}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            shape={(props: any) => <CustomDot {...props} />}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
