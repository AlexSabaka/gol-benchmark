import { useMemo, useState } from "react"
import type { ColumnDef, Table } from "@tanstack/react-table"
import { toast } from "sonner"
import { useNavigate } from "react-router"
import { Eye, BarChart3, FileText, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
import { useResults, useResult, useAnalyzeResults, useGenerateReport } from "@/hooks/use-results"
import type { ResultSummary, ResultEntry, ModelAnalysis } from "@/types"

export default function ResultsPage() {
  const nav = useNavigate()
  const { data: results, isLoading } = useResults()
  const analyzeMutation = useAnalyzeResults()
  const reportMutation = useGenerateReport()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailTarget, setDetailTarget] = useState<string | null>(null)
  const { data: detail } = useResult(detailTarget)

  const toggleSelect = (filename: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(filename)) next.delete(filename)
      else next.add(filename)
      return next
    })
  }

  const handleAnalyze = async () => {
    if (selected.size === 0) { toast.error("Select result files to analyze"); return }
    try {
      const res = await analyzeMutation.mutateAsync({ result_filenames: Array.from(selected), comparison: selected.size > 1 })
      toast.success(`Analysis complete — ${res.model_count} model(s)`)
    } catch (err) {
      toast.error(`Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    }
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

  const toolbar = (table: Table<ResultSummary>) => (
    <>
      {table.getColumn("model_name") && modelOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("model_name")} title="Model" options={modelOptions} />
      )}
      {table.getColumn("task_types") && taskOptions.length > 1 && (
        <DataTableFacetedFilter column={table.getColumn("task_types")} title="Task" options={taskOptions} />
      )}
    </>
  )

  const columns: ColumnDef<ResultSummary>[] = [
    {
      id: "select",
      header: () => null,
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
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleAnalyze} disabled={selected.size === 0 || analyzeMutation.isPending}>
              {analyzeMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
              Analyze ({selected.size})
            </Button>
            <Button onClick={handleGenerateReport} disabled={selected.size === 0 || reportMutation.isPending}>
              {reportMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
              Generate Report
            </Button>
          </div>
        }
      />

      <DataTable columns={columns} data={results ?? []} loading={isLoading} searchKey="model_name" searchPlaceholder="Search results..." toolbar={toolbar} />

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
