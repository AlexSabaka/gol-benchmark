import { Check } from "lucide-react"

export interface StepDefinition<Id extends string = string> {
  id: Id
  label: string
  description: string
}

export interface StepButtonProps<Id extends string = string> {
  step: StepDefinition<Id>
  index: number
  active: boolean
  complete: boolean
  summary: string
  onClick: () => void
}

export function StepButton<Id extends string = string>({
  step,
  index,
  active,
  complete,
  summary,
  onClick,
}: StepButtonProps<Id>) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border px-4 py-3 text-left transition-colors ${
        active
          ? "border-primary bg-primary/5 shadow-sm"
          : complete
            ? "border-border bg-card hover:border-primary/50 hover:bg-accent/30"
            : "border-border bg-card hover:bg-accent/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
            active
              ? "bg-primary text-primary-foreground"
              : complete
                ? "bg-emerald-600 text-white"
                : "bg-muted text-muted-foreground"
          }`}
        >
          {complete && !active ? <Check className="h-3.5 w-3.5" /> : index + 1}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium">{step.label}</p>
          <p className="text-xs text-muted-foreground">{step.description}</p>
          {summary && (
            <p className="mt-1.5 truncate text-xs text-muted-foreground">{summary}</p>
          )}
        </div>
      </div>
    </button>
  )
}
