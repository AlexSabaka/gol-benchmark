import { useQuery } from "@tanstack/react-query"
import { fetchMetadata } from "@/api/metadata"

export function useMetadata() {
  return useQuery({
    queryKey: ["metadata"],
    queryFn: fetchMetadata,
    staleTime: Infinity,
  })
}
