import { MessageSquare, Settings2 } from "lucide-react"

interface PromptStyleBadgeProps {
  style: string
  type: "user" | "system"
}

export function PromptStyleBadge({ style, type }: PromptStyleBadgeProps) {
  const Icon = type === "user" ? MessageSquare : Settings2
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <Icon className="h-3 w-3 text-muted-foreground/60" aria-hidden="true" />
      {style}
    </span>
  )
}
