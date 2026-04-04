import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchTestsets, fetchTestset, deleteTestset, generateTestset, uploadYaml, uploadGz } from "@/api/testsets"
import type { GenerateRequest } from "@/types"

export function useTestsets() {
  return useQuery({
    queryKey: ["testsets"],
    queryFn: fetchTestsets,
    refetchOnWindowFocus: true,
  })
}

export function useTestset(filename: string | null, page: number = 1, pageSize: number = 50) {
  return useQuery({
    queryKey: ["testset", filename, page, pageSize],
    queryFn: () => fetchTestset(filename!, page, pageSize),
    enabled: !!filename,
  })
}

export function useDeleteTestset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (filename: string) => deleteTestset(filename),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testsets"] }),
  })
}

export function useGenerateTestset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: GenerateRequest) => generateTestset(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testsets"] }),
  })
}

export function useUploadYaml() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadYaml(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testsets"] }),
  })
}

export function useUploadGz() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadGz(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testsets"] }),
  })
}
