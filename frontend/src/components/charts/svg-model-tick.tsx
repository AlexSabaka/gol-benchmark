import { getFamilyColor, getModelInfo, formatModelSize } from "@/lib/model-sizes"
import { getThemeColors } from "./chart-theme"

/**
 * Pure-SVG alternative to `ModelBadge` for axis ticks.
 *
 * `ModelBadge` renders inside a `foreignObject`, which `html-to-image` does not
 * reliably serialize — PNG exports come out faded. This component renders the
 * same visual information (family dot + family name + variant + size chip)
 * using only native SVG primitives so the badge survives export cleanly.
 *
 * Layout (right-aligned within `[rightEdge - width, rightEdge]`):
 *   • circle                 left-most
 *   • family (bold)          line 1, top
 *   • variant (muted)        line 2, bottom
 *   • size chip (mono, muted)  right-most
 */
export interface SvgModelTickProps {
  /** Model name — resolved via `getModelInfo`. */
  model: string
  /** Right edge of the tick's available horizontal space. */
  rightEdge: number
  /** Vertical center of the tick row. */
  y: number
  /** Horizontal space available for the whole tick. */
  width: number
  /** Faded when false — used for non-highlighted families. */
  active?: boolean
}

const APPROX_MONO_CHAR_W = 6

export function SvgModelTick({ model, rightEdge, y, width, active = true }: SvgModelTickProps) {
  const info = getModelInfo(model)
  const color = info ? getFamilyColor(info.family) : "#9ca3af"
  const family = info?.family ?? model
  const variant = info?.variant ?? ""
  const size = info ? formatModelSize(info) : ""

  const theme = getThemeColors()
  const groupOpacity = active ? 1 : 0.3

  // Right-aligned size chip
  const chipPaddingX = 4
  const chipH = 14
  const chipTextW = size.length * APPROX_MONO_CHAR_W
  const chipW = chipTextW + chipPaddingX * 2
  const chipRightX = rightEdge
  const chipLeftX = chipRightX - chipW
  const chipMid = chipLeftX + chipW / 2

  // Text block goes to the left of the chip
  const dotCx = rightEdge - width + 4
  const textX = dotCx + 8
  const textRightBound = size ? chipLeftX - 8 : rightEdge - 2

  return (
    <g opacity={groupOpacity}>
      <circle cx={dotCx} cy={y} r={3} fill={color} />
      <text
        x={textX}
        y={variant ? y - 5 : y}
        dominantBaseline={variant ? "alphabetic" : "central"}
        fontSize={11}
        fontWeight={600}
        fill={theme.foreground}
      >
        <title>{variant ? `${family} ${variant}` : family}</title>
        {truncateToWidth(family, textRightBound - textX, 6.6)}
      </text>
      {variant && (
        <text
          x={textX}
          y={y + 9}
          dominantBaseline="alphabetic"
          fontSize={10}
          fill={theme.mutedForeground}
        >
          {truncateToWidth(variant, textRightBound - textX, 6)}
        </text>
      )}
      {size && (
        <>
          <rect
            x={chipLeftX}
            y={y - chipH / 2}
            width={chipW}
            height={chipH}
            rx={3}
            fill={theme.chipBg}
          />
          <text
            x={chipMid}
            y={y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={10}
            fontFamily="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
            fill={theme.mutedForeground}
          >
            {size}
          </text>
        </>
      )}
    </g>
  )
}

function truncateToWidth(text: string, maxPx: number, charW: number): string {
  if (maxPx <= 0) return ""
  const maxChars = Math.max(1, Math.floor(maxPx / charW))
  if (text.length <= maxChars) return text
  return text.slice(0, Math.max(1, maxChars - 1)) + "\u2026"
}
