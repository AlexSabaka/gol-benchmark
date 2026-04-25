import { Button } from "@/components/ui/button"
import type { ResponseClass } from "@/types"

export interface ClassificationDef {
  key: string
  /** v4: optional letter shortcut (WASD-adjacent). Hedge has none. */
  letter?: string
  code: ResponseClass
  label: string
  /** Tailwind classes for OFF state (muted/dark). */
  offTone: string
  /** Tailwind classes for ON state (filled/bright). */
  onTone: string
}

/**
 * v4 (Phase 1) — four canonical classes with WASD-adjacent letter bindings.
 *
 * Key slot 1 is reserved for implicit Extractable (no button, default when
 * a span exists). Number keys 2–5 duplicate the letter shortcuts for users
 * who prefer numeric IDs.
 *
 * Dropped vs v3: `gibberish` / `refusal` / `language_error` folded into
 * `unrecoverable`; `verbose` dropped (implicit when a span exists).
 */
export const CLASSES: ClassificationDef[] = [
  {
    key: "2",
    letter: "E",
    code: "truncated",
    label: "Truncated",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-slate-500/10 hover:text-slate-600",
    onTone: "bg-slate-500/25 text-slate-700 border-slate-500 ring-1 ring-slate-400/40 dark:text-slate-400",
  },
  {
    key: "3",
    letter: "Q",
    code: "unrecoverable",
    label: "Unrecoverable",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-rose-500/10 hover:text-rose-600",
    onTone: "bg-rose-500/25 text-rose-700 border-rose-500 ring-1 ring-rose-400/40 dark:text-rose-400",
  },
  {
    key: "4",
    letter: "F",
    code: "false_positive",
    label: "False-pos.",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-fuchsia-500/10 hover:text-fuchsia-600",
    onTone: "bg-fuchsia-500/25 text-fuchsia-700 border-fuchsia-500 ring-1 ring-fuchsia-400/40 dark:text-fuchsia-400",
  },
  {
    key: "5",
    code: "hedge",
    label: "Hedge",
    offTone: "bg-muted/60 text-muted-foreground border-transparent hover:bg-amber-500/10 hover:text-amber-600",
    onTone: "bg-amber-500/25 text-amber-700 border-amber-500 ring-1 ring-amber-400/40 dark:text-amber-400",
  },
]

interface Props {
  active: ResponseClass[]
  onToggle: (code: ResponseClass) => void
}

export function ClassificationBar({ active, onToggle }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {CLASSES.map(({ key, letter, code, label, offTone, onTone }) => {
        const isOn = active.includes(code)
        const shortcutLabel = letter ? `${key} / ${letter}` : key
        return (
          <Button
            key={code}
            variant="outline"
            size="sm"
            onClick={() => onToggle(code)}
            className={`h-8 gap-1.5 border font-medium transition-all ${isOn ? onTone : offTone}`}
            title={`${isOn ? "Remove" : "Add"} ${label} (shortcut ${shortcutLabel})`}
          >
            <kbd className="rounded border border-current/30 bg-background/60 px-1 font-mono text-[10px] leading-none">
              {shortcutLabel}
            </kbd>
            <span className="text-xs">{label}</span>
          </Button>
        )
      })}
    </div>
  )
}
