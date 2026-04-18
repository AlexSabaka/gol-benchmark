import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

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
      className={cn(
        "flex min-h-9 flex-1 items-center gap-2 px-3 py-1.5 text-left transition-colors hover:bg-accent/50",
        active && "bg-primary/5",
      )}
    >
      <span
        className={cn(
          "flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
          active
            ? "bg-primary text-primary-foreground"
            : complete
              ? "bg-emerald-600 text-white"
              : "bg-muted text-muted-foreground/70",
        )}
      >
        {complete && !active ? <Check className="h-2.5 w-2.5" /> : index + 1}
      </span>
      <div className="min-w-0">
        <p
          className={cn(
            "text-xs font-medium leading-tight",
            active ? "text-foreground" : complete ? "text-foreground/80" : "text-muted-foreground",
          )}
        >
          {step.label}
        </p>
        {complete && summary && (
          <p className="truncate text-[10px] leading-tight text-muted-foreground/70">{summary}</p>
        )}
      </div>
    </button>
  )
}
