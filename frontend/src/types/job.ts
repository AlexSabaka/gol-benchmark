// ── Job types ──

export type JobState = "pending" | "running" | "completed" | "failed" | "cancelled"

export interface Job {
  id: string
  model_name: string
  testset_path: string
  state: JobState
  progress_current: number
  progress_total: number
  result_path?: string
  error?: string
  created_at: number
  elapsed_seconds?: number
}

export interface RunRequest {
  testset_path?: string
  testset_filename?: string
  models: string[]
  provider: string
  ollama_host?: string
  temperature?: number
  max_tokens?: number
  no_think?: boolean
  output_dir?: string
  api_key?: string
  api_base?: string
}

export interface RunResponse {
  jobs: { job_id: string; model: string }[]
}
