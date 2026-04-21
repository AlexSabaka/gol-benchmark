import { memo, useState, useMemo, useCallback } from "react"
import { accuracyBucket, accuracyColor, accuracyTextColor } from "@/lib/chart-colors"
import { suffixDisplay } from "@/lib/utils"
import { wilsonCI, LOW_SAMPLE_THRESHOLD } from "@/lib/stats"
import type { HeatmapCell } from "@/types"
import { ModelBadge } from "./model-badge"
import { SvgModelTick } from "./svg-model-tick"
import { familyOf, isFamilyActive } from "./family-legend"
import { getThemeColors } from "./chart-theme"

interface AccuracyHeatmapProps {
  data: HeatmapCell[]
  xKey: "model" | "task"
  yKey: "model" | "task"
  highlightedFamilies?: Set<string>
}

interface TooltipState {
  x: number
  y: number
  cell: HeatmapCell
}

/** Format task name for display: snake_case → Title Case */
function formatLabel(s: string): string {
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Truncate label to maxLen characters */
function truncate(s: string, maxLen: number): string {
  return s.length > maxLen ? s.slice(0, maxLen - 1) + "\u2026" : s
}

function axisLabel(value: string, axis: "model" | "task", maxLen: number): string {
  return axis === "model" ? suffixDisplay(value, maxLen) : truncate(formatLabel(value), maxLen)
}

export const AccuracyHeatmap = memo(function AccuracyHeatmap({
  data,
  xKey,
  yKey,
  highlightedFamilies,
}: AccuracyHeatmapProps) {
  const highlighted = highlightedFamilies ?? new Set<string>()
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const theme = getThemeColors()

  // Build axes and lookup
  const { xLabels, yLabels, lookup } = useMemo(() => {
    const xs = new Set<string>()
    const ys = new Set<string>()
    const lk = new Map<string, HeatmapCell>()

    for (const cell of data) {
      const xVal = cell[xKey]
      const yVal = cell[yKey]
      xs.add(xVal)
      ys.add(yVal)
      lk.set(`${xVal}|${yVal}`, cell)
    }

    return {
      xLabels: [...xs].sort(),
      yLabels: [...ys].sort(),
      lookup: lk,
    }
  }, [data, xKey, yKey])

  const handleMouseEnter = useCallback(
    (e: React.MouseEvent<SVGRectElement>, cell: HeatmapCell) => {
      const rect = e.currentTarget.getBoundingClientRect()
      const parent = e.currentTarget.closest("svg")?.getBoundingClientRect()
      if (parent) {
        setTooltip({
          x: rect.left - parent.left + rect.width / 2,
          y: rect.top - parent.top - 8,
          cell,
        })
      }
    },
    []
  )

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  /** For a given (x,y) pair, decide whether either axis's model is hidden by the family filter. */
  const cellActive = useCallback(
    (xVal: string, yVal: string): boolean => {
      if (highlighted.size === 0) return true
      if (xKey === "model" && !isFamilyActive(familyOf(xVal), highlighted)) return false
      if (yKey === "model" && !isFamilyActive(familyOf(yVal), highlighted)) return false
      return true
    },
    [highlighted, xKey, yKey],
  )

  const modelActive = useCallback(
    (axis: "model" | "task", label: string): boolean => {
      if (highlighted.size === 0) return true
      if (axis !== "model") return true
      return isFamilyActive(familyOf(label), highlighted)
    },
    [highlighted],
  )

  if (!data.length || !xLabels.length || !yLabels.length) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">No data available</div>
  }

  const xDisplayLabels = xLabels.map((label) => axisLabel(label, xKey, xKey === "model" ? 24 : 18))
  const yDisplayLabels = yLabels.map((label) => axisLabel(label, yKey, yKey === "model" ? 28 : 24))
  const longestXLabel = xDisplayLabels.reduce((max, label) => Math.max(max, label.length), 0)
  const longestYLabel = yDisplayLabels.reduce((max, label) => Math.max(max, label.length), 0)

  // Layout
  const density = Math.max(xLabels.length, yLabels.length)
  const cellSize = density > 18 ? 34 : density > 12 ? 40 : 48
  const gap = 2
  // Widen the Y-axis margin when rendering model badges (dot + family/variant + size chip)
  const yLabelMinWidth = yKey === "model" ? 220 : 168
  const marginLeft = Math.min(Math.max(longestYLabel * 7 + 28, yLabelMinWidth), 280)
  const marginTop = Math.min(Math.max(longestXLabel * 5 + 44, 100), 180)
  const marginRight = 120
  const marginBottom = 20
  const valueFontSize = cellSize >= 42 ? 11 : 10

  const gridW = xLabels.length * (cellSize + gap)
  const gridH = yLabels.length * (cellSize + gap)
  const svgW = marginLeft + gridW + marginRight
  const svgH = marginTop + gridH + marginBottom

  return (
    <div className="relative overflow-auto">
      <svg width={svgW} height={svgH} className="select-none" role="img" aria-label={`Accuracy heatmap: ${yLabels.length} ${yKey}s by ${xLabels.length} ${xKey}s`}>
        <title>Accuracy Heatmap</title>
        <desc>Heatmap showing benchmark accuracy for each {yKey} and {xKey} combination</desc>
        {/* Y-axis labels — pure SVG badge when axis is models (survives PNG export) */}
        {yLabels.map((label, yi) => {
          const cy = marginTop + yi * (cellSize + gap) + cellSize / 2
          const active = modelActive(yKey, label)
          if (yKey === "model") {
            return (
              <SvgModelTick
                key={`y-${label}`}
                model={label}
                rightEdge={marginLeft - 8}
                y={cy}
                width={marginLeft - 8}
                active={active}
              />
            )
          }
          return (
            <text
              key={`y-${label}`}
              x={marginLeft - 8}
              y={cy}
              textAnchor="end"
              dominantBaseline="central"
              fontSize={12}
              fill={theme.foreground}
              opacity={active ? 1 : 0.3}
            >
              {yDisplayLabels[yi]}
            </text>
          )
        })}

        {/* X-axis labels — pivot at the label's bottom-left corner so adjacent
            labels fan out in parallel up-right, preventing the overlap that
            occurred with a center-pivot rotation. */}
        {xLabels.map((label, xi) => {
          const active = modelActive(xKey, label)
          const pivotX = marginLeft + xi * (cellSize + gap) + cellSize / 2
          const pivotY = marginTop - 6
          return (
            <text
              key={`x-${label}`}
              x={0}
              y={0}
              textAnchor="start"
              dominantBaseline="text-after-edge"
              fontSize={12}
              fill={theme.foreground}
              opacity={active ? 1 : 0.3}
              transform={`translate(${pivotX}, ${pivotY}) rotate(-45)`}
            >
              {xDisplayLabels[xi]}
            </text>
          )
        })}

        {/* Heatmap cells */}
        {xLabels.map((xLabel, xi) =>
          yLabels.map((yLabel, yi) => {
            const cell = lookup.get(`${xLabel}|${yLabel}`)
            if (!cell) return null
            const bucket = accuracyBucket(cell.accuracy)
            const active = cellActive(xLabel, yLabel)
            return (
              <rect
                key={`${xLabel}-${yLabel}`}
                x={marginLeft + xi * (cellSize + gap)}
                y={marginTop + yi * (cellSize + gap)}
                width={cellSize}
                height={cellSize}
                rx={4}
                fill={accuracyColor(cell.accuracy)}
                stroke="rgba(255,255,255,0.45)"
                strokeWidth={bucket === "high" ? 2 : 1.25}
                strokeDasharray={bucket === "low" ? "5 3" : bucket === "mid" ? "2 2" : undefined}
                opacity={active ? 0.95 : 0.2}
                className="cursor-pointer transition-opacity hover:opacity-100"
                onMouseEnter={(e) => handleMouseEnter(e, cell)}
                onMouseLeave={handleMouseLeave}
              />
            )
          })
        )}

        {/* Cell value labels */}
        {xLabels.map((xLabel, xi) =>
          yLabels.map((yLabel, yi) => {
            const cell = lookup.get(`${xLabel}|${yLabel}`)
            if (!cell) return null
            const active = cellActive(xLabel, yLabel)
            return (
              <text
                key={`v-${xLabel}-${yLabel}`}
                x={marginLeft + xi * (cellSize + gap) + cellSize / 2}
                y={marginTop + yi * (cellSize + gap) + cellSize / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={valueFontSize}
                className="pointer-events-none font-semibold"
                fill={accuracyTextColor(cell.accuracy)}
                opacity={active ? 1 : 0.3}
              >
                {(cell.accuracy * 100).toFixed(0)}
              </text>
            )
          })
        )}

        {/* Color legend */}
        <defs>
          <linearGradient id="heatmap-legend" x1="0" x2="0" y1="1" y2="0">
            <stop offset="0%" stopColor={accuracyColor(0)} />
            <stop offset="50%" stopColor={accuracyColor(0.5)} />
            <stop offset="100%" stopColor={accuracyColor(1)} />
          </linearGradient>
        </defs>
        <rect
          x={marginLeft + gridW + 12}
          y={marginTop}
          width={16}
          height={gridH}
          rx={4}
          fill="url(#heatmap-legend)"
          transform={`rotate(0)`}
        />
        <text
          x={marginLeft + gridW + 36}
          y={marginTop + 6}
          fontSize={12}
          fill={theme.mutedForeground}
          dominantBaseline="central"
        >
          100%
        </text>
        <text
          x={marginLeft + gridW + 36}
          y={marginTop + gridH / 2}
          fontSize={12}
          fill={theme.mutedForeground}
          dominantBaseline="central"
        >
          50%
        </text>
        <text
          x={marginLeft + gridW + 36}
          y={marginTop + gridH - 6}
          fontSize={12}
          fill={theme.mutedForeground}
          dominantBaseline="central"
        >
          0%
        </text>
      </svg>

      {/* Tooltip */}
      {tooltip && (() => {
        const correct = Math.round(tooltip.cell.accuracy * tooltip.cell.total)
        const { low, high } = wilsonCI(correct, tooltip.cell.total)
        const lowSample = tooltip.cell.total < LOW_SAMPLE_THRESHOLD
        return (
          <div
            className="pointer-events-none absolute z-50 space-y-1.5 rounded-md border bg-popover px-3 py-2 text-sm shadow-md"
            style={{
              left: Math.max(80, tooltip.x),
              top: Math.max(40, tooltip.y),
              transform: "translate(-50%, -100%)",
            }}
          >
            <ModelBadge
              model={tooltip.cell.model}
              layout="inline"
              mergedCount={tooltip.cell.aliases?.length}
            />
            <p className="text-xs text-muted-foreground">{formatLabel(tooltip.cell.task)}</p>
            <p className="text-xs">
              Accuracy: {(tooltip.cell.accuracy * 100).toFixed(1)}%{" "}
              <span className="text-muted-foreground">(n={tooltip.cell.total.toLocaleString()})</span>
            </p>
            <p className="text-xs text-muted-foreground">
              95% CI [{(low * 100).toFixed(1)}%, {(high * 100).toFixed(1)}%]
            </p>
            {lowSample && (
              <p className="text-[10px] text-amber-600 dark:text-amber-400">Low sample size — CI is wide.</p>
            )}
            {tooltip.cell.aliases && tooltip.cell.aliases.length > 1 && (
              <p className="text-[10px] text-muted-foreground">
                Merged from: {tooltip.cell.aliases.join(", ")}
              </p>
            )}
          </div>
        )
      })()}

      <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="font-medium">Encoding:</span>
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-5 rounded-sm border-2 border-white/60 bg-transparent" />
          high bucket border
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-5 rounded-sm border border-white/60 border-dashed bg-transparent" />
          lower buckets use dashed borders
        </span>
        <span>numbers in cells show exact accuracy %</span>
      </div>
    </div>
  )
})
