import { Button } from "@/components/ui/button"
import type { ResponseClass } from "@/types"

export interface ClassificationDef {
  key: string
  code: ResponseClass
  label: string
  /** Tailwind classes for OFF state (muted/dark). */
  offTone: string
  /** Tailwind classes for ON state (filled/bright). */
  onTone: string
}

/**
 * Ordered so numeric keys 1–7 line up with the visual order.
 *
 * v3 changes:
 * - Removed `parser_ok` (auto-inferred at aggregation time).
 * - Renamed: `verbose_correct` → `verbose`, `parser_false_positive` → `false_positive`.
 * - Added: `truncated`.
 * - Buttons are now two-state toggles (off=muted, on=filled).
 * - Multi-select: any combination is valid.
 */
export const CLASSES: ClassificationDef[] = [
  {
    key: "1",
    code: "hedge",
    label: "Hedge",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-amber-500/10 hover:text-amber-600",
    onTone: "bg-amber-500/25 text-amber-700 border-amber-500 ring-1 ring-amber-400/40 dark:text-amber-400",
  },
  {
    key: "2",
    code: "truncated",
    label: "Truncated",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-slate-500/10 hover:text-slate-600",
    onTone: "bg-slate-500/25 text-slate-700 border-slate-500 ring-1 ring-slate-400/40 dark:text-slate-400",
  },
  {
    key: "3",
    code: "gibberish",
    label: "Gibberish",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-rose-500/10 hover:text-rose-600",
    onTone: "bg-rose-500/25 text-rose-700 border-rose-500 ring-1 ring-rose-400/40 dark:text-rose-400",
  },
  {
    key: "4",
    code: "refusal",
    label: "Refusal",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-red-500/10 hover:text-red-600",
    onTone: "bg-red-500/25 text-red-700 border-red-500 ring-1 ring-red-400/40 dark:text-red-400",
  },
  {
    key: "5",
    code: "language_error",
    label: "Lang. error",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-orange-500/10 hover:text-orange-600",
    onTone: "bg-orange-500/25 text-orange-700 border-orange-500 ring-1 ring-orange-400/40 dark:text-orange-400",
  },
  {
    key: "6",
    code: "verbose",
    label: "Verbose",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-sky-500/10 hover:text-sky-600",
    onTone: "bg-sky-500/25 text-sky-700 border-sky-500 ring-1 ring-sky-400/40 dark:text-sky-400",
  },
  {
    key: "7",
    code: "false_positive",
    label: "False-pos.",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-fuchsia-500/10 hover:text-fuchsia-600",
    onTone: "bg-fuchsia-500/25 text-fuchsia-700 border-fuchsia-500 ring-1 ring-fuchsia-400/40 dark:text-fuchsia-400",
  },
]

interface Props {
  active: ResponseClass[]
  onToggle: (code: ResponseClass) => void
}

export function ClassificationBar({ active, onToggle }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {CLASSES.map(({ key, code, label, offTone, onTone }) => {
        const isOn = active.includes(code)
        return (
          <Button
            key={code}
            variant="outline"
            size="sm"
            onClick={() => onToggle(code)}
            className={`h-8 gap-1.5 border font-medium transition-all ${isOn ? onTone : offTone}`}
            title={`${isOn ? "Remove" : "Add"} ${label} (shortcut ${key})`}
          >
            <kbd className="rounded border border-current/30 bg-background/60 px-1 font-mono text-[10px] leading-none">
              {key}
            </kbd>
            <span className="text-xs">{label}</span>
          </Button>
        )
      })}
    </div>
  )
}
