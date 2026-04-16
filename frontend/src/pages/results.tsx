import { useCallback, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { toast } from "sonner"
import {
  BarChart3,
  Eraser,
  Eye,
  FileBarChart,
  FileText,
  LineChart,
  Loader2,
  MoreHorizontal,
  PenLine,
  RefreshCw,
  RotateCcw,
  Scale,
  Search,
  Trash2,
} from "lucide-react"

import { DataTable } from "@/components/data-table/data-table"
import { GroupedGridSection } from "@/components/grouped-grid-section"
import { JudgeSetupSheet } from "@/components/judge-setup-sheet"
import { ImprovementReportDialog } from "@/components/review/improvement-report-dialog"
import { PageHeader } from "@/components/layout/page-header"
import { languageFilterOptions } from "@/components/language-filter-chip"
import { PageFacetFilter } from "@/components/page-facet-filter"
import { ParamOverrideModal } from "@/components/param-override-modal"
import { ResultSummaryCard } from "@/components/result-summary-card"
import { TaskBadge } from "@/components/task-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useAnalyzeResults, useDeleteResult, useGenerateReport, useReanalyzeResult, useResult, useResults } from "@/hooks/use-results"
import { useDeleteAnnotations } from "@/hooks/use-review"
import { useTestsets } from "@/hooks/use-testsets"
import { langFlags } from "@/lib/language-flags"
import { makeStorageKey, useLocalStorageState } from "@/lib/local-storage"
import { formatDate, formatDuration, formatPercent } from "@/lib/utils"
import type { ModelAnalysis, ResultEntry, ResultSummary, TestsetSummary } from "@/types"

type ViewMode = "table" | "cards"
type GroupMode = "none" | "model" | "task_type" | "testset" | "matrix_batch" | "run"

interface ResultGroup {
  key: string
  title: string
  subtitle?: string
  countLabel: string
  items: ResultSummary[]
  headerExtras?: React.ReactNode
}

function matchesAny(values: string[] | undefined, selected: string[]) {
  if (selected.length === 0) return true
  return selected.some((value) => (values ?? []).includes(value))
}

function matchesSearch(summary: ResultSummary, query: string) {
  if (!query) return true

  const haystack = [
    summary.filename,
    summary.model_name,
    summary.testset_name,
    summary.task_types.join(" "),
    summary.languages.join(" "),
    summary.matrix_label ?? "",
    summary.matrix_plugin ?? "",
    summary.matrix_batch_id ?? "",
    summary.run_group_id ?? "",
  ].join(" ").toLowerCase()

  return haystack.includes(query)
}

function normalizeName(value: string | null | undefined) {
  return (value ?? "").replace(/\.json\.gz$/i, "").trim().toLowerCase()
}

function buildGroups(results: ResultSummary[], groupBy: GroupMode): ResultGroup[] {
  if (groupBy === "none") return []

  const grouped = new Map<string, ResultSummary[]>()
  for (const summary of results) {
    let key = "all"
    switch (groupBy) {
      case "model":
        key = summary.model_name || "Unknown Model"
        break
      case "task_type":
        key = summary.task_types.length === 1 ? summary.task_types[0] : summary.task_types.join(", ") || "unknown"
        break
      case "testset":
        key = summary.testset_name || "Unknown Test Set"
        break
      case "matrix_batch":
        key = summary.matrix_batch_id ?? "__standalone__"
        break
      case "run":
        key = summary.run_group_id ?? "__ungrouped__"
        break
    }

    const items = grouped.get(key) ?? []
    items.push(summary)
    grouped.set(key, items)
  }

  return Array.from(grouped.entries()).map(([key, items]) => {
    const first = items[0]
    const distinctModels = new Set(items.map((item) => item.model_name)).size

    if (groupBy === "model") {
      return {
        key,
        title: key,
        subtitle: `${items.length} result${items.length !== 1 ? "s" : ""}`,
        countLabel: `${items.length} items`,
        items,
      }
    }

    if (groupBy === "task_type") {
      return {
        key,
        title: key === "unknown" ? "Unknown Task" : key,
        subtitle: `${items.length} result${items.length !== 1 ? "s" : ""}`,
        countLabel: `${items.length} items`,
        items,
      }
    }

    if (groupBy === "testset") {
      return {
        key,
        title: key,
        subtitle: `${distinctModels} model${distinctModels !== 1 ? "s" : ""}`,
        countLabel: `${items.length} results`,
        items,
      }
    }

    if (groupBy === "matrix_batch") {
      if (key === "__standalone__") {
        return {
          key,
          title: "Standalone Results",
          subtitle: "Results without matrix metadata",
          countLabel: `${items.length} results`,
          items,
        }
      }

      return {
        key,
        title: `Matrix Batch ${key}`,
        subtitle: `${first.matrix_plugin ?? first.testset_name ?? "Matrix"} • ${distinctModels} model${distinctModels !== 1 ? "s" : ""}`,
        countLabel: `${items.length} results`,
        items,
      }
    }

    if (key === "__ungrouped__") {
      return {
        key,
        title: "Ungrouped Results",
        subtitle: "Results without run-group metadata",
        countLabel: `${items.length} results`,
        items,
      }
    }

    return {
      key,
      title: `Run ${key.slice(0, 8)}`,
      subtitle: `${first.testset_name || "Unknown Test Set"} • ${distinctModels} model${distinctModels !== 1 ? "s" : ""}`,
      countLabel: `${items.length} results`,
      items,
    }
  })
}

export default function ResultsPage() {
  const storageScope = "results-page"
  const nav = useNavigate()
  const { data: results, isLoading } = useResults()
  const analyzeMutation = useAnalyzeResults()
  const reportMutation = useGenerateReport()
  const reanalyzeMutation = useReanalyzeResult()
  const deleteMutation = useDeleteResult()
  const { data: testsets } = useTestsets()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailTarget, setDetailTarget] = useState<string | null>(null)
  const { data: detail } = useResult(detailTarget)
  const [storedViewMode, setStoredViewMode] = useLocalStorageState<ViewMode>(makeStorageKey(storageScope, "view-mode"), "table")
  const [groupBy, setGroupBy] = useLocalStorageState<GroupMode>(makeStorageKey(storageScope, "group-by"), "none")
  const [rerunTarget, setRerunTarget] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [judgeOpen, setJudgeOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [removeAnnotationsTarget, setRemoveAnnotationsTarget] = useState<string | null>(null)
  const deleteAnnotationsMutation = useDeleteAnnotations()
  const [searchTerm, setSearchTerm] = useLocalStorageState<string>(makeStorageKey(storageScope, "search"), "")
  const [modelFilter, setModelFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "model-filter"), [])
  const [taskFilter, setTaskFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "task-filter"), [])
  const [languageFilter, setLanguageFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "language-filter"), [])
  const [userStyleFilter, setUserStyleFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "user-style-filter"), [])
  const [systemStyleFilter, setSystemStyleFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "system-style-filter"), [])
  const viewMode: ViewMode = groupBy === "none" && storedViewMode === "cards" ? "table" : storedViewMode

  const setSelectionFor = useCallback((filenames: string[], nextChecked: boolean) => {
    setSelected((previous) => {
      const next = new Set(previous)
      for (const filename of filenames) {
        if (nextChecked) next.add(filename)
        else next.delete(filename)
      }
      return next
    })
  }, [])

  const toggleSelect = useCallback((filename: string) => {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(filename)) next.delete(filename)
      else next.add(filename)
      return next
    })
  }, [])

  const filteredResults = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    return [...(results ?? [])]
      .filter((summary) => matchesSearch(summary, query))
      .filter((summary) => modelFilter.length === 0 || modelFilter.includes(summary.model_name))
      .filter((summary) => taskFilter.length === 0 || taskFilter.some((value) => summary.task_types.includes(value)))
      .filter((summary) => matchesAny(summary.languages, languageFilter))
      .filter((summary) => matchesAny(summary.user_styles, userStyleFilter))
      .filter((summary) => matchesAny(summary.system_styles, systemStyleFilter))
      .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())
  }, [languageFilter, modelFilter, results, searchTerm, systemStyleFilter, taskFilter, userStyleFilter])

  const filteredFilenames = useMemo(() => filteredResults.map((summary) => summary.filename), [filteredResults])

  // ── Human-review gating ──────────────────────────────────────────────
  // "Review manually" is enabled only when every selected file belongs to the
  // same plugin, so regex/ordering heuristics in the aggregator stay coherent.
  const selectedSummaries = useMemo(
    () => (results ?? []).filter((r) => selected.has(r.filename)),
    [results, selected],
  )
  const selectedPluginsSet = useMemo(() => {
    const set = new Set<string>()
    for (const r of selectedSummaries) (r.task_types ?? []).forEach((t) => set.add(t))
    return set
  }, [selectedSummaries])
  const reviewEnabled = selected.size > 0 && selectedPluginsSet.size === 1
  const reviewTooltip = selected.size === 0
    ? "Select at least one result file"
    : selectedPluginsSet.size !== 1
      ? "Select files from the same plugin to review"
      : "Open the annotation workspace"
  const annotatedFiles = useMemo(
    () => selectedSummaries.filter((r) => !!r.has_annotations).map((r) => r.filename),
    [selectedSummaries],
  )
  const reportEnabled = annotatedFiles.length > 0
  const reportTooltip = reportEnabled
    ? `Aggregate ${annotatedFiles.length} annotated file${annotatedFiles.length === 1 ? "" : "s"}`
    : "Annotate at least one selected result file first"
  const allFilteredSelected = filteredFilenames.length > 0 && filteredFilenames.every((filename) => selected.has(filename))
  const someFilteredSelected = filteredFilenames.some((filename) => selected.has(filename)) && !allFilteredSelected
  const showFlatOrGroupedTable = viewMode === "table" || groupBy === "none"

  const buildDisplayGroups = useCallback((rows: ResultSummary[]) => {
    return buildGroups(rows, groupBy).map((group) => {
      const groupFilenames = group.items.map((item) => item.filename)
      const allSelectedInGroup = groupFilenames.every((filename) => selected.has(filename))
      const selectedCount = groupFilenames.filter((filename) => selected.has(filename)).length
      const matrixPlugin = groupBy === "matrix_batch" ? group.items[0]?.matrix_plugin : null

      return {
        ...group,
        headerExtras: (
          <div className="flex items-center gap-2">
            {matrixPlugin && <Badge variant="outline">{matrixPlugin}</Badge>}
            {selectedCount > 0 && <Badge variant="secondary">{selectedCount} selected</Badge>}
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={(event) => {
                event.stopPropagation()
                setSelectionFor(groupFilenames, !allSelectedInGroup)
              }}
            >
              {allSelectedInGroup ? "Deselect Group" : "Select Group"}
            </Button>
          </div>
        ),
      }
    })
  }, [groupBy, selected, setSelectionFor])

  const groups = useMemo(() => {
    if (groupBy === "none") return []
    return buildDisplayGroups(filteredResults)
  }, [buildDisplayGroups, filteredResults, groupBy])

  const handleSelectAll = useCallback(() => {
    setSelectionFor(filteredFilenames, true)
  }, [filteredFilenames, setSelectionFor])

  const handleDeselectAll = useCallback(() => {
    setSelectionFor(filteredFilenames, false)
  }, [filteredFilenames, setSelectionFor])

  const resolveTestsetFilename = useCallback((summary: ResultSummary) => {
    const target = normalizeName(summary.testset_name)
    const match = testsets?.find((testset: TestsetSummary) => {
      const filename = normalizeName(testset.filename)
      const metadataName = normalizeName(String((testset.metadata as Record<string, unknown>)?.name ?? ""))
      return filename === target || metadataName === target
    })
    return match?.filename
  }, [testsets])

  const openRerun = useCallback((summary: ResultSummary) => {
    const filename = resolveTestsetFilename(summary)
    if (filename) {
      setRerunTarget(filename)
      return
    }

    toast.info("Testset not found — redirecting to Execute page")
    nav("/execute")
  }, [nav, resolveTestsetFilename])

  const handleAnalyze = async () => {
    if (selected.size === 0) {
      toast.error("Select result files to analyze")
      return
    }
    try {
      const response = await analyzeMutation.mutateAsync({
        result_filenames: Array.from(selected),
        comparison: selected.size > 1,
      })
      toast.success(`Analysis complete — ${response.model_count} model(s)`)
    } catch (error) {
      toast.error(`Analysis failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const handleReanalyze = async () => {
    if (selected.size === 0) {
      toast.error("Select result files to reanalyze")
      return
    }

    let totalChanges = 0
    for (const filename of selected) {
      try {
        const response = await reanalyzeMutation.mutateAsync(filename)
        totalChanges += response.changes
        if (response.changes > 0) {
          toast.success(
            `${filename.slice(0, 40)}: ${response.changes} changes, accuracy ${(response.old_accuracy * 100).toFixed(1)}% → ${(response.new_accuracy * 100).toFixed(1)}%`,
          )
        }
      } catch (error) {
        toast.error(`Reanalysis failed for ${filename}: ${error instanceof Error ? error.message : "Unknown error"}`)
      }
    }

    if (totalChanges === 0) {
      toast.info("No evaluation changes detected")
    }
  }

  const handleDelete = async () => {
    for (const filename of selected) {
      try {
        await deleteMutation.mutateAsync(filename)
      } catch {
        toast.error(`Delete failed: ${filename}`)
      }
    }
    toast.success(`Deleted ${selected.size} result(s)`)
    setSelected(new Set())
    setDeleteConfirm(false)
  }

  const handleGenerateReport = async () => {
    if (selected.size === 0) {
      toast.error("Select result files for report")
      return
    }
    try {
      const response = await reportMutation.mutateAsync({ result_filenames: Array.from(selected) })
      toast.success(`Report generated: ${response.filename}`)
      nav("/reports")
    } catch (error) {
      toast.error(`Report failed: ${error instanceof Error ? error.message : "Unknown error"}`)
    }
  }

  const modelOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).map((summary) => summary.model_name))].sort()
    return unique.map((model) => ({ label: model, value: model }))
  }, [results])

  const taskOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((summary) => summary.task_types))].sort()
    return unique.map((task) => ({ label: task, value: task }))
  }, [results])

  const languageOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((summary) => summary.languages ?? []))].sort()
    return languageFilterOptions(unique)
  }, [results])

  const userStyleOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((summary) => summary.user_styles ?? []))].sort()
    return unique.map((style) => ({ label: style, value: style }))
  }, [results])

  const systemStyleOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((summary) => summary.system_styles ?? []))].sort()
    return unique.map((style) => ({ label: style, value: style }))
  }, [results])

  const columns: ColumnDef<ResultSummary>[] = [
    {
      id: "select",
      header: () => (
        <Checkbox
          checked={allFilteredSelected ? true : someFilteredSelected ? "indeterminate" : false}
          onCheckedChange={(checked) => {
            if (checked) handleSelectAll()
            else handleDeselectAll()
          }}
          aria-label="Select visible results"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={selected.has(row.original.filename)}
          onCheckedChange={() => toggleSelect(row.original.filename)}
          aria-label={`Select ${row.original.filename}`}
        />
      ),
      size: 32,
    },
    {
      accessorKey: "model_name",
      header: "Model",
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium">{row.original.model_name}</span>
          {row.original.has_annotations && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-primary"
                  aria-label="Has annotations"
                >
                  <PenLine className="h-2.5 w-2.5" />
                </span>
              </TooltipTrigger>
              <TooltipContent>Annotated — open Improvement report to aggregate</TooltipContent>
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      accessorKey: "task_types",
      header: "Tasks",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.task_types.map((task) => (
            <TaskBadge key={task} task={task} />
          ))}
        </div>
      ),
    },
    {
      accessorKey: "languages",
      header: "Lang",
      cell: ({ row }) => {
        const languages = row.original.languages ?? []
        if (languages.length === 0) return <span className="text-xs text-muted-foreground">-</span>
        return <span className="text-sm" title={languages.join(", ")}>{langFlags(languages)}</span>
      },
    },
    {
      accessorKey: "user_styles",
      header: "User",
      cell: ({ row }) => {
        const styles = row.original.user_styles ?? []
        if (styles.length === 0) return <span className="text-xs text-muted-foreground">-</span>
        if (styles.length === 1) return <span className="text-xs">{styles[0]}</span>
        return <span className="text-xs" title={styles.join(", ")}>multi</span>
      },
    },
    {
      accessorKey: "system_styles",
      header: "System",
      cell: ({ row }) => {
        const styles = row.original.system_styles ?? []
        if (styles.length === 0) return <span className="text-xs text-muted-foreground">-</span>
        if (styles.length === 1) return <span className="text-xs">{styles[0]}</span>
        return <span className="text-xs" title={styles.join(", ")}>multi</span>
      },
    },
    {
      accessorKey: "accuracy",
      header: "Accuracy",
      cell: ({ row }) => {
        const accuracy = row.original.accuracy
        const color = accuracy >= 0.7 ? "text-green-600" : accuracy >= 0.4 ? "text-yellow-600" : "text-red-600"
        return <span className={`font-mono text-xs font-medium ${color}`}>{formatPercent(accuracy)}</span>
      },
    },
    {
      accessorKey: "total_tests",
      header: "Tests",
      cell: ({ row }) => <Badge variant="secondary">{row.original.correct}/{row.original.total_tests}</Badge>,
    },
    {
      accessorKey: "parse_error_rate",
      header: "Parse Errors",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatPercent(row.original.parse_error_rate)}</span>,
    },
    {
      accessorKey: "total_tokens",
      header: "Tokens",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.total_tokens.toLocaleString()}</span>,
    },
    {
      accessorKey: "duration_seconds",
      header: "Duration",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDuration(row.original.duration_seconds)}</span>,
    },
    {
      accessorKey: "created",
      header: "Created",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDate(row.original.created)}</span>,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setDetailTarget(row.original.filename)}>
              <Eye className="mr-2 h-3.5 w-3.5" /> View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => nav(`/review?files=${row.original.filename}`)}>
              <PenLine className="mr-2 h-3.5 w-3.5" /> Verify Manually
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openRerun(row.original)}>
              <RotateCcw className="mr-2 h-3.5 w-3.5" /> Rerun with Params
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {row.original.has_annotations && (
              <DropdownMenuItem
                variant="destructive"
                onClick={() => setRemoveAnnotationsTarget(row.original.filename)}
              >
                <Eraser className="mr-2 h-3.5 w-3.5" /> Remove Annotations
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              variant="destructive"
              onClick={async () => {
                try {
                  await deleteMutation.mutateAsync(row.original.filename)
                  toast.success(`Deleted ${row.original.filename.slice(0, 40)}...`)
                } catch {
                  toast.error(`Delete failed: ${row.original.filename}`)
                }
              }}
            >
              <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Results"
        description="Browse benchmark results, compare models and generate reports"
        actions={
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" className="relative h-8 w-8" onClick={handleReanalyze} disabled={selected.size === 0 || reanalyzeMutation.isPending}>
                  {reanalyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reanalyze</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" className="relative h-8 w-8" onClick={handleAnalyze} disabled={selected.size === 0 || analyzeMutation.isPending}>
                  {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BarChart3 className="h-4 w-4" />}
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Analyze</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" className="relative h-8 w-8" onClick={() => nav(`/charts?files=${Array.from(selected).join(",")}`)} disabled={selected.size === 0}>
                  <LineChart className="h-4 w-4" />
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Charts</TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" className="relative h-8 w-8" onClick={() => setJudgeOpen(true)} disabled={selected.size === 0}>
                  <Scale className="h-4 w-4" />
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>LLM Judge</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="relative h-8 w-8"
                  onClick={() => nav(`/review?files=${Array.from(selected).join(",")}`)}
                  disabled={!reviewEnabled}
                >
                  <PenLine className="h-4 w-4" />
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Review manually — {reviewTooltip}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="relative h-8 w-8"
                  onClick={() => setReportOpen(true)}
                  disabled={!reportEnabled}
                >
                  <FileBarChart className="h-4 w-4" />
                  {annotatedFiles.length > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{annotatedFiles.length}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Improvement report — {reportTooltip}</TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="destructive" size="icon" className="relative h-8 w-8" onClick={() => setDeleteConfirm(true)} disabled={selected.size === 0}>
                  <Trash2 className="h-4 w-4" />
                  {selected.size > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[10px] text-primary-foreground">{selected.size}</span>}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete</TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <Button onClick={handleGenerateReport} disabled={selected.size === 0 || reportMutation.isPending}>
              {reportMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
              Generate Report
            </Button>
          </div>
        }
      />

      <div className="space-y-3 rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-60 flex-1 sm:max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search results..."
              className="pl-8"
            />
          </div>
          {modelOptions.length > 1 && (
            <PageFacetFilter title="Model" options={modelOptions} selectedValues={modelFilter} onChange={setModelFilter} />
          )}
          {taskOptions.length > 1 && (
            <PageFacetFilter title="Task" options={taskOptions} selectedValues={taskFilter} onChange={setTaskFilter} />
          )}
          {languageOptions.length > 1 && (
            <PageFacetFilter title="Lang" options={languageOptions} selectedValues={languageFilter} onChange={setLanguageFilter} />
          )}
          {userStyleOptions.length > 1 && (
            <PageFacetFilter title="User Style" options={userStyleOptions} selectedValues={userStyleFilter} onChange={setUserStyleFilter} />
          )}
          {systemStyleOptions.length > 1 && (
            <PageFacetFilter title="Sys Style" options={systemStyleOptions} selectedValues={systemStyleFilter} onChange={setSystemStyleFilter} />
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Format</span>
          {([
            ["table", "Table"],
            ["cards", "Cards"],
          ] as const).map(([value, label]) => (
            <Button
              key={value}
              variant={viewMode === value ? "secondary" : "outline"}
              size="sm"
              className="h-8 text-xs"
              onClick={() => setStoredViewMode(value)}
              disabled={value === "cards" && groupBy === "none"}
              title={value === "cards" && groupBy === "none" ? "Choose a grouping to enable cards" : undefined}
            >
              {label}
            </Button>
          ))}
          <Separator orientation="vertical" className="h-6" />
          <span className="text-xs text-muted-foreground">Group By</span>
          {([
            ["none", "None"],
            ["run", "Run"],
            ["matrix_batch", "Matrix Batch"],
            ["testset", "Test Set"],
            ["model", "Model"],
            ["task_type", "Task"],
          ] as const).map(([value, label]) => (
            <Button
              key={value}
              variant={groupBy === value ? "secondary" : "outline"}
              size="sm"
              className="h-8 text-xs"
              onClick={() => {
                if (value === "none" && viewMode === "cards") {
                  setStoredViewMode("table")
                }
                setGroupBy(value)
              }}
            >
              {label}
            </Button>
          ))}
          <Badge variant="secondary">{filteredResults.length} visible</Badge>
          <Badge variant="secondary">{selected.size} selected</Badge>
          <Button variant="outline" size="sm" className="ml-auto h-8 text-xs" onClick={handleSelectAll} disabled={filteredFilenames.length === 0}>
            Select Visible
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs" onClick={() => setSelected(new Set())} disabled={selected.size === 0}>
            Clear Selection
          </Button>
        </div>
      </div>

      {showFlatOrGroupedTable ? (
        <DataTable
          columns={columns}
          data={filteredResults}
          loading={isLoading}
          grouping={groupBy === "none" ? undefined : { buildGroups: buildDisplayGroups }}
          persistKey="results-table"
          getRowId={(row) => row.filename}
        />
      ) : groups.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No results match the current filters.
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group, index) => (
            <GroupedGridSection
              key={group.key}
              title={group.title}
              subtitle={group.subtitle}
              countLabel={group.countLabel}
              defaultOpen={groups.length === 1 || index === 0}
              headerExtras={group.headerExtras}
            >
              <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {group.items.map((summary) => (
                  <ResultSummaryCard
                    key={summary.filename}
                    summary={summary}
                    selected={selected.has(summary.filename)}
                    onToggleSelect={() => toggleSelect(summary.filename)}
                    onView={() => setDetailTarget(summary.filename)}
                    onRerun={() => openRerun(summary)}
                    onDelete={async () => {
                      try {
                        await deleteMutation.mutateAsync(summary.filename)
                        toast.success(`Deleted ${summary.filename.slice(0, 40)}...`)
                      } catch {
                        toast.error(`Delete failed: ${summary.filename}`)
                      }
                    }}
                  />
                ))}
              </div>
            </GroupedGridSection>
          ))}
        </div>
      )}

      {analyzeMutation.isSuccess && analyzeMutation.data && (
        <div className="space-y-3 rounded-md border p-4">
          <h3 className="text-sm font-medium">Analysis Summary — {analyzeMutation.data.model_count} model(s)</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(analyzeMutation.data.models).map(([model, analysis]: [string, ModelAnalysis]) => (
              <div key={model} className="space-y-1.5 rounded border p-3">
                <p className="text-xs font-medium">{model}</p>
                <p className="text-xs">
                  Accuracy: <span className="font-mono">{formatPercent(analysis.accuracy)}</span>
                  {" · "}Tests: {analysis.total_tests}
                  {" · "}Parse errors: {formatPercent(analysis.parse_error_rate)}
                </p>
                {Object.entries(analysis.task_breakdown).length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {Object.entries(analysis.task_breakdown).map(([task, taskBreakdown]) => (
                      <span key={task} className="mr-2">
                        <TaskBadge task={task} /> {formatPercent(taskBreakdown.accuracy)} ({taskBreakdown.total})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <Dialog open={deleteConfirm} onOpenChange={setDeleteConfirm}>
        <DialogContent className="max-w-lg sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Delete {selected.size} result(s)?</DialogTitle>
            <DialogDescription>
              This will permanently delete the selected result files. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {rerunTarget && (
        <ParamOverrideModal
          open={!!rerunTarget}
          onOpenChange={(open) => { if (!open) setRerunTarget(null) }}
          testsetFilename={rerunTarget}
          mode="rerun"
        />
      )}

      <Sheet open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <SheetContent className="overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle className="truncate text-sm">{detailTarget}</SheetTitle>
          </SheetHeader>
          {detail && (
            <Tabs defaultValue="overview" className="mt-4">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="cases">Cases ({detail.results_count})</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-3 space-y-4 text-xs">
                <section>
                  <h4 className="mb-1 font-medium">Model Info</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.model_info, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="mb-1 font-medium">Execution</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.execution_info, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="mb-1 font-medium">Summary Statistics</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.summary_statistics, null, 2)}</pre>
                </section>
              </TabsContent>

              <TabsContent value="cases" className="mt-3 space-y-2">
                {detail.results.slice(0, 50).map((result: ResultEntry, index: number) => (
                  <details key={result.test_id || index} className="rounded border text-xs">
                    <summary className="flex cursor-pointer items-center justify-between p-2">
                      <span className="font-mono">{result.test_id}</span>
                      <Badge variant={result.status === "correct" ? "default" : "destructive"} className="text-[10px]">
                        {result.status}
                      </Badge>
                    </summary>
                    <div className="space-y-2 bg-muted/50 p-2">
                      <div>
                        <h5 className="mb-0.5 font-medium">Input</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(result.input, null, 2)}</pre>
                      </div>
                      <div>
                        <h5 className="mb-0.5 font-medium">Output</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(result.output, null, 2)}</pre>
                      </div>
                      <div>
                        <h5 className="mb-0.5 font-medium">Evaluation</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(result.evaluation, null, 2)}</pre>
                      </div>
                    </div>
                  </details>
                ))}
                {detail.results_count > 50 && (
                  <p className="text-center text-xs text-muted-foreground">Showing first 50 of {detail.results_count} results</p>
                )}
              </TabsContent>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>

      <JudgeSetupSheet open={judgeOpen} onOpenChange={setJudgeOpen} selectedFiles={Array.from(selected)} />
      <ImprovementReportDialog open={reportOpen} onOpenChange={setReportOpen} fileIds={annotatedFiles} />

      <Dialog
        open={removeAnnotationsTarget !== null}
        onOpenChange={(v) => !v && setRemoveAnnotationsTarget(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Remove annotations?</DialogTitle>
            <DialogDescription>
              This deletes the annotation sidecar file for{" "}
              <span className="font-mono">{removeAnnotationsTarget}</span>. The result file itself is untouched, but all human-reviewed spans, notes, and verdicts will be lost. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveAnnotationsTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteAnnotationsMutation.isPending}
              onClick={async () => {
                if (!removeAnnotationsTarget) return
                try {
                  await deleteAnnotationsMutation.mutateAsync(removeAnnotationsTarget)
                  toast.success("Annotations removed")
                  setRemoveAnnotationsTarget(null)
                } catch (err) {
                  toast.error(`Remove failed: ${err instanceof Error ? err.message : "unknown"}`)
                }
              }}
            >
              {deleteAnnotationsMutation.isPending && (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              )}
              Delete annotations
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}