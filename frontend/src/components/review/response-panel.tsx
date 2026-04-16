import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { AlertTriangle, CheckCircle2, Copy, Crosshair, Languages } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AnnotationSpan, ResponseClass, ReviewCase } from "@/types"
import { AnnotationDock, autoFormat, autoPosition, type PendingSpan } from "./annotation-dock"
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
  pending: PendingSpan | null
  /** Current classification verdict (if any) — used to compute the
   * disagreement alert + strike-through parser badge. */
  responseClass: ResponseClass | null
  /** Session-wide target language for the Translate button. */
  targetLang: string
  /** Session-wide peek-translate toggle (chunked gutter + hover popover). */
  peekTranslateOn: boolean
  onTogglePeekTranslate: () => void
  onSetPending: (next: PendingSpan | null) => void
  onCommitPending: () => void
  /** Immediate add (no pending / dock). Used by word-level click-to-mark. */
  onAddSpan: (span: AnnotationSpan) => void
  onRemoveSpan: (index: number) => void
  onChangeNote: (next: string) => void
  onChangePosition: (position: PendingSpan["position"]) => void
  onChangeFormat: (format: PendingSpan["format"]) => void
  onFlagFalsePositive?: () => void
  onRegisterCommit?: (commit: (() => void) | null) => void
}

/** Find the first occurrence of parser-extracted text inside the response. */
function findParserMatch(
  response: string,
  parsed: unknown,
): { start: number; end: number } | null {
  if (typeof parsed !== "string" || !parsed) return null
  const needle = parsed.trim()
  if (!needle) return null
  const idx = response.toLowerCase().indexOf(needle.toLowerCase())
  if (idx < 0) return null
  return { start: idx, end: idx + needle.length }
}

// Owner tag per character position. Spans take precedence over parser-match,
// and both take precedence over plain. Negative sentinel values:
//   -2  → plain text (no decoration)
//   -1  → parser-match ghost
//   >=0 → annotation span (value is the span index)
const OWN_PLAIN = -2
const OWN_PARSER = -1

/** Build a per-character owner map so the word-level renderer can decorate
 *  each token without re-scanning the whole span list. */
function classifyChars(
  len: number,
  spans: AnnotationSpan[],
  parserMatch: { start: number; end: number } | null,
): Int32Array {
  const owner = new Int32Array(len).fill(OWN_PLAIN)
  if (parserMatch) {
    for (let i = parserMatch.start; i < parserMatch.end && i < len; i++) {
      owner[i] = OWN_PARSER
    }
  }
  // Spans win over parser-match (they encode verified annotator intent).
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

    if (!runStartsWord) {
      if (consistent && firstOwner >= 0) {
        out.push(
          <span key={runStart} className="border-b-2 border-primary bg-primary/15">
            {chunk}
          </span>,
        )
      } else if (consistent && firstOwner === OWN_PARSER) {
        out.push(
          <span key={runStart} className="border-b border-dashed border-amber-500 bg-amber-400/10">
            {chunk}
          </span>,
        )
      } else {
        out.push(<span key={runStart}>{chunk}</span>)
      }
      i = j
      continue
    }

    if (consistent && firstOwner >= 0) {
      const spanIdx = firstOwner
      out.push(
        <mark
          key={runStart}
          onClick={(e) => {
            e.stopPropagation()
            onRemoveSpan(spanIdx)
          }}
          className="cursor-pointer rounded-sm border-b-2 border-primary bg-primary/15 px-0.5 text-foreground hover:bg-primary/25"
          title="Click to remove annotation"
        >
          {chunk}
        </mark>,
      )
    } else if (consistent && firstOwner === OWN_PARSER) {
      const isFirstParserWord = !parserAttached.value
      if (isFirstParserWord) parserAttached.value = true
      out.push(
        <span
          key={runStart}
          ref={isFirstParserWord ? parserHighlightRef : undefined}
          onClick={(e) => {
            e.stopPropagation()
            onWordClick(runStart, j, chunk)
          }}
          className={`cursor-pointer rounded-sm border-b border-dashed border-amber-500 bg-amber-400/10 px-0.5 text-foreground transition-colors hover:bg-amber-400/25 ${flashing ? "ring-2 ring-amber-400" : ""}`}
          title={`Parser extracted: ${parserHint} · click to mark this word as the answer`}
        >
          {chunk}
        </span>,
      )
    } else if (consistent && firstOwner === OWN_PLAIN) {
      out.push(
        <span
          key={runStart}
          onClick={(e) => {
            e.stopPropagation()
            onWordClick(runStart, j, chunk)
          }}
          className="cursor-pointer rounded-sm px-0.5 transition-colors hover:bg-primary/10 hover:underline hover:decoration-primary hover:decoration-2 hover:underline-offset-4"
          title="Click to mark as answer (or drag-select for a phrase)"
        >
          {chunk}
        </span>,
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

/** Does the parser's extracted text (as a string) overlap *any* span? */
function parserMatchesAnySpan(parsed: unknown, spans: AnnotationSpan[]): boolean {
  if (typeof parsed !== "string" || !parsed.trim()) return false
  if (spans.length === 0) return false
  const needle = parsed.trim().toLowerCase()
  return spans.some((s) => {
    const hay = s.text.trim().toLowerCase()
    return hay.includes(needle) || needle.includes(hay)
  })
}

function stringifyAnswer(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "string") return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export function ResponsePanel({
  caseData,
  spans,
  note,
  annotatorVerified,
  pending,
  responseClass,
  targetLang,
  peekTranslateOn,
  onTogglePeekTranslate,
  onSetPending,
  onCommitPending,
  onAddSpan,
  onRemoveSpan,
  onChangeNote,
  onChangePosition,
  onChangeFormat,
  onFlagFalsePositive,
  onRegisterCommit,
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
    () => findParserMatch(caseData.raw_response, caseData.parsed_answer),
    [caseData.raw_response, caseData.parsed_answer],
  )

  const charOwner = useMemo(
    () => classifyChars(caseData.raw_response.length, spans, parserMatch),
    [caseData.raw_response, spans, parserMatch],
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

  /** One-click word-marking: commit the clicked word as an answer span
   *  immediately, without routing through the pending / dock flow. The dock is
   *  still used for drag-selected multi-word spans. */
  const handleWordClick = useCallback(
    (start: number, end: number, text: string) => {
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
    [caseData.raw_response, onAddSpan],
  )

  // ── Selection handling ────────────────────────────────────────────────
  const handleMouseUp = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    const container = responseRef.current
    if (!container) return
    const selected = sel.toString()
    if (!selected.trim()) return

    const anchor = sel.anchorNode
    const focus = sel.focusNode
    if (!anchor || !focus) return
    if (!container.contains(anchor) || !container.contains(focus)) return

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

    onSetPending({
      text: selected,
      char_start,
      char_end,
      position: autoPosition(char_start, full.length),
      format: autoFormat(full, char_start, char_end),
    })
  }, [caseData.raw_response, onSetPending])

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="text-[10px]">
          Parser: <span className="ml-1 font-mono">{stringifyAnswer(caseData.parsed_answer)}</span>
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          Expected: <span className="ml-1 font-mono">{stringifyAnswer(caseData.expected)}</span>
        </Badge>
        {responseClass === "parser_false_positive" ? (
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

      {/* Parser-disagreement callout: persistent, one-click flag to `parser_false_positive`. */}
      {(() => {
        const hasSpans = spans.length > 0
        const parserStr = typeof caseData.parsed_answer === "string" ? caseData.parsed_answer.trim() : ""
        const disagrees = hasSpans && parserStr.length > 0 && !parserMatchesAnySpan(caseData.parsed_answer, spans)
        const flagged = responseClass === "parser_false_positive"

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

      {spans.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">Answer spans:</span>
          {spans.map((s, i) => (
            <Button
              key={i}
              variant="outline"
              size="sm"
              onClick={() => onRemoveSpan(i)}
              className="h-6 gap-1 px-1.5 text-[10px] font-mono"
              title="Click to remove"
            >
              <span className="max-w-30 truncate">{s.text}</span>
              <span className="text-muted-foreground">[{s.position}/{s.format}]</span>
            </Button>
          ))}
        </div>
      )}

      <AnnotationDock
        pending={pending}
        note={note}
        onCommit={onCommitPending}
        onDismiss={() => {
          onSetPending(null)
          window.getSelection()?.removeAllRanges()
        }}
        onChangePosition={onChangePosition}
        onChangeFormat={onChangeFormat}
        onChangeNote={onChangeNote}
        onRegisterCommit={onRegisterCommit}
      />
    </div>
  )
}
