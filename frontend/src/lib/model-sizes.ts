/**
 * Static lookup for model parameter counts.
 * Infers size from model name patterns (e.g. "3b", "7b", "27b").
 * This is intentionally approximate — extend as needed.
 */

const KNOWN_MODELS: Record<string, number> = {
  // Qwen family
  "qwen3:0.6b": 0.6e9,
  "qwen3:1.7b": 1.7e9,
  "qwen3:4b": 4e9,
  "qwen3:8b": 8e9,
  "qwen3:14b": 14e9,
  "qwen3:30b": 30e9,
  "qwen3:32b": 32e9,
  "qwen2.5:0.5b": 0.5e9,
  "qwen2.5:1.5b": 1.5e9,
  "qwen2.5:3b": 3e9,
  "qwen2.5:7b": 7e9,
  "qwen2.5:14b": 14e9,
  "qwen2.5:32b": 32e9,
  "qwen2.5:72b": 72e9,
  // Gemma family
  "gemma3:1b": 1e9,
  "gemma3:4b": 4e9,
  "gemma3:12b": 12e9,
  "gemma3:27b": 27e9,
  "gemma2:2b": 2e9,
  "gemma2:9b": 9e9,
  "gemma2:27b": 27e9,
  // Llama family
  "llama3.2:1b": 1e9,
  "llama3.2:3b": 3e9,
  "llama3.1:8b": 8e9,
  "llama3.1:70b": 70e9,
  "llama3.3:70b": 70e9,
  // Phi family
  "phi4:14b": 14e9,
  "phi3:3.8b": 3.8e9,
  "phi3:14b": 14e9,
  // Mistral
  "mistral:7b": 7e9,
  "mistral-small:24b": 24e9,
  "mixtral:8x7b": 47e9,
  "mixtral:8x22b": 141e9,
  // DeepSeek
  "deepseek-r1:1.5b": 1.5e9,
  "deepseek-r1:7b": 7e9,
  "deepseek-r1:8b": 8e9,
  "deepseek-r1:14b": 14e9,
  "deepseek-r1:32b": 32e9,
  "deepseek-r1:70b": 70e9,
  // Closed models — estimated parameter counts (publicly reported or community estimates)
  // OpenAI
  "gpt-4o": 200e9,
  "gpt-4o-mini": 8e9,
  "gpt-4-turbo": 200e9,
  "gpt-4": 200e9,
  "gpt-3.5-turbo": 20e9,
  "o1": 200e9,
  "o1-mini": 100e9,
  "o1-preview": 200e9,
  "o3": 200e9,
  "o3-mini": 100e9,
  "o4-mini": 100e9,
  // Anthropic
  "claude-3.5-haiku": 8e9,
  "claude-3-haiku": 8e9,
  "claude-3.5-sonnet": 70e9,
  "claude-3-sonnet": 70e9,
  "claude-3-opus": 137e9,
  "claude-3.5-opus": 137e9,
  "claude-sonnet-4": 70e9,
  "claude-opus-4": 137e9,
  // Google
  "gemini-1.5-flash": 9e9,
  "gemini-1.5-pro": 50e9,
  "gemini-2.0-flash": 9e9,
  "gemini-2.5-pro": 50e9,
  "gemini-2.5-flash": 9e9,
  // Mistral (API)
  "mistral-large": 123e9,
  "mistral-medium": 70e9,
  "mistral-small": 24e9,
  // Cohere
  "command-r": 35e9,
  "command-r-plus": 104e9,
  // DeepSeek (API)
  "deepseek-v3": 671e9,
  "deepseek-r1": 671e9,
  // Moonshot / Kimi
  "kimi-k2": 1000e9,
  "kimi-k2.5": 1000e9,
  "moonshot-v1": 200e9,
}

/** Regex to extract size from model name, e.g. "27b" → 27e9 */
const SIZE_PATTERN = /(\d+(?:\.\d+)?)\s*[bB]\b/

export function getModelSize(name: string): number | null {
  const lower = name.toLowerCase()

  // Direct lookup
  if (KNOWN_MODELS[lower]) return KNOWN_MODELS[lower]

  // Partial match (model name may include quantization suffix)
  for (const [key, size] of Object.entries(KNOWN_MODELS)) {
    if (lower.startsWith(key) || lower.includes(key)) return size
  }

  // Regex fallback: extract "Nb" pattern
  const match = lower.match(SIZE_PATTERN)
  if (match) return parseFloat(match[1]) * 1e9

  return null
}

export function formatParamCount(count: number): string {
  if (count >= 1e9) return `${(count / 1e9).toFixed(1)}B`
  if (count >= 1e6) return `${(count / 1e6).toFixed(0)}M`
  return `${count}`
}
