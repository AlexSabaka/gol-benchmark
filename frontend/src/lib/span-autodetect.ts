import type { AnnotationSpan, SpanFormat, SpanPosition } from "@/types"

/**
 * Auto-detect annotation position from char offset in the response string.
 * Split equally: first third → start, middle third → middle, last third → end.
 */
export function autoPosition(char_start: number, total_length: number): SpanPosition {
  if (total_length <= 0) return "middle"
  const ratio = char_start / total_length
  if (ratio < 0.33) return "start"
  if (ratio < 0.66) return "middle"
  return "end"
}

/**
 * Auto-detect markdown format by probing a small window around the selection.
 * Handles bold / italic / strikethrough / boxed / header / labelled-answer
 * and multilingual label variants (English, Spanish, French, German, Chinese,
 * Ukrainian). Used by both click-to-mark and drag-select-to-mark paths since
 * the user no longer gets a chance to correct via the dock (Phase 1 removal).
 */
export function autoFormat(response: string, char_start: number, char_end: number): SpanFormat {
  const before = response.slice(Math.max(0, char_start - 16), char_start)
  const after = response.slice(char_end, char_end + 16)
  const inside = response.slice(char_start, char_end)
  const window = `${before}${inside}${after}`.toLowerCase()

  if (/\\boxed\s*\{/.test(window) || /\\boxed/.test(before)) return "boxed"
  if (before.endsWith("**") || after.startsWith("**")) return "bold"
  if (before.endsWith("~~") || after.startsWith("~~")) return "strikethrough"
  if (/(^|[^*])\*$/.test(before) && /^\*(?!\*)/.test(after)) return "italic"
  if (/(^|[^\w])_$/.test(before) && /^_(?!\w)/.test(after)) return "italic"
  const lineStart = before.lastIndexOf("\n")
  const linePrefix = lineStart >= 0 ? before.slice(lineStart + 1) : before
  if (/^#{1,6}\s/.test(linePrefix)) return "header"
  if (
    /\b(answer|result|respuesta|resultado|antwort|réponse|答案|відповідь|recommendation|recomendación|recommandation|empfehlung|рекомендація|conclusion|conclusión|висновок|bottom line|in short|in summary|тldr|tl;dr)\s*[:：]\s*\**$/i.test(
      before,
    )
  ) {
    return "label"
  }
  return "plain"
}

/**
 * Does the parser's extracted text (as a string) overlap any of the given
 * spans? Phase 2: consolidated from two duplicate copies that lived in
 * `review.tsx` and `response-panel.tsx`. Used by:
 *   - `handleAddSpan` — fire the "parser extracted X" toast on first
 *     contradicting answer span.
 *   - `ResponsePanel` disagreement callout — persistent rose banner when
 *     the user's span doesn't match what the parser pulled.
 *   - Phase 2 auto-inference predicate — decide whether to synthesise a
 *     negative span at the parser region.
 *
 * Threshold is bidirectional substring containment (case-insensitive,
 * whitespace-trimmed): either the span text contains the parser token or
 * vice-versa counts as a match. Matches loose models that emphasise the
 * same word with extra words around it.
 */
export function parserMatchesAnySpan(
  parsed: unknown,
  spans: AnnotationSpan[],
): boolean {
  if (typeof parsed !== "string" || !parsed.trim()) return false
  if (spans.length === 0) return false
  const needle = parsed.trim().toLowerCase()
  return spans.some((s) => {
    const hay = s.text.trim().toLowerCase()
    return hay.includes(needle) || needle.includes(hay)
  })
}
