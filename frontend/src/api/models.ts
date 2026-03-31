import { get } from "./client"
import type { OllamaModelsResponse, OpenAIModelsResponse, HFModelsResponse } from "@/types"

export function fetchOllamaModels(host?: string): Promise<OllamaModelsResponse> {
  return get<OllamaModelsResponse>("/api/models", host ? { host } : undefined)
}

export function fetchOpenAIModels(baseUrl: string, apiKey?: string): Promise<OpenAIModelsResponse> {
  const params: Record<string, string> = { base_url: baseUrl }
  if (apiKey) params.api_key = apiKey
  return get<OpenAIModelsResponse>("/api/models/openai", params)
}

export function fetchHFModels(query: string, apiKey?: string, limit?: number): Promise<HFModelsResponse> {
  const params: Record<string, string> = { query }
  if (apiKey) params.api_key = apiKey
  if (limit) params.limit = String(limit)
  return get<HFModelsResponse>("/api/models/huggingface/search", params)
}
