import { useCallback, useMemo, useState } from "react"
import type { ColumnDef, Table } from "@tanstack/react-table"
import { toast } from "sonner"
import { useNavigate } from "react-router"
import { Eye, BarChart3, LineChart, FileText, Loader2, RefreshCw, RotateCcw, Trash2, CheckSquare, Square } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DataTable } from "@/components/data-table/data-table"
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter"
import { PageHeader } from "@/components/layout/page-header"
import { TaskBadge } from "@/components/task-badge"
import { formatDuration, formatPercent } from "@/lib/utils"
import { langFlags } from "@/lib/language-flags"
import { useResults, useResult, useAnalyzeResults, useGenerateReport, useReanalyzeResult, useDeleteResult } from "@/hooks/use-results"
import { useTestsets } from "@/hooks/use-testsets"
import { ParamOverrideModal } from "@/components/param-override-modal"
import type { ResultSummary, ResultEntry, ModelAnalysis } from "@/types"

export default function ResultsPage() {
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
  const [groupBy, setGroupBy] = useState<"none" | "task_type" | "model">("none")
  const [rerunTarget, setRerunTarget] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const toggleSelect = useCallback((filename: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(filename)) next.delete(filename)
      else next.add(filename)
      return next
    })
  }, [])

  const handleAnalyze = async () => {
    if (selected.size === 0) { toast.error("Select result files to analyze"); return }
    try {
      const res = await analyzeMutation.mutateAsync({ result_filenames: Array.from(selected), comparison: selected.size > 1 })
      toast.success(`Analysis complete — ${res.model_count} model(s)`)
    } catch (err) {
      toast.error(`Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const handleReanalyze = async () => {
    if (selected.size === 0) { toast.error("Select result files to reanalyze"); return }
    let totalChanges = 0
    for (const filename of selected) {
      try {
        const res = await reanalyzeMutation.mutateAsync(filename)
        totalChanges += res.changes
        if (res.changes > 0) {
          toast.success(
            `${filename.slice(0, 40)}: ${res.changes} changes, accuracy ${(res.old_accuracy * 100).toFixed(1)}% → ${(res.new_accuracy * 100).toFixed(1)}%`
          )
        }
      } catch (err) {
        toast.error(`Reanalysis failed for ${filename}: ${err instanceof Error ? err.message : "Unknown error"}`)
      }
    }
    if (totalChanges === 0) toast.info("No evaluation changes detected")
  }

  const handleSelectAll = () => {
    if (results) setSelected(new Set(results.map((r) => r.filename)))
  }
  const handleDeselectAll = () => setSelected(new Set())

  const handleDelete = async () => {
    for (const filename of selected) {
      try {
        await deleteMutation.mutateAsync(filename)
      } catch (err) {
        toast.error(`Delete failed: ${filename}`)
      }
    }
    toast.success(`Deleted ${selected.size} result(s)`)
    setSelected(new Set())
    setDeleteConfirm(false)
  }

  const handleGenerateReport = async () => {
    if (selected.size === 0) { toast.error("Select result files for report"); return }
    try {
      const res = await reportMutation.mutateAsync({ result_filenames: Array.from(selected) })
      toast.success(`Report generated: ${res.filename}`)
      nav("/reports")
    } catch (err) {
      toast.error(`Report failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
  }

  const modelOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).map((r) => r.model_name))].sort()
    return unique.map((m) => ({ label: m, value: m }))
  }, [results])

  const taskOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((r) => r.task_types))].sort()
    return unique.map((t) => ({ label: t, value: t }))
  }, [results])

  const langOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((r) => r.languages ?? []))].sort()
    return unique.map((l) => ({ label: l, value: l }))
  }, [results])

  const userStyleOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((r) => r.user_styles ?? []))].sort()
    return unique.map((s) => ({ label: s, value: s }))
  }, [results])

  const systemStyleOptions = useMemo(() => {
    const unique = [...new Set((results ?? []).flatMap((r) => r.system_styles ?? []))].sort()
    return unique.map((s) => ({ label: s, value: s }))
  }, [results])

  // Group results for display
  const groupedResults = useMemo(() => {
    if (groupBy === "none" || !results) return results ?? []
    const sorted = [...results]
    if (groupBy === "model") {
      sorted.sort((a, b) => a.model_name.localeCompare(b.model_name))
    } else if (groupBy === "task_type") {
      sorted.sort((a, b) => (a.task_types[0] ?? "").localeCompare(b.task_types[0] ?? ""))
    }
    return sorted
  }, [results, groupBy])

  const toolbar = (table: Table<ResultSummary>) => (
    <>
      {table.getColumn("model_name") && modelOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("model_name")} title="Model" options={modelOptions} />
      )}
      {table.getColumn("task_types") && taskOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("task_types")} title="Task" options={taskOptions} />
      )}
      {table.getColumn("languages") && langOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("languages")} title="Lang" options={langOptions} />
      )}
      {table.getColumn("user_styles") && userStyleOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("user_styles")} title="User Style" options={userStyleOptions} />
      )}
      {table.getColumn("system_styles") && systemStyleOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("system_styles")} title="Sys Style" options={systemStyleOptions} />
      )}
      <div className="flex items-center gap-1 ml-2">
        <span className="text-xs text-muted-foreground">Group:</span>
        {(["none", "model", "task_type"] as const).map((g) => (
          <Button
            key={g}
            variant={groupBy === g ? "secondary" : "ghost"}
            size="sm"
            className="h-6 text-xs px-2"
            onClick={() => setGroupBy(g)}
          >
            {g === "none" ? "None" : g === "model" ? "Model" : "Task"}
          </Button>
        ))}
      </div>
    </>
  )

  const columns: ColumnDef<ResultSummary>[] = [
    {
      id: "select",
      header: () => {
        const allSelected = (results?.length ?? 0) > 0 && selected.size === (results?.length ?? 0)
        const someSelected = selected.size > 0 && !allSelected
        return (
          <button
            onClick={allSelected ? handleDeselectAll : handleSelectAll}
            className="flex items-center"
            title={allSelected ? "Deselect all" : "Select all"}
          >
            {allSelected ? <CheckSquare className="h-3.5 w-3.5" /> : someSelected ? <Square className="h-3.5 w-3.5 opacity-60" /> : <Square className="h-3.5 w-3.5 opacity-30" />}
          </button>
        )
      },
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={selected.has(row.original.filename)}
          onChange={() => toggleSelect(row.original.filename)}
          className="h-3.5 w-3.5"
        />
      ),
      size: 32,
    },
    {
      accessorKey: "model_name",
      header: "Model",
      cell: ({ row }) => <span className="font-medium text-xs">{row.original.model_name}</span>,
      filterFn: (row, _id, value: string[]) => value.includes(row.original.model_name),
    },
    {
      accessorKey: "task_types",
      header: "Tasks",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.task_types.map((t) => (
            <TaskBadge key={t} task={t} />
          ))}
        </div>
      ),
      filterFn: (row, _id, value: string[]) =>
        value.some((v) => row.original.task_types.includes(v)),
    },
    {
      accessorKey: "languages",
      header: "Lang",
      cell: ({ row }) => {
        const langs = row.original.languages ?? []
        if (langs.length === 0) return <span className="text-xs text-muted-foreground">-</span>
        return <span className="text-sm" title={langs.join(", ")}>{langFlags(langs)}</span>
      },
      filterFn: (row, _id, value: string[]) =>
        value.some((v) => (row.original.languages ?? []).includes(v)),
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
      filterFn: (row, _id, value: string[]) =>
        value.some((v) => (row.original.user_styles ?? []).includes(v)),
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
      filterFn: (row, _id, value: string[]) =>
        value.some((v) => (row.original.system_styles ?? []).includes(v)),
    },
    {
      accessorKey: "accuracy",
      header: "Accuracy",
      cell: ({ row }) => {
        const acc = row.original.accuracy
        const color = acc >= 0.7 ? "text-green-600" : acc >= 0.4 ? "text-yellow-600" : "text-red-600"
        return <span className={`font-mono text-xs font-medium ${color}`}>{formatPercent(acc)}</span>
      },
    },
    {
      accessorKey: "total_tests",
      header: "Tests",
      cell: ({ row }) => (
        <Badge variant="secondary">
          {row.original.correct}/{row.original.total_tests}
        </Badge>
      ),
    },
    {
      accessorKey: "parse_error_rate",
      header: "Parse Errors",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">{formatPercent(row.original.parse_error_rate)}</span>
      ),
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
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{new Date(row.original.created).toLocaleString()}</span>,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setDetailTarget(row.original.filename)}>
          <Eye className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Results"
        description="Browse benchmark results, compare models and generate reports"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleReanalyze} disabled={selected.size === 0 || reanalyzeMutation.isPending}>
              {reanalyzeMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              Reanalyze ({selected.size})
            </Button>
            <Button variant="outline" onClick={handleAnalyze} disabled={selected.size === 0 || analyzeMutation.isPending}>
              {analyzeMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
              Analyze ({selected.size})
            </Button>
            <Button
              variant="outline"
              onClick={() => nav(`/charts?files=${Array.from(selected).join(",")}`)}
              disabled={selected.size === 0}
            >
              <LineChart className="mr-2 h-4 w-4" />
              Charts ({selected.size})
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                const first = Array.from(selected)[0]
                const r = results?.find((res) => res.filename === first)
                if (!r?.testset_name) { toast.error("No testset info"); return }
                // Find matching testset filename by metadata name
                const match = testsets?.find((ts) =>
                  ts.filename.includes(r.testset_name) ||
                  (ts.metadata as Record<string, string>)?.name === r.testset_name
                )
                if (match) {
                  setRerunTarget(match.filename)
                } else {
                  // Fallback: go straight to execute page, let user pick
                  toast.info("Testset not found — redirecting to Execute page")
                  nav("/execute")
                }
              }}
              disabled={selected.size !== 1}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Rerun with Params
            </Button>
            <Button onClick={handleGenerateReport} disabled={selected.size === 0 || reportMutation.isPending}>
              {reportMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
              Generate Report
            </Button>
            <Button variant="destructive" onClick={() => setDeleteConfirm(true)} disabled={selected.size === 0}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete ({selected.size})
            </Button>
          </div>
        }
      />

      <DataTable columns={columns} data={groupedResults} loading={isLoading} searchKey="model_name" searchPlaceholder="Search results..." toolbar={toolbar} />

      {/* Analyze results dialog (inline) */}
      {analyzeMutation.isSuccess && analyzeMutation.data && (
        <div className="rounded-md border p-4 space-y-3">
          <h3 className="text-sm font-medium">Analysis Summary — {analyzeMutation.data.model_count} model(s)</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(analyzeMutation.data.models).map(([model, analysis]: [string, ModelAnalysis]) => (
              <div key={model} className="rounded border p-3 space-y-1.5">
                <p className="text-xs font-medium">{model}</p>
                <p className="text-xs">
                  Accuracy: <span className="font-mono">{formatPercent(analysis.accuracy)}</span>
                  {" · "}Tests: {analysis.total_tests}
                  {" · "}Parse errors: {formatPercent(analysis.parse_error_rate)}
                </p>
                {Object.entries(analysis.task_breakdown).length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {Object.entries(analysis.task_breakdown).map(([task, tb]) => (
                      <span key={task} className="mr-2">
                        <TaskBadge task={task} /> {formatPercent(tb.accuracy)} ({tb.total})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      <Dialog open={deleteConfirm} onOpenChange={setDeleteConfirm}>
        <DialogContent className="max-w-sm">
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

      {/* Rerun with params modal */}
      {rerunTarget && (
        <ParamOverrideModal
          open={!!rerunTarget}
          onOpenChange={(open) => { if (!open) setRerunTarget(null) }}
          testsetFilename={rerunTarget}
          mode="rerun"
        />
      )}

      {/* Detail sheet */}
      <Sheet open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <SheetContent className="sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-sm truncate">{detailTarget}</SheetTitle>
          </SheetHeader>
          {detail && (
            <Tabs defaultValue="overview" className="mt-4">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="cases">Cases ({detail.results_count})</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4 mt-3 text-xs">
                <section>
                  <h4 className="font-medium mb-1">Model Info</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.model_info, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="font-medium mb-1">Execution</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.execution_info, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="font-medium mb-1">Summary Statistics</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.summary_statistics, null, 2)}</pre>
                </section>
              </TabsContent>

              <TabsContent value="cases" className="mt-3 space-y-2">
                {detail.results.slice(0, 50).map((r: ResultEntry, i: number) => (
                  <details key={r.test_id || i} className="rounded border text-xs">
                    <summary className="p-2 cursor-pointer flex items-center justify-between">
                      <span className="font-mono">{r.test_id}</span>
                      <Badge variant={r.status === "correct" ? "default" : "destructive"} className="text-[10px]">
                        {r.status}
                      </Badge>
                    </summary>
                    <div className="p-2 space-y-2 bg-muted/50">
                      <div>
                        <h5 className="font-medium mb-0.5">Input</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(r.input, null, 2)}</pre>
                      </div>
                      <div>
                        <h5 className="font-medium mb-0.5">Output</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(r.output, null, 2)}</pre>
                      </div>
                      <div>
                        <h5 className="font-medium mb-0.5">Evaluation</h5>
                        <pre className="overflow-x-auto">{JSON.stringify(r.evaluation, null, 2)}</pre>
                      </div>
                    </div>
                  </details>
                ))}
                {detail.results_count > 50 && (
                  <p className="text-xs text-muted-foreground text-center">Showing first 50 of {detail.results_count} results</p>
                )}
              </TabsContent>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
