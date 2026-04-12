import { useMutation, useQueryClient } from "@tanstack/react-query"

import { runMatrixExecution } from "@/api/matrix"
import type { MatrixRunRequest } from "@/types"

export function useRunMatrixExecution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: MatrixRunRequest) => runMatrixExecution(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] })
      qc.invalidateQueries({ queryKey: ["testsets"] })
    },
  })
}