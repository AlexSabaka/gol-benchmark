import { useQuery } from "@tanstack/react-query"
import { fetchOllamaModels, fetchOpenAIModels, fetchHFModels } from "@/api/models"

export function useOllamaModels(host?: string, enabled = false) {
  return useQuery({
    queryKey: ["models", "ollama", host],
    queryFn: () => fetchOllamaModels(host),
    enabled,
    staleTime: 30_000,
  })
}

export function useOpenAIModels(baseUrl: string, apiKey?: string, enabled = false) {
  return useQuery({
    queryKey: ["models", "openai", baseUrl, apiKey],
    queryFn: () => fetchOpenAIModels(baseUrl, apiKey),
    enabled,
    staleTime: 30_000,
  })
}

export function useHFModels(query: string, apiKey?: string, enabled = false) {
  return useQuery({
    queryKey: ["models", "hf", query, apiKey],
    queryFn: () => fetchHFModels(query, apiKey),
    enabled,
    staleTime: 60_000,
  })
}
