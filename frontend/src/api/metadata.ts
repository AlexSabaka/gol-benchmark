import { get } from "./client"

export interface MetadataPromptEntry {
  id: string
  name: string
  latest_version: number | null
  is_builtin: boolean
  language_codes: string[]
}

export interface BenchmarkMetadata {
  languages: string[]
  user_styles: string[]
  system_styles: string[]
  /** Prompt Studio catalog summary — populated by the backend lifespan. */
  prompts: MetadataPromptEntry[]
}

export function fetchMetadata(): Promise<BenchmarkMetadata> {
  return get<BenchmarkMetadata>("/api/metadata")
}
