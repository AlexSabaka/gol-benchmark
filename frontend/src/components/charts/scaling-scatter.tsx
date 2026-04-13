import { useMemo } from "react"
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
  logScale?: boolean
  labelMode?: "hover" | "smart" | "all"
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

function buildSmartLabelSet(data: Array<{ model: string; x: number; y: number }>): Set<string> {
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

// Custom dot with model name label
function CustomDot(props: {
  cx?: number
  cy?: number
  payload?: { model: string; x: number; y: number }
  index?: number
  showLabel?: boolean
}) {
  const { cx, cy, payload, index, showLabel } = props
  if (cx == null || cy == null || !payload) return null
  const color = CHART_COLORS_HEX[(index ?? 0) % CHART_COLORS_HEX.length]
  const showLabelAbove = ((index ?? 0) % 2) === 0

  return (
    <g>
      <circle cx={cx} cy={cy} r={6} fill={color} stroke="#fff" strokeWidth={1.5} opacity={0.85} />
      {showLabel ? (
        <text
          x={cx + 10}
          y={showLabelAbove ? cy - 10 : cy + 16}
          className="text-xs"
          fill="currentColor"
          opacity={0.8}
        >
          {payload.model.length > 20 ? payload.model.slice(0, 18) + "\u2026" : payload.model}
        </text>
      ) : null}
    </g>
  )
}

export function ScalingScatter({ data, logScale = true, labelMode = "smart" }: ScalingScatterProps) {
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

  const labeledModels = useMemo(() => {
    if (labelMode === "all") return new Set(chartData.map((entry) => entry.model))
    if (labelMode === "hover") return new Set<string>()
    return buildSmartLabelSet(chartData)
  }, [chartData, labelMode])

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
            scale={logScale ? "log" : "linear"}
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
            shape={(props: any) => <CustomDot {...props} showLabel={labeledModels.has(props.payload.model)} />}
          />
        </ScatterChart>
      </ResponsiveContainer>
      <p className="text-xs text-muted-foreground">
        {labelMode === "hover"
          ? "Labels are hidden until hover for maximum clarity."
          : labelMode === "smart"
            ? "Smart labels highlight a smaller representative subset of models."
            : "All model labels are shown. Use hover for exact values when labels overlap."}
      </p>
    </div>
  )
}
