import { get } from "./client"
import type { PluginInfo, PluginSchema } from "@/types"

export function fetchPlugins(): Promise<PluginInfo[]> {
  return get<PluginInfo[]>("/api/plugins")
}

export function fetchPluginSchema(taskType: string): Promise<PluginSchema> {
  return get<PluginSchema>(`/api/plugins/${encodeURIComponent(taskType)}/schema`)
}
