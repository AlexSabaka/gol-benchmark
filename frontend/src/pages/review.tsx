import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link, Navigate, useSearchParams } from "react-router"
import { ArrowLeft, ArrowRight, Loader2, SkipForward } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { StimulusPanel } from "@/components/review/stimulus-panel"
import { ResponsePanel } from "@/components/review/response-panel"
import { ClassificationBar, CLASSES } from "@/components/review/classification-bar"
import { CaseProgress, MATCH_FILTER_PRESETS } from "@/components/review/case-progress"
import { VerdictPill } from "@/components/review/verdict-pill"
import type { PendingSpan } from "@/components/review/annotation-dock"
import { useReviewCases, useSaveAnnotation } from "@/hooks/use-review"
import { useResults } from "@/hooks/use-results"
import { useLocalStorageState, makeStorageKey } from "@/lib/local-storage"
import type { Annotation, AnnotationSpan, ResponseClass, ReviewCase, SpanFormat, SpanPosition } from "@/types"

interface DraftAnnotation {
  spans: AnnotationSpan[]
  response_class: ResponseClass | null
  note: string
  dirty: boolean
}

function emptyDraft(existing?: Annotation): DraftAnnotation {
  return {
    spans: existing?.spans ?? [],
    response_class: existing?.response_class ?? null,
    note: existing?.annotator_note ?? "",
    dirty: false,
  }
}

function hasAnnotation(draft: DraftAnnotation): boolean {
  return draft.spans.length > 0 || draft.response_class !== null
}

function buildAnnotation(draft: DraftAnnotation): Annotation | null {
  if (!hasAnnotation(draft)) return null
  return {
    spans: draft.spans,
    response_class: draft.response_class,
    annotator_note: draft.note,
  }
}

/** Does the parser's extracted answer (as a string) match any of the spans? */
function parserMatchesAnySpan(parsed: unknown, spans: AnnotationSpan[]): boolean {
  if (typeof parsed !== "string" || !parsed.trim()) return false
  const needle = parsed.trim().toLowerCase()
  return spans.some((s) => s.text.toLowerCase().includes(needle) || needle.includes(s.text.toLowerCase()))
}

/**
 * Composite key for draft / saved / unsaved state. Earlier versions keyed by
 * `case_id` alone, which collides when the annotator opens multiple result
 * files at once and two cases share the same `case_id` (e.g. carwash_0001
 * exists in both a UA and a DE result file) — drafts from one file would leak
 * into the other. The `result_file_id::case_id` pairing restores uniqueness.
 */
function caseKey(c: ReviewCase | undefined | null): string {
  return c ? `${c.result_file_id}::${c.case_id}` : ""
}

export default function ReviewPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filesParam = searchParams.get("files") || ""
  const fileIds = useMemo(
    () => filesParam.split(",").map((s) => s.trim()).filter(Boolean),
    [filesParam],
  )

  // Bare /review (no files) → bounce to Results so the user picks.
  if (fileIds.length === 0) {
    return <Navigate to="/results" replace />
  }

  return (
    <ReviewWorkspace
      fileIds={fileIds}
      caseIdFromURL={searchParams.get("case_id")}
      matchFilterParam={searchParams.get("match_types")}
      onChangeMatchFilter={(preset) => {
        const next = new URLSearchParams(searchParams)
        if (preset.matches === null) next.delete("match_types")
        else next.set("match_types", preset.matches.join(","))
        setSearchParams(next, { replace: true })
      }}
    />
  )
}

function ReviewWorkspace({
  fileIds,
  caseIdFromURL,
  matchFilterParam,
  onChangeMatchFilter,
}: {
  fileIds: string[]
  caseIdFromURL: string | null
  matchFilterParam: string | null
  onChangeMatchFilter: (preset: { key: string; matches: string[] | null }) => void
}) {
  const storageScope = `review:${fileIds.slice().sort().join("|")}`
  const [skipEmpty, setSkipEmpty] = useLocalStorageState<boolean>(
    makeStorageKey("review-page", "skip-empty"),
    true,
  )
  const [skipCorrect, setSkipCorrect] = useLocalStorageState<boolean>(
    makeStorageKey("review-page", "skip-correct"),
    false,
  )
  const [targetLang, setTargetLang] = useLocalStorageState<string>(
    makeStorageKey("review-page", "target-lang"),
    "en",
  )
  // Session-wide toggle for the peek-translate gutter (chunked, hover-to-peek).
  // Deliberately NOT persisted to localStorage — reset on reload is expected;
  // persists across case navigation within a single session.
  const [peekTranslateOn, setPeekTranslateOn] = useState(false)

  // ── Match-type filter from URL (preset keys map to match_types lists) ──
  const matchTypes = useMemo(() => {
    if (!matchFilterParam) return undefined
    return matchFilterParam.split(",").map((s) => s.trim()).filter(Boolean)
  }, [matchFilterParam])

  const activePresetKey = useMemo(() => {
    if (!matchTypes || matchTypes.length === 0) return "all"
    const found = MATCH_FILTER_PRESETS.find(
      (p) => p.matches && p.matches.length === matchTypes.length && p.matches.every((m) => matchTypes.includes(m)),
    )
    return found?.key ?? "custom"
  }, [matchTypes])

  const casesQuery = useReviewCases(fileIds, { skipEmpty, skipCorrect, matchTypes })
  const saveMutation = useSaveAnnotation()
  const { data: resultsSummary } = useResults()

  const cases: ReviewCase[] = useMemo(() => casesQuery.data?.cases ?? [], [casesQuery.data])

  // Persist the active index per file-set so resuming a session lands where we left off.
  const [activeIndex, setActiveIndex] = useLocalStorageState<number>(
    makeStorageKey(storageScope, "active-index"),
    0,
  )

  // Once cases load, jump to the URL-provided case_id if present.
  const appliedURLRef = useRef(false)
  useEffect(() => {
    if (appliedURLRef.current) return
    if (!caseIdFromURL || cases.length === 0) return
    const idx = cases.findIndex((c) => c.case_id === caseIdFromURL)
    if (idx >= 0) setActiveIndex(idx)
    appliedURLRef.current = true
  }, [caseIdFromURL, cases, setActiveIndex])

  // Clamp active index if the list shrinks (Skip/filter changed).
  useEffect(() => {
    if (cases.length === 0) {
      if (activeIndex !== 0) setActiveIndex(0)
      return
    }
    if (activeIndex >= cases.length) setActiveIndex(cases.length - 1)
  }, [cases.length, activeIndex, setActiveIndex])

  // Drafts buffered locally; flushed on Next.
  const [drafts, setDrafts] = useState<Record<string, DraftAnnotation>>({})
  const [unsaved, setUnsaved] = useState<Set<string>>(new Set())
  // Case IDs confirmed saved (by this session or pre-existing before load).
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())

  // Seed `savedIds` from any case that arrived with an `existing_annotation`.
  useEffect(() => {
    if (cases.length === 0) return
    setSavedIds((prev) => {
      const next = new Set(prev)
      for (const c of cases) {
        if (c.existing_annotation && (c.existing_annotation.spans.length > 0 || c.existing_annotation.response_class)) {
          next.add(caseKey(c))
        }
      }
      return next
    })
  }, [cases])

  // Active selection living OUTSIDE the response panel so the parent review
  // page can react to it (keyboard commit, etc.).
  const [pending, setPending] = useState<PendingSpan | null>(null)
  const commitHandlerRef = useRef<(() => void) | null>(null)

  const activeCase = cases[activeIndex]
  const activeKey = caseKey(activeCase)
  const activeDraft: DraftAnnotation = useMemo(() => {
    if (!activeCase) return { spans: [], response_class: null, note: "", dirty: false }
    return drafts[activeKey] ?? emptyDraft(activeCase.existing_annotation)
  }, [activeCase, activeKey, drafts])

  const updateDraft = useCallback(
    (patch: Partial<DraftAnnotation> | ((prev: DraftAnnotation) => DraftAnnotation)) => {
      if (!activeCase) return
      setDrafts((prev) => {
        const current = prev[activeKey] ?? emptyDraft(activeCase.existing_annotation)
        const next = typeof patch === "function" ? patch(current) : { ...current, ...patch }
        return { ...prev, [activeKey]: { ...next, dirty: true } }
      })
    },
    [activeCase, activeKey],
  )

  // ── Annotator verified: has the human engaged with the parser's claim? ──
  // Not "dirty" — we need to also honor previously-saved annotations where the
  // saved annotation had a response_class (e.g. parser_ok / parser_false_positive).
  const annotatorVerified = useMemo(() => {
    if (activeDraft.response_class !== null) return true
    if (activeDraft.spans.length > 0) return true
    return false
  }, [activeDraft])

  const handleAddSpan = useCallback(
    (span: AnnotationSpan) => {
      if (!activeCase) return
      updateDraft((prev) => ({
        ...prev,
        spans: [...prev.spans, span],
        dirty: true,
      }))

      // Auto-suggest `parser_false_positive` — but only on the *first*
      // contradicting span. The persistent callout in the response panel
      // covers subsequent cases so we don't pile toasts.
      const parsed = activeCase.parsed_answer
      const combined = [...activeDraft.spans, span]
      const firstContradicting = activeDraft.spans.length === 0
        && typeof parsed === "string"
        && parsed.trim().length > 0
        && !parserMatchesAnySpan(parsed, combined)
        && activeDraft.response_class !== "parser_false_positive"
      if (firstContradicting) {
        toast(`Parser extracted "${parsed}", your span is different.`, {
          action: {
            label: "Flag as false-positive",
            onClick: () => {
              updateDraft((prev) => ({ ...prev, response_class: "parser_false_positive", dirty: true }))
              toast.success("Marked as parser false-positive")
            },
          },
        })
      }
    },
    [activeCase, activeDraft, updateDraft],
  )

  const handleRemoveSpan = useCallback(
    (index: number) => {
      updateDraft((prev) => ({
        ...prev,
        spans: prev.spans.filter((_, i) => i !== index),
        dirty: true,
      }))
    },
    [updateDraft],
  )

  const handleChangeNote = useCallback((next: string) => {
    updateDraft({ note: next })
  }, [updateDraft])

  const handleFlagFalsePositive = useCallback(() => {
    if (!activeCase) return
    updateDraft((prev) => ({ ...prev, response_class: "parser_false_positive", dirty: true }))
  }, [activeCase, updateDraft])

  const handleClearVerdict = useCallback(() => {
    if (!activeCase) return
    updateDraft((prev) => ({ ...prev, response_class: null, dirty: true }))
  }, [activeCase, updateDraft])

  const handleChooseClass = useCallback(
    (code: ResponseClass) => {
      if (!activeCase) return
      setDrafts((prev) => {
        const current = prev[activeKey] ?? emptyDraft(activeCase.existing_annotation)
        // Spans + verdict are both valid evidence — keep them. The backend
        // invariant permits coexistence, and many realistic cases need both
        // (e.g. `verbose_correct` where the parser grabbed the wrong token
        // but the real answer is also present in the response — the span
        // pinpoints where, the verdict explains the failure mode).
        return {
          ...prev,
          [activeKey]: {
            ...current,
            response_class: code,
            dirty: true,
          },
        }
      })
    },
    [activeCase, activeKey],
  )

  const commitPending = useCallback(() => {
    if (!pending) return
    handleAddSpan({
      text: pending.text,
      char_start: pending.char_start,
      char_end: pending.char_end,
      position: pending.position,
      format: pending.format,
      confidence: "high",
    })
    setPending(null)
    window.getSelection()?.removeAllRanges()
  }, [pending, handleAddSpan])

  const saveDraft = useCallback(
    async (draft: DraftAnnotation, target: ReviewCase): Promise<boolean> => {
      const annotation = buildAnnotation(draft)
      if (!annotation) return true // nothing to save; treat as success
      const key = caseKey(target)
      try {
        await saveMutation.mutateAsync({
          result_file_id: target.result_file_id,
          case_id: target.case_id,
          annotation,
        })
        setUnsaved((prev) => {
          const next = new Set(prev)
          next.delete(key)
          return next
        })
        setSavedIds((prev) => {
          if (prev.has(key)) return prev
          const next = new Set(prev)
          next.add(key)
          return next
        })
        return true
      } catch (err) {
        setUnsaved((prev) => new Set(prev).add(key))
        toast.error(`Save failed — kept in buffer to retry. ${err instanceof Error ? err.message : ""}`)
        return false
      }
    },
    [saveMutation],
  )

  const goToIndex = useCallback(
    async (nextIdx: number) => {
      if (cases.length === 0) return
      const clamped = Math.max(0, Math.min(cases.length - 1, nextIdx))
      if (activeCase) {
        const draft = drafts[activeKey]
        if (draft?.dirty && buildAnnotation(draft)) {
          await saveDraft(draft, activeCase)
        }
      }
      setActiveIndex(clamped)
      setPending(null)
    },
    [cases.length, activeCase, activeKey, drafts, saveDraft, setActiveIndex],
  )

  const goNext = useCallback(() => goToIndex(activeIndex + 1), [activeIndex, goToIndex])
  const goPrev = useCallback(() => goToIndex(activeIndex - 1), [activeIndex, goToIndex])
  const skipCurrent = useCallback(() => {
    // Advance without saving — explicit pass-over.
    if (cases.length === 0) return
    setActiveIndex(Math.min(cases.length - 1, activeIndex + 1))
    setPending(null)
  }, [cases.length, activeIndex, setActiveIndex])

  const classifyByIndex = useCallback(
    (i: number) => {
      if (i < 0 || i >= CLASSES.length) return
      handleChooseClass(CLASSES[i].code)
    },
    [handleChooseClass],
  )

  // ── Keyboard shortcuts ────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
      ) {
        return
      }
      // Space / Enter commits pending selection when active.
      if ((e.key === " " || e.key === "Enter") && commitHandlerRef.current) {
        e.preventDefault()
        commitHandlerRef.current()
        return
      }
      if (e.key === "ArrowRight") {
        e.preventDefault()
        goNext()
      } else if (e.key === "ArrowLeft") {
        e.preventDefault()
        goPrev()
      } else if (e.key.toLowerCase() === "s") {
        e.preventDefault()
        skipCurrent()
      } else if (/^[1-7]$/.test(e.key)) {
        e.preventDefault()
        classifyByIndex(parseInt(e.key, 10) - 1)
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [goNext, goPrev, skipCurrent, classifyByIndex])

  // Register the imperative commit handler so keyboard shortcuts can fire it
  // without re-rendering the response panel.
  const registerCommit = useCallback((fn: (() => void) | null) => {
    commitHandlerRef.current = fn
  }, [])

  // ── Session metadata from the Results summary ────────────────────────
  const resultForCase = useMemo(() => {
    if (!activeCase || !resultsSummary) return null
    return resultsSummary.find((r) => r.filename === activeCase.result_file_id) ?? null
  }, [activeCase, resultsSummary])

  // ── Loading / error states ───────────────────────────────────────────
  if (casesQuery.isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading cases…
      </div>
    )
  }
  if (casesQuery.isError) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <div className="text-sm text-rose-600">Failed to load cases.</div>
        <Link to="/results" className="mt-4 inline-block text-xs text-muted-foreground underline">
          Back to Results
        </Link>
      </div>
    )
  }
  if (cases.length === 0) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <div className="text-lg font-semibold">Nothing to review</div>
        <p className="mt-2 text-sm text-muted-foreground">
          No cases match the current filters.
          {skipEmpty && " Try disabling 'Skip empty'."}
          {matchFilterParam && " Or widen the match-type filter."}
        </p>
        <Link to="/results" className="mt-4 inline-block text-xs text-muted-foreground underline">
          Back to Results
        </Link>
      </div>
    )
  }

  const atLast = activeIndex >= cases.length - 1
  const caseHasAnnotation = hasAnnotation(activeDraft)
  const nextLabel = caseHasAnnotation ? (atLast ? "Finish" : "Next") : atLast ? "Finish" : "Next"
  const showSkipInstead = !caseHasAnnotation

  const handleMatchPresetClick = (key: string) => {
    const preset = MATCH_FILTER_PRESETS.find((p) => p.key === key)
    if (preset) onChangeMatchFilter(preset)
  }

  return (
    <div className="relative -mx-4 -mt-4 flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden sm:-mx-6 sm:-mt-6">
      {/* Sticky header */}
      <div className="sticky top-0 z-20 border-b border-border/60 bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
        <CaseProgress
          plugin={casesQuery.data?.plugin || "review"}
          modelName={resultForCase?.model_name}
          testsetName={resultForCase?.testset_name || undefined}
          current={activeIndex}
          total={cases.length}
          savedCount={savedIds.size}
          unsavedCount={unsaved.size}
          skipEmpty={skipEmpty}
          skipCorrect={skipCorrect}
          matchFilterKey={activePresetKey}
          targetLang={targetLang}
          onToggleSkipEmpty={setSkipEmpty}
          onToggleSkipCorrect={setSkipCorrect}
          onChangeMatchFilter={handleMatchPresetClick}
          onChangeTargetLang={setTargetLang}
        />
      </div>

      {/* Two-column reading workspace: response gets ~65% of width. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 overflow-hidden px-4 py-4 md:grid-cols-[minmax(280px,35fr)_65fr] sm:px-6">
        <div className="min-h-0 overflow-hidden">
          {activeCase && <StimulusPanel caseData={activeCase} targetLang={targetLang} />}
        </div>
        <div className="min-h-0 overflow-hidden">
          {activeCase && (
            <ResponsePanel
              caseData={activeCase}
              spans={activeDraft.spans}
              note={activeDraft.note}
              annotatorVerified={annotatorVerified}
              pending={pending}
              responseClass={activeDraft.response_class}
              targetLang={targetLang}
              peekTranslateOn={peekTranslateOn}
              onTogglePeekTranslate={() => setPeekTranslateOn((v) => !v)}
              onSetPending={setPending}
              onCommitPending={commitPending}
              onAddSpan={handleAddSpan}
              onRemoveSpan={handleRemoveSpan}
              onChangeNote={handleChangeNote}
              onChangePosition={(position: SpanPosition) => setPending((p) => p && { ...p, position })}
              onChangeFormat={(format: SpanFormat) => setPending((p) => p && { ...p, format })}
              onFlagFalsePositive={handleFlagFalsePositive}
              onRegisterCommit={registerCommit}
            />
          )}
        </div>
      </div>

      {/* Sticky footer */}
      <div className="sticky bottom-0 z-20 border-t border-border/60 bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <ClassificationBar active={activeDraft.response_class} onChoose={handleChooseClass} />
            {activeDraft.response_class && (
              <VerdictPill verdict={activeDraft.response_class} onClear={handleClearVerdict} />
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Prev / Next / Skip */}
            <Button variant="outline" size="sm" onClick={goPrev} disabled={activeIndex === 0}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Prev
            </Button>
            {showSkipInstead ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={skipCurrent}
                disabled={saveMutation.isPending}
                title="Advance without saving (S)"
              >
                <SkipForward className="mr-1.5 h-3.5 w-3.5" />
                Skip
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={goNext}
                disabled={saveMutation.isPending}
                title={caseHasAnnotation ? "Save and advance (→)" : "Advance (→)"}
              >
                {saveMutation.isPending ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ArrowRight className="mr-1.5 h-3.5 w-3.5" />
                )}
                {nextLabel}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
