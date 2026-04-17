import { ArrowLeft, Languages } from "lucide-react"
import { Link } from "react-router"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ModelBadge } from "@/components/charts/model-badge"

const TRANSLATE_TARGETS = ["en", "es", "fr", "de", "zh", "ua"] as const

export const MATCH_FILTER_PRESETS: Array<{ key: string; label: string; matches: string[] | null }> = [
  { key: "all", label: "All", matches: null },
  { key: "incorrect", label: "Incorrect only", matches: ["parse_error", "mismatch", "wrong", "unknown"] },
  { key: "parse_error", label: "Parse errors", matches: ["parse_error"] },
  { key: "mismatch", label: "Mismatches", matches: ["mismatch"] },
]

interface Props {
  plugin: string
  modelName?: string | null
  testsetName?: string | null
  current: number
  total: number
  /** Count of cases with a saved annotation in this session (or pre-existing). */
  savedCount: number
  /** Count of cases with unsaved drafts pending retry. */
  unsavedCount: number
  /** Authoritative annotated count from sidecar files — includes cases hidden by
   *  filters. When greater than `savedCount`, a "(N filtered)" hint is shown so
   *  the annotator knows work from previous sessions is preserved but not visible. */
  totalAnnotatedInSidecars?: number
  skipEmpty: boolean
  skipCorrect: boolean
  matchFilterKey: string
  targetLang: string
  onToggleSkipEmpty: (next: boolean) => void
  onToggleSkipCorrect: (next: boolean) => void
  onChangeMatchFilter: (key: string) => void
  onChangeTargetLang: (lang: string) => void
}

export function CaseProgress({
  plugin,
  modelName,
  testsetName,
  current,
  total,
  savedCount,
  unsavedCount,
  totalAnnotatedInSidecars,
  skipEmpty,
  skipCorrect,
  matchFilterKey,
  targetLang,
  onToggleSkipEmpty,
  onToggleSkipCorrect,
  onChangeMatchFilter,
  onChangeTargetLang,
}: Props) {
  const hiddenAnnotatedCount =
    totalAnnotatedInSidecars !== undefined && totalAnnotatedInSidecars > savedCount
      ? totalAnnotatedInSidecars - savedCount
      : 0
  // Segmented progress: saved portion (filled primary) + current position marker.
  const savedPct = total > 0 ? Math.min(100, Math.round((savedCount / total) * 100)) : 0
  const positionPct = total > 0 ? Math.min(100, Math.round(((current + 1) / total) * 100)) : 0

  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/results"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Results
          </Link>
          <div className="flex items-center gap-2 text-xs">
            <span className="font-mono tabular-nums text-muted-foreground">
              <span className="text-emerald-600">{savedCount}</span> annotated
              {hiddenAnnotatedCount > 0 && (
                <span
                  className="ml-1 text-muted-foreground"
                  title={`${hiddenAnnotatedCount} annotated cases hidden by current filter`}
                >
                  (+{hiddenAnnotatedCount} filtered)
                </span>
              )}
              <span className="mx-1">·</span>
              <span className="text-foreground">{total === 0 ? "0 / 0" : `${current + 1} / ${total}`}</span>
            </span>
            {unsavedCount > 0 && (
              <Badge variant="outline" className="border-amber-500/50 bg-amber-500/10 text-[10px] text-amber-600">
                {unsavedCount} retry
              </Badge>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            {MATCH_FILTER_PRESETS.map((preset) => (
              <Button
                key={preset.key}
                variant="ghost"
                size="sm"
                onClick={() => onChangeMatchFilter(preset.key)}
                data-active={matchFilterKey === preset.key}
                className="h-6 px-2 text-[11px] data-[active=true]:bg-primary/10 data-[active=true]:text-primary"
              >
                {preset.label}
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-muted-foreground">
              <Checkbox checked={skipEmpty} onCheckedChange={(v) => onToggleSkipEmpty(!!v)} />
              Skip empty
            </label>
            <label className="flex items-center gap-1.5 text-muted-foreground">
              <Checkbox checked={skipCorrect} onCheckedChange={(v) => onToggleSkipCorrect(!!v)} />
              Skip already-correct
            </label>
            <label
              className="flex items-center gap-1 text-muted-foreground"
              title="Target language for machine translation"
            >
              <Languages className="h-3.5 w-3.5" />
              <select
                value={targetLang}
                onChange={(e) => onChangeTargetLang(e.target.value)}
                className="h-6 rounded border border-input bg-background px-1 text-[11px] uppercase"
              >
                {TRANSLATE_TARGETS.map((code) => (
                  <option key={code} value={code}>{code.toUpperCase()}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </div>

      {/* Segmented progress bar: saved fill + current-position marker. */}
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-primary/15">
        <div
          className="absolute inset-y-0 left-0 bg-emerald-500/80 transition-all"
          style={{ width: `${savedPct}%` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-primary transition-all"
          style={{ left: `calc(${positionPct}% - 1px)` }}
          aria-hidden
        />
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">
          {plugin}
        </Badge>
        {modelName && <ModelBadge model={modelName} layout="inline" className="text-[11px]" />}
        {testsetName && (
          <Badge variant="outline" className="text-[10px]">
            {testsetName}
          </Badge>
        )}
      </div>
    </div>
  )
}
