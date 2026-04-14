/**
 * Model registry: canonical name → family / variant / size / aliases.
 *
 * Sources: official model cards, technical reports, and HuggingFace pages.
 * Anything marked `estimated: true` is a community-sourced guess — rendered
 * with a "~" prefix on chart badges so viewers know.
 *
 * Aliases lifted from carwash_matrix.py MODEL_ALIASES plus extras:
 *   gemma3:4b-cloud, google/gemma-3-4b-it, etc. all fold into "gemma3-4b".
 *
 * Model families that are closed-weight have [EST] sizes — treat those bars
 * and dots with appropriate skepticism.
 */

export interface ModelEntry {
  /** Short family name shown on the first line of the badge — e.g. "Gemma 3", "GLM", "Claude Sonnet". */
  family: string
  /** Optional variant/nickname shown on the second line — e.g. "Maverick", "Scout", "Air". */
  variant?: string
  /** Total parameters in billions. For MoE models, the "total" (not active) figure. */
  size: number
  /** When true, size is a community estimate; badge renders a "~" prefix. */
  estimated?: boolean
  /** Alternative raw tags that canonicalize to this entry. */
  aliases?: string[]
}

/** Canonical keys follow the short "family-size" or "family-size-variant" style (hyphenated, lowercase). */
export const KNOWN_MODELS: Record<string, ModelEntry> = {
  // ── Meta Llama 4 ──────────────────────────────────────────────────────────
  // MoE; both models share 17B active params per token
  "llama-4-maverick": {
    family: "Llama 4", variant: "Maverick", size: 400,
    aliases: ["meta-llama/llama-4-maverick"],
  },
  "llama-4-scout": {
    family: "Llama 4", variant: "Scout", size: 109,
    aliases: ["meta-llama/llama-4-scout"],
  },

  // ── Meta Llama 3.x (common OSS baselines) ────────────────────────────────
  "llama-3.1-8b": {
    family: "Llama 3.1", size: 8,
    aliases: [
      "meta-llama/llama-3.1-8b-instruct", "llama-3.1-8b-instruct",
      "llama3.1:8b", "llama3.1:8b-instruct",
    ],
  },
  "llama-3.1-70b": {
    family: "Llama 3.1", size: 70,
    aliases: [
      "meta-llama/llama-3.1-70b-instruct", "llama-3.1-70b-instruct",
      "llama3.1:70b", "llama3.1:70b-instruct",
    ],
  },
  "llama-3.1-405b": {
    family: "Llama 3.1", size: 405,
    aliases: ["meta-llama/llama-3.1-405b-instruct", "llama-3.1-405b-instruct"],
  },
  "llama-3.2-1b": {
    family: "Llama 3.2", size: 1,
    aliases: [
      "meta-llama/llama-3.2-1b-instruct", "llama-3.2-1b-instruct",
      "llama3.2:1b", "llama3.2:1b-instruct",
    ],
  },
  "llama-3.2-3b": {
    family: "Llama 3.2", size: 3,
    aliases: [
      "meta-llama/llama-3.2-3b-instruct", "llama-3.2-3b-instruct",
      "llama3.2:3b", "llama3.2:3b-instruct",
    ],
  },
  "llama-3.2-11b-vision": {
    family: "Llama 3.2", variant: "Vision", size: 11,
    aliases: [
      "meta-llama/llama-3.2-11b-vision-instruct", "llama-3.2-11b-vision-instruct",
      "llama3.2-vision:11b",
    ],
  },
  "llama-3.2-90b-vision": {
    family: "Llama 3.2", variant: "Vision", size: 90,
    aliases: [
      "meta-llama/llama-3.2-90b-vision-instruct", "llama-3.2-90b-vision-instruct",
      "llama3.2-vision:90b",
    ],
  },
  "llama-3.3-70b": {
    family: "Llama 3.3", size: 70,
    aliases: [
      "meta-llama/llama-3.3-70b-instruct", "llama-3.3-70b-instruct",
      "llama3.3:70b", "llama3.3:70b-instruct",
    ],
  },

  // ── DeepSeek ──────────────────────────────────────────────────────────────
  // All V3/R1 family: 671B total MoE, 37B active
  "deepseek-r1": {
    family: "DeepSeek R1", size: 671,
    aliases: ["deepseek/deepseek-r1", "deepseek/deepseek-r1-0528"],
  },
  "deepseek-v3": {
    family: "DeepSeek V3", size: 671,
    aliases: [
      "deepseek/deepseek-chat",
      "deepseek/deepseek-chat-v3-0324",
      "deepseek/deepseek-chat-v3.1",
      "deepseek/deepseek-v3.1",
      "deepseek/deepseek-v3.1-terminus",
      // V3.2 is a post-trained checkpoint; still 671B per official docs
      "deepseek/deepseek-v3.2",
      "deepseek/deepseek-v3.2-exp",
      "deepseek/deepseek-v3.2-speciale",
    ],
  },

  // ── Mistral AI ────────────────────────────────────────────────────────────
  "mistral-large": {
    family: "Mistral", variant: "Large 2", size: 123,
    aliases: ["mistralai/mistral-large", "mistralai/mistral-large-2407", "mistralai/mistral-large-2411"],
  },
  "mistral-large-3": {
    family: "Mistral", variant: "Large 3", size: 675,
    aliases: ["mistralai/mistral-large-2512"],
  },
  "mistral-nemo": { family: "Mistral", variant: "Nemo", size: 12, aliases: ["mistralai/mistral-nemo"] },
  "mistral-saba": { family: "Mistral", variant: "Saba", size: 24, aliases: ["mistralai/mistral-saba"] },
  "mistral-small": {
    family: "Mistral", variant: "Small 3", size: 24,
    aliases: ["mistralai/mistral-small-2603", "mistralai/mistral-small-creative"],
  },
  "pixtral-large": {
    family: "Mistral", variant: "Pixtral Large", size: 123,
    aliases: ["mistralai/pixtral-large-2411"],
  },
  "devstral-2": {
    family: "Mistral", variant: "Devstral 2", size: 123,
    aliases: ["mistralai/devstral-2512"],
  },
  "codestral": {
    family: "Mistral", variant: "Codestral", size: 22,
    aliases: ["mistralai/codestral-2508"],
  },

  // ── Microsoft ─────────────────────────────────────────────────────────────
  "phi-4": { family: "Phi 4", size: 14, aliases: ["microsoft/phi-4"] },

  // ── Cohere ────────────────────────────────────────────────────────────────
  "command-a": { family: "Command", variant: "A", size: 111, aliases: ["cohere/command-a"] },
  "command-r": { family: "Command", variant: "R", size: 35, aliases: ["cohere/command-r-08-2024"] },
  "command-r-plus": { family: "Command", variant: "R+", size: 104, aliases: ["cohere/command-r-plus-08-2024"] },

  // ── Qwen / Alibaba ────────────────────────────────────────────────────────
  // Qwen3-Max: closed-weight trillion-parameter tier
  "qwen3-max": {
    family: "Qwen 3", variant: "Max", size: 1000,
    aliases: ["qwen/qwen3-max", "qwen/qwen3-max-thinking"],
  },
  "qwen3-coder": {
    family: "Qwen 3", variant: "Coder", size: 480,
    aliases: ["qwen/qwen3-coder"],
  },
  // Qwen 3 dense / MoE
  "qwen3-0.6b": { family: "Qwen 3", size: 0.6, aliases: ["qwen3:0.6b"] },
  "qwen3-1.7b": { family: "Qwen 3", size: 1.7, aliases: ["qwen3:1.7b"] },
  "qwen3-4b": { family: "Qwen 3", size: 4, aliases: ["qwen3:4b", "qwen/qwen3-4b"] },
  "qwen3-8b": { family: "Qwen 3", size: 8, aliases: ["qwen3:8b", "qwen/qwen3-8b"] },
  "qwen3-14b": { family: "Qwen 3", size: 14, aliases: ["qwen3:14b", "qwen/qwen3-14b"] },
  "qwen3-30b-a3b": {
    family: "Qwen 3", size: 30,
    aliases: ["qwen/qwen3-30b-a3b", "qwen/qwen3-30b-a3b-instruct-2507"],
  },
  "qwen3-next-80b": {
    family: "Qwen 3", variant: "Next", size: 80,
    aliases: ["qwen3-next:80b-cloud", "qwen/qwen3-next-80b-a3b-instruct"],
  },
  // Qwen 3 VL
  "qwen3-vl-2b": { family: "Qwen 3 VL", size: 2, aliases: ["qwen3-vl:2b"] },
  "qwen3-vl-8b": { family: "Qwen 3 VL", size: 8, aliases: ["qwen/qwen3-vl-8b-instruct"] },
  // Qwen 3.5 — estimates, closed-weight
  "qwen3.5-0.8b": { family: "Qwen 3.5", size: 0.8, estimated: true, aliases: ["qwen3.5:0.8b"] },
  "qwen3.5-2b": { family: "Qwen 3.5", size: 2, estimated: true, aliases: ["qwen3.5:2b"] },
  "qwen3.5-9b": { family: "Qwen 3.5", size: 9, estimated: true, aliases: ["qwen3.5:9b", "qwen/qwen3.5-9b"] },
  "qwen3.5-27b": { family: "Qwen 3.5", size: 27, estimated: true, aliases: ["qwen/qwen3.5-27b"] },
  "qwen3.5-35b-a3b": { family: "Qwen 3.5", size: 35, estimated: true, aliases: ["qwen/qwen3.5-35b-a3b"] },
  "qwen3.5-122b-a10b": { family: "Qwen 3.5", size: 122, estimated: true, aliases: ["qwen/qwen3.5-122b-a10b"] },
  // Qwen 2.5
  "qwen2.5-1.5b": { family: "Qwen 2.5", size: 1.5, aliases: ["qwen2.5:1.5b"] },
  "qwen2.5-3b": { family: "Qwen 2.5", size: 3, aliases: ["qwen2.5:3b"] },
  "qwen2.5-72b": { family: "Qwen 2.5", size: 72, aliases: ["qwen/qwen-2.5-72b-instruct"] },
  "qwen2.5-vl-72b": { family: "Qwen 2.5 VL", size: 72, aliases: ["qwen/qwen2.5-vl-72b-instruct"] },

  // ── Zhipu AI / Z.ai (GLM family) ─────────────────────────────────────────
  // GLM-4.5 / 4.6 / 4.7 share the same MoE backbone: 355B total / 32B active
  "glm-4.5": { family: "GLM 4.5", size: 355, aliases: ["z-ai/glm-4.5"] },
  "glm-4.6": { family: "GLM 4.6", size: 355, aliases: ["z-ai/glm-4.6"] },
  "glm-4.7": { family: "GLM 4.7", size: 355, aliases: ["z-ai/glm-4.7"] },
  "glm-4.5-air": {
    family: "GLM 4.5", variant: "Air", size: 106,
    aliases: ["z-ai/glm-4.5-air", "z-ai/glm-4.5-air:free"],
  },
  "glm-4.5v": { family: "GLM 4.5", variant: "V", size: 108, estimated: true, aliases: ["z-ai/glm-4.5v"] },
  "glm-4.6v": { family: "GLM 4.6", variant: "V", size: 355, aliases: ["z-ai/glm-4.6v"] },
  "glm-5": { family: "GLM 5", size: 744, estimated: true, aliases: ["z-ai/glm-5"] },

  // ── MiniMax ───────────────────────────────────────────────────────────────
  "minimax-01": { family: "MiniMax", variant: "01", size: 456, aliases: ["minimax/minimax-01"] },
  "minimax-m1": { family: "MiniMax", variant: "M1", size: 456, aliases: ["minimax/minimax-m1"] },
  "minimax-m2": {
    family: "MiniMax", variant: "M2", size: 230,
    aliases: ["minimax/minimax-m2", "minimax/minimax-m2-her"],
  },

  // ── Moonshot AI (Kimi) ────────────────────────────────────────────────────
  "kimi-k2": {
    family: "Kimi", variant: "K2", size: 1000,
    aliases: ["moonshotai/kimi-k2", "moonshotai/kimi-k2-0905", "moonshotai/kimi-k2-thinking"],
  },
  "kimi-k2.5": { family: "Kimi", variant: "K2.5", size: 1000, estimated: true, aliases: ["moonshotai/kimi-k2.5"] },

  // ── xAI Grok (all [EST] — never officially confirmed) ────────────────────
  "grok-3": { family: "Grok 3", size: 3000, estimated: true, aliases: ["x-ai/grok-3"] },
  "grok-4": { family: "Grok 4", size: 3000, estimated: true, aliases: ["x-ai/grok-4"] },
  "grok-4.1-fast": { family: "Grok 4", variant: "4.1 Fast", size: 3000, estimated: true, aliases: ["x-ai/grok-4.1-fast"] },
  "grok-4.20": { family: "Grok 4", variant: "4.20", size: 3000, estimated: true, aliases: ["x-ai/grok-4.20"] },
  "grok-4.20-beta": { family: "Grok 4", variant: "4.20 Beta", size: 3000, estimated: true, aliases: ["x-ai/grok-4.20-beta"] },

  // ── AI21 Labs ─────────────────────────────────────────────────────────────
  "jamba-large-1.7": {
    family: "Jamba", variant: "Large 1.7", size: 398,
    aliases: ["ai21/jamba-large-1.7"],
  },

  // ── Anthropic (all [EST] — closed-weight) ────────────────────────────────
  "claude-3-haiku": {
    family: "Claude Haiku", variant: "3", size: 20, estimated: true,
    aliases: ["anthropic/claude-3-haiku"],
  },
  "claude-3.5-haiku": {
    family: "Claude Haiku", variant: "3.5", size: 25, estimated: true,
    aliases: ["anthropic/claude-3.5-haiku"],
  },
  "claude-haiku-4.5": {
    family: "Claude Haiku", variant: "4.5", size: 30, estimated: true,
    aliases: ["anthropic/claude-haiku-4.5"],
  },
  "claude-3.5-sonnet": {
    family: "Claude Sonnet", variant: "3.5", size: 175, estimated: true,
    aliases: ["anthropic/claude-3.5-sonnet"],
  },
  "claude-3.7-sonnet": {
    family: "Claude Sonnet", variant: "3.7", size: 175, estimated: true,
    aliases: ["anthropic/claude-3.7-sonnet"],
  },
  "claude-sonnet-4": {
    family: "Claude Sonnet", variant: "4", size: 200, estimated: true,
    aliases: ["anthropic/claude-sonnet-4"],
  },
  "claude-sonnet-4.5": {
    family: "Claude Sonnet", variant: "4.5", size: 200, estimated: true,
    aliases: ["anthropic/claude-sonnet-4.5"],
  },
  "claude-sonnet-4.6": {
    family: "Claude Sonnet", variant: "4.6", size: 200, estimated: true,
    aliases: ["anthropic/claude-sonnet-4.6"],
  },
  "claude-opus-3": {
    family: "Claude Opus", variant: "3", size: 2000, estimated: true,
    aliases: ["anthropic/claude-opus-3"],
  },
  "claude-opus-4": {
    family: "Claude Opus", variant: "4", size: 2500, estimated: true,
    aliases: ["anthropic/claude-opus-4"],
  },
  "claude-opus-4.1": {
    family: "Claude Opus", variant: "4.1", size: 2500, estimated: true,
    aliases: ["anthropic/claude-opus-4.1"],
  },
  "claude-opus-4.5": {
    family: "Claude Opus", variant: "4.5", size: 2700, estimated: true,
    aliases: ["anthropic/claude-opus-4.5"],
  },
  "claude-opus-4.6": {
    family: "Claude Opus", variant: "4.6", size: 3000, estimated: true,
    aliases: ["anthropic/claude-opus-4.6"],
  },

  // ── OpenAI (all [EST] — no public disclosure of modern models) ───────────
  "gpt-3.5-turbo": { family: "GPT 3.5", size: 20, estimated: true, aliases: ["openai/gpt-3.5-turbo"] },
  "gpt-4": { family: "GPT 4", size: 1700, estimated: true, aliases: ["openai/gpt-4"] },
  "gpt-4o": { family: "GPT 4o", size: 200, estimated: true, aliases: ["openai/gpt-4o"] },
  "gpt-4.1": { family: "GPT 4.1", size: 1700, estimated: true, aliases: ["openai/gpt-4.1"] },
  "gpt-4.1-mini": { family: "GPT 4.1", variant: "Mini", size: 8, estimated: true, aliases: ["openai/gpt-4.1-mini"] },
  "gpt-4.1-nano": { family: "GPT 4.1", variant: "Nano", size: 3, estimated: true, aliases: ["openai/gpt-4.1-nano"] },
  // GPT-5 family — rough class sizes: flagship / mini / nano
  "gpt-5": {
    family: "GPT 5", size: 1700, estimated: true,
    aliases: ["openai/gpt-5", "openai/gpt-5-chat", "openai/gpt-5-pro", "openai/gpt-5.4"],
  },
  "gpt-5-mini": {
    family: "GPT 5", variant: "Mini", size: 25, estimated: true,
    aliases: ["openai/gpt-5-mini", "openai/gpt-5.4-mini"],
  },
  "gpt-5-nano": {
    family: "GPT 5", variant: "Nano", size: 8, estimated: true,
    aliases: ["openai/gpt-5-nano", "openai/gpt-5.4-nano"],
  },
  "gpt-5.1": {
    family: "GPT 5.1", size: 1700, estimated: true,
    aliases: ["openai/gpt-5.1", "openai/gpt-5.1-chat", "openai/gpt-5.1-codex", "openai/gpt-5.1-codex-max"],
  },
  "gpt-5.1-codex-mini": {
    family: "GPT 5.1", variant: "Codex Mini", size: 25, estimated: true,
    aliases: ["openai/gpt-5.1-codex-mini"],
  },
  "gpt-5.2": {
    family: "GPT 5.2", size: 1700, estimated: true,
    aliases: ["openai/gpt-5.2", "openai/gpt-5.2-chat", "openai/gpt-5.2-codex", "openai/gpt-5.2-pro"],
  },
  "gpt-5.3": {
    family: "GPT 5.3", size: 1700, estimated: true,
    aliases: ["openai/gpt-5.3-chat", "openai/gpt-5.3-codex"],
  },
  "gpt-5.4-pro": {
    family: "GPT 5.4", variant: "Pro", size: 1700, estimated: true,
    aliases: ["openai/gpt-5.4-pro"],
  },
  // o-series reasoning
  "o1": { family: "o1", size: 300, estimated: true, aliases: ["openai/o1"] },
  "o3": { family: "o3", size: 1700, estimated: true, aliases: ["openai/o3"] },
  "o4-mini": { family: "o4", variant: "Mini", size: 25, estimated: true, aliases: ["openai/o4-mini"] },

  // ── Google Gemini (all [EST] — closed-weight) ────────────────────────────
  "gemini-2.0-flash": {
    family: "Gemini 2.0", variant: "Flash", size: 80, estimated: true,
    aliases: ["google/gemini-2.0-flash-001"],
  },
  "gemini-2.0-flash-lite": {
    family: "Gemini 2.0", variant: "Flash Lite", size: 8, estimated: true,
    aliases: ["google/gemini-2.0-flash-lite-001"],
  },
  "gemini-2.5-flash": {
    family: "Gemini 2.5", variant: "Flash", size: 80, estimated: true,
    aliases: ["google/gemini-2.5-flash", "google/gemini-2.5-flash-image"],
  },
  "gemini-2.5-flash-lite": {
    family: "Gemini 2.5", variant: "Flash Lite", size: 8, estimated: true,
    aliases: ["google/gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite-preview-09-2025"],
  },
  "gemini-2.5-pro": {
    family: "Gemini 2.5", variant: "Pro", size: 400, estimated: true,
    aliases: ["google/gemini-2.5-pro", "google/gemini-2.5-pro-preview", "google/gemini-2.5-pro-preview-05-06"],
  },
  "gemini-3-flash": {
    family: "Gemini 3", variant: "Flash", size: 80, estimated: true,
    aliases: ["google/gemini-3-flash-preview"],
  },
  "gemini-3-pro": {
    family: "Gemini 3", variant: "Pro", size: 400, estimated: true,
    aliases: ["google/gemini-3-pro-image-preview"],
  },
  "gemini-3.1-flash-image": {
    family: "Gemini 3.1", variant: "Flash Image", size: 80, estimated: true,
    aliases: ["google/gemini-3.1-flash-image-preview"],
  },
  "gemini-3.1-flash-lite": {
    family: "Gemini 3.1", variant: "Flash Lite", size: 8, estimated: true,
    aliases: ["google/gemini-3.1-flash-lite-preview"],
  },
  "gemini-3.1-pro": {
    family: "Gemini 3.1", variant: "Pro", size: 400, estimated: true,
    aliases: ["google/gemini-3.1-pro-preview", "google/gemini-3.1-pro-preview-customtools"],
  },

  // ── Google Gemma (open weights) ──────────────────────────────────────────
  "gemma2-27b": { family: "Gemma 2", size: 27, aliases: ["google/gemma-2-27b-it"] },
  "gemma3-1b": { family: "Gemma 3", size: 1, aliases: ["gemma3:1b"] },
  "gemma3-4b": {
    family: "Gemma 3", size: 4,
    aliases: ["gemma3:4b", "gemma3:4b-cloud", "google/gemma-3-4b-it"],
  },
  "gemma3-12b": {
    family: "Gemma 3", size: 12,
    aliases: ["gemma3:12b", "gemma3:12b-cloud", "google/gemma-3-12b-it"],
  },
  "gemma3-27b": {
    family: "Gemma 3", size: 27,
    aliases: ["gemma3:27b", "gemma3:27b-cloud", "google/gemma-3-27b-it"],
  },
  "gemma4-e2b": { family: "Gemma 4", variant: "E2B", size: 2, estimated: true, aliases: ["gemma4:e2b"] },
  "gemma4-e4b": { family: "Gemma 4", variant: "E4B", size: 4, estimated: true, aliases: ["gemma4:e4b"] },
  "gemma4-26b-a4b": {
    family: "Gemma 4", size: 26, estimated: true,
    aliases: ["google/gemma-4-26b-a4b-it"],
  },
  "gemma4-31b": {
    family: "Gemma 4", size: 31, estimated: true,
    aliases: ["google/gemma-4-31b-it"],
  },

  // ── OpenAI GPT-OSS (open-weight MoE) ─────────────────────────────────────
  "gpt-oss-20b": {
    family: "GPT-OSS", size: 20,
    aliases: ["gpt-oss:20b-cloud", "openai/gpt-oss-20b"],
  },
  "gpt-oss-120b": {
    family: "GPT-OSS", size: 120,
    aliases: ["gpt-oss:120b-cloud", "openai/gpt-oss-120b"],
  },

  // ── AllenAI ──────────────────────────────────────────────────────────────
  "olmo-3-32b-think": {
    family: "OLMo 3", variant: "Think", size: 32,
    aliases: ["allenai/olmo-3-32b-think"],
  },

  // ── HuggingFace SmolLM ───────────────────────────────────────────────────
  "smollm-135m": { family: "SmolLM", size: 0.135, aliases: ["HuggingFaceTB/SmolLM-135M-Instruct"] },
  "smollm2-135m": { family: "SmolLM 2", size: 0.135, aliases: ["HuggingFaceTB/SmolLM2-135M-Instruct"] },
  "smollm2-360m": { family: "SmolLM 2", size: 0.360, aliases: ["HuggingFaceTB/SmolLM2-360M-Instruct"] },
}

// ── Canonical name resolution ────────────────────────────────────────────────

const PROVIDER_PREFIXES = [
  "anthropic/", "openai/", "google/", "meta-llama/",
  "allenai/", "x-ai/", "qwen/", "moonshotai/",
  "z-ai/", "huggingfacetb/", "mistralai/", "deepseek/",
  "cohere/", "minimax/", "ai21/", "microsoft/",
]

/** Build alias → canonical index once at module load. */
const ALIAS_TO_CANONICAL: Record<string, string> = (() => {
  const index: Record<string, string> = {}
  for (const [canonical, entry] of Object.entries(KNOWN_MODELS)) {
    index[canonical.toLowerCase()] = canonical
    for (const alias of entry.aliases ?? []) {
      index[alias.toLowerCase()] = canonical
    }
  }
  return index
})()

/**
 * Common trailing tokens we strip when resolving an unknown raw name. Order
 * matters: `-instruct` is checked before `-it` etc. We deliberately keep this
 * list short — explicit aliases in `KNOWN_MODELS` should be the primary path,
 * this is just a safety net for new provider tags.
 */
const TRAILING_TUNING_SUFFIXES = ["-instruct", "-chat", "-it"]

/** Port of carwash_matrix.py:canonical_model(). Returns a stable canonical name. */
export function canonicalModelName(raw: string): string {
  const lower = raw.toLowerCase()
  if (ALIAS_TO_CANONICAL[lower]) return ALIAS_TO_CANONICAL[lower]

  // Strip a known provider prefix, swap colons for dashes
  let name = lower
  for (const prefix of PROVIDER_PREFIXES) {
    if (name.startsWith(prefix)) {
      name = name.slice(prefix.length)
      break
    }
  }
  name = name.replace(/:/g, "-")
  if (ALIAS_TO_CANONICAL[name]) return ALIAS_TO_CANONICAL[name]

  // Fallback: drop a trailing tuning suffix (`-instruct`, `-chat`, `-it`) and retry
  for (const suffix of TRAILING_TUNING_SUFFIXES) {
    if (name.endsWith(suffix)) {
      const stripped = name.slice(0, -suffix.length)
      if (ALIAS_TO_CANONICAL[stripped]) return ALIAS_TO_CANONICAL[stripped]
    }
  }
  return name
}

/** Resolve a raw or canonical name to its full entry, or null if unknown. */
export function getModelInfo(raw: string): ModelEntry | null {
  const canonical = canonicalModelName(raw)
  return KNOWN_MODELS[canonical] ?? null
}

// ── Size lookup (back-compat) ────────────────────────────────────────────────

/** Regex to extract size from model name as a fallback, e.g. "27b" → 27e9. */
const SIZE_PATTERN = /(\d+(?:\.\d+)?)\s*([bBmM])\b/

export function getModelSize(name: string): number | null {
  const info = getModelInfo(name)
  if (info) return info.size * 1e9

  // Regex fallback: extract "Nb" pattern from a raw name we don't know
  const match = name.toLowerCase().match(SIZE_PATTERN)
  if (match) {
    const value = parseFloat(match[1])
    const unit = match[2].toLowerCase()
    if (unit === "b") return value * 1e9
    if (unit === "m") return value * 1e6
  }
  return null
}

export function formatParamCount(count: number): string {
  if (count >= 1e12) return `${(count / 1e12).toFixed(1)}T`
  if (count >= 1e9) return `${(count / 1e9).toFixed(1)}B`
  if (count >= 1e6) return `${(count / 1e6).toFixed(0)}M`
  return `${count}`
}

/** Format a model entry's size for badge display: "~27B" or "400B". */
export function formatModelSize(entry: ModelEntry): string {
  const sized = formatParamCount(entry.size * 1e9)
  return entry.estimated ? `~${sized}` : sized
}

// ── Family colour palette ────────────────────────────────────────────────────

/**
 * Explicit colour assignment per known family.
 * Picked to stay distinguishable against both light and dark backgrounds.
 * Unknown families fall back to a deterministic hash → HSL rotation.
 */
const FAMILY_COLORS: Record<string, string> = {
  // Meta
  "Llama 4":        "#1e88e5",
  "Llama 3.1":      "#1976d2",
  "Llama 3.3":      "#1565c0",
  // DeepSeek
  "DeepSeek R1":    "#6a1b9a",
  "DeepSeek V3":    "#8e24aa",
  // Mistral
  "Mistral":        "#fb8c00",
  // Microsoft
  "Phi 4":          "#00897b",
  // Cohere
  "Command":        "#d81b60",
  // Qwen
  "Qwen 2.5":       "#4e7a4a",
  "Qwen 2.5 VL":    "#4e7a4a",
  "Qwen 3":         "#689f38",
  "Qwen 3 VL":      "#7cb342",
  "Qwen 3.5":       "#9ccc65",
  // Zhipu
  "GLM 4.5":        "#00acc1",
  "GLM 4.6":        "#00838f",
  "GLM 4.7":        "#006064",
  "GLM 5":          "#26c6da",
  // MiniMax
  "MiniMax":        "#5d4037",
  // Moonshot
  "Kimi":           "#7b1fa2",
  // xAI
  "Grok 3":         "#455a64",
  "Grok 4":         "#37474f",
  // AI21
  "Jamba":          "#afb42b",
  // Anthropic
  "Claude Haiku":   "#ef6c00",
  "Claude Sonnet":  "#e64a19",
  "Claude Opus":    "#bf360c",
  // OpenAI
  "GPT 3.5":        "#43a047",
  "GPT 4":          "#2e7d32",
  "GPT 4o":         "#388e3c",
  "GPT 4.1":        "#1b5e20",
  "GPT 5":          "#0d47a1",
  "GPT 5.1":        "#0c3e87",
  "GPT 5.2":        "#0a356f",
  "GPT 5.3":        "#082c57",
  "GPT 5.4":        "#06233f",
  "GPT-OSS":        "#5e35b1",
  "o1":             "#3949ab",
  "o3":             "#303f9f",
  "o4":             "#283593",
  // Google
  "Gemini 2.0":     "#c62828",
  "Gemini 2.5":     "#b71c1c",
  "Gemini 3":       "#d32f2f",
  "Gemini 3.1":     "#e53935",
  "Gemma 2":        "#757575",
  "Gemma 3":        "#616161",
  "Gemma 4":        "#424242",
  // AllenAI
  "OLMo 3":         "#795548",
  // HF
  "SmolLM":         "#ffb300",
  "SmolLM 2":       "#ff8f00",
}

/** Stable colour for a family, with a hash-to-HSL fallback for unknown families. */
export function getFamilyColor(family: string): string {
  const explicit = FAMILY_COLORS[family]
  if (explicit) return explicit
  // Deterministic fallback: hash string → hue
  let hash = 0
  for (let i = 0; i < family.length; i++) {
    hash = (hash * 31 + family.charCodeAt(i)) | 0
  }
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 55%, 45%)`
}

/** Convenience: resolve a raw model name all the way to its family colour. */
export function getModelFamilyColor(rawName: string): string {
  const info = getModelInfo(rawName)
  return info ? getFamilyColor(info.family) : "#9ca3af" // neutral grey
}
