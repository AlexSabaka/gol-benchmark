// ── Job types ──

export type JobState = "pending" | "running" | "paused" | "completed" | "failed" | "cancelled"

export interface Job {
  id: string
  model_name: string
  testset_path: string
  run_group_id?: string | null
  state: JobState
  progress_current: number
  progress_total: number
  result_path?: string
  error?: string
  created_at: number
  elapsed_seconds?: number
  eta_seconds?: number | null
  paused_at_index?: number | null
  partial_result_path?: string | null
}

export interface RunRequest {
  testset_path?: string
  testset_filename?: string
  testset_filenames?: string[]
  models: string[]
  provider: string
  ollama_host?: string
  run_group_id?: string
  temperature?: number
  max_tokens?: number
  no_think?: boolean
  output_dir?: string
  api_key?: string
  api_base?: string
}

export interface RunResponse {
  run_group_id?: string | null
  jobs: { job_id: string; model: string; testset_filename?: string }[]
}
