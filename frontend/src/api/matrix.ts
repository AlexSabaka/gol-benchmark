import { post } from "./client"
import type { MatrixRunRequest, MatrixRunResponse } from "@/types"

export function runMatrixExecution(req: MatrixRunRequest): Promise<MatrixRunResponse> {
  return post<MatrixRunResponse>("/api/matrix/run", req)
}