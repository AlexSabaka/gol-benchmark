import { ArrowLeft, ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"

export interface StepFooterProps {
  previousLabel?: string
  nextLabel?: string
  onPrevious?: () => void
  onNext?: () => void
  nextDisabled?: boolean
}

export function StepFooter({
  previousLabel,
  nextLabel,
  onPrevious,
  onNext,
  nextDisabled,
}: StepFooterProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
      <div>
        {onPrevious && (
          <Button variant="outline" onClick={onPrevious}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {previousLabel ?? "Back"}
          </Button>
        )}
      </div>
      {onNext ? (
        <Button onClick={onNext} disabled={nextDisabled}>
          {nextLabel ?? "Continue"}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      ) : null}
    </div>
  )
}
