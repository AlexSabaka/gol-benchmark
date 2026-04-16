import { Button } from "@/components/ui/button"
import type { ResponseClass } from "@/types"

export interface ClassificationDef {
  key: string
  code: ResponseClass
  label: string
  tone: string
}

/**
 * Ordered so numeric keys 1–7 line up with the visual order.
 * Key 7 — `parser_false_positive` — is the diagnostic introduced in v2.20.0:
 * the parser confidently extracted the wrong token. This verdict may coexist
 * with an answer span (the span being the evidence for the correct answer).
 *
 * Active state is intentionally strong (`/30` fill + solid border + ring) so
 * the annotator can tell at a glance which verdict is committed — a pale
 * alpha wash is too easy to miss on busy screens.
 */
export const CLASSES: ClassificationDef[] = [
  { key: "1", code: "hedge",                 label: "Hedge",             tone: "border-amber-400/60 text-amber-600 hover:bg-amber-500/10 data-[active=true]:border-amber-500 data-[active=true]:border-solid data-[active=true]:bg-amber-500/30 data-[active=true]:text-amber-700 data-[active=true]:ring-1 data-[active=true]:ring-amber-400/40" },
  { key: "2", code: "gibberish",             label: "Gibberish",         tone: "border-rose-400/60 text-rose-600 hover:bg-rose-500/10 data-[active=true]:border-rose-500 data-[active=true]:border-solid data-[active=true]:bg-rose-500/30 data-[active=true]:text-rose-700 data-[active=true]:ring-1 data-[active=true]:ring-rose-400/40" },
  { key: "3", code: "refusal",               label: "Refusal",           tone: "border-red-400/60 text-red-600 hover:bg-red-500/10 data-[active=true]:border-red-500 data-[active=true]:border-solid data-[active=true]:bg-red-500/30 data-[active=true]:text-red-700 data-[active=true]:ring-1 data-[active=true]:ring-red-400/40" },
  { key: "4", code: "language_error",        label: "Lang. error",       tone: "border-orange-400/60 text-orange-600 hover:bg-orange-500/10 data-[active=true]:border-orange-500 data-[active=true]:border-solid data-[active=true]:bg-orange-500/30 data-[active=true]:text-orange-700 data-[active=true]:ring-1 data-[active=true]:ring-orange-400/40" },
  { key: "5", code: "verbose_correct",       label: "Verbose correct",   tone: "border-sky-400/60 text-sky-600 hover:bg-sky-500/10 data-[active=true]:border-sky-500 data-[active=true]:border-solid data-[active=true]:bg-sky-500/30 data-[active=true]:text-sky-700 data-[active=true]:ring-1 data-[active=true]:ring-sky-400/40" },
  { key: "6", code: "parser_ok",             label: "Parser OK",         tone: "border-emerald-400/60 text-emerald-600 hover:bg-emerald-500/10 data-[active=true]:border-emerald-500 data-[active=true]:border-solid data-[active=true]:bg-emerald-500/30 data-[active=true]:text-emerald-700 data-[active=true]:ring-1 data-[active=true]:ring-emerald-400/40" },
  { key: "7", code: "parser_false_positive", label: "Parser false-pos.", tone: "border-fuchsia-400/60 text-fuchsia-600 hover:bg-fuchsia-500/10 data-[active=true]:border-fuchsia-500 data-[active=true]:border-solid data-[active=true]:bg-fuchsia-500/30 data-[active=true]:text-fuchsia-700 data-[active=true]:ring-1 data-[active=true]:ring-fuchsia-400/40" },
]

interface Props {
  active: ResponseClass | null
  onChoose: (code: ResponseClass) => void
}

export function ClassificationBar({ active, onChoose }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {CLASSES.map(({ key, code, label, tone }) => (
        <Button
          key={code}
          data-active={active === code}
          variant="outline"
          size="sm"
          onClick={() => onChoose(code)}
          className={`h-8 gap-1.5 border-dashed font-medium transition-all ${tone}`}
          title={`Classify as ${label} (shortcut ${key})`}
        >
          <kbd className="rounded border border-current/30 bg-background/60 px-1 font-mono text-[10px] leading-none">
            {key}
          </kbd>
          <span className="text-xs">{label}</span>
        </Button>
      ))}
    </div>
  )
}
