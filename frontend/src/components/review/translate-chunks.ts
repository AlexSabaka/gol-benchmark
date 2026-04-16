// Chunking helper for the peek-translate overlay.
//
// The translator API chokes on long model responses (the response shows as
// `[DOT][DOT]`-riddled garbage once the provider truncates). Splitting the
// response into paragraph-sized pieces (~500 chars) keeps each request well
// under provider limits and lets the UI translate on-demand per chunk.
//
// Offsets are preserved into the original string so the annotation layer's
// char_start / char_end math stays identical — chunking never touches span
// data, only the overlay.

export interface TranslateChunk {
  /** Inclusive start char offset into the source string. */
  start: number
  /** Exclusive end char offset (Python-style). */
  end: number
  /** Slice of the original string. Matches `source.slice(start, end)` exactly. */
  text: string
}

const DEFAULT_MAX_CHARS = 500
const SENTENCE_BOUNDARY = /(?<=[.!?。！？])\s+|\n+/g

/**
 * Split `text` into paragraph-sized chunks suitable for per-chunk translation.
 *
 * Strategy:
 *   1. Paragraphs — split on `\n{2,}` (blank-line separators).
 *   2. For any paragraph > maxChars, further split on sentence boundaries
 *      (`.!?` / CJK punctuation / internal newlines) and greedily re-group
 *      into ≤ maxChars sub-chunks so we don't emit 20-char orphans.
 *   3. If a single "sentence" still exceeds maxChars (no punctuation in a
 *      very long run), hard-split at maxChars as a last resort.
 *
 * Empty/whitespace-only input → empty list (nothing to translate).
 */
export function chunkResponse(text: string, maxChars = DEFAULT_MAX_CHARS): TranslateChunk[] {
  if (!text) return []
  const out: TranslateChunk[] = []

  // Paragraph-level split. `\n{2,}` is the separator; we keep char offsets by
  // scanning rather than String.split (which loses indices across repeats).
  const paragraphBreak = /\n{2,}/g
  let paraStart = 0
  const paragraphs: Array<{ start: number; end: number }> = []
  let m: RegExpExecArray | null
  while ((m = paragraphBreak.exec(text)) !== null) {
    paragraphs.push({ start: paraStart, end: m.index })
    paraStart = m.index + m[0].length
  }
  paragraphs.push({ start: paraStart, end: text.length })

  for (const p of paragraphs) {
    const slice = text.slice(p.start, p.end)
    if (!slice.trim()) continue

    if (slice.length <= maxChars) {
      out.push({ start: p.start, end: p.end, text: slice })
      continue
    }

    // Paragraph too long — sentence-split and greedy-regroup.
    const sentences = collectSentences(slice, p.start)
    let acc: TranslateChunk | null = null
    for (const s of sentences) {
      if (!acc) {
        acc = { ...s }
        continue
      }
      // Would appending overflow? If so, flush the accumulator.
      if (s.end - acc.start > maxChars) {
        out.push(acc)
        acc = { ...s }
      } else {
        acc = { start: acc.start, end: s.end, text: text.slice(acc.start, s.end) }
      }
    }
    if (acc) out.push(acc)
  }

  // Safety: hard-split any chunk that's STILL too long (pathological input —
  // a single sentence with no punctuation longer than maxChars). Preserves
  // translation usability; visual gutter gets one extra bar per split.
  const hardSplit: TranslateChunk[] = []
  for (const c of out) {
    if (c.text.length <= maxChars * 1.5) {
      hardSplit.push(c)
      continue
    }
    for (let off = 0; off < c.text.length; off += maxChars) {
      const sub = c.text.slice(off, off + maxChars)
      hardSplit.push({
        start: c.start + off,
        end: c.start + off + sub.length,
        text: sub,
      })
    }
  }
  return hardSplit
}

/** Sentence-level split of `slice` (with offsets rebased to `baseOffset`). */
function collectSentences(slice: string, baseOffset: number): TranslateChunk[] {
  const out: TranslateChunk[] = []
  let cursor = 0
  SENTENCE_BOUNDARY.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = SENTENCE_BOUNDARY.exec(slice)) !== null) {
    const boundaryEnd = m.index + m[0].length
    const sentence = slice.slice(cursor, boundaryEnd)
    if (sentence.trim()) {
      out.push({
        start: baseOffset + cursor,
        end: baseOffset + boundaryEnd,
        text: sentence,
      })
    }
    cursor = boundaryEnd
  }
  if (cursor < slice.length) {
    const tail = slice.slice(cursor)
    if (tail.trim()) {
      out.push({
        start: baseOffset + cursor,
        end: baseOffset + slice.length,
        text: tail,
      })
    }
  }
  return out
}
