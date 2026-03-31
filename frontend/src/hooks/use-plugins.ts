import { useQuery } from "@tanstack/react-query"
import { fetchPlugins, fetchPluginSchema } from "@/api/plugins"

export function usePlugins() {
  return useQuery({
    queryKey: ["plugins"],
    queryFn: fetchPlugins,
    staleTime: Infinity,
  })
}

export function usePluginSchema(taskType: string | null) {
  return useQuery({
    queryKey: ["plugin-schema", taskType],
    queryFn: () => fetchPluginSchema(taskType!),
    enabled: !!taskType,
    staleTime: Infinity,
  })
}
