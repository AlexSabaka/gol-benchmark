import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  archivePrompt,
  createPrompt,
  createPromptVersion,
  fetchPrompt,
  fetchPromptVersion,
  fetchPromptVersions,
  fetchPrompts,
  restorePrompt,
  translatePromptText,
  updatePromptMetadata,
} from "@/api/prompts"
import type {
  CreatePromptRequest,
  CreateVersionRequest,
  UpdatePromptRequest,
} from "@/types"

const PROMPTS_KEY = "prompts"

export const usePrompts = (includeArchived = false) =>
  useQuery({
    queryKey: [PROMPTS_KEY, { archived: includeArchived }],
    queryFn: () => fetchPrompts(includeArchived),
    staleTime: 30_000,
  })

export const usePrompt = (id: string | undefined) =>
  useQuery({
    queryKey: [PROMPTS_KEY, id],
    queryFn: () => fetchPrompt(id as string),
    enabled: Boolean(id),
    staleTime: 30_000,
  })

export const usePromptVersions = (id: string | undefined) =>
  useQuery({
    queryKey: [PROMPTS_KEY, id, "versions"],
    queryFn: () => fetchPromptVersions(id as string),
    enabled: Boolean(id),
    staleTime: 30_000,
  })

/** Versions are immutable on the backend → never refetch a fetched version. */
export const usePromptVersion = (
  id: string | undefined,
  version: number | null | undefined,
) =>
  useQuery({
    queryKey: [PROMPTS_KEY, id, "versions", version],
    queryFn: () => fetchPromptVersion(id as string, version as number),
    enabled: Boolean(id) && version != null,
    staleTime: Infinity,
  })

export const useCreatePrompt = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreatePromptRequest) => createPrompt(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: [PROMPTS_KEY] }),
  })
}

export const useCreatePromptVersion = (id: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateVersionRequest) => createPromptVersion(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY] })
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY, id] })
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY, id, "versions"] })
    },
  })
}

export const useUpdatePromptMetadata = (id: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UpdatePromptRequest) => updatePromptMetadata(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY] })
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY, id] })
    },
  })
}

export const useArchivePrompt = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => archivePrompt(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY] })
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY, id] })
    },
  })
}

export const useRestorePrompt = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => restorePrompt(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY] })
      qc.invalidateQueries({ queryKey: [PROMPTS_KEY, id] })
    },
  })
}

export const useTranslatePrompt = () =>
  useMutation({
    mutationFn: (args: {
      text: string
      sourceLang: string
      targetLangs: string[]
    }) =>
      translatePromptText(args.text, args.sourceLang, args.targetLangs),
  })
