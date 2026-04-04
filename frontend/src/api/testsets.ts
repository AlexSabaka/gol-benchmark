import { get, post, postFormData, del } from "./client"
import type { TestsetSummary, TestsetDetail, GenerateRequest, GenerateResponse } from "@/types"

export function fetchTestsets(): Promise<TestsetSummary[]> {
  return get<TestsetSummary[]>("/api/testsets")
}

export function fetchTestset(filename: string, page: number = 1, pageSize: number = 50): Promise<TestsetDetail> {
  return get<TestsetDetail>(`/api/testsets/${encodeURIComponent(filename)}?page=${page}&page_size=${pageSize}`)
}

export function fetchPromptFromUrl(url: string): Promise<{ status: string; text: string }> {
  return post("/api/testsets/fetch-prompt-url", { url })
}

export function deleteTestset(filename: string): Promise<{ status: string; filename: string }> {
  return del(`/api/testsets/${encodeURIComponent(filename)}`)
}

export function generateTestset(req: GenerateRequest): Promise<GenerateResponse> {
  return post<GenerateResponse>("/api/testsets/generate", req)
}

export function uploadYaml(file: File): Promise<GenerateResponse> {
  const fd = new FormData()
  fd.append("file", file)
  return postFormData<GenerateResponse>("/api/testsets/upload-yaml", fd)
}

export function uploadGz(file: File): Promise<{ status: string; filename: string; path: string }> {
  const fd = new FormData()
  fd.append("file", file)
  return postFormData("/api/testsets/upload-gz", fd)
}
