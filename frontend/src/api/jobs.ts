import { get, post } from "./client"
import type { Job, RunRequest, RunResponse } from "@/types"

export function fetchJobs(): Promise<Job[]> {
  return get<Job[]>("/api/jobs")
}

export function fetchJobStatus(jobId: string): Promise<Job> {
  return get<Job>(`/api/jobs/${encodeURIComponent(jobId)}/status`)
}

export function runBenchmark(req: RunRequest): Promise<RunResponse> {
  return post<RunResponse>("/api/jobs/run", req)
}

export function cancelJob(jobId: string): Promise<{ status: string; job_id: string }> {
  return post(`/api/jobs/${encodeURIComponent(jobId)}/cancel`)
}

export function pauseJob(jobId: string): Promise<{ status: string; job_id: string }> {
  return post(`/api/jobs/${encodeURIComponent(jobId)}/pause`)
}

export function resumeJob(jobId: string): Promise<{ status: string; job_id: string; new_job_id: string }> {
  return post(`/api/jobs/${encodeURIComponent(jobId)}/resume`)
}
