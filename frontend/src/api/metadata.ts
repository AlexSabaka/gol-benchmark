import { get } from "./client"

export interface BenchmarkMetadata {
  languages: string[]
  user_styles: string[]
  system_styles: string[]
}

export function fetchMetadata(): Promise<BenchmarkMetadata> {
  return get<BenchmarkMetadata>("/api/metadata")
}
