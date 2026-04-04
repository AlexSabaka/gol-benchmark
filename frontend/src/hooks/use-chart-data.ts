import { useQuery } from "@tanstack/react-query"
import { analyzeResults } from "@/api/results"
import { getModelSize } from "@/lib/model-sizes"
import type { AnalyzeResponse, HeatmapCell, ScatterPoint, DimensionBucket } from "@/types"

export interface ChartData {
  raw: AnalyzeResponse
  models: string[]
  tasks: string[]
  heatmapData: HeatmapCell[]
  scatterData: ScatterPoint[]
  getBarData: (task: string | null) => BarDataPoint[]
  dimensionBreakdowns: {
    language: Record<string, DimensionBucket>
    user_style: Record<string, DimensionBucket>
    system_style: Record<string, DimensionBucket>
  }
}

export interface BarDataPoint {
  model: string
  accuracy: number
  correct: number
  total: number
}

function transformAnalyzeResponse(data: AnalyzeResponse): ChartData {
  const models = Object.keys(data.models).sort()
  const taskSet = new Set<string>()

  // Build heatmap data and collect tasks
  const heatmapData: HeatmapCell[] = []
  for (const [model, analysis] of Object.entries(data.models)) {
    for (const [task, breakdown] of Object.entries(analysis.task_breakdown)) {
      taskSet.add(task)
      heatmapData.push({
        model,
        task,
        accuracy: breakdown.accuracy,
        total: breakdown.total,
      })
    }
  }
  const tasks = [...taskSet].sort()

  // Build scatter data (model param count vs accuracy)
  const scatterData: ScatterPoint[] = models.map((model) => ({
    model,
    paramCount: getModelSize(model),
    accuracy: data.models[model].accuracy,
  }))

  // Bar data factory filtered by task
  const getBarData = (task: string | null): BarDataPoint[] => {
    if (!task) {
      // Overall accuracy
      return models
        .map((model) => ({
          model,
          accuracy: data.models[model].accuracy,
          correct: data.models[model].correct,
          total: data.models[model].total_tests,
        }))
        .sort((a, b) => b.accuracy - a.accuracy)
    }
    return models
      .filter((model) => data.models[model].task_breakdown[task])
      .map((model) => {
        const tb = data.models[model].task_breakdown[task]
        return {
          model,
          accuracy: tb.accuracy,
          correct: Math.round(tb.accuracy * tb.total),
          total: tb.total,
        }
      })
      .sort((a, b) => b.accuracy - a.accuracy)
  }

  const dimensionBreakdowns = data.dimension_breakdowns ?? {
    language: {}, user_style: {}, system_style: {},
  }

  return { raw: data, models, tasks, heatmapData, scatterData, getBarData, dimensionBreakdowns }
}

export function useChartData(filenames: string[]) {
  return useQuery({
    queryKey: ["chart-data", ...filenames.sort()],
    queryFn: async () => {
      const response = await analyzeResults({
        result_filenames: filenames,
        comparison: true,
      })
      return transformAnalyzeResponse(response)
    },
    enabled: filenames.length > 0,
    staleTime: 5 * 60 * 1000, // 5 min cache
  })
}
