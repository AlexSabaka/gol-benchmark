import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { languageFlag } from "@/lib/constants"
import { cn } from "@/lib/utils"
import { LANGUAGE_NAMES, LANGUAGE_ORDER, type LanguageCode } from "@/types"

interface Props {
  value: LanguageCode
  onValueChange: (value: LanguageCode) => void
  /** Map of language → text. Filled-or-not drives the per-tab indicator. */
  content: Record<string, string>
  /** Mark EN tab with a small ★ indicating "required". */
  markEnglishRequired?: boolean
  /** Render the per-language content body inside `<TabsContent>` slots. */
  children: (lang: LanguageCode, isPresent: boolean) => React.ReactNode
}

/**
 * Six-tab strip for language selection. Each trigger carries a flag emoji
 * — bright when the language has non-empty content on the active version,
 * desaturated/dimmed when it falls back to English.
 */
export function LanguageTabs({
  value,
  onValueChange,
  content,
  markEnglishRequired,
  children,
}: Props) {
  return (
    <Tabs
      value={value}
      onValueChange={(v) => onValueChange(v as LanguageCode)}
      className="gap-4"
    >
      <TabsList variant="line">
        {LANGUAGE_ORDER.map((code) => {
          const present = isPresent(content[code])
          return (
            <TabsTrigger
              key={code}
              value={code}
              className="gap-1.5 px-3"
              aria-label={`${LANGUAGE_NAMES[code]} ${present ? "present" : "missing"}`}
            >
              <span
                className={cn(
                  "text-sm leading-none transition-all select-none",
                  present
                    ? "opacity-100"
                    : "opacity-40 [filter:grayscale(1)_brightness(0.85)]",
                )}
                aria-hidden="true"
              >
                {languageFlag(code)}
              </span>
              <span className="text-[11px] font-semibold uppercase tracking-widest">
                {code}
              </span>
              {markEnglishRequired && code === "en" && (
                <span className="text-[10px] text-muted-foreground/70">★</span>
              )}
            </TabsTrigger>
          )
        })}
      </TabsList>
      {LANGUAGE_ORDER.map((code) => (
        <TabsContent key={code} value={code} className="mt-0">
          {children(code, isPresent(content[code]))}
        </TabsContent>
      ))}
    </Tabs>
  )
}

function isPresent(value: string | undefined): boolean {
  return Boolean(value && value.trim().length > 0)
}
