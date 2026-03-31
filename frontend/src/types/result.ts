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

export interface AnalyzeResponse {
  status: string
  model_count: number
  models: Record<string, ModelAnalysis>
  summaries: unknown[]
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
