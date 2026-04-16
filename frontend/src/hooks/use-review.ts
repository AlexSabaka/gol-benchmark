import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  fetchReviewCases,
  saveAnnotation,
  fetchAnnotations,
  fetchImprovementReport,
  deleteAnnotations,
  translate,
} from "@/api/human-review"
import type {
  Annotation,
  AnnotationFile,
  ImprovementReport,
  ReviewCasesResponse,
  TranslateRequest,
  TranslateResponse,
} from "@/types"

export function useReviewCases(
  fileIds: string[],
  opts: { skipCorrect: boolean; skipEmpty: boolean; matchTypes?: string[] },
) {
  const key = fileIds.slice().sort().join(",")
  const matchKey = (opts.matchTypes ?? []).slice().sort().join(",")
  return useQuery<ReviewCasesResponse>({
    queryKey: ["review-cases", key, opts.skipCorrect, opts.skipEmpty, matchKey],
    queryFn: () =>
      fetchReviewCases({
        file_ids: fileIds,
        skip_correct: opts.skipCorrect,
        skip_empty: opts.skipEmpty,
        match_types: opts.matchTypes,
      }),
    enabled: fileIds.length > 0,
    // The case list is a snapshot — no background refetching while annotating.
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  })
}

export function useSaveAnnotation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { result_file_id: string; case_id: string; annotation: Annotation }) =>
      saveAnnotation(body),
    onSuccess: () => {
      // Refresh row-level `has_annotations` flag on the Results page.
      qc.invalidateQueries({ queryKey: ["results"] })
    },
  })
}

export function useAnnotations(result_file_id: string | null) {
  return useQuery<AnnotationFile>({
    queryKey: ["annotations", result_file_id],
    queryFn: () => fetchAnnotations(result_file_id!),
    enabled: !!result_file_id,
  })
}

export function useImprovementReport(fileIds: string[], enabled: boolean) {
  const key = fileIds.slice().sort().join(",")
  return useQuery<ImprovementReport>({
    queryKey: ["improvement-report", key],
    queryFn: () => fetchImprovementReport({ result_file_ids: fileIds }),
    enabled: enabled && fileIds.length > 0,
    refetchOnWindowFocus: false,
  })
}

export function useDeleteAnnotations() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (result_file_id: string) => deleteAnnotations(result_file_id),
    onSuccess: (_data, filename) => {
      // The `has_annotations` flag on the Results list changes — refresh it.
      qc.invalidateQueries({ queryKey: ["results"] })
      qc.invalidateQueries({ queryKey: ["annotations", filename] })
    },
  })
}

/**
 * Translate an arbitrary piece of text. Results cache forever per (text, target)
 * so toggling the "translate" panel back and forth is free. The source-lang
 * axis is folded into the query key so two cases in different languages can't
 * share a cache slot by accident.
 */
export function useTranslation(
  text: string,
  sourceLang: string | null | undefined,
  targetLang: string,
  enabled: boolean,
) {
  return useQuery<TranslateResponse>({
    queryKey: ["translate", sourceLang ?? "auto", targetLang, text],
    queryFn: () =>
      translate({ text, source_lang: sourceLang ?? null, target_lang: targetLang } satisfies TranslateRequest),
    enabled: enabled && !!text && text.trim().length > 0,
    // Translations are deterministic for a given (text, langs) triple.
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    retry: false,
  })
}
