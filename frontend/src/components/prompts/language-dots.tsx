import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { LANGUAGE_NAMES, LANGUAGE_ORDER } from "@/types"
import { languageFlag } from "@/lib/constants"
import { cn } from "@/lib/utils"

interface Props {
  /**
   * Either an array of language codes that are present, OR a content map
   * (any language with a non-empty value counts as present).
   */
  present: readonly string[] | Record<string, string>
  /** Compact = smaller flags without tooltips. Used inside tab triggers. */
  compact?: boolean
  className?: string
}

/**
 * Six flag-emoji coverage strip — en es fr de zh ua. Bright when the
 * language is present on the prompt; greyed out (saturate-0 + opacity)
 * when it falls back to English.
 *
 * Kept as ``LanguageDots`` for compatibility with existing call sites; the
 * "dots" framing was an early read of the design — flags carry the signal
 * far better than circles do.
 */
export function LanguageDots({ present, compact = false, className }: Props) {
  const presence = normalisePresence(present)
  const size = compact ? "text-sm" : "text-base"
  const gap = compact ? "gap-0.5" : "gap-1"
  return (
    <div
      className={cn(
        "flex items-center select-none leading-none",
        gap,
        className,
      )}
    >
      {LANGUAGE_ORDER.map((code) => {
        const filled = presence.has(code)
        const flag = (
          <span
            key={code}
            className={cn(
              size,
              "transition-all",
              filled
                ? "opacity-100"
                // Grayscale + dim — the absent emoji still shows the country
                // shape but reads as "off" at a glance.
                : "opacity-40 grayscale [filter:grayscale(1)_brightness(0.85)]",
            )}
            aria-label={`${LANGUAGE_NAMES[code]} ${
              filled ? "present" : "missing — falls back to English"
            }`}
          >
            {languageFlag(code)}
          </span>
        )
        if (compact) return flag
        return (
          <Tooltip key={code}>
            <TooltipTrigger asChild>
              <span className="inline-flex">{flag}</span>
            </TooltipTrigger>
            <TooltipContent>
              <span className="text-xs">
                {LANGUAGE_NAMES[code]} ·{" "}
                {filled ? "present" : "falls back to English"}
              </span>
            </TooltipContent>
          </Tooltip>
        )
      })}
    </div>
  )
}

function normalisePresence(
  source: readonly string[] | Record<string, string>,
): Set<string> {
  if (Array.isArray(source)) return new Set(source)
  const set = new Set<string>()
  for (const [k, v] of Object.entries(source)) {
    if (typeof v === "string" && v.trim().length > 0) set.add(k)
  }
  return set
}
