// ── Plugin types ──

export interface PluginInfo {
  task_type: string
  display_name: string
  description: string
  version: string
}

export interface ConfigField {
  name: string
  label: string
  /** Backend serialises as "type" via ConfigField.to_dict() */
  type: "number" | "select" | "multi-select" | "text" | "boolean" | "range" | "weight_map"
  default: unknown
  help?: string
  group?: string
  min?: number
  max?: number
  step?: number
  options?: (string | number)[]
  range_min_default?: number
  range_max_default?: number
  weight_keys?: string[]
}

export interface PluginSchema {
  task_type: string
  fields: ConfigField[]
  groups: string[]
}
