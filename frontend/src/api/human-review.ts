import { get, post, del } from "./client"
import type {
  Annotation,
  AnnotationFile,
  DeleteAnnotationsResponse,
  ImprovementReport,
  ReviewCasesResponse,
  TranslateRequest,
  TranslateResponse,
} from "@/types"

export function fetchReviewCases(params: {
  file_ids: string[]
  skip_correct?: boolean
  skip_empty?: boolean
  /** Filter to specific parser match_type values (omit for "all"). */
  match_types?: string[]
}): Promise<ReviewCasesResponse> {
  const query: Record<string, string> = {
    file_ids: params.file_ids.join(","),
    skip_correct: params.skip_correct ? "true" : "false",
    skip_empty: params.skip_empty === false ? "false" : "true",
  }
  if (params.match_types && params.match_types.length > 0) {
    query.match_types = params.match_types.join(",")
  }
  return get<ReviewCasesResponse>("/api/human-review/cases", query)
}

export function saveAnnotation(body: {
  result_file_id: string
  case_id: string
  annotation: Annotation
}): Promise<{ status: string; case_id: string; annotation_file: string }> {
  return post("/api/human-review/annotate", body)
}

export function fetchAnnotations(result_file_id: string): Promise<AnnotationFile> {
  return get<AnnotationFile>(`/api/human-review/annotations/${encodeURIComponent(result_file_id)}`)
}

export function fetchImprovementReport(body: {
  result_file_ids: string[]
}): Promise<ImprovementReport> {
  return post<ImprovementReport>("/api/human-review/report", body)
}

export function deleteAnnotations(result_file_id: string): Promise<DeleteAnnotationsResponse> {
  return del<DeleteAnnotationsResponse>(
    `/api/human-review/annotations/${encodeURIComponent(result_file_id)}`,
  )
}

export function translate(body: TranslateRequest): Promise<TranslateResponse> {
  return post<TranslateResponse>("/api/human-review/translate", body)
}
