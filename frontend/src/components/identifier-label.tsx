import { cn, prefixHint, suffixDisplay } from "@/lib/utils"

interface IdentifierLabelProps {
  value: string
  secondary?: string | null
  showPrefixHint?: boolean
  primaryMax?: number
  secondaryMax?: number
  mono?: boolean
  className?: string
  primaryClassName?: string
  secondaryClassName?: string
}

export function IdentifierLabel({
  value,
  secondary,
  showPrefixHint = true,
  primaryMax = 42,
  secondaryMax = 28,
  mono = false,
  className,
  primaryClassName,
  secondaryClassName,
}: IdentifierLabelProps) {
  const normalized = value.trim()
  const secondaryText = secondary ?? (showPrefixHint ? prefixHint(normalized, secondaryMax) : undefined)

  return (
    <div className={cn("min-w-0", className)} title={normalized}>
      <p className={cn("truncate font-medium", mono && "font-mono", primaryClassName)}>
        {suffixDisplay(normalized, primaryMax)}
      </p>
      {secondaryText ? (
        <p className={cn("mt-1 truncate text-[11px] text-muted-foreground", mono && "font-mono", secondaryClassName)}>
          {secondaryText}
        </p>
      ) : null}
    </div>
  )
}