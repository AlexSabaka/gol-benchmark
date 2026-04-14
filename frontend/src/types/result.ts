// ── Result types ──

export interface ResultSummary {
  filename: string
  path: string
  size_bytes: number
  model_name: string
  provider: string
  accuracy: number
  correct: number
  total_tests: number
  parse_error_rate: number
  duration_seconds: number
  total_tokens: number
  testset_name: string
  run_group_id?: string | null
  matrix_batch_id?: string | null
  matrix_cell_id?: string | null
  matrix_label?: string | null
  matrix_plugin?: string | null
  matrix_axes?: Record<string, unknown> | null
  task_types: string[]
  languages: string[]
  user_styles: string[]
  system_styles: string[]
  created: string
  error?: string
}

export interface ResultDetail {
  filename: string
  metadata: Record<string, unknown>
  model_info: Record<string, unknown>
  testset_metadata: Record<string, unknown>
  execution_info: Record<string, unknown>
  summary_statistics: Record<string, unknown>
  results_count: number
  results: ResultEntry[]
}

export interface ResultEntry {
  test_id: string
  status: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  evaluation: Record<string, unknown>
  tokens: Record<string, unknown>
  duration: number
}

export interface AnalyzeRequest {
  result_filenames: string[]
  comparison?: boolean
}

export interface DimensionBucket {
  total: number
  correct: number
  accuracy: number
}

export interface AnalyzeResponse {
  status: string
  model_count: number
  models: Record<string, ModelAnalysis>
  summaries: unknown[]
  dimension_breakdowns?: {
    language: Record<string, DimensionBucket>
    user_style: Record<string, DimensionBucket>
    system_style: Record<string, DimensionBucket>
  }
}

export interface ModelAnalysis {
  accuracy: number
  total_tests: number
  correct: number
  parse_error_rate: number
  duration: number
  task_breakdown: Record<string, { accuracy: number; total: number }>
}

export interface ReportInfo {
  filename: string
  size_bytes: number
  created: string
}

export interface GenerateReportResponse {
  status: string
  report_path: string
  filename: string
  viz_warning?: string
}

export interface ReanalyzeResponse {
  status: string
  filename: string
  total_results: number
  changes: number
  new_accuracy: number
  old_accuracy: number
}

// ── Chart types ──

export interface HeatmapCell {
  model: string
  task: string
  accuracy: number
  total: number
  /** Raw provider tags that were merged into this canonical model (for tooltip disclosure). */
  aliases?: string[]
}

export interface ScatterPoint {
  model: string
  paramCount: number | null
  accuracy: number
  /** Raw provider tags that were merged into this canonical model (for tooltip disclosure). */
  aliases?: string[]
}

// ── Judge types ──

export interface JudgeRequest {
  result_filenames: string[]
  provider: string
  model: string
  api_base?: string
  api_key?: string
  ollama_host?: string
  system_prompt?: string
  user_prompt_template?: string
  temperature?: number
  max_tokens?: number
  only_incorrect?: boolean
}

export interface JudgeSubmitResponse {
  status: string
  job_id: string
  model: string
}

export interface JudgeSummary {
  filename: string
  judge_model: string
  judge_provider: string
  total_judged: number
  true_incorrect: number
  false_negative: number
  parser_failure: number
  source_results: string[]
  created: string
  duration_seconds: number
}

export interface JudgmentEntry {
  source_file: string
  test_id: string
  model: string
  verdict: string
  parser_issue: string | null
  confidence: string
  notes: string
  user_prompt: string
  raw_response: string
  parsed_answer: string
  expected_answer: string
  language?: string
  task_type?: string
  user_style?: string
  system_style?: string
  parse_strategy?: string
}

export interface JudgeResult {
  format_version: string
  metadata: Record<string, unknown>
  source_results: string[]
  summary: {
    total_judged: number
    true_incorrect: number
    false_negative: number
    parser_failure: number
    parser_issues: Record<string, number>
  }
  judgments: JudgmentEntry[]
}
