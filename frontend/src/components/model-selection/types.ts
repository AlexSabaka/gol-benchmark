// Shared types and helpers for model-selection UI used by Execute and Matrix wizards.

export interface SelectedModel {
  id: string
  provider: "ollama" | "openai_compatible" | "huggingface"
  /** Only for openai_compatible */
  apiBase?: string
  apiKey?: string
  /** Only for ollama */
  ollamaHost?: string
}

export interface OpenAIEndpoint {
  key: string
  apiBase: string
  apiKey: string
}

/** Unique Map key for a selected model. OpenAI-compatible models are keyed by endpoint too. */
export function selectedModelKey(m: SelectedModel): string {
  if (m.provider === "openai_compatible") return `openai_compatible:${m.apiBase}:${m.id}`
  return `${m.provider}:${m.id}`
}
