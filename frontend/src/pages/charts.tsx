import { useMemo, useCallback, useDeferredValue, useEffect } from "react"
import { useSearchParams } from "react-router"
import { PageHeader } from "@/components/layout/page-header"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Card, CardContent } from "@/components/ui/card"
import { ChartCard } from "@/components/charts/chart-card"
import { ChartFilters } from "@/components/charts/chart-filters"
import { AccuracyHeatmap } from "@/components/charts/accuracy-heatmap"
import { ModelBarChart } from "@/components/charts/model-bar-chart"
import { ScalingScatter } from "@/components/charts/scaling-scatter"
import { DimensionBarChart } from "@/components/charts/dimension-bar-chart"
import { languageLabel } from "@/components/language-filter-chip"
import { useResults } from "@/hooks/use-results"
import { useChartData } from "@/hooks/use-chart-data"
import { makeStorageKey, useLocalStorageSetState, useLocalStorageState } from "@/lib/local-storage"
import { formatPercent } from "@/lib/utils"
import { canonicalModelName, getModelSize } from "@/lib/model-sizes"
import {
  Loader2,
  Grid3X3,
  BarChart3,
  ScatterChart,
  Search,
  ChevronRight,
  Check,
  Languages,
} from "lucide-react"
import type { ResultSummary } from "@/types"

type HeatmapAxis = "model" | "task"
type DimensionTab = "language" | "user_style" | "system_style"
type ChartTab = "heatmap" | "bars" | "scatter" | "dimensions"
type ScatterLabelMode = "hover" | "smart" | "all"

/** Group results by model name */
function groupByModel(results: ResultSummary[]): Record<string, ResultSummary[]> {
  const groups: Record<string, ResultSummary[]> = {}
  for (const r of results) {
    ;(groups[r.model_name] ??= []).push(r)
  }
  // Sort each group by date descending
  for (const arr of Object.values(groups)) {
    arr.sort((a, b) => b.created.localeCompare(a.created))
  }
  return groups
}

export default function ChartsPage() {
  const storageScope = "charts-page"
  const [searchParams] = useSearchParams()
  const { data: results, isLoading: resultsLoading } = useResults()

  // Pre-select from query params
  const initialFiles = useMemo(() => {
    const param = searchParams.get("files")
    return param ? param.split(",").filter(Boolean) : []
  }, [searchParams])

  const [selectedFiles, setSelectedFiles] = useLocalStorageSetState<string>(makeStorageKey(storageScope, "selected-files"), initialFiles)
  const [heatmapX, setHeatmapX] = useLocalStorageState<HeatmapAxis>(makeStorageKey(storageScope, "heatmap-x"), "task")
  const [heatmapY, setHeatmapY] = useLocalStorageState<HeatmapAxis>(makeStorageKey(storageScope, "heatmap-y"), "model")
  const [barTask, setBarTask] = useLocalStorageState<string | null>(makeStorageKey(storageScope, "bar-task"), null)
  const [search, setSearch] = useLocalStorageState<string>(makeStorageKey(storageScope, "search"), "")
  const deferredSearch = useDeferredValue(search)
  const [selectorOpen, setSelectorOpen] = useLocalStorageState<boolean>(makeStorageKey(storageScope, "selector-open"), true)
  const [taskTypeFilter, setTaskTypeFilter] = useLocalStorageSetState<string>(makeStorageKey(storageScope, "task-filter"))
  const [languageFilter, setLanguageFilter] = useLocalStorageSetState<string>(makeStorageKey(storageScope, "language-filter"))
  const [logScale, setLogScale] = useLocalStorageState<boolean>(makeStorageKey(storageScope, "log-scale"), true)
  const [scatterLabelMode, setScatterLabelMode] = useLocalStorageState<ScatterLabelMode>(
    makeStorageKey(storageScope, "scatter-label-mode"),
    "smart",
    {
      sanitize: (value) => (
        value === "hover" || value === "smart" || value === "all"
          ? value
          : "smart"
      ),
    },
  )
  const [dimTab, setDimTab] = useLocalStorageState<DimensionTab>(makeStorageKey(storageScope, "dimension-tab"), "language")
  const [activeTab, setActiveTab] = useLocalStorageState<ChartTab>(makeStorageKey(storageScope, "active-tab"), "heatmap")

  useEffect(() => {
    if (initialFiles.length === 0) return
    setSelectedFiles(new Set(initialFiles))
  }, [initialFiles, setSelectedFiles])

  useEffect(() => {
    if (!results?.length) return

    const valid = new Set(results.map((result) => result.filename))
    setSelectedFiles((previous) => {
      const next = new Set([...previous].filter((filename) => valid.has(filename)))
      if (next.size === previous.size && [...next].every((filename) => previous.has(filename))) {
        return previous
      }
      return next
    })
  }, [results, setSelectedFiles])

  // Apply language filter at file-selection level
  const filenames = useMemo(() => {
    if (languageFilter.size === 0 || !results) return [...selectedFiles]
    // Only include files whose languages overlap with the filter
    return [...selectedFiles].filter((f) => {
      const r = results.find((res) => res.filename === f)
      if (!r?.languages) return true // no language info = include
      return r.languages.some((l) => languageFilter.has(l))
    })
  }, [selectedFiles, languageFilter, results])
  const { data: chartData, isLoading: chartLoading, error } = useChartData(filenames)

  // Extract available filter values from chart data
  const availableTaskTypes = useMemo(
    () => chartData?.tasks ?? [],
    [chartData]
  )
  const availableLanguages = useMemo(() => {
    if (!results) return []
    const langs = new Set<string>()
    for (const r of results) {
      if (selectedFiles.has(r.filename) && r.languages) {
        for (const l of r.languages) langs.add(l)
      }
    }
    return [...langs].sort()
  }, [results, selectedFiles])

  // Apply task type filter to chart data
  const filteredHeatmapData = useMemo(() => {
    if (!chartData) return []
    if (taskTypeFilter.size === 0) return chartData.heatmapData
    return chartData.heatmapData.filter((c) => taskTypeFilter.has(c.task))
  }, [chartData, taskTypeFilter])

  const filteredScatterData = useMemo(() => {
    if (!chartData) return []
    if (taskTypeFilter.size === 0) return chartData.scatterData

    // Re-bucket raw provider tags by canonical model, summing correct/total
    // across only the tasks that pass the filter.
    const buckets: Record<string, { total: number; correct: number; aliases: string[] }> = {}
    for (const [rawModel, analysis] of Object.entries(chartData.raw.models)) {
      const canonical = canonicalModelName(rawModel)
      const b = (buckets[canonical] ??= { total: 0, correct: 0, aliases: [] })
      b.aliases.push(rawModel)
      for (const [task, tb] of Object.entries(analysis.task_breakdown)) {
        if (taskTypeFilter.has(task)) {
          b.total += tb.total
          b.correct += Math.round(tb.accuracy * tb.total)
        }
      }
    }

    return Object.entries(buckets)
      .map(([model, b]) => ({
        model,
        paramCount: getModelSize(model),
        accuracy: b.total > 0 ? b.correct / b.total : 0,
        aliases: b.aliases.length > 1 ? b.aliases : undefined,
      }))
      .filter((d) => d.accuracy > 0)
  }, [chartData, taskTypeFilter])

  const barData = useMemo(() => {
    const raw = chartData?.getBarData(barTask) ?? []
    // If task filter is set and barTask is "all", the bar data shows overall —
    // but we can't filter individual models' overall accuracy by task here
    // since the bar data is pre-aggregated. Task-specific filtering works
    // through the barTask dropdown selector instead.
    return raw
  }, [chartData, barTask])

  // Grouped + filtered results
  const grouped = useMemo(() => {
    if (!results) return {}
    const filtered = deferredSearch
      ? results.filter(
          (r) =>
            r.model_name.toLowerCase().includes(deferredSearch.toLowerCase()) ||
            r.task_types.some((t) => t.toLowerCase().includes(deferredSearch.toLowerCase())) ||
            r.testset_name.toLowerCase().includes(deferredSearch.toLowerCase())
        )
      : results
    return groupByModel(filtered)
  }, [results, deferredSearch])

  const modelNames = useMemo(() => Object.keys(grouped).sort(), [grouped])

  const toggleFile = useCallback((filename: string) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev)
      if (next.has(filename)) next.delete(filename)
      else next.add(filename)
      return next
    })
  }, [setSelectedFiles])

  const toggleModel = useCallback(
    (model: string) => {
      const files = grouped[model] ?? []
      setSelectedFiles((prev) => {
        const next = new Set(prev)
        const allSelected = files.every((f) => next.has(f.filename))
        for (const f of files) {
          if (allSelected) next.delete(f.filename)
          else next.add(f.filename)
        }
        return next
      })
    },
    [grouped, setSelectedFiles]
  )

  const selectAll = () => {
    if (results) setSelectedFiles(new Set(results.map((r) => r.filename)))
  }

  const clearAll = () => setSelectedFiles(new Set())

  const swapAxes = () => {
    setHeatmapX(heatmapY)
    setHeatmapY(heatmapX)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Charts"
        description="Interactive analysis of benchmark results"
      />

      {/* Result selector */}
      <Collapsible open={selectorOpen} onOpenChange={setSelectorOpen}>
        <Card>
          <CardContent className="pt-4 pb-3">
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center justify-between text-sm font-medium hover:text-foreground text-foreground/80 transition-colors">
                <span className="flex items-center gap-2">
                  <ChevronRight
                    className={`h-4 w-4 transition-transform ${selectorOpen ? "rotate-90" : ""}`}
                  />
                  Select Results
                  {selectedFiles.size > 0 && (
                    <Badge variant="secondary">{selectedFiles.size} selected</Badge>
                  )}
                </span>
                <span className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button variant="ghost" size="sm" onClick={selectAll} disabled={resultsLoading}>
                    All
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearAll} disabled={!selectedFiles.size}>
                    Clear
                  </Button>
                </span>
              </button>
            </CollapsibleTrigger>

            <CollapsibleContent>
              <div className="mt-3 space-y-2">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Filter by model, task, or testset..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-8 h-8 text-xs"
                  />
                </div>

                {/* Model groups */}
                {resultsLoading ? (
                  <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading results...
                  </div>
                ) : (
                  <div className="max-h-64 overflow-y-auto rounded border divide-y">
                    {modelNames.map((model) => {
                      const files = grouped[model]
                      const selectedCount = files.filter((f) =>
                        selectedFiles.has(f.filename)
                      ).length
                      const allSelected = selectedCount === files.length
                      return (
                        <div key={model}>
                          {/* Model header row */}
                          <button
                            role="checkbox"
                            aria-checked={allSelected ? "true" : selectedCount > 0 ? "mixed" : "false"}
                            onClick={() => toggleModel(model)}
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs hover:bg-accent/50 transition-colors"
                          >
                            <div
                              className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm border ${
                                allSelected
                                  ? "border-primary bg-primary text-primary-foreground"
                                  : selectedCount > 0
                                    ? "border-primary bg-primary/20"
                                    : "border-muted-foreground/30"
                              }`}
                            >
                              {allSelected && <Check className="h-2.5 w-2.5" />}
                            </div>
                            <span className="font-medium">{model}</span>
                            <span className="text-muted-foreground ml-auto">
                              {files.length} run{files.length > 1 ? "s" : ""}
                            </span>
                          </button>

                          {/* Individual result rows (shown if model has >1 run) */}
                          {files.length > 1 &&
                            files.map((r) => {
                              const checked = selectedFiles.has(r.filename)
                              return (
                                <button
                                  key={r.filename}
                                  role="checkbox"
                                  aria-checked={checked}
                                  onClick={() => toggleFile(r.filename)}
                                  className="flex w-full items-center gap-2 px-3 py-1 pl-8 text-xs hover:bg-accent/50 transition-colors text-muted-foreground"
                                >
                                  <div
                                    className={`flex h-3 w-3 shrink-0 items-center justify-center rounded-sm border ${
                                      checked
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-muted-foreground/30"
                                    }`}
                                  >
                                    {checked && <Check className="h-2 w-2" />}
                                  </div>
                                  <span className="truncate">
                                    {r.task_types.join(", ")}
                                  </span>
                                  <span className="ml-auto shrink-0 tabular-nums">
                                    {formatPercent(r.accuracy)}
                                  </span>
                                  <span className="shrink-0 text-muted-foreground/60">
                                    {r.created.slice(0, 10)}
                                  </span>
                                </button>
                              )
                            })}
                        </div>
                      )
                    })}
                    {modelNames.length === 0 && (
                      <div className="py-4 text-center text-xs text-muted-foreground">
                        {search ? "No results match your filter" : "No results available"}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CollapsibleContent>
          </CardContent>
        </Card>
      </Collapsible>

      {/* Charts */}
      {selectedFiles.size === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <BarChart3 className="mb-4 h-12 w-12 opacity-30" />
            <p className="text-lg font-medium">No results selected</p>
            <p className="text-sm">Select result files above to generate charts</p>
          </CardContent>
        </Card>
      ) : chartLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-16">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-muted-foreground">Analyzing results...</span>
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="py-16 text-center text-destructive">
            Failed to analyze results: {error instanceof Error ? error.message : "Unknown error"}
          </CardContent>
        </Card>
      ) : chartData ? (
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as ChartTab)}>
          <TabsList>
            <TabsTrigger value="heatmap">
              <Grid3X3 className="mr-1.5 h-4 w-4" />
              Heatmap
            </TabsTrigger>
            <TabsTrigger value="bars">
              <BarChart3 className="mr-1.5 h-4 w-4" />
              Model Comparison
            </TabsTrigger>
            <TabsTrigger value="scatter">
              <ScatterChart className="mr-1.5 h-4 w-4" />
              Scaling
            </TabsTrigger>
            <TabsTrigger value="dimensions">
              <Languages className="mr-1.5 h-4 w-4" />
              By Dimension
            </TabsTrigger>
          </TabsList>

          {/* Heatmap tab */}
          <TabsContent value="heatmap">
            <ChartCard
              title="Accuracy Heatmap"
              description={`${heatmapY === "model" ? "Models" : "Tasks"} vs ${heatmapX === "task" ? "Tasks" : "Models"} — color, numeric labels, and border styles all encode accuracy`}
              actions={
                <div className="flex items-center gap-2">
                  <ChartFilters
                    availableTaskTypes={availableTaskTypes}
                    availableLanguages={availableLanguages}
                    selectedTaskTypes={taskTypeFilter}
                    selectedLanguages={languageFilter}
                    onTaskTypesChange={setTaskTypeFilter}
                    onLanguagesChange={setLanguageFilter}
                  />
                  <Button variant="outline" size="sm" onClick={swapAxes}>
                    Swap Axes
                  </Button>
                </div>
              }
            >
              <AccuracyHeatmap data={filteredHeatmapData} xKey={heatmapX} yKey={heatmapY} />
            </ChartCard>
          </TabsContent>

          {/* Bar chart tab */}
          <TabsContent value="bars">
            <ChartCard
              title="Model Comparison"
              description={barTask ? `Accuracy on: ${barTask.replace(/_/g, " ")}` : "Overall accuracy across all tasks"}
              actions={
                <div className="flex items-center gap-2">
                  <ChartFilters
                    availableTaskTypes={availableTaskTypes}
                    availableLanguages={availableLanguages}
                    selectedTaskTypes={taskTypeFilter}
                    selectedLanguages={languageFilter}
                    onTaskTypesChange={setTaskTypeFilter}
                    onLanguagesChange={setLanguageFilter}
                  />
                  <Select
                    value={barTask ?? "__all__"}
                    onValueChange={(v) => setBarTask(v === "__all__" ? null : v)}
                  >
                    <SelectTrigger className="w-50">
                      <SelectValue placeholder="All tasks" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__all__">All Tasks (Overall)</SelectItem>
                      {chartData.tasks.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t.replace(/_/g, " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              }
            >
              <ModelBarChart data={barData} />
            </ChartCard>
          </TabsContent>

          {/* Scatter tab */}
          <TabsContent value="scatter">
            <ChartCard
              title="Inverse Scaling"
              description="Model parameter count vs accuracy — does bigger mean better?"
              actions={
                <div className="flex items-center gap-2">
                  <ChartFilters
                    availableTaskTypes={availableTaskTypes}
                    availableLanguages={availableLanguages}
                    selectedTaskTypes={taskTypeFilter}
                    selectedLanguages={languageFilter}
                    onTaskTypesChange={setTaskTypeFilter}
                    onLanguagesChange={setLanguageFilter}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setLogScale((v) => !v)}
                  >
                    {logScale ? "Linear" : "Log"} Scale
                  </Button>
                  <Select value={scatterLabelMode} onValueChange={(value) => setScatterLabelMode(value as ScatterLabelMode)}>
                    <SelectTrigger className="w-38">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hover">Hover Labels</SelectItem>
                      <SelectItem value="smart">Smart Labels</SelectItem>
                      <SelectItem value="all">All Labels</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              }
            >
              <ScalingScatter data={filteredScatterData} logScale={logScale} labelMode={scatterLabelMode} />
            </ChartCard>
          </TabsContent>

          {/* Dimension breakdown tab */}
          <TabsContent value="dimensions">
            <ChartCard
              title="Accuracy by Dimension"
              description="Performance breakdown by language, user prompt style, and system prompt style"
              actions={
                <div className="flex items-center gap-1">
                  {(["language", "user_style", "system_style"] as const).map((d) => (
                    <Button
                      key={d}
                      variant={dimTab === d ? "secondary" : "ghost"}
                      size="sm"
                      className="text-xs h-7"
                      onClick={() => setDimTab(d)}
                    >
                      {d === "language" ? "Language" : d === "user_style" ? "User Style" : "System Style"}
                    </Button>
                  ))}
                </div>
              }
            >
              <DimensionBarChart
                data={
                  dimTab === "language"
                    ? Object.fromEntries(
                        Object.entries(chartData.dimensionBreakdowns.language).map(
                          ([code, bucket]) => [languageLabel(code), bucket],
                        ),
                      )
                    : chartData.dimensionBreakdowns[dimTab]
                }
                label={dimTab === "language" ? "Language" : dimTab === "user_style" ? "User Style" : "System Style"}
              />
            </ChartCard>
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  )
}
