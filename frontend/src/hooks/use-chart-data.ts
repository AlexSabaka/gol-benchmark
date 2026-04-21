import { useQuery } from "@tanstack/react-query"
import { analyzeResults } from "@/api/results"
import { canonicalModelName, getModelSize } from "@/lib/model-sizes"
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
  /** Raw provider tags that merged into this canonical entry. */
  aliases?: string[]
}

/** Per-canonical aggregation bucket used while merging raw provider tags. */
interface CanonicalBucket {
  aliases: string[]
  correct: number
  total: number
  /** Per-task merged counts (accuracy is derived later as correct / total). */
  taskBreakdown: Record<string, { correct: number; total: number }>
}

function bucketByCanonical(raw: AnalyzeResponse): Record<string, CanonicalBucket> {
  const byCanonical: Record<string, CanonicalBucket> = {}

  for (const [rawModel, analysis] of Object.entries(raw.models)) {
    const canonical = canonicalModelName(rawModel)
    const bucket = (byCanonical[canonical] ??= {
      aliases: [],
      correct: 0,
      total: 0,
      taskBreakdown: {},
    })
    bucket.aliases.push(rawModel)
    bucket.correct += analysis.correct
    bucket.total += analysis.total_tests

    for (const [task, tb] of Object.entries(analysis.task_breakdown)) {
      const slot = (bucket.taskBreakdown[task] ??= { correct: 0, total: 0 })
      slot.correct += tb.correct ?? Math.round(tb.accuracy * tb.total)
      slot.total += tb.total
    }
  }

  return byCanonical
}

function transformAnalyzeResponse(data: AnalyzeResponse): ChartData {
  const byCanonical = bucketByCanonical(data)
  const models = Object.keys(byCanonical).sort()

  // Tasks — collected across merged buckets
  const taskSet = new Set<string>()
  for (const bucket of Object.values(byCanonical)) {
    for (const task of Object.keys(bucket.taskBreakdown)) taskSet.add(task)
  }
  const tasks = [...taskSet].sort()

  // Heatmap: one cell per (canonical model × task), accuracy = weighted by total
  const heatmapData: HeatmapCell[] = []
  for (const model of models) {
    const bucket = byCanonical[model]
    for (const [task, slot] of Object.entries(bucket.taskBreakdown)) {
      heatmapData.push({
        model,
        task,
        accuracy: slot.total > 0 ? slot.correct / slot.total : 0,
        total: slot.total,
        aliases: bucket.aliases.length > 1 ? [...bucket.aliases] : undefined,
      })
    }
  }

  // Scatter: one dot per canonical, accuracy = correct / total across all aliases
  const scatterData: ScatterPoint[] = models.map((model) => {
    const bucket = byCanonical[model]
    return {
      model,
      paramCount: getModelSize(model),
      accuracy: bucket.total > 0 ? bucket.correct / bucket.total : 0,
      total: bucket.total,
      aliases: bucket.aliases.length > 1 ? [...bucket.aliases] : undefined,
    }
  })

  // Bar data factory: overall or per-task, sorted by accuracy desc
  const getBarData = (task: string | null): BarDataPoint[] => {
    if (!task) {
      return models
        .map((model) => {
          const bucket = byCanonical[model]
          return {
            model,
            accuracy: bucket.total > 0 ? bucket.correct / bucket.total : 0,
            correct: bucket.correct,
            total: bucket.total,
            aliases: bucket.aliases.length > 1 ? [...bucket.aliases] : undefined,
          }
        })
        .sort((a, b) => b.accuracy - a.accuracy)
    }
    return models
      .filter((model) => byCanonical[model].taskBreakdown[task])
      .map((model) => {
        const bucket = byCanonical[model]
        const slot = bucket.taskBreakdown[task]
        return {
          model,
          accuracy: slot.total > 0 ? slot.correct / slot.total : 0,
          correct: slot.correct,
          total: slot.total,
          aliases: bucket.aliases.length > 1 ? [...bucket.aliases] : undefined,
        }
      })
      .sort((a, b) => b.accuracy - a.accuracy)
  }

  // Dimension breakdowns (per-language, per-style) aren't keyed by model — pass through
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
