import { ChevronDown, Loader2, Languages, RefreshCw } from "lucide-react"
import type { UseQueryResult } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { useTranslation } from "@/hooks/use-review"
import { languageLabel } from "@/components/language-filter-chip"
import type { TranslateResponse } from "@/types"

/**
 * State-lifting hook for the translate trigger + content pair. The caller owns
 * `open` so the button and the rendered translation can live in different
 * parts of the DOM (e.g. button in the badge row, content below the response
 * text) while sharing a single query.
 */
export function useTranslationPanel(
  text: string,
  sourceLang: string,
  targetLang: string,
  open: boolean,
) {
  const src = (sourceLang || "auto").toLowerCase()
  const tgt = (targetLang || "en").toLowerCase()
  const sameLang = !!src && src !== "auto" && src === tgt
  const query = useTranslation(text, sourceLang || null, targetLang, open && !sameLang)
  return { sameLang, query }
}

interface TriggerProps {
  open: boolean
  onToggle: () => void
  sourceLang: string
  targetLang: string
  label?: string
  className?: string
}

/**
 * Button that toggles a translation pane. Renders nothing when source and
 * target languages match (no translation to offer) or when the text is empty.
 */
export function TranslationTrigger({
  open,
  onToggle,
  sourceLang,
  targetLang,
  label = "Translate",
  className,
}: TriggerProps) {
  const src = (sourceLang || "auto").toLowerCase()
  const tgt = (targetLang || "en").toLowerCase()
  if (src && src !== "auto" && src === tgt) return null
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onToggle}
      className={`h-6 gap-1 px-1.5 text-[11px] text-muted-foreground hover:text-foreground ${className ?? ""}`}
      title={open ? "Hide translation" : `Translate to ${tgt.toUpperCase()}`}
    >
      <Languages className="h-3 w-3" />
      {label}
      <ChevronDown className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
    </Button>
  )
}

interface ContentProps {
  query: UseQueryResult<TranslateResponse, Error>
  targetLang: string
}

/**
 * Read-only reveal of the translated text. Deliberately `select-none` so
 * annotations can't accidentally refer to translated char offsets.
 */
export function TranslationContent({ query, targetLang }: ContentProps) {
  const tgt = (targetLang || "en").toLowerCase()
  return (
    <div className="mt-2 select-none rounded-md border border-dashed border-border/60 bg-muted/30 p-3">
      <div className="mb-1.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <span className="font-medium uppercase tracking-wider">
          Translation · {languageLabel(tgt)}
        </span>
        {query.data?.provider && (
          <span className="opacity-70">via {query.data.provider}</span>
        )}
        {query.isError && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => query.refetch()}
            className="ml-auto h-5 w-5 text-muted-foreground"
            title="Retry translation"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        )}
      </div>

      {query.isLoading && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Translating…
        </div>
      )}
      {query.isError && (
        <div className="text-xs text-rose-600">
          Translation unavailable.{" "}
          <span className="text-muted-foreground">
            {query.error instanceof Error ? query.error.message : "Unknown error"}
          </span>
        </div>
      )}
      {query.data && (
        <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-muted-foreground">
          {query.data.translated}
        </div>
      )}
    </div>
  )
}
