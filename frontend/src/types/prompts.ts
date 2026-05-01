/** Prompt Studio — system prompts (versioned, multi-language). */

export type PromptSummary = {
  id: string
  name: string
  slug: string
  description: string
  is_builtin: boolean
  tags: string[]
  archived_at: string | null
  created_at: string
  created_by: string | null
  updated_at: string
  latest_version: number | null
  /** Languages with non-empty content on the latest version. */
  language_codes: string[]
}

export type PromptDetail = PromptSummary & {
  content: Record<string, string>
  change_note: string
}

export type PromptVersionMeta = {
  version: number
  parent_version: number | null
  change_note: string
  created_at: string
  created_by: string | null
}

export type PromptVersionDetail = PromptVersionMeta & {
  prompt_id: string
  content: Record<string, string>
}

export type CreatePromptRequest = {
  name: string
  slug?: string | null
  description?: string
  content: Record<string, string>
  tags?: string[]
  created_by?: string | null
}

export type CreateVersionRequest = {
  content: Record<string, string>
  change_note?: string
  parent_version?: number | null
  created_by?: string | null
}

export type UpdatePromptRequest = {
  name?: string | null
  description?: string | null
  tags?: string[] | null
}

/** Display order for languages — matches the dot-strip order on cards/tabs. */
export const LANGUAGE_ORDER = ["en", "es", "fr", "de", "zh", "ua"] as const
export type LanguageCode = (typeof LANGUAGE_ORDER)[number]

export const LANGUAGE_NAMES: Record<LanguageCode, string> = {
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  zh: "Chinese",
  ua: "Ukrainian",
}
