import { memo } from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { getModelInfo, getFamilyColor } from "@/lib/model-sizes"

export const UNKNOWN_FAMILY = "Unknown"

/** Resolve a model name to its family, using a sentinel for unknowns. */
export function familyOf(model: string): string {
  return getModelInfo(model)?.family ?? UNKNOWN_FAMILY
}

/** Returns true if a family should render at full color given the current highlight set. */
export function isFamilyActive(family: string, highlighted: Set<string>): boolean {
  return highlighted.size === 0 || highlighted.has(family)
}

export interface FamilyLegendEntry {
  name: string
  color: string
  count: number
}

/** Derive legend entries from a list of model names — sorted by count desc. */
export function buildFamilyEntries(models: string[]): FamilyLegendEntry[] {
  const counts = new Map<string, number>()
  for (const model of models) {
    const family = familyOf(model)
    counts.set(family, (counts.get(family) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, count]) => ({
      name,
      count,
      color: name === UNKNOWN_FAMILY ? "#9ca3af" : getFamilyColor(name),
    }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
}

interface FamilyLegendProps {
  entries: FamilyLegendEntry[]
  highlighted: Set<string>
  onToggle: (family: string, additive: boolean) => void
  onClear: () => void
  className?: string
}

export const FamilyLegend = memo(function FamilyLegend({
  entries,
  highlighted,
  onToggle,
  onClear,
  className,
}: FamilyLegendProps) {
  if (!entries.length) return null
  const hasSelection = highlighted.size > 0

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-1.5 rounded-md border bg-muted/30 px-2 py-1.5",
        className,
      )}
      role="group"
      aria-label="Filter by model family. Click to highlight, shift-click to add."
    >
      <span className="mr-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        Families
      </span>
      {entries.map((entry) => {
        const active = isFamilyActive(entry.name, highlighted)
        const soloed = highlighted.has(entry.name)
        return (
          <button
            key={entry.name}
            type="button"
            onClick={(e) => onToggle(entry.name, e.shiftKey || e.metaKey || e.ctrlKey)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs transition-opacity",
              soloed
                ? "border-foreground/20 bg-background shadow-sm"
                : "border-transparent bg-transparent hover:bg-background/60",
              active ? "opacity-100" : "opacity-40",
            )}
            title={`${entry.name} — ${entry.count} model${entry.count > 1 ? "s" : ""}`}
          >
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="font-medium">{entry.name}</span>
            <span className="text-[10px] text-muted-foreground">{entry.count}</span>
          </button>
        )
      })}
      {hasSelection && (
        <button
          type="button"
          onClick={onClear}
          className="ml-auto inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-background/60 hover:text-foreground"
          title="Clear family highlight"
        >
          <X className="h-3 w-3" />
          Clear
        </button>
      )}
    </div>
  )
})
