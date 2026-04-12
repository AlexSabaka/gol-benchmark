// ── Test set types ──

export interface TestsetSummary {
  filename: string
  path: string
  size_bytes: number
  metadata: Record<string, unknown>
  generation_params: Record<string, unknown>
  statistics: Record<string, unknown>
  test_count: number
  task_types: string[]
  languages: string[]
  user_styles: string[]
  system_styles: string[]
  matrix_batch_id?: string | null
  matrix_cell_id?: string | null
  matrix_label?: string | null
  matrix_plugin?: string | null
  matrix_axes?: Record<string, unknown> | null
  created: string
  error?: string
}

export interface TestsetDetail {
  filename: string
  metadata: Record<string, unknown>
  generation_params: Record<string, unknown>
  sampling_params: Record<string, unknown>
  execution_params: Record<string, unknown>
  statistics: Record<string, unknown>
  test_count: number
  task_types: string[]
  sample_cases: Record<string, unknown>[]
  total_cases?: number
  page?: number
  page_size?: number
}

export interface PromptConfig {
  user_style: string
  system_style: string
  language: string
}

export interface TaskConfig {
  type: string
  generation: Record<string, unknown>
  prompt_configs: PromptConfig[]
}

export interface GenerateRequest {
  name: string
  description: string
  tasks: TaskConfig[]
  temperature?: number
  max_tokens?: number
  no_thinking?: boolean
  cell_markers: string[]
  seed: number
  custom_system_prompt?: string
}

export interface ParamOverrides {
  user_style?: string
  system_style?: string
  custom_system_prompt?: string
  language?: string
}

export interface GenerateResponse {
  status: string
  testset_path: string
  filename: string
}
