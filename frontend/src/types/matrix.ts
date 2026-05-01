import type { Provider } from "./model"
import type { PromptConfig } from "./testset"

export interface MatrixPromptAxes {
  user_styles: string[]
  system_styles: string[]
  languages: string[]
  /**
   * Prompt Studio refs in "<id>" or "<id>@<version>" form. When non-empty,
   * the matrix axis becomes ``user_style × prompt × language`` and
   * ``system_styles`` is ignored for resolution (it's still surfaced as a
   * derived back-compat tag in result files).
   */
  prompt_ids?: string[]
}

export interface MatrixFieldAxis {
  field_name: string
  values: unknown[]
}

export interface MatrixModelGroup {
  provider: Provider
  models: string[]
  ollama_host?: string
  api_key?: string
  api_base?: string
}

export interface MatrixRunRequest {
  plugin_type: string
  name_prefix: string
  description?: string
  generate_only?: boolean
  seed: number
  temperature: number
  max_tokens: number
  no_think: boolean
  cell_markers?: string[]
  custom_system_prompt?: string
  base_generation: Record<string, unknown>
  prompt_axes: MatrixPromptAxes
  field_axes: MatrixFieldAxis[]
  model_groups: MatrixModelGroup[]
}

export interface MatrixGeneratedTestset {
  cell_id: string
  cell_label: string
  testset_path: string
  filename: string
  prompt_config: PromptConfig
  generation: Record<string, unknown>
  axis_values: Record<string, unknown>
}

export interface MatrixRunJob {
  job_id: string
  model: string
  cell_id: string
  cell_label: string
  testset_filename: string
  run_group_id?: string | null
}

export interface MatrixRunResponse {
  status: string
  batch_id: string
  plugin_type: string
  generate_only?: boolean
  total_cells: number
  total_jobs: number
  generated_testsets: MatrixGeneratedTestset[]
  jobs: MatrixRunJob[]
}