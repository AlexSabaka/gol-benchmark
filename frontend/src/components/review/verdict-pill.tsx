import { X } from "lucide-react"
import type { ResponseClass } from "@/types"

const VERDICT_LABEL: Record<ResponseClass, string> = {
  hedge: "Hedge",
  gibberish: "Gibberish",
  refusal: "Refusal",
  language_error: "Language error",
  verbose_correct: "Verbose correct",
  parser_ok: "Parser OK",
  parser_false_positive: "Parser false-positive",
}

const VERDICT_TONE: Record<ResponseClass, string> = {
  hedge: "border-amber-500/50 bg-amber-500/15 text-amber-700 dark:text-amber-400",
  gibberish: "border-rose-500/50 bg-rose-500/15 text-rose-700 dark:text-rose-400",
  refusal: "border-red-500/50 bg-red-500/15 text-red-700 dark:text-red-400",
  language_error: "border-orange-500/50 bg-orange-500/15 text-orange-700 dark:text-orange-400",
  verbose_correct: "border-sky-500/50 bg-sky-500/15 text-sky-700 dark:text-sky-400",
  parser_ok: "border-emerald-500/50 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  parser_false_positive: "border-fuchsia-500/50 bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400",
}

interface Props {
  verdict: ResponseClass
  onClear?: () => void
}

/**
 * Small pill shown in the footer next to the classification bar so the
 * annotator can see the current verdict at a glance without scanning the row
 * of dashed buttons. Clicking the × clears the verdict.
 */
export function VerdictPill({ verdict, onClear }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${VERDICT_TONE[verdict]}`}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {VERDICT_LABEL[verdict]}
      {onClear && (
        <button
          onClick={onClear}
          title="Clear verdict"
          className="ml-0.5 rounded-full opacity-70 hover:opacity-100"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  )
}
