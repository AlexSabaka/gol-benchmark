import { get, post, del } from "./client"
import type { ResultSummary, ResultDetail, AnalyzeRequest, AnalyzeResponse, ReportInfo, GenerateReportResponse, ReanalyzeResponse, JudgeRequest, JudgeSubmitResponse, JudgeSummary, JudgeResult } from "@/types"

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

export function submitJudge(req: JudgeRequest): Promise<JudgeSubmitResponse> {
  return post<JudgeSubmitResponse>("/api/results/judge", req)
}

export function fetchJudgeResults(): Promise<JudgeSummary[]> {
  return get<JudgeSummary[]>("/api/results/judge-results")
}

export function fetchJudgeResult(filename: string): Promise<JudgeResult> {
  return get<JudgeResult>(`/api/results/judge-results/${encodeURIComponent(filename)}`)
}
