import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchResults, fetchResult, analyzeResults, generateReport, fetchReports } from "@/api/results"
import type { AnalyzeRequest } from "@/types"

export function useResults() {
  return useQuery({
    queryKey: ["results"],
    queryFn: fetchResults,
    refetchOnWindowFocus: true,
  })
}

export function useResult(filename: string | null) {
  return useQuery({
    queryKey: ["result", filename],
    queryFn: () => fetchResult(filename!),
    enabled: !!filename,
  })
}

export function useAnalyzeResults() {
  return useMutation({
    mutationFn: (req: AnalyzeRequest) => analyzeResults(req),
  })
}

export function useGenerateReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: AnalyzeRequest) => generateReport(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  })
}

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
    refetchOnWindowFocus: true,
  })
}
