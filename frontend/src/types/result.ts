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
}

export interface ScatterPoint {
  model: string
  paramCount: number | null
  accuracy: number
}
