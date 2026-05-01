import { get, post, patch } from "./client"
import type {
  CreatePromptRequest,
  CreateVersionRequest,
  PromptDetail,
  PromptSummary,
  PromptVersionDetail,
  PromptVersionMeta,
  UpdatePromptRequest,
} from "@/types"

export const fetchPrompts = (
  includeArchived = false,
): Promise<PromptSummary[]> =>
  get<PromptSummary[]>("/api/prompts", {
    include_archived: includeArchived ? "true" : "",
  })

export const fetchPrompt = (id: string): Promise<PromptDetail> =>
  get<PromptDetail>(`/api/prompts/${id}`)

export const fetchPromptVersions = (
  id: string,
): Promise<PromptVersionMeta[]> =>
  get<PromptVersionMeta[]>(`/api/prompts/${id}/versions`)

export const fetchPromptVersion = (
  id: string,
  version: number,
): Promise<PromptVersionDetail> =>
  get<PromptVersionDetail>(`/api/prompts/${id}/versions/${version}`)

export const createPrompt = (
  body: CreatePromptRequest,
): Promise<{ prompt_id: string }> => post("/api/prompts", body)

export const createPromptVersion = (
  id: string,
  body: CreateVersionRequest,
): Promise<{ prompt_id: string; version: number }> =>
  post(`/api/prompts/${id}/versions`, body)

export const updatePromptMetadata = (
  id: string,
  body: UpdatePromptRequest,
): Promise<{ ok: boolean }> => patch(`/api/prompts/${id}`, body)

export const archivePrompt = (id: string): Promise<{ ok: boolean }> =>
  post(`/api/prompts/${id}/archive`, {})

export const restorePrompt = (id: string): Promise<{ ok: boolean }> =>
  post(`/api/prompts/${id}/restore`, {})

export interface TranslatePromptResponse {
  translations: Record<string, string>
  provider: string
  failed: string[]
}

export const translatePromptText = (
  text: string,
  sourceLang: string,
  targetLangs: string[],
): Promise<TranslatePromptResponse> =>
  post<TranslatePromptResponse>("/api/prompts/translate", {
    text,
    source_lang: sourceLang,
    target_langs: targetLangs,
  })
