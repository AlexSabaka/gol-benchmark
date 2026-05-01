import { cn } from "@/lib/utils"
import type { PromptVersionMeta } from "@/types"

interface Props {
  versions: PromptVersionMeta[]
  activeVersion: number | null
  onSelect: (version: number) => void
}

/**
 * Vertical version spine. Newest first. Active node filled with primary;
 * others ring-only. Dashed connector between nodes makes the immutability
 * visually obvious — versions are append-only.
 */
export function VersionTimeline({ versions, activeVersion, onSelect }: Props) {
  if (versions.length === 0) {
    return (
      <p className="px-1 text-xs text-muted-foreground">
        No versions yet.
      </p>
    )
  }
  return (
    <ol className="relative flex flex-col">
      {versions.map((v, i) => {
        const isActive = v.version === activeVersion
        const isLast = i === versions.length - 1
        return (
          <li key={v.version} className="relative pl-7 pb-5 last:pb-0">
            {/* Connector */}
            {!isLast && (
              <span
                aria-hidden="true"
                className="absolute left-[7px] top-4 bottom-0 w-px border-l border-dashed border-border/70"
              />
            )}
            {/* Node */}
            <button
              type="button"
              aria-current={isActive ? "true" : undefined}
              onClick={() => onSelect(v.version)}
              className={cn(
                "absolute left-0 top-1.5 size-3.5 rounded-full transition-all",
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                isActive
                  ? "scale-110 bg-primary shadow-[0_0_0_3px_hsl(var(--background))]"
                  : "border-2 border-border bg-background hover:border-foreground/50",
              )}
              aria-label={`Select version ${v.version}`}
            />
            {/* Body */}
            <button
              type="button"
              onClick={() => onSelect(v.version)}
              className="block w-full text-left"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span
                  className={cn(
                    "font-mono text-sm font-semibold",
                    isActive ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  v{v.version}
                </span>
                <span className="text-[10px] tabular-nums text-muted-foreground/70">
                  {formatRelativeTime(v.created_at)}
                </span>
              </div>
              <p
                className={cn(
                  "mt-0.5 line-clamp-2 text-xs leading-snug",
                  v.change_note ? "text-muted-foreground" : "italic text-muted-foreground/50",
                )}
              >
                {v.change_note || "no note"}
              </p>
            </button>
          </li>
        )
      })}
    </ol>
  )
}

function formatRelativeTime(iso: string): string {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ""
  const delta = Date.now() - t
  const m = Math.floor(delta / 60_000)
  if (m < 1) return "just now"
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d}d ago`
  return new Date(t).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}
