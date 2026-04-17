import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchJobs, fetchJobStatus, runBenchmark, cancelJob, pauseJob, resumeJob, stopAndDumpJob } from "@/api/jobs"
import type { RunRequest, Job } from "@/types"

export function useJobs(polling = false) {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: polling ? 3000 : false,
  })
}

export function useJobStatus(jobId: string | null, enabled = false) {
  return useQuery({
    queryKey: ["job-status", jobId],
    queryFn: () => fetchJobStatus(jobId!),
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      const state = (query.state.data as Job | undefined)?.state
      if (state === "completed" || state === "failed" || state === "cancelled") return false
      return 3000
    },
  })
}

export function useRunBenchmark() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: RunRequest) => runBenchmark(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function useCancelJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => cancelJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function usePauseJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => pauseJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function useResumeJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => resumeJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function useStopAndDumpJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => stopAndDumpJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}
