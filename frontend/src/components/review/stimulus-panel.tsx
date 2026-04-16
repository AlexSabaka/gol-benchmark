import { useState } from "react"
import { ChevronRight } from "lucide-react"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import { languageLabel } from "@/components/language-filter-chip"
import type { ReviewCase } from "@/types"
import { TranslationContent, TranslationTrigger, useTranslationPanel } from "./translation-panel"

interface Props {
  caseData: ReviewCase
  /** Session target language (for the Translate button). */
  targetLang: string
}

/** Shorten a string to `max` chars with an ellipsis, preserving word-boundaries. */
function previewText(text: string, max = 80): string {
  const single = text.replace(/\s+/g, " ").trim()
  if (single.length <= max) return single
  const slice = single.slice(0, max)
  const lastSpace = slice.lastIndexOf(" ")
  return `${slice.slice(0, lastSpace > max * 0.6 ? lastSpace : max).trimEnd()}…`
}

/**
 * Left reading column. Deliberately chrome-light so the annotator reads rather
 * than navigates. System prompt is collapsed but exposes a one-line preview so
 * the annotator can decide whether to expand without losing their place.
 */
export function StimulusPanel({ caseData, targetLang }: Props) {
  const [sysOpen, setSysOpen] = useState(false)
  const [translateOpen, setTranslateOpen] = useState(false)
  const { sameLang, query } = useTranslationPanel(
    caseData.user_prompt,
    caseData.language,
    targetLang,
    translateOpen,
  )

  const sysPreview = caseData.system_prompt ? previewText(caseData.system_prompt) : ""
  const sysStyle = caseData.system_style

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="font-mono text-[10px]">{caseData.case_id}</Badge>
        <Badge variant="outline" className="text-[10px]">{languageLabel(caseData.language)}</Badge>
        {caseData.user_style && (
          <Badge variant="outline" className="text-[10px]">user: {caseData.user_style}</Badge>
        )}
      </div>

      {caseData.system_prompt && (
        <Collapsible open={sysOpen} onOpenChange={setSysOpen}>
          <CollapsibleTrigger className="group flex w-full items-start gap-1.5 text-left text-[11px] text-muted-foreground hover:text-foreground">
            <ChevronRight
              className={`mt-0.5 h-3 w-3 shrink-0 transition-transform ${sysOpen ? "rotate-90" : ""}`}
            />
            <span className="min-w-0 flex-1 leading-snug">
              <span className="font-medium uppercase tracking-wider">
                System{sysStyle ? ` · ${sysStyle}` : ""}
              </span>
              {!sysOpen && sysPreview && (
                <span className="ml-1.5 italic text-muted-foreground/80">“{sysPreview}”</span>
              )}
            </span>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <pre className="whitespace-pre-wrap rounded-md border border-dashed border-border/60 bg-muted/30 p-3 font-mono text-xs text-muted-foreground">
              {caseData.system_prompt}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            User prompt
          </div>
          {!sameLang && caseData.user_prompt && (
            <TranslationTrigger
              open={translateOpen}
              onToggle={() => setTranslateOpen((v) => !v)}
              sourceLang={caseData.language}
              targetLang={targetLang}
            />
          )}
        </div>
        <pre className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap rounded-md border border-border/60 bg-muted/20 p-4 font-mono text-sm leading-relaxed">
          {caseData.user_prompt || <span className="text-muted-foreground">(empty)</span>}
        </pre>
        {translateOpen && !sameLang && (
          <TranslationContent query={query} targetLang={targetLang} />
        )}
      </div>
    </div>
  )
}
