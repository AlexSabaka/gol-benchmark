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
  temperature: number
  max_tokens: number
  no_thinking: boolean
  cell_markers: string[]
  seed: number
}

export interface GenerateResponse {
  status: string
  testset_path: string
  filename: string
}
