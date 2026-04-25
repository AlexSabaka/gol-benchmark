import { X } from "lucide-react"
import type { ResponseClass } from "@/types"

const VERDICT_LABEL: Record<ResponseClass, string> = {
  hedge: "Hedge",
  truncated: "Truncated",
  unrecoverable: "Unrecoverable",
  false_positive: "False-positive",
}

const VERDICT_TONE: Record<ResponseClass, string> = {
  hedge: "border-amber-500/50 bg-amber-500/15 text-amber-700 dark:text-amber-400",
  truncated: "border-slate-500/50 bg-slate-500/15 text-slate-700 dark:text-slate-400",
  unrecoverable: "border-rose-500/50 bg-rose-500/15 text-rose-700 dark:text-rose-400",
  false_positive: "border-fuchsia-500/50 bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400",
}

interface Props {
  verdicts: ResponseClass[]
  onClear?: (code: ResponseClass) => void
}

/**
 * Row of small pills in the footer — one per active classification.
 * Each pill has its own x button to remove that specific verdict.
 */
export function VerdictPill({ verdicts, onClear }: Props) {
  if (verdicts.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-1">
      {verdicts.map((v) => (
        <span
          key={v}
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${VERDICT_TONE[v]}`}
        >
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
          {VERDICT_LABEL[v]}
          {onClear && (
            <button
              onClick={() => onClear(v)}
              title={`Remove ${VERDICT_LABEL[v]}`}
              className="ml-0.5 rounded-full opacity-70 hover:opacity-100"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </span>
      ))}
    </div>
  )
}
