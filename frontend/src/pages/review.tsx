import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router"
import { ArrowLeft, ArrowRight, HelpCircle, Loader2, SkipForward } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { StimulusPanel } from "@/components/review/stimulus-panel"
import { ResponsePanel } from "@/components/review/response-panel"
import { ClassificationBar, CLASSES } from "@/components/review/classification-bar"
import { CaseProgress, MATCH_FILTER_PRESETS } from "@/components/review/case-progress"
import { VerdictPill } from "@/components/review/verdict-pill"
import { HelpDialog } from "@/components/review/help-dialog"
import { useReviewCases, useSaveAnnotation } from "@/hooks/use-review"
import { useReviewKeybindings } from "@/hooks/use-review-keybindings"
import { useModifierState } from "@/hooks/use-modifier-state"
import { useUndoStack } from "@/hooks/use-undo-stack"
import { useResults } from "@/hooks/use-results"
import { useLocalStorageState, makeStorageKey } from "@/lib/local-storage"
import { parserMatchesAnySpan } from "@/lib/span-autodetect"
import type { Annotation, AnnotationSpan, MarkSpan, ResponseClass, ReviewCase } from "@/types"

interface DraftAnnotation {
  spans: AnnotationSpan[]
  response_classes: ResponseClass[]
  note: string
  dirty: boolean
  // v3 mark types
  context_anchors: MarkSpan[]
  answer_keywords: MarkSpan[]
  negative_spans: MarkSpan[]
  negative_keywords: MarkSpan[]
  /**
   * Phase 2: sticky per-draft flag. Set `true` after the auto-negative-span
   * synthesis fires once on this case; prevents re-creation on subsequent
   * span edits (so dismissing an auto-inferred mark by removal stays
   * dismissed for the rest of the case). Not persisted — cleared on case
   * advance (new draft, new chance).
   */
  auto_negative_inferred: boolean
}

function emptyDraft(
  existing?: Annotation,
  responseLength?: number,
  wasTruncated?: boolean,
): DraftAnnotation {
  const rawSpans = existing?.spans ?? []
  // Drop spans whose char offsets fall outside the current response text.
  // This silently neutralises contaminated sidecar entries that were written
  // by a pre-fix version of the code when two result files shared a case_id
  // and the wrong file's annotation was saved into the other file's sidecar.
  const spans =
    responseLength !== undefined
      ? rawSpans.filter(
          (s) => s.char_start >= 0 && s.char_end <= responseLength && s.char_start < s.char_end,
        )
      : rawSpans
  let response_classes = existing?.response_classes ?? []
  let dirty = false
  // Phase 3: auto-toggle the Truncated chip when the inference-time flag is
  // set AND the annotator hasn't already recorded any classification on this
  // case. Respects prior annotator judgment over auto-detect — if the user
  // saved ANY response_classes (even empty after un-toggling, though that
  // case doesn't save), we don't override. `dirty = true` so Space saves
  // the confirmed flag to the sidecar.
  if (wasTruncated && response_classes.length === 0) {
    response_classes = ["truncated"]
    dirty = true
  }
  return {
    spans,
    response_classes,
    note: existing?.annotator_note ?? "",
    dirty,
    context_anchors: existing?.context_anchors ?? [],
    answer_keywords: existing?.answer_keywords ?? [],
    negative_spans: existing?.negative_spans ?? [],
    negative_keywords: existing?.negative_keywords ?? [],
    auto_negative_inferred: false,
  }
}

function hasAnnotation(draft: DraftAnnotation): boolean {
  return (
    draft.spans.length > 0 ||
    draft.response_classes.length > 0 ||
    draft.context_anchors.length > 0 ||
    draft.answer_keywords.length > 0 ||
    draft.negative_spans.length > 0 ||
    draft.negative_keywords.length > 0
  )
}

function buildAnnotation(draft: DraftAnnotation): Annotation | null {
  if (!hasAnnotation(draft)) return null
  return {
    spans: draft.spans,
    response_classes: draft.response_classes,
    annotator_note: draft.note,
    context_anchors: draft.context_anchors,
    answer_keywords: draft.answer_keywords,
    negative_spans: draft.negative_spans,
    negative_keywords: draft.negative_keywords,
  }
}

// `parserMatchesAnySpan` lives in `@/lib/span-autodetect` as of Phase 2 —
// previously duplicated here and in response-panel.tsx.

/**
 * Composite key for draft / saved / unsaved state.  Must be unique per
 * distinct result entry.  Uses response_hash (fingerprint of the actual
 * response) — unique across all dimensions: language × user_style ×
 * system_style × run index.
 */
function caseKey(c: ReviewCase | undefined | null): string {
  return c ? `${c.result_file_id}::${c.case_id}::${c.response_hash}` : ""
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
  const navigate = useNavigate()
  const [helpOpen, setHelpOpen] = useState(false)

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

  // Sort so the backend case order is stable regardless of URL param order.
  // `storageScope` already sorts, so `activeIndex` now consistently refers to
  // the same case even if the user reloads with a different param ordering.
  const sortedFileIds = useMemo(() => fileIds.slice().sort(), [fileIds])
  const casesQuery = useReviewCases(sortedFileIds, { skipEmpty, skipCorrect, matchTypes })
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
        if (c.existing_annotation && (c.existing_annotation.spans.length > 0 || (c.existing_annotation.response_classes?.length ?? 0) > 0)) {
          next.add(caseKey(c))
        }
      }
      return next
    })
  }, [cases])

  // v4: held A / D / Shift drives mark-type selection at drag-commit time.
  const { activeModifier } = useModifierState()

  const activeCase = cases[activeIndex]
  const activeKey = caseKey(activeCase)
  const activeDraft: DraftAnnotation = useMemo(() => {
    if (!activeCase) return { spans: [], response_classes: [], note: "", dirty: false, context_anchors: [], answer_keywords: [], negative_spans: [], negative_keywords: [], auto_negative_inferred: false }
    return drafts[activeKey] ?? emptyDraft(
      activeCase.existing_annotation,
      activeCase.raw_response.length,
      activeCase.was_truncated ?? false,
    )
  }, [activeCase, activeKey, drafts])

  // ── Undo/redo (Phase 1 §3.5) ──
  // `activeKey` closes over the snapshot restore so an undo event always
  // lands on the case the user is looking at. Resetting on case advance
  // (see `goToIndex`) guarantees undo never crosses case boundaries.
  const onRestoreDraft = useCallback(
    (snapshot: DraftAnnotation) => {
      if (!activeKey) return
      setDrafts((prev) => ({ ...prev, [activeKey]: { ...snapshot, dirty: true } }))
    },
    [activeKey],
  )
  const undoStack = useUndoStack<DraftAnnotation>(activeDraft, onRestoreDraft, 10)

  const updateDraft = useCallback(
    (patch: Partial<DraftAnnotation> | ((prev: DraftAnnotation) => DraftAnnotation)) => {
      if (!activeCase) return
      // Snapshot the CURRENT draft value before mutating. Using `activeDraft`
      // (the memoized render value) rather than reading from inside setDrafts
      // keeps snapshot ordering deterministic — every user-visible change
      // produces exactly one undo entry.
      undoStack.push(activeDraft)
      setDrafts((prev) => {
        const current = prev[activeKey] ?? emptyDraft(
          activeCase.existing_annotation,
          activeCase.raw_response.length,
          activeCase.was_truncated ?? false,
        )
        const next = typeof patch === "function" ? patch(current) : { ...current, ...patch }
        return { ...prev, [activeKey]: { ...next, dirty: true } }
      })
    },
    [activeCase, activeKey, activeDraft, undoStack],
  )

  // ── Annotator verified: has the human engaged with the parser's claim? ──
  // Not "dirty" — we need to also honor previously-saved annotations where the
  // saved annotation had response_classes (e.g. false_positive).
  const annotatorVerified = useMemo(() => {
    if (activeDraft.response_classes.length > 0) return true
    if (activeDraft.spans.length > 0) return true
    return false
  }, [activeDraft])

  /** Merge a new mark into an existing array if adjacent (within 1 char gap),
   *  otherwise append. Returns the updated array. */
  const mergeOrAppendMark = useCallback(
    <T extends { char_start: number; char_end: number; text: string }>(
      existing: T[],
      newMark: T,
    ): T[] => {
      const response = activeCase?.raw_response ?? ""
      const adj = existing.findIndex(
        (s) => s.char_end >= newMark.char_start - 1 && s.char_start <= newMark.char_end + 1,
      )
      if (adj >= 0) {
        const merged = { ...existing[adj] }
        merged.char_start = Math.min(merged.char_start, newMark.char_start)
        merged.char_end = Math.max(merged.char_end, newMark.char_end)
        merged.text = response.slice(merged.char_start, merged.char_end)
        return existing.map((s, i) => (i === adj ? merged : s) as T)
      }
      return [...existing, newMark]
    },
    [activeCase],
  )

  const handleAddSpan = useCallback(
    (span: AnnotationSpan) => {
      if (!activeCase) return
      // Phase 2: fold the auto-inferred negative into the SAME updateDraft
      // setter as the answer-span mutation so one undo entry captures both.
      // Splitting the mutations would let Ctrl+Z leave the answer span and
      // only undo the auto-negative (R5 in the Phase 2 plan).
      const parserStart = activeCase.parsed_char_start
      const parserEnd = activeCase.parsed_char_end
      const hasParserRegion =
        typeof parserStart === "number" &&
        typeof parserEnd === "number" &&
        parserEnd > parserStart
      const raw = activeCase.raw_response

      updateDraft((prev) => {
        const newSpans = mergeOrAppendMark(prev.spans, span)
        // Auto-inference fires iff: parser has offsets, no prior firing on
        // this draft, and no answer span (existing or just-added) overlaps
        // the parser region.
        const overlapsParser =
          hasParserRegion &&
          newSpans.some(
            (s) => s.char_end > parserStart! && s.char_start < parserEnd!,
          )
        const shouldAuto =
          hasParserRegion && !prev.auto_negative_inferred && !overlapsParser
        if (!shouldAuto) {
          return { ...prev, spans: newSpans, dirty: true }
        }
        const autoNegative: MarkSpan = {
          text: raw.slice(parserStart!, parserEnd!),
          char_start: parserStart!,
          char_end: parserEnd!,
          source: "auto_inferred",
        }
        return {
          ...prev,
          spans: newSpans,
          // Direct append — auto-inferred negatives SKIP mergeOrAppendMark
          // so a later manual drag that overlaps keeps the source distinction
          // clean. handleAddNegativeSpan removes any overlapping auto entry
          // before appending the manual one.
          negative_spans: [...prev.negative_spans, autoNegative],
          auto_negative_inferred: true,
          dirty: true,
        }
      })

      // Existing "Parser extracted X" toast — still fires alongside the
      // auto-inferred mark. The toast's "Flag as false-positive" button
      // complements the auto-negative: the former classifies the case,
      // the latter marks the specific misextraction region.
      const parsed = activeCase.parsed_answer
      const combined = [...activeDraft.spans, span]
      const firstContradicting = activeDraft.spans.length === 0
        && typeof parsed === "string"
        && parsed.trim().length > 0
        && !parserMatchesAnySpan(parsed, combined)
        && !activeDraft.response_classes.includes("false_positive")
      if (firstContradicting) {
        toast(`Parser extracted "${parsed}", your span is different.`, {
          action: {
            label: "Flag as false-positive",
            onClick: () => {
              updateDraft((prev) => ({
                ...prev,
                response_classes: prev.response_classes.includes("false_positive")
                  ? prev.response_classes
                  : [...prev.response_classes, "false_positive"],
                dirty: true,
              }))
              toast.success("Marked as parser false-positive")
            },
          },
        })
      }
    },
    [activeCase, activeDraft, updateDraft, mergeOrAppendMark],
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

  // ── v3 mark type handlers ──────────────────────────────────────────────
  const handleAddContextAnchor = useCallback(
    (mark: MarkSpan) => updateDraft((prev) => ({ ...prev, context_anchors: mergeOrAppendMark(prev.context_anchors, mark), dirty: true })),
    [updateDraft, mergeOrAppendMark],
  )
  const handleAddAnswerKeyword = useCallback(
    (mark: MarkSpan) => updateDraft((prev) => ({ ...prev, answer_keywords: mergeOrAppendMark(prev.answer_keywords, mark), dirty: true })),
    [updateDraft, mergeOrAppendMark],
  )
  const handleAddNegativeSpan = useCallback(
    (mark: MarkSpan) =>
      updateDraft((prev) => {
        // Phase 2: if the new (manual) negative overlaps an auto-inferred
        // one, remove the auto entry first so the manual span supersedes it
        // cleanly. Prevents "half auto / half manual" merged marks where the
        // source field becomes ambiguous.
        const overlapsAuto = (s: MarkSpan) =>
          s.source === "auto_inferred" &&
          s.char_end > mark.char_start &&
          s.char_start < mark.char_end
        const withoutOverlappingAuto = prev.negative_spans.filter(
          (s) => !overlapsAuto(s),
        )
        const next: MarkSpan = { ...mark, source: "manual" }
        return {
          ...prev,
          negative_spans: mergeOrAppendMark(withoutOverlappingAuto, next),
          dirty: true,
        }
      }),
    [updateDraft, mergeOrAppendMark],
  )
  const handleRemoveContextAnchor = useCallback(
    (index: number) => updateDraft((prev) => ({ ...prev, context_anchors: prev.context_anchors.filter((_, i) => i !== index), dirty: true })),
    [updateDraft],
  )
  const handleRemoveAnswerKeyword = useCallback(
    (index: number) => updateDraft((prev) => ({ ...prev, answer_keywords: prev.answer_keywords.filter((_, i) => i !== index), dirty: true })),
    [updateDraft],
  )
  const handleRemoveNegativeSpan = useCallback(
    (index: number) => updateDraft((prev) => ({ ...prev, negative_spans: prev.negative_spans.filter((_, i) => i !== index), dirty: true })),
    [updateDraft],
  )
  const handleRemoveNegativeKeyword = useCallback(
    (index: number) => updateDraft((prev) => ({ ...prev, negative_keywords: prev.negative_keywords.filter((_, i) => i !== index), dirty: true })),
    [updateDraft],
  )

  const handleFlagFalsePositive = useCallback(() => {
    if (!activeCase) return
    updateDraft((prev) => ({
      ...prev,
      response_classes: prev.response_classes.includes("false_positive")
        ? prev.response_classes
        : [...prev.response_classes, "false_positive"],
      dirty: true,
    }))
  }, [activeCase, updateDraft])

  const handleClearVerdict = useCallback(
    (code: ResponseClass) => {
      if (!activeCase) return
      updateDraft((prev) => ({
        ...prev,
        response_classes: prev.response_classes.filter((c) => c !== code),
        dirty: true,
      }))
    },
    [activeCase, updateDraft],
  )

  const handleToggleClass = useCallback(
    (code: ResponseClass) => {
      if (!activeCase) return
      updateDraft((prev) => ({
        ...prev,
        // Toggle: remove if present, add if absent.
        response_classes: prev.response_classes.includes(code)
          ? prev.response_classes.filter((c) => c !== code)
          : [...prev.response_classes, code],
        dirty: true,
      }))
    },
    [activeCase, updateDraft],
  )

  const saveDraft = useCallback(
    async (draft: DraftAnnotation, target: ReviewCase): Promise<boolean> => {
      const annotation = buildAnnotation(draft)
      if (!annotation) return true // nothing to save; treat as success
      const key = caseKey(target)
      try {
        await saveMutation.mutateAsync({
          result_file_id: target.result_file_id,
          case_id: target.case_id,
          response_hash: target.response_hash,
          language: target.language,
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
        toast.success("saved ✓", { duration: 1500 })
        return true
      } catch (err) {
        setUnsaved((prev) => new Set(prev).add(key))
        toast.error(`Save failed — kept in buffer to retry. ${err instanceof Error ? err.message : ""}`)
        return false
      }
    },
    [saveMutation],
  )

  // v4 race guard (spec §9 Risk #4): drop a second Space-press while a save
  // is already in flight. Avoids duplicate POSTs when Space is mashed.
  const savingRef = useRef(false)

  const goToIndex = useCallback(
    async (nextIdx: number) => {
      if (cases.length === 0) return
      const clamped = Math.max(0, Math.min(cases.length - 1, nextIdx))
      if (activeCase) {
        const draft = drafts[activeKey]
        if (draft?.dirty && buildAnnotation(draft)) {
          if (savingRef.current) return
          savingRef.current = true
          try {
            await saveDraft(draft, activeCase)
          } finally {
            savingRef.current = false
          }
        }
      }
      // Case boundary: undo/redo must not cross it (spec §3.5). Reset first,
      // then advance — if the advance re-renders with a different activeDraft,
      // the hook picks up the fresh baseline on the next mutation.
      undoStack.reset()
      setActiveIndex(clamped)
    },
    [cases.length, activeCase, activeKey, drafts, saveDraft, setActiveIndex, undoStack],
  )

  const handleFinish = useCallback(async () => {
    // Save current draft if dirty, then navigate back to Results.
    if (activeCase) {
      const draft = drafts[activeKey]
      if (draft?.dirty && buildAnnotation(draft)) {
        await saveDraft(draft, activeCase)
      }
    }
    navigate("/results")
  }, [activeCase, activeKey, drafts, saveDraft, navigate])

  /** v4: discard the active draft and advance. Bound to Ctrl/Meta+Space —
   *  the pinky-friction is the deliberate "this is destructive" signal.
   *  At the last case, navigates to /results. */
  const rejectAndAdvance = useCallback(() => {
    if (!activeCase) {
      navigate("/results")
      return
    }
    const key = activeKey
    const hadDraft = drafts[key] !== undefined
    setDrafts((prev) => {
      if (!(key in prev)) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
    setUnsaved((prev) => {
      if (!prev.has(key)) return prev
      const next = new Set(prev)
      next.delete(key)
      return next
    })
    undoStack.reset()
    if (hadDraft) {
      toast("discarded", { duration: 1500, className: "text-rose-600" })
    }
    if (activeIndex >= cases.length - 1) {
      navigate("/results")
    } else {
      setActiveIndex(activeIndex + 1)
    }
  }, [activeCase, activeKey, activeIndex, cases.length, drafts, navigate, setActiveIndex, undoStack])

  const goNext = useCallback(() => {
    if (activeIndex >= cases.length - 1) {
      handleFinish()
    } else {
      goToIndex(activeIndex + 1)
    }
  }, [activeIndex, cases.length, handleFinish, goToIndex])
  const goPrev = useCallback(() => goToIndex(activeIndex - 1), [activeIndex, goToIndex])

  /** v4: lookup by CLASSES[].key string (e.g. "2", "3"), not positional index.
   *  The class array is not densely numbered — key "1" is reserved for
   *  implicit Extractable. */
  const classifyByKey = useCallback(
    (key: string) => {
      const def = CLASSES.find((c) => c.key === key)
      if (def) handleToggleClass(def.code)
    },
    [handleToggleClass],
  )

  /** v4: lookup by CLASSES[].letter ("Q" / "E" / "F"). Case-insensitive. */
  const classifyByLetter = useCallback(
    (letter: "Q" | "E" | "F") => {
      const def = CLASSES.find((c) => c.letter?.toUpperCase() === letter)
      if (def) handleToggleClass(def.code)
    },
    [handleToggleClass],
  )

  /** v4: Space semantics. If the draft has content, save and advance; if
   *  empty, just advance (skip-equivalent). */
  const handleSpace = goNext

  const toggleHelp = useCallback(() => setHelpOpen((v) => !v), [])

  useReviewKeybindings({
    onClassifyByKey: classifyByKey,
    onClassifyByLetter: classifyByLetter,
    onSpace: handleSpace,
    onCtrlSpace: rejectAndAdvance,
    onPrev: goPrev,
    onUndo: undoStack.undo,
    onRedo: undoStack.redo,
    onToggleHelp: toggleHelp,
  })

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
  const nextLabel = atLast ? "Finish" : "Next"

  const handleMatchPresetClick = (key: string) => {
    const preset = MATCH_FILTER_PRESETS.find((p) => p.key === key)
    if (preset) onChangeMatchFilter(preset)
  }

  return (
    <div className="relative -mx-4 -mt-4 flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden sm:-mx-6 sm:-mt-6">
      <HelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
      {/* Sticky header */}
      <div className="sticky top-0 z-20 border-b border-border/60 bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <CaseProgress
              plugin={casesQuery.data?.plugin || "review"}
              modelName={resultForCase?.model_name}
              testsetName={resultForCase?.testset_name || undefined}
              current={activeIndex}
              total={cases.length}
              savedCount={savedIds.size}
              unsavedCount={unsaved.size}
              totalAnnotatedInSidecars={casesQuery.data?.total_annotated_in_sidecars}
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
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setHelpOpen(true)}
            className="mt-0.5 h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
            title="Keyboard shortcuts & help (?)"
          >
            <HelpCircle className="h-4 w-4" />
          </Button>
        </div>
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
              activeModifier={activeModifier}
              responseClasses={activeDraft.response_classes}
              targetLang={targetLang}
              peekTranslateOn={peekTranslateOn}
              onTogglePeekTranslate={() => setPeekTranslateOn((v) => !v)}
              onAddSpan={handleAddSpan}
              onRemoveSpan={handleRemoveSpan}
              onChangeNote={handleChangeNote}
              onFlagFalsePositive={handleFlagFalsePositive}
              contextAnchors={activeDraft.context_anchors}
              answerKeywords={activeDraft.answer_keywords}
              negativeSpans={activeDraft.negative_spans}
              negativeKeywords={activeDraft.negative_keywords}
              onAddContextAnchor={handleAddContextAnchor}
              onAddAnswerKeyword={handleAddAnswerKeyword}
              onAddNegativeSpan={handleAddNegativeSpan}
              onRemoveContextAnchor={handleRemoveContextAnchor}
              onRemoveAnswerKeyword={handleRemoveAnswerKeyword}
              onRemoveNegativeSpan={handleRemoveNegativeSpan}
              onRemoveNegativeKeyword={handleRemoveNegativeKeyword}
            />
          )}
        </div>
      </div>

      {/* Sticky footer */}
      <div className="sticky bottom-0 z-20 border-t border-border/60 bg-background/85 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <ClassificationBar active={activeDraft.response_classes} onToggle={handleToggleClass} />
            {activeDraft.response_classes.length > 0 && (
              <VerdictPill verdicts={activeDraft.response_classes} onClear={handleClearVerdict} />
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Prev / Discard / Next.
              * v4: Skip button is gone — Space with an empty draft is the
              * skip path; the primary "Next" button always saves-and-advances
              * (or just advances if the draft is empty). Discard is kept as
              * an explicit button equivalent of Ctrl+Space for mouse users. */}
            <Button
              variant="outline"
              size="sm"
              onClick={goPrev}
              disabled={activeIndex === 0}
              title="Previous case (←)"
            >
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Prev
            </Button>
            {caseHasAnnotation && (
              <Button
                variant="ghost"
                size="sm"
                onClick={rejectAndAdvance}
                disabled={saveMutation.isPending}
                title="Discard draft and advance (Ctrl+Space)"
              >
                <SkipForward className="mr-1.5 h-3.5 w-3.5" />
                Discard
              </Button>
            )}
            <Button
              size="sm"
              onClick={goNext}
              disabled={saveMutation.isPending}
              title={caseHasAnnotation ? "Save and advance (Space)" : "Advance (Space)"}
            >
              {saveMutation.isPending ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowRight className="mr-1.5 h-3.5 w-3.5" />
              )}
              {nextLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
