import {
  formatModelSize,
  getFamilyColor,
  getModelInfo,
  type ModelEntry,
} from "@/lib/model-sizes"

export interface ModelBadgeProps {
  /** Raw or canonical model name — resolved to family/variant/size via `getModelInfo`. */
  model: string
  /**
   * `stacked` renders a two-line text block (family + variant) next to a small
   * family-colour dot and a size chip — best for axis ticks and legends.
   * `inline` packs everything into one short line — best for tooltips.
   */
  layout?: "stacked" | "inline"
  /** Disclosure label shown when the badge represents merged aliases. */
  mergedCount?: number
  className?: string
}

function FallbackBadge({
  model,
  layout,
  className,
}: {
  model: string
  layout: "stacked" | "inline"
  className?: string
}) {
  const color = "#9ca3af"
  if (layout === "inline") {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs ${className ?? ""}`}>
        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-medium truncate">{model}</span>
      </span>
    )
  }
  return (
    <div className={`inline-flex items-center gap-2 text-left ${className ?? ""}`}>
      <span
        className="inline-block h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span className="truncate text-xs font-medium">{model}</span>
    </div>
  )
}

export function ModelBadge({
  model,
  layout = "stacked",
  mergedCount,
  className,
}: ModelBadgeProps) {
  const info = getModelInfo(model)
  if (!info) return <FallbackBadge model={model} layout={layout} className={className} />

  const color = getFamilyColor(info.family)
  const size = formatModelSize(info)
  const title = buildTitle(info, mergedCount)

  if (layout === "inline") {
    return (
      <span
        className={`inline-flex items-center gap-1.5 whitespace-nowrap text-xs ${className ?? ""}`}
        title={title}
      >
        <span className="inline-block h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
        <span className="font-medium">{info.family}</span>
        {info.variant && <span className="text-muted-foreground">{info.variant}</span>}
        <span className="rounded bg-muted px-1 font-mono text-[10px] text-muted-foreground">
          {size}
        </span>
        {mergedCount && mergedCount > 1 && (
          <span className="text-[10px] text-muted-foreground">· {mergedCount}×</span>
        )}
      </span>
    )
  }

  return (
    <div
      className={`inline-flex min-w-0 items-center gap-2 text-left ${className ?? ""}`}
      title={title}
    >
      <span
        className="inline-block h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
      />
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-xs font-medium leading-tight">{info.family}</span>
        {info.variant ? (
          <span className="truncate text-[11px] leading-tight text-muted-foreground">
            {info.variant}
          </span>
        ) : null}
      </div>
      <span className="ml-auto shrink-0 rounded bg-muted px-1 font-mono text-[10px] text-muted-foreground">
        {size}
      </span>
      {mergedCount && mergedCount > 1 ? (
        <span className="shrink-0 text-[10px] text-muted-foreground">{mergedCount}×</span>
      ) : null}
    </div>
  )
}

function buildTitle(info: ModelEntry, mergedCount?: number): string {
  const parts = [info.variant ? `${info.family} ${info.variant}` : info.family]
  parts.push(formatModelSize(info))
  if (info.estimated) parts.push("(size estimated)")
  if (mergedCount && mergedCount > 1) parts.push(`merged from ${mergedCount} provider tags`)
  return parts.join(" • ")
}
