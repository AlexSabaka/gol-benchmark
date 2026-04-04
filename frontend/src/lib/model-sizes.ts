/**
 * Known model sizes in BILLIONS of total parameters.
 *
 * For MoE models, "total" is used (not active/activated), since that's the
 * standard convention on model cards and HuggingFace. Active params are noted
 * in comments where meaningfully different.
 *
 * Sources: official model cards, technical reports, and HuggingFace pages.
 * Estimates are clearly marked with [EST] — treat with appropriate skepticism.
 *
 * Models omitted entirely:
 *   - OpenAI GPT-4/GPT-4o/o-series  → no public disclosure
 *   - Anthropic Claude family        → no public disclosure
 *   - Google Gemini family           → no public disclosure
 *   - Amazon Nova family             → no public disclosure
 *   - xAI Grok-3-mini / grok-code-*  → no public disclosure
 *   - Various boutique providers     → no reliable public data
 */
const KNOWN_MODELS: Record<string, number> = {
  // ── Meta Llama 4 ──────────────────────────────────────────────────────────
  // MoE; both models share 17B active params per token
  "meta-llama/llama-4-maverick": 400,   // 128 experts
  "meta-llama/llama-4-scout":    109,   // 16 experts
 
  // ── DeepSeek ──────────────────────────────────────────────────────────────
  // All V3/R1 family: 671B total MoE, 37B active
  "deepseek/deepseek-r1":              671,
  "deepseek/deepseek-r1-0528":         671,
  "deepseek/deepseek-chat":            671,  // alias → V3 family
  "deepseek/deepseek-chat-v3-0324":    671,
  "deepseek/deepseek-chat-v3.1":       671,
  "deepseek/deepseek-v3.1":            671,
  "deepseek/deepseek-v3.1-terminus":   671,
  // V3.2 is an updated post-trained checkpoint; some sources claim 385B for a
  // new architecture, but official docs still cite 671B — using 671 pending
  // a definitive technical report.
  "deepseek/deepseek-v3.2":           671,
  "deepseek/deepseek-v3.2-exp":       671,
  "deepseek/deepseek-v3.2-speciale":  671,
 
  // ── Mistral AI ────────────────────────────────────────────────────────────
  // Large 2 (dense, 123B) — all 2407 / 2411 tags
  "mistralai/mistral-large":       123,
  "mistralai/mistral-large-2407":  123,
  "mistralai/mistral-large-2411":  123,
  // Large 3 (MoE, 675B total / 41B active) — 2512 tag
  "mistralai/mistral-large-2512":  675,
  // Nemo (12B dense, co-developed with NVIDIA)
  "mistralai/mistral-nemo":        12,
  // Saba (24B dense, Arabic/South-Asian specialisation)
  "mistralai/mistral-saba":        24,
  // Small 3.x (24B dense)
  "mistralai/mistral-small-2603":  24,
  "mistralai/mistral-small-creative": 24,  // same base as Small 3.x
  // Pixtral Large (multimodal wrapper over Large 2 backbone)
  "mistralai/pixtral-large-2411":  123,
  // Devstral 2 (dense, 123B, Apache 2.0)
  "mistralai/devstral-2512":       123,
  // Codestral family: original 22B; 2508 checkpoint assumed same architecture
  "mistralai/codestral-2508":      22,
 
  // ── Microsoft ─────────────────────────────────────────────────────────────
  "microsoft/phi-4":  14,   // dense SLM (confirmed in technical report)
 
  // ── Cohere ────────────────────────────────────────────────────────────────
  "cohere/command-a":             111,   // dense; confirmed on docs.cohere.com
  "cohere/command-r-08-2024":      35,   // open-weight research release
  "cohere/command-r-plus-08-2024": 104,  // open-weight research release
 
  // ── Qwen / Alibaba ────────────────────────────────────────────────────────
  // Qwen3-Max: closed-weight trillion-parameter model (Sept 2025 announcement)
  "qwen/qwen3-max":          1000,
  "qwen/qwen3-max-thinking": 1000,
  // Qwen3-Coder (480B total MoE, 35B active — 8 of 160 experts per token)
  "qwen/qwen3-coder":        480,
  // qwen/qwen-max
  // qwen/qwen-plus
  // qwen/qwen-plus-2025-07-28
  // qwen/qwen-plus-2025-07-28:thinking
  // qwen/qwen-turbo
  // qwen/qwen-vl-max
  // qwen/qwen-vl-plus
  // qwen/qwen3.5-flash-02-23
  // qwen/qwen3.5-plus-02-15
  // qwen/qwen3.6-plus-preview:free
 
  // ── Zhipu AI / Z.ai (GLM family) ─────────────────────────────────────────
  // GLM-4.5 / 4.6 / 4.7 share the same MoE backbone: 355B total / 32B active
  "z-ai/glm-4.5":          355,
  "z-ai/glm-4.6":          355,
  "z-ai/glm-4.7":          355,
  // Air variant: 106B total / 12B active
  "z-ai/glm-4.5-air":       106,
  "z-ai/glm-4.5-air:free":  106,
  // Vision variants inherit the text backbone size (4.5V ≈ 108B per one source)
  "z-ai/glm-4.5v":  108,   // [EST] vision variant; Zhipu cites ~108B
  "z-ai/glm-4.6v":  355,   // multimodal build on 4.6 backbone
  "z-ai/glm-5": 744,       // 744B total for GLM-5, no official data
 
  // ── MiniMax ───────────────────────────────────────────────────────────────
  // Text-01 / MiniMax-01: 456B total MoE / 45.9B active (hybrid-attention)
  "minimax/minimax-01":  456,
  // M1 is built on the Text-01 checkpoint (same 456B / 45.9B architecture)
  "minimax/minimax-m1":  456,
  // M2: lighter MoE, 230B total / 10B active
  "minimax/minimax-m2":      230,
  "minimax/minimax-m2-her":  230,   // same base, different RLHF variant
 
  // ── Moonshot AI (Kimi) ────────────────────────────────────────────────────
  // Kimi K2: 1T total MoE / ~32B active
  "moonshotai/kimi-k2":          1000,
  "moonshotai/kimi-k2-0905":     1000,
  "moonshotai/kimi-k2-thinking": 1000,
 
  // ── xAI Grok ─────────────────────────────────────────────────────────────
  // xAI has never officially confirmed post-Grok-1 parameter counts.
  // Community consensus places Grok-3/4/4.1/4.20 at ~3T total (MoE).
  // Treat all Grok entries below as [EST] — omit if you prefer hard data only.
  "x-ai/grok-3":               3000,  // [EST] ~3T MoE
  "x-ai/grok-4":               3000,  // [EST] (some sources say ~1.7T)
  "x-ai/grok-4.1-fast":        3000,  // [EST]
  "x-ai/grok-4.20":            3000,  // elon is truly overgrown teenager
 
  // ── AI21 Labs ─────────────────────────────────────────────────────────────
  // Jamba 1.5 Large: SSM-Transformer hybrid MoE, 398B total / 94B active
  "ai21/jamba-large-1.7":  398,
 
  // –– Anthropic ––───────────────────────────────────────────────────────────
  "anthropic/claude-3-haiku": 20, // [EST] some sources claim 20B total for Haiku 3
  "anthropic/claude-3.5-haiku": 25, // [EST] some sources claim 25B total for Haiku 3.5
  "anthropic/claude-haiku-4.5": 30, // [EST] some sources claim 30B total for Haiku 4.5
  "anthropic/claude-3.5-sonnet": 175,  // [EST] some sources claim 175B total for Sonnet 3.5
  "anthropic/claude-3.7-sonnet": 175,  // [EST] some sources claim 175B total for Sonnet 3.5
  "anthropic/claude-sonnet-4": 200,  // [EST] some sources claim 200B total for Sonnet 4.5
  "anthropic/claude-sonnet-4.5": 200,  // [EST] some sources claim 200B total for Sonnet 4.5
  "anthropic/claude-sonnet-4.6": 200,  // [EST] some sources claim 200B total for Sonnet 4.6
  "anthropic/claude-opus-3": 2000,  // [EST] some sources claim 2T total for Opus 3
  "anthropic/claude-opus-4": 2500,  // [EST] some sources claim 2.5T total for Opus 4
  "anthropic/claude-opus-4.1": 2500,  // [EST] some sources claim 2.5T total for Opus 4
  "anthropic/claude-opus-4.5": 2700,  // [EST] some sources claim 2.7T total for Opus 4.5
  "anthropic/claude-opus-4.6": 3000,  // [EST] some sources claim 3T total for Opus 4.6

  // ── OpenAI (GPT-4 family) ─────────────────────────────────────────────────
  "openai/gpt-3.5-turbo": 20,
  "openai/gpt-4": 1700,
  "openai/gpt-4.1": 1700,
  "openai/gpt-4o": 200,
  // "openai/gpt-5": -1,
  // "openai/gpt-5-chat": -1,
  // "openai/gpt-5-codex": -1,
  // "openai/gpt-5-image": -1,
  // "openai/gpt-5-image-mini": -1,
  // "openai/gpt-5-mini": -1,
  // "openai/gpt-5-nano": -1,
  // "openai/gpt-5-pro": -1,
  // "openai/gpt-5.1": -1,
  // "openai/gpt-5.1-chat": -1,
  // "openai/gpt-5.1-codex": -1,
  // "openai/gpt-5.1-codex-max": -1,
  // "openai/gpt-5.1-codex-mini": -1,
  // "openai/gpt-5.2": -1,
  // "openai/gpt-5.2-chat": -1,
  // "openai/gpt-5.2-codex": -1,
  // "openai/gpt-5.2-pro": -1,
  // "openai/gpt-5.3-chat": -1,
  // "openai/gpt-5.3-codex": -1,
  // "openai/gpt-5.4": -1,
  // "openai/gpt-5.4-mini": -1,
  // "openai/gpt-5.4-nano": -1,
  // "openai/gpt-5.4-pro": -1,
   "openai/o1": 300,
  // "openai/o3": -1,
  // "openai/o4-mini": -1,

  // ── Google Gemini ───────────────────────────────────────────────────────────
  // "google/gemini-2.0-flash-001": -1,
  // "google/gemini-2.0-flash-lite-001": -1,
  // "google/gemini-2.5-flash": -1,
  // "google/gemini-2.5-flash-image": -1,
  // "google/gemini-2.5-flash-lite": -1,
  // "google/gemini-2.5-flash-lite-preview-09-2025": -1,
  // "google/gemini-2.5-pro": -1,
  // "google/gemini-2.5-pro-preview": -1,
  // "google/gemini-2.5-pro-preview-05-06": -1,
  // "google/gemini-3-flash-preview": -1,
  // "google/gemini-3-pro-image-preview": -1,
  // "google/gemini-3.1-flash-image-preview": -1,
  // "google/gemini-3.1-flash-lite-preview": -1,
  // "google/gemini-3.1-pro-preview": -1,
  // "google/gemini-3.1-pro-preview-customtools": -1,
  // "google/lyria-3-clip-preview": -1,
  // "google/lyria-3-pro-preview": -1,
};

/** Regex to extract size from model name, e.g. "27b" → 27e9 */
const SIZE_PATTERN = /(\d+(?:\.\d+)?)\s*([bBmM])\b/

export function getModelSize(name: string): number | null {
  const lower = name.toLowerCase()

  // Direct lookup
  if (KNOWN_MODELS[lower]) return KNOWN_MODELS[lower] * 1e9

  // Partial match (model name may include quantization suffix)
  for (const [key, size] of Object.entries(KNOWN_MODELS)) {
    if (lower.startsWith(key) || lower.includes(key)) return size * 1e9
  }

  // Regex fallback: extract "Nb" pattern
  const match = lower.match(SIZE_PATTERN)
  if (match) {
    const value = parseFloat(match[1])
    const unit = match[2].toLowerCase()
    if (unit === "b") return value * 1e9
    if (unit === "m") return value * 1e6
  }

  return null
}

export function formatParamCount(count: number): string {
  if (count >= 1e9) return `${(count / 1e9).toFixed(1)}B`
  if (count >= 1e6) return `${(count / 1e6).toFixed(0)}M`
  return `${count}`
}
