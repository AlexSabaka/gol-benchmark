// ── Model provider types ──

export type Provider = "ollama" | "openai_compatible" | "huggingface"

export interface OllamaModel {
  name: string
  size_human: string
  quantization: string
  family: string
  display_name: string
}

export interface OllamaModelsResponse {
  host: string
  models: OllamaModel[]
  error?: string
}

export interface OpenAIModel {
  name: string
  owned_by: string
  display_name: string
}

export interface OpenAIModelsResponse {
  base_url: string
  models: OpenAIModel[]
  error?: string
}

export interface HFModel {
  id: string
  author: string
  downloads: number
  likes: number
  pipeline_tag: string
  tags: string[]
  display_name: string
}

export interface HFModelsResponse {
  query: string
  models: HFModel[]
  error?: string
}
