// ── Human Review / Annotation types ──

export type ResponseClass =
  | "hedge"
  | "gibberish"
  | "refusal"
  | "language_error"
  | "verbose_correct"
  | "parser_ok"
  | "parser_false_positive"

export type SpanPosition = "start" | "middle" | "end"
export type SpanFormat =
  | "bold"
  | "italic"
  | "strikethrough"
  | "header"
  | "boxed"
  | "label"
  | "plain"
  | "other"

export interface AnnotationSpan {
  text: string
  char_start: number
  char_end: number
  position: SpanPosition
  format: SpanFormat
  confidence?: "high" | "medium" | "low"
}

export interface Annotation {
  spans: AnnotationSpan[]
  response_class: ResponseClass | null
  annotator_note: string
  timestamp?: string
}

export interface ReviewCase {
  result_file_id: string
  case_id: string
  task_type: string
  language: string
  user_style?: string | null
  system_style?: string | null
  user_prompt: string
  system_prompt: string
  raw_response: string
  parsed_answer: unknown
  expected: unknown
  parser_match_type: string
  parser_correct: boolean
  existing_annotation?: Annotation
}

export interface ReviewCasesResponse {
  plugin: string
  plugins: string[]
  mixed_plugins: boolean
  total: number
  cases: ReviewCase[]
}

export interface AnnotationFile {
  meta: {
    result_file?: string
    plugin?: string
    annotated_by?: string
    created_at?: string
    updated_at?: string
    annotated_count?: number
    skipped_count?: number
  }
  cases: Record<string, {
    case_id: string
    response_length: number
    parser_match_type: string
    parser_extracted: unknown
    expected: unknown
    annotation: Annotation
  }>
}

// ── Improvement report ──

export interface ReportSummary {
  total_cases: number
  annotated: number
  skipped: number
  parser_was_correct: number
  parser_false_positive?: number
  parser_missed_extractable: number
  true_unparseable: number
  false_positive_rate?: number
  // v2.3 — breakdown of `parser_missed_extractable`
  parser_missed_aligned?: number       // parser extracted correctly but annotator used spans-only
  parser_missed_misaligned?: number    // true parser failure — extracted wrong token
  parser_missed_no_output?: number     // parse_error with empty extracted value
}

export interface SpanExample {
  text: string
  before: string
  after: string
  sentence?: string           // v2.1 — full containing sentence
  parser_extracted?: unknown  // v2.2 — what the parser said (for diff)
  parser_match_type?: string  // v2.2 — correct / mismatch / naive_trap / …
  case_id: string
  language: string
}

export interface SpanRegexCandidate {
  pattern: string
  kind: "anchor" | "disjunction"
  support: number
  anchor_words?: string[] | null
}

// v2.1 — per-group structural signal ratios
export interface StructuralRatios {
  line_start: number
  paragraph_start: number
  list_marker: number
  label_colon: number
  bold_wrap: number
  quote_wrap: number
  answer_label_match: number
}

// v2.1 → v2.4 — per-group prefix anchor (trailing N-gram of `before`)
export interface PrefixAnchor {
  phrase: string
  count: number
  ratio: number
  /** v2.4 — classification used for sorting + merging */
  type?: "label" | "format" | "phrase"
}

// v2.1 → v2.3 — regex candidate scored against every example in the group
export interface RegexCaptureSample {
  case_id: string
  captured: string
  annotated: string
  exact_match: boolean
  aligned: boolean
}

export interface RegexTestResult {
  pattern: string
  kind:
    | "anchor"                     // v1: span-text anchor (legacy)
    | "disjunction"                // v1: span-text disjunction (legacy)
    | "context_anchor"             // v2.2: `before` prefix + format capture
    | "format_only"                // v2.2: bare format wrapper (safety net)
    | "text_pattern"               // v2.2: fallback — legacy span-text LCP
    | "merged_label_disjunction"   // v2.4: `(?:atom1|atom2):\s*(...)` across labels
  support: number
  anchor_words?: string[] | null
  anchor_phrase?: string | null    // v2.2 — human-readable locate string
  /** v2.4 — for merged_label_disjunction, the distinct label atoms combined */
  participating_atoms?: string[]
  match_rate: number                // -1 means regex failed to compile
  matched_count: number
  total: number
  // v2.3 — capture quality (match_rate alone can hide a useless regex)
  capture_exact_rate?: number       // fraction where capture == annotated span
  capture_contains_rate?: number    // fraction where capture aligns with span
  sample_captures?: RegexCaptureSample[]
}

// v2.3 — top-level parser-vs-annotator agreement metric
export interface ParserSpanAlignmentSample {
  case_id: string
  parser_extracted: unknown
  annotated_spans: string[]
  parser_match_type: string
}
export interface ParserSpanAlignment {
  total_comparable: number
  aligned_with_parser: number
  misaligned_with_parser: number
  no_parser_output: number
  alignment_ratio: number
  sample_misaligned: ParserSpanAlignmentSample[]
}

// v2.3 — data quality diagnostics
export interface DataQualityWarning {
  code: string
  detail: string
}
export interface DataQuality {
  warnings: DataQualityWarning[]
  suppressed_sections: string[]
}

// v2.2 — per-group label-word counts (break down answer_label_match_ratio)
export interface LabelTaxonomyRow {
  label: string
  count: number
}

// v2.4 — raw-text variants per normalized model-answer bucket
export interface ModelAnswerVariantRow {
  text: string
  count: number
}
export interface ModelAnswerBucket {
  total: number
  variants: ModelAnswerVariantRow[]
}

export interface SpanGroup {
  position: SpanPosition
  format: SpanFormat
  count: number
  languages?: string[]
  /**
   * v2: now an array of objects with surrounding context. Backwards-compat
   * legacy reports may still pass strings — UI should narrow at render time.
   */
  example_spans: SpanExample[] | string[]
  suggested_strategy: string
  /**
   * v2: weighted regex candidates with `kind` + `support`. Legacy reports may
   * pass plain strings.
   */
  suggested_regex: SpanRegexCandidate[] | string[]
  confidence?: "high" | "medium" | "low"
  missed_by_existing: boolean

  // v2.1 additions — all optional so v1/v2 payloads still parse cleanly.
  structural_ratios?: StructuralRatios
  prefix_anchors?: PrefixAnchor[]
  regex_test?: RegexTestResult[]

  // v2.2 additions
  label_taxonomy?: LabelTaxonomyRow[]
}

export interface OrderingHint {
  observation: string
  recommendation: string
}

// ── v2 sections ──

export interface AxisBucket {
  total: number
  parser_was_correct: number
  parser_missed_extractable: number
  parser_false_positive: number
  true_unparseable: number
  verbose_correct: number
  miss_rate: number
}

export interface StrategyBucket {
  total_fired: number
  parser_ok: number
  parser_false_positive: number
  recoverable_miss: number
  false_positive_rate: number
}

export interface ExpectedDistractorPair {
  expected: string
  parser_extracted: string
  count: number
  example_case_ids: string[]
}

export interface AnswerWhenMissed {
  by_expected: Record<string, number>
  by_extracted_distractor: Record<string, number>
  expected_distractor_pairs: ExpectedDistractorPair[]
}

export interface AnchorFrequencyRow {
  anchor: string
  count: number
  languages: string[]
  spans_seen_in: string[]
}

export interface AnnotatorNote {
  case_id: string
  language: string
  verdict: string
  note: string
}

export interface ImprovementReport {
  format_version?: string
  source_files: string[]
  summary: ReportSummary
  false_positive_rate?: number
  confusion_matrix?: Record<string, Record<string, number>>
  language_breakdown?: Record<string, AxisBucket>
  config_breakdown?: Record<string, AxisBucket>
  user_style_breakdown?: Record<string, AxisBucket>
  strategy_breakdown?: Record<string, StrategyBucket>
  answer_when_missed?: AnswerWhenMissed
  // v2.2 — what the *model* answered (normalized across markdown wrappers).
  model_answer_distribution?: Record<string, number>
  // v2.4 — raw-text variants per normalized bucket.
  model_answer_variants?: Record<string, ModelAnswerBucket>
  // v2.3 — top-level parser-vs-annotator alignment + data quality diagnostics
  parser_span_alignment?: ParserSpanAlignment
  data_quality?: DataQuality
  span_groups: SpanGroup[]
  anchor_frequency?: AnchorFrequencyRow[]
  ordering_hints: OrderingHint[]
  response_classes: Record<string, number>
  annotator_notes?: AnnotatorNote[]
}

// ── Translation ──

export interface TranslateRequest {
  text: string
  source_lang?: string | null
  target_lang?: string
}

export interface TranslateResponse {
  translated: string
  provider: string
  source_lang: string
  target_lang: string
}

export interface DeleteAnnotationsResponse {
  status: string
  deleted: boolean
  filename: string
}
