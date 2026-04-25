import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { AlertTriangle, CheckCircle2, Copy, Crosshair, Languages } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AnnotationSpan, MarkSpan, ResponseClass, ReviewCase } from "@/types"
import { autoFormat, autoPosition, parserMatchesAnySpan } from "@/lib/span-autodetect"
import type { ActiveModifier } from "@/hooks/use-modifier-state"
import { NotePanel } from "./note-panel"
import { chunkResponse, type TranslateChunk } from "./translate-chunks"
import { ChunkGutter } from "./chunk-gutter"

interface Props {
  caseData: ReviewCase
  spans: AnnotationSpan[]
  note: string
  /** Set `true` once the annotator has explicitly endorsed or contradicted the
   * parser via a classification — until then the green "correct" badge renders
   * muted so it doesn't falsely reassure the annotator. */
  annotatorVerified: boolean
  /** v4 (Phase 1): null → answer span; anchor/keyword/negative for held A/D/Shift. */
  activeModifier: ActiveModifier
  /** Current classification verdicts — used to compute the
   * disagreement alert + strike-through parser badge. */
  responseClasses: ResponseClass[]
  /** Session-wide target language for the Translate button. */
  targetLang: string
  /** Session-wide peek-translate toggle (chunked gutter + hover popover). */
  peekTranslateOn: boolean
  onTogglePeekTranslate: () => void
  /** Immediate add with auto-detected position/format. Used by both click-to-mark
   *  and drag-select-to-mark paths since Phase 1 removed the pending dock. */
  onAddSpan: (span: AnnotationSpan) => void
  onRemoveSpan: (index: number) => void
  onChangeNote: (next: string) => void
  onFlagFalsePositive?: () => void
  // v3 mark types
  contextAnchors: MarkSpan[]
  answerKeywords: MarkSpan[]
  negativeSpans: MarkSpan[]
  /** v4: retained in the type surface so legacy annotations with stored
   *  negative_keywords still render during the Phase 1 migration window, but
   *  no longer authored via the UI. */
  negativeKeywords: MarkSpan[]
  onAddContextAnchor: (mark: MarkSpan) => void
  onAddAnswerKeyword: (mark: MarkSpan) => void
  onAddNegativeSpan: (mark: MarkSpan) => void
  onRemoveContextAnchor: (index: number) => void
  onRemoveAnswerKeyword: (index: number) => void
  onRemoveNegativeSpan: (index: number) => void
  onRemoveNegativeKeyword: (index: number) => void
}

/**
 * Resolve the parser-highlight region in `caseData.raw_response`.
 *
 * Phase 2: prefer backend-emitted `parsed_char_start` / `parsed_char_end`
 * over client-side substring search. Backend offsets are populated either
 * natively by a migrated plugin parser OR by the universal
 * `resolve_parser_offsets` fallback at result-write time — so every
 * freshly-run case carries reliable anchors.
 *
 * Falls back to client-side substring search for legacy result files that
 * predate Phase 2 (fields absent). Substring search returns `null` for
 * non-string `parsed_answer` (grids, dicts); that's the intended behaviour
 * — no amber highlight, no parser-click affordance.
 */
function resolveParserMatch(
  caseData: ReviewCase,
): { start: number; end: number } | null {
  const { parsed_char_start, parsed_char_end, raw_response, parsed_answer } = caseData
  if (
    typeof parsed_char_start === "number" &&
    typeof parsed_char_end === "number" &&
    parsed_char_start >= 0 &&
    parsed_char_end > parsed_char_start &&
    parsed_char_end <= raw_response.length
  ) {
    return { start: parsed_char_start, end: parsed_char_end }
  }
  // Legacy fallback: client-side substring search over stringified value.
  if (typeof parsed_answer !== "string" || !parsed_answer) return null
  const needle = parsed_answer.trim()
  if (!needle) return null
  const idx = raw_response.toLowerCase().indexOf(needle.toLowerCase())
  if (idx < 0) return null
  return { start: idx, end: idx + needle.length }
}

// Owner tag per character position. Higher-priority marks overwrite lower ones.
// Negative sentinel values encode mark type; non-negative values are span indices.
const OWN_PLAIN = -2
const OWN_PARSER = -1
// >=0 → annotation span (value is the span index)
const OWN_ANCHOR = -3    // context anchor (A+click/drag)
const OWN_KEYWORD = -4   // answer keyword (D+click/drag)
const OWN_NEG_SPAN = -5  // negative span (Shift+click/drag), source="manual"
// v4: OWN_NEG_KW retained for legacy-annotation rendering only — new author
// paths can't produce one. Old sidecars migrated on read fold their keyword
// entries into negative_spans, but some rows may still carry non-empty
// `negative_keywords` until they're re-saved.
const OWN_NEG_KW = -6
// Phase 2: auto-inferred negative span (dotted-rose, ~60% opacity). Painted
// BEFORE OWN_NEG_SPAN in classifyChars so manual marks win visual priority
// when they overlap (which they shouldn't after Phase 2C's overlap-removal
// logic, but legacy data may still have both).
const OWN_NEG_SPAN_AUTO = -7

/** Build a per-character owner map so the word-level renderer can decorate
 *  each token without re-scanning the whole span list. */
function classifyChars(
  len: number,
  spans: AnnotationSpan[],
  parserMatch: { start: number; end: number } | null,
  contextAnchors: MarkSpan[],
  answerKeywords: MarkSpan[],
  negativeSpans: MarkSpan[],
  negativeKeywords: MarkSpan[],
): Int32Array {
  const owner = new Int32Array(len).fill(OWN_PLAIN)
  // Paint in priority order (lowest first → highest overwrites).
  if (parserMatch) {
    for (let i = parserMatch.start; i < parserMatch.end && i < len; i++) {
      owner[i] = OWN_PARSER
    }
  }
  // Phase 2: paint auto-inferred negatives first so manual negatives
  // (painted next) visually override on the rare overlap case.
  for (const s of negativeSpans) {
    if (s.source !== "auto_inferred") continue
    for (let i = s.char_start; i < s.char_end && i < len; i++) owner[i] = OWN_NEG_SPAN_AUTO
  }
  for (const s of negativeSpans) {
    if (s.source === "auto_inferred") continue
    for (let i = s.char_start; i < s.char_end && i < len; i++) owner[i] = OWN_NEG_SPAN
  }
  for (const s of negativeKeywords) {
    for (let i = s.char_start; i < s.char_end && i < len; i++) owner[i] = OWN_NEG_KW
  }
  for (const s of contextAnchors) {
    for (let i = s.char_start; i < s.char_end && i < len; i++) owner[i] = OWN_ANCHOR
  }
  for (const s of answerKeywords) {
    for (let i = s.char_start; i < s.char_end && i < len; i++) owner[i] = OWN_KEYWORD
  }
  // Answer spans win over everything (primary annotator intent).
  spans.forEach((s, idx) => {
    for (let i = s.char_start; i < s.char_end && i < len; i++) {
      owner[i] = idx
    }
  })
  return owner
}

/** Is a character part of a word token? Unicode-letter/number/underscore/apostrophe. */
function isWordChar(ch: string): boolean {
  return /[\p{L}\p{N}_']/u.test(ch)
}

interface RenderWordsArgs {
  text: string
  owner: Int32Array
  parserHighlightRef: React.RefObject<HTMLSpanElement | null>
  flashing: boolean
  parserHint: string
  onWordClick: (start: number, end: number, text: string) => void
  onRemoveSpan: (index: number) => void
  /**
   * When provided, output is wrapped in `<span data-chunk-idx="…">` elements
   * aligned with each chunk's range. The refs in `chunkRefsOut` are populated
   * with the wrapper DOM nodes so ChunkGutter can measure their bounding
   * boxes. `display: inline` keeps layout identical to the unchunked render.
   */
  chunks?: TranslateChunk[]
  chunkRefsOut?: React.RefObject<(HTMLSpanElement | null)[]>
}

/**
 * Walk the response string and emit a mix of:
 *   - non-word runs (whitespace, punctuation) — inert text, decorated if they
 *     fall inside a mark / parser-match region
 *   - word tokens — interactive spans with hover affordance, click-to-mark
 *     for plain/parser-match words, click-to-remove for already-marked words
 *
 * The parser-match ref is attached to the first word of the parser-match
 * region so `Jump to parser match` has a stable scroll target.
 *
 * Mixed-owner words (rare: happens when a drag-selected span ends mid-word)
 * fall back to plain rendering — the annotator can still remove via the
 * "Answer spans" chip row below.
 */
function renderWords(args: RenderWordsArgs) {
  const { text, owner, parserHighlightRef, flashing, parserHint, onWordClick, onRemoveSpan, chunks, chunkRefsOut } = args
  // `parserAttached` is shared across chunk boundaries so the parser-match ref
  // attaches exactly once to the first matching word, regardless of chunking.
  const parserAttached = { value: false }

  if (chunks && chunks.length > 0) {
    const out: React.ReactNode[] = []
    let cursor = 0
    if (chunkRefsOut) chunkRefsOut.current = new Array(chunks.length).fill(null)
    chunks.forEach((chunk, idx) => {
      if (chunk.start > cursor) {
        out.push(<span key={`gap-${cursor}`}>{text.slice(cursor, chunk.start)}</span>)
      }
      out.push(
        <span
          key={`chunk-${chunk.start}`}
          data-chunk-idx={idx}
          ref={(el) => {
            if (chunkRefsOut) chunkRefsOut.current[idx] = el
          }}
        >
          {renderRange(text, owner, chunk.start, chunk.end, parserHighlightRef, parserAttached, flashing, parserHint, onWordClick, onRemoveSpan)}
        </span>,
      )
      cursor = chunk.end
    })
    if (cursor < text.length) {
      out.push(
        <span key={`tail-${cursor}`}>
          {renderRange(text, owner, cursor, text.length, parserHighlightRef, parserAttached, flashing, parserHint, onWordClick, onRemoveSpan)}
        </span>,
      )
    }
    return out
  }

  return renderRange(text, owner, 0, text.length, parserHighlightRef, parserAttached, flashing, parserHint, onWordClick, onRemoveSpan)
}

/** Walk `text[start..end)` and emit the word/non-word runs with interactive
 *  affordances. Mutates `parserAttached.value` so the parser-match ref is
 *  attached exactly once across sequential calls (chunked render path). */
function renderRange(
  text: string,
  owner: Int32Array,
  start: number,
  end: number,
  parserHighlightRef: React.RefObject<HTMLSpanElement | null>,
  parserAttached: { value: boolean },
  flashing: boolean,
  parserHint: string,
  onWordClick: (start: number, end: number, text: string) => void,
  onRemoveSpan: (index: number) => void,
): React.ReactNode[] {
  const out: React.ReactNode[] = []
  let i = start

  while (i < end) {
    const runStartsWord = isWordChar(text[i])
    let j = i
    while (j < end && isWordChar(text[j]) === runStartsWord) j++
    const chunk = text.slice(i, j)
    const runStart = i
    const firstOwner = owner[runStart] ?? OWN_PLAIN
    let consistent = true
    for (let k = runStart + 1; k < j; k++) {
      if (owner[k] !== firstOwner) { consistent = false; break }
    }

    // ── Non-word runs (whitespace, punctuation) — inert decorations ──
    if (!runStartsWord) {
      if (consistent && firstOwner >= 0) {
        out.push(<span key={runStart} className="border-b-2 border-primary bg-primary/15">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_ANCHOR) {
        out.push(<span key={runStart} className="border-b border-dashed border-indigo-500 bg-indigo-400/15">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_KEYWORD) {
        out.push(<span key={runStart} className="border-b border-dotted border-violet-500 bg-violet-400/15">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_NEG_SPAN) {
        out.push(<span key={runStart} className="border-b-2 border-rose-500 bg-rose-400/15">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_NEG_SPAN_AUTO) {
        // Phase 2: auto-inferred negative — muted, dotted, ~60% opacity of
        // a manual negative. Visually distinct so annotators can tell the
        // difference at a glance.
        out.push(<span key={runStart} className="border-b border-dotted border-rose-400 bg-rose-400/8">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_NEG_KW) {
        out.push(<span key={runStart} className="border-b border-dotted border-rose-600 bg-rose-500/20">{chunk}</span>)
      } else if (consistent && firstOwner === OWN_PARSER) {
        out.push(<span key={runStart} className="border-b border-dashed border-amber-500 bg-amber-400/10">{chunk}</span>)
      } else {
        out.push(<span key={runStart}>{chunk}</span>)
      }
      i = j
      continue
    }

    // ── Word tokens — interactive ──
    if (consistent && firstOwner >= 0) {
      const spanIdx = firstOwner
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onRemoveSpan(spanIdx) }}
          className="cursor-pointer rounded-sm border-b-2 border-primary bg-primary/15 px-0.5 text-foreground hover:bg-primary/25"
          title="Click to remove annotation"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_ANCHOR) {
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="cursor-pointer rounded-sm border-b border-dashed border-indigo-500 bg-indigo-400/15 px-0.5 text-foreground hover:bg-indigo-400/25"
          title="Context anchor · click to remove"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_KEYWORD) {
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="cursor-pointer rounded-sm border-b border-dotted border-violet-500 bg-violet-400/15 px-0.5 text-foreground hover:bg-violet-400/25"
          title="Answer keyword · click to remove"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_NEG_SPAN) {
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="cursor-pointer rounded-sm border-b-2 border-rose-500 bg-rose-400/15 px-0.5 text-foreground hover:bg-rose-400/25"
          title="Negative span · click to remove"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_NEG_SPAN_AUTO) {
      // Phase 2: auto-inferred negative rendering. Same click-routing as
      // other mark types (removal via the chip row below); the dotted style
      // tells annotators this was synthesised, not hand-placed.
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="cursor-pointer rounded-sm border-b border-dotted border-rose-400 bg-rose-400/8 px-0.5 text-foreground hover:bg-rose-400/20"
          title="Auto-inferred from parser disagreement · remove from chip row below"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_NEG_KW) {
      out.push(
        <mark
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="cursor-pointer rounded-sm border-b border-dotted border-rose-600 bg-rose-500/20 px-0.5 text-foreground hover:bg-rose-500/30"
          title="Negative keyword · click to remove"
        >{chunk}</mark>,
      )
    } else if (consistent && firstOwner === OWN_PARSER) {
      const isFirstParserWord = !parserAttached.value
      if (isFirstParserWord) parserAttached.value = true
      out.push(
        <span
          key={runStart}
          ref={isFirstParserWord ? parserHighlightRef : undefined}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className={`cursor-pointer rounded-sm border-b border-dashed border-amber-500 bg-amber-400/10 px-0.5 text-foreground transition-colors hover:bg-amber-400/25 ${flashing ? "ring-2 ring-amber-400" : ""}`}
          title={`Parser extracted: ${parserHint} · click to confirm · Shift+click to flag false-positive · Shift+drag for negative span`}
        >{chunk}</span>,
      )
    } else if (consistent && firstOwner === OWN_PLAIN) {
      // v4 modifier-hold hover preview: inherits the target mark color from
      // the enclosing `group` container via `group-data-[modifier=...]`, so
      // the annotator sees what the commit will produce before releasing.
      out.push(
        <span
          key={runStart}
          onClick={(e) => { e.stopPropagation(); onWordClick(runStart, j, chunk) }}
          className="
            cursor-pointer rounded-sm px-0.5 transition-colors
            hover:bg-primary/10 hover:underline hover:decoration-primary hover:decoration-2 hover:underline-offset-4
            group-data-[modifier=anchor]:hover:bg-indigo-400/35 group-data-[modifier=anchor]:hover:decoration-indigo-600
            group-data-[modifier=keyword]:hover:bg-violet-400/35 group-data-[modifier=keyword]:hover:decoration-violet-600
            group-data-[modifier=negative]:hover:bg-rose-400/35 group-data-[modifier=negative]:hover:decoration-rose-600
          "
          title="Click/drag to mark · A: anchor · D: keyword · Shift: negative"
        >{chunk}</span>,
      )
    } else {
      out.push(<span key={runStart}>{chunk}</span>)
    }
    i = j
  }
  return out
}

function matchBadgeClass(matchType: string, verified: boolean): string {
  // Until the annotator has explicitly endorsed the parser verdict, render the
  // match-type badge in a muted style so the UI doesn't gaslight the reviewer
  // into trusting a false positive.
  if (!verified) return "bg-muted text-muted-foreground border-border/60"
  switch (matchType) {
    case "correct":
      return "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
    case "parse_error":
      return "bg-amber-500/10 text-amber-600 border-amber-500/30"
    case "mismatch":
      return "bg-rose-500/10 text-rose-600 border-rose-500/30"
    case "localized_match":
      return "bg-sky-500/10 text-sky-600 border-sky-500/30"
    default:
      return "bg-muted text-muted-foreground border-border"
  }
}

// `parserMatchesAnySpan` lives in `@/lib/span-autodetect` as of Phase 2 —
// previously duplicated here and in review.tsx.

function stringifyAnswer(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

/** Reusable chip row for any mark type (spans, anchors, keywords, negatives). */
function MarkChipRow({
  label,
  color,
  items,
  onRemove,
}: {
  label: string
  color: string
  items: { text: string; detail?: string }[]
  onRemove: (index: number) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`text-[11px] ${color}`}>{label}:</span>
      {items.map((item, i) => (
        <Button
          key={i}
          variant="outline"
          size="sm"
          onClick={() => onRemove(i)}
          className={`h-6 gap-1 px-1.5 text-[10px] font-mono ${color}`}
          title="Click to remove"
        >
          <span className="max-w-30 truncate">{item.text}</span>
          {item.detail && <span className="text-muted-foreground">[{item.detail}]</span>}
        </Button>
      ))}
    </div>
  )
}

export function ResponsePanel({
  caseData,
  spans,
  note,
  annotatorVerified,
  activeModifier,
  responseClasses,
  targetLang,
  peekTranslateOn,
  onTogglePeekTranslate,
  onAddSpan,
  onRemoveSpan,
  onChangeNote,
  onFlagFalsePositive,
  contextAnchors,
  answerKeywords,
  negativeSpans,
  negativeKeywords,
  onAddContextAnchor,
  onAddAnswerKeyword,
  onAddNegativeSpan,
  onRemoveContextAnchor,
  onRemoveAnswerKeyword,
  onRemoveNegativeSpan,
  onRemoveNegativeKeyword,
}: Props) {
  const responseRef = useRef<HTMLDivElement | null>(null)
  const parserHighlightRef = useRef<HTMLSpanElement | null>(null)
  const chunkRefs = useRef<(HTMLSpanElement | null)[]>([])
  const [flashing, setFlashing] = useState(false)

  const sameLang = useMemo(() => {
    const src = (caseData.language || "").toLowerCase()
    const tgt = (targetLang || "en").toLowerCase()
    return !!src && src === tgt
  }, [caseData.language, targetLang])

  const parserMatch = useMemo(
    () => resolveParserMatch(caseData),
    [caseData],
  )

  const charOwner = useMemo(
    () => classifyChars(
      caseData.raw_response.length, spans, parserMatch,
      contextAnchors, answerKeywords, negativeSpans, negativeKeywords,
    ),
    [caseData.raw_response, spans, parserMatch, contextAnchors, answerKeywords, negativeSpans, negativeKeywords],
  )

  // Chunking is cheap (pure string ops) but still skip it when the feature is
  // off OR the source/target languages match — both paths have zero use for
  // gutter bars.
  const chunks = useMemo(
    () => (peekTranslateOn && !sameLang ? chunkResponse(caseData.raw_response) : []),
    [peekTranslateOn, sameLang, caseData.raw_response],
  )

  // Reset scroll to top whenever the case changes. Prevents the response
  // panel opening mid-paragraph and hiding the lead.
  useEffect(() => {
    const el = responseRef.current
    if (el) el.scrollTop = 0
    setFlashing(false)
  }, [caseData.case_id])

  const handleCopyResponse = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(caseData.raw_response)
      toast.success("Response copied")
    } catch (err) {
      toast.error(`Copy failed: ${err instanceof Error ? err.message : "unknown"}`)
    }
  }, [caseData.raw_response])

  const handleJumpToParserMatch = useCallback(() => {
    const el = parserHighlightRef.current
    const container = responseRef.current
    if (!el || !container) return
    const elTop = el.offsetTop - container.offsetTop
    container.scrollTo({ top: Math.max(0, elTop - 40), behavior: "smooth" })
    setFlashing(true)
    setTimeout(() => setFlashing(false), 1400)
  }, [])

  /** v4 (Phase 1 + Phase 2): one-click word-marking with modifier-mode detection.
   *  - No modifier held → answer span (blue, auto-detected position/format).
   *    Plain-click on the parser-highlighted amber region also lands here,
   *    effectively "confirming the parser's extraction at word granularity."
   *  - A held          → context anchor (indigo).
   *  - D held          → answer keyword (violet).
   *  - Shift held      → negative span (rose) — UNLESS the click falls inside
   *    the parser-highlight region, in which case it toggles the
   *    `false_positive` response class instead (Phase 2 §3.2). Shift+drag
   *    across the parser region still commits a negative span because drag
   *    never enters this click handler — so the drag-wins-over-click rule
   *    falls out automatically.
   */
  const handleWordClick = useCallback(
    (start: number, end: number, text: string) => {
      const mark: MarkSpan = { text, char_start: start, char_end: end }
      const inParserRegion =
        parserMatch !== null && start >= parserMatch.start && end <= parserMatch.end
      if (activeModifier === "negative") {
        if (inParserRegion && onFlagFalsePositive) {
          onFlagFalsePositive()
          return
        }
        onAddNegativeSpan(mark)
        return
      }
      if (activeModifier === "anchor") {
        onAddContextAnchor(mark)
        return
      }
      if (activeModifier === "keyword") {
        onAddAnswerKeyword(mark)
        return
      }
      const full = caseData.raw_response
      onAddSpan({
        text,
        char_start: start,
        char_end: end,
        position: autoPosition(start, full.length),
        format: autoFormat(full, start, end),
        confidence: "high",
      })
    },
    [
      activeModifier,
      caseData.raw_response,
      parserMatch,
      onAddSpan,
      onAddContextAnchor,
      onAddAnswerKeyword,
      onAddNegativeSpan,
      onFlagFalsePositive,
    ],
  )

  // ── Drag-select handling ───────────────────────────────────────────────
  // v4 (Phase 1): commit IMMEDIATELY on mouse-up. No pending/dock step.
  // Mark type driven by `activeModifier` at commit time (release-wins: if the
  // user releases the modifier before mouse-up, the span commits as plain
  // answer — intended behaviour).
  const handleMouseUp = useCallback(
    () => {
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed) return
      const container = responseRef.current
      if (!container) return
      const selected = sel.toString()
      if (!selected.trim()) return

      const anchorNode = sel.anchorNode
      const focusNode = sel.focusNode
      if (!anchorNode || !focusNode) return
      if (!container.contains(anchorNode) || !container.contains(focusNode)) return

      const full = caseData.raw_response
      const range = sel.getRangeAt(0)

      // Walk from the container to the anchor-range start to compute char offset.
      const pre = range.cloneRange()
      pre.selectNodeContents(container)
      pre.setEnd(range.startContainer, range.startOffset)
      const startHint = pre.toString().length

      let char_start = full.indexOf(selected, Math.max(0, startHint - 3))
      if (char_start < 0) char_start = full.indexOf(selected)
      if (char_start < 0) return
      const char_end = char_start + selected.length

      if (activeModifier === "negative") {
        onAddNegativeSpan({ text: selected, char_start, char_end })
      } else if (activeModifier === "anchor") {
        onAddContextAnchor({ text: selected, char_start, char_end })
      } else if (activeModifier === "keyword") {
        onAddAnswerKeyword({ text: selected, char_start, char_end })
      } else {
        onAddSpan({
          text: selected,
          char_start,
          char_end,
          position: autoPosition(char_start, full.length),
          format: autoFormat(full, char_start, char_end),
          confidence: "high",
        })
      }
      sel.removeAllRanges()
    },
    [
      activeModifier,
      caseData.raw_response,
      onAddSpan,
      onAddContextAnchor,
      onAddAnswerKeyword,
      onAddNegativeSpan,
    ],
  )

  return (
    <div
      className="group flex h-full flex-col gap-3 overflow-hidden transition-colors data-[modifier=anchor]:bg-indigo-500/15 data-[modifier=keyword]:bg-violet-500/15 data-[modifier=negative]:bg-rose-500/15 data-[modifier=anchor]:ring-2 data-[modifier=keyword]:ring-2 data-[modifier=negative]:ring-2 data-[modifier=anchor]:ring-indigo-500/40 data-[modifier=keyword]:ring-violet-500/40 data-[modifier=negative]:ring-rose-500/40 data-[modifier=anchor]:ring-inset data-[modifier=keyword]:ring-inset data-[modifier=negative]:ring-inset"
      data-modifier={activeModifier ?? "none"}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="text-[10px]">
          Parser: <span className="ml-1 font-mono">{stringifyAnswer(caseData.parsed_answer)}</span>
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          Expected: <span className="ml-1 font-mono">{stringifyAnswer(caseData.expected)}</span>
        </Badge>
        {responseClasses.includes("false_positive") ? (
          <Badge className="bg-fuchsia-500/15 text-[10px] text-fuchsia-700 border-fuchsia-500/40 dark:text-fuchsia-400">
            <span className="line-through opacity-70">{caseData.parser_match_type}</span>
            <span className="ml-1">→ false-positive</span>
          </Badge>
        ) : (
          <Badge className={`text-[10px] ${matchBadgeClass(caseData.parser_match_type, annotatorVerified)}`}>
            {caseData.parser_match_type}
            {!annotatorVerified && " · unverified"}
          </Badge>
        )}
        <div className="ml-auto flex items-center gap-1">
          {caseData.raw_response && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopyResponse}
              className="h-6 gap-1 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
              title="Copy raw response to clipboard"
            >
              <Copy className="h-3 w-3" />
              Copy
            </Button>
          )}
          {!sameLang && caseData.raw_response && (
            <Button
              variant={peekTranslateOn ? "secondary" : "ghost"}
              size="sm"
              onClick={onTogglePeekTranslate}
              className={`h-6 gap-1 px-1.5 text-[11px] ${
                peekTranslateOn ? "text-sky-700 dark:text-sky-400" : "text-muted-foreground hover:text-foreground"
              }`}
              title={
                peekTranslateOn
                  ? "Hide peek-translate bars"
                  : `Peek-translate to ${(targetLang || "en").toUpperCase()} · hover gutter bars`
              }
              aria-pressed={peekTranslateOn}
            >
              <Languages className="h-3 w-3" />
              Translate
            </Button>
          )}
          {parserMatch && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleJumpToParserMatch}
              className="h-6 gap-1 px-2 text-[11px]"
              title="Scroll to the parser-extracted token"
            >
              <Crosshair className="h-3 w-3" />
              Jump to parser match
            </Button>
          )}
        </div>
      </div>

      {/* Parser-disagreement callout: persistent, one-click flag to `false_positive`. */}
      {(() => {
        const hasSpans = spans.length > 0
        const parserStr = typeof caseData.parsed_answer === "string" ? caseData.parsed_answer.trim() : ""
        const disagrees = hasSpans && parserStr.length > 0 && !parserMatchesAnySpan(caseData.parsed_answer, spans)
        const flagged = responseClasses.includes("false_positive")

        if (flagged) {
          return (
            <div className="flex items-center gap-2 rounded-md border border-fuchsia-500/40 bg-fuchsia-500/10 px-3 py-1.5 text-[11px] text-fuchsia-700 dark:text-fuchsia-300">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span>
                Parser false-positive confirmed —{" "}
                <span className="font-mono">{stringifyAnswer(caseData.parsed_answer)}</span> was a distractor.
              </span>
            </div>
          )
        }
        if (disagrees) {
          return (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-[11px] text-rose-700 dark:text-rose-300">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>
                Parser extracted{" "}
                <span className="font-mono font-semibold">
                  “{stringifyAnswer(caseData.parsed_answer)}”
                </span>{" "}
                — your span is different.
              </span>
              {onFlagFalsePositive && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onFlagFalsePositive}
                  className="ml-auto h-6 gap-1 border-rose-500/50 bg-background px-2 text-[11px] text-rose-700 hover:bg-rose-500/20 dark:text-rose-300"
                >
                  Flag as false-positive
                </Button>
              )}
            </div>
          )
        }
        return null
      })()}

      <div className="relative min-h-0 flex-1">
        {/* Top scroll shadow */}
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-4 bg-linear-to-b from-background to-transparent rounded-t-md" />
        {/* Bottom scroll shadow */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-4 bg-linear-to-t from-background to-transparent rounded-b-md" />

        <div
          ref={responseRef}
          onMouseUp={handleMouseUp}
          onMouseDown={(e) => {
            // v4: Shift is still a native browser "extend-selection" modifier
            // even though we no longer use event.shiftKey for mark-type
            // routing. Preventing default on Shift-down keeps single-click
            // Shift-as-negative functional instead of extending the previous
            // selection. Also suppress Alt/Option on macOS — some inputs
            // interpret it as a special-char modifier that eats the click.
            if (e.shiftKey || e.altKey) e.preventDefault()
          }}
          className={`relative h-full select-text overflow-y-auto whitespace-pre-wrap rounded-md border border-border/60 bg-background font-mono text-sm leading-relaxed ${
            chunks.length > 0 ? "py-4 pl-8 pr-4" : "p-4"
          }`}
        >
          {caseData.raw_response ? (
            renderWords({
              text: caseData.raw_response,
              owner: charOwner,
              parserHighlightRef,
              flashing,
              parserHint: stringifyAnswer(caseData.parsed_answer),
              onWordClick: handleWordClick,
              onRemoveSpan,
              chunks: chunks.length > 0 ? chunks : undefined,
              chunkRefsOut: chunks.length > 0 ? chunkRefs : undefined,
            })
          ) : (
            <span className="text-muted-foreground">(empty response)</span>
          )}
          {chunks.length > 0 && (
            <ChunkGutter
              chunks={chunks}
              containerRef={responseRef}
              chunkElementRefs={chunkRefs}
              sourceLang={caseData.language}
              targetLang={targetLang}
            />
          )}
        </div>
      </div>

      {/* Mark chip rows — one per non-empty mark type */}
      {spans.length > 0 && (
        <MarkChipRow
          label="Answer spans"
          color="text-primary border-primary/40"
          items={spans.map((s) => ({ text: s.text, detail: `${s.position}/${s.format}` }))}
          onRemove={onRemoveSpan}
        />
      )}
      {contextAnchors.length > 0 && (
        <MarkChipRow
          label="Anchors"
          color="text-indigo-600 border-indigo-400/40 dark:text-indigo-400"
          items={contextAnchors.map((s) => ({ text: s.text }))}
          onRemove={onRemoveContextAnchor}
        />
      )}
      {answerKeywords.length > 0 && (
        <MarkChipRow
          label="Keywords"
          color="text-violet-600 border-violet-400/40 dark:text-violet-400"
          items={answerKeywords.map((s) => ({ text: s.text }))}
          onRemove={onRemoveAnswerKeyword}
        />
      )}
      {negativeSpans.length > 0 && (
        <MarkChipRow
          label="Negative spans"
          color="text-rose-600 border-rose-400/40 dark:text-rose-400"
          items={negativeSpans.map((s) => ({ text: s.text }))}
          onRemove={onRemoveNegativeSpan}
        />
      )}
      {negativeKeywords.length > 0 && (
        <MarkChipRow
          label="Neg. keywords"
          color="text-rose-700 border-rose-500/40 dark:text-rose-500"
          items={negativeKeywords.map((s) => ({ text: s.text }))}
          onRemove={onRemoveNegativeKeyword}
        />
      )}

      <NotePanel note={note} onChangeNote={onChangeNote} />
    </div>
  )
}
