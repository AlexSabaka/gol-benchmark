import { get, post, del } from "./client"
import type { ResultSummary, ResultDetail, AnalyzeRequest, AnalyzeResponse, ReportInfo, GenerateReportResponse, ReanalyzeResponse } from "@/types"

export function fetchResults(): Promise<ResultSummary[]> {
  return get<ResultSummary[]>("/api/results")
}

export function fetchResult(filename: string): Promise<ResultDetail> {
  return get<ResultDetail>(`/api/results/${encodeURIComponent(filename)}`)
}

export function analyzeResults(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>("/api/results/analyze", req)
}

export function generateReport(req: AnalyzeRequest): Promise<GenerateReportResponse> {
  return post<GenerateReportResponse>("/api/results/generate-report", req)
}

export function fetchReports(): Promise<ReportInfo[]> {
  return get<ReportInfo[]>("/api/results/reports")
}

export function reanalyzeResult(filename: string): Promise<ReanalyzeResponse> {
  return post<ReanalyzeResponse>(`/api/results/${encodeURIComponent(filename)}/reanalyze`)
}

export function deleteResult(filename: string): Promise<{ status: string; filename: string }> {
  return del(`/api/results/${encodeURIComponent(filename)}`)
}

export function reportUrl(filename: string): string {
  return `/api/results/report/${encodeURIComponent(filename)}`
}
