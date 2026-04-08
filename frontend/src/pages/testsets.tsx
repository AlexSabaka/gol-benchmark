import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import type { ColumnDef, Table } from "@tanstack/react-table"
import { toast } from "sonner"
import { Trash2, Play, Eye, MoreHorizontal, RotateCcw } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
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
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DataTable } from "@/components/data-table/data-table"
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter"
import { PageHeader } from "@/components/layout/page-header"
import { TaskBadge } from "@/components/task-badge"
import { ParamOverrideModal } from "@/components/param-override-modal"
import { formatBytes } from "@/lib/utils"
import { langFlags } from "@/lib/language-flags"
import { languageFilterOptions } from "@/components/language-filter-chip"
import { useTestsets, useTestset, useDeleteTestset } from "@/hooks/use-testsets"
import type { TestsetSummary } from "@/types"

export default function TestSetsPage() {
  const nav = useNavigate()
  const { data: testsets, isLoading } = useTestsets()
  const deleteMutation = useDeleteTestset()
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [detailTarget, setDetailTarget] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<string>("overview")
  const [regenTarget, setRegenTarget] = useState<string | null>(null)
  const [casesPage, setCasesPage] = useState(1)
  const { data: detail } = useTestset(detailTarget, casesPage)

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteMutation.mutateAsync(deleteTarget)
      toast.success("Test set deleted")
    } catch {
      toast.error("Delete failed")
    }
    setDeleteTarget(null)
  }

  const taskOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((ts) => ts.task_types))].sort()
    return unique.map((t) => ({ label: t, value: t }))
  }, [testsets])

  const langOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((ts) => ts.languages ?? []))].sort()
    return languageFilterOptions(unique)
  }, [testsets])

  const userStyleOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((ts) => ts.user_styles ?? []))].sort()
    return unique.map((s) => ({ label: s, value: s }))
  }, [testsets])

  const systemStyleOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((ts) => ts.system_styles ?? []))].sort()
    return unique.map((s) => ({ label: s, value: s }))
  }, [testsets])

  const [groupBy, setGroupBy] = useState<"none" | "task_type">("none")

  const sortedTestsets = useMemo(() => {
    if (!testsets) return []
    if (groupBy === "none") return testsets
    return [...testsets].sort((a, b) => (a.task_types[0] ?? "").localeCompare(b.task_types[0] ?? ""))
  }, [testsets, groupBy])

  const toolbar = (table: Table<TestsetSummary>) => (
    <>
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
        {(["none", "task_type"] as const).map((g) => (
          <Button
            key={g}
            variant={groupBy === g ? "secondary" : "ghost"}
            size="sm"
            className="h-6 text-xs px-2"
            onClick={() => setGroupBy(g)}
          >
            {g === "none" ? "None" : "Task"}
          </Button>
        ))}
      </div>
    </>
  )

  const columns: ColumnDef<TestsetSummary>[] = [
    {
      accessorKey: "filename",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium text-xs truncate max-w-[300px] block" title={row.original.filename}>
          {row.original.filename.replace(".json.gz", "")}
        </span>
      ),
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
      filterFn: (row, _col, value: string[]) =>
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
      filterFn: (row, _col, value: string[]) =>
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
      filterFn: (row, _col, value: string[]) =>
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
      filterFn: (row, _col, value: string[]) =>
        value.some((v) => (row.original.system_styles ?? []).includes(v)),
    },
    {
      accessorKey: "test_count",
      header: "Tests",
      cell: ({ row }) => <Badge variant="secondary">{row.original.test_count}</Badge>,
    },
    {
      accessorKey: "size_bytes",
      header: "Size",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatBytes(row.original.size_bytes)}</span>,
    },
    {
      accessorKey: "created",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {new Date(row.original.created).toLocaleString()}
        </span>
      ),
    },
    {
      id: "view_details",
      header: "Details",
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={() => { setDetailTarget(row.original.filename); setCasesPage(1) }}
        >
          <Eye className="mr-1.5 h-3.5 w-3.5" /> View
        </Button>
      ),
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
            <DropdownMenuItem onClick={() => nav(`/execute?testset=${row.original.filename}`)}>
              <Play className="mr-2 h-3.5 w-3.5" /> Run Benchmark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setRegenTarget(row.original.filename)}>
              <RotateCcw className="mr-2 h-3.5 w-3.5" /> Regenerate with Params
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive" onClick={() => setDeleteTarget(row.original.filename)}>
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
        title="Test Sets"
        description="Browse, inspect and manage generated test sets"
        actions={<Button onClick={() => nav("/configure")}>New Test Set</Button>}
      />

      <DataTable columns={columns} data={sortedTestsets} loading={isLoading} searchKey="filename" searchPlaceholder="Search test sets..." toolbar={toolbar} />

      {/* Delete confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete test set?</DialogTitle>
            <DialogDescription>
              This will permanently delete:
              <span className="font-mono text-xs block truncate mt-1" title={deleteTarget ?? ""}>
                {deleteTarget?.replace(".json.gz", "")}
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate with params modal */}
      {regenTarget && (
        <ParamOverrideModal
          open={!!regenTarget}
          onOpenChange={(open) => { if (!open) setRegenTarget(null) }}
          testsetFilename={regenTarget}
          mode="regenerate"
        />
      )}

      {/* Detail sheet */}
      <Sheet open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <SheetContent className="sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-sm truncate">{detailTarget}</SheetTitle>
          </SheetHeader>
          {detail && (
            <Tabs value={detailTab} onValueChange={setDetailTab} className="mt-4">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="cases">
                  Cases ({detail.total_cases ?? detail.test_count})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4 mt-3 text-xs">
                <section>
                  <h4 className="font-medium mb-1">Metadata</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.metadata, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="font-medium mb-1">Generation Params</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.generation_params, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="font-medium mb-1">Sampling Params</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.sampling_params, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="font-medium mb-1">Statistics</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(detail.statistics, null, 2)}</pre>
                </section>
              </TabsContent>

              <TabsContent value="cases" className="mt-3 space-y-2 text-xs">
                {detail.sample_cases.map((tc, i) => (
                  <details key={i} className="rounded border">
                    <summary className="p-2 cursor-pointer flex items-center justify-between">
                      <span className="font-mono">
                        {(tc as Record<string, unknown>).test_id as string ?? `Case ${(detail.page ?? 1 - 1) * (detail.page_size ?? 50) + i + 1}`}
                      </span>
                      <Badge variant="secondary" className="text-[10px]">
                        {(tc as Record<string, unknown>).task_type as string ?? "unknown"}
                      </Badge>
                    </summary>
                    <pre className="p-2 bg-muted/50 overflow-x-auto">
                      {JSON.stringify(tc, null, 2)}
                    </pre>
                  </details>
                ))}

                {/* Pagination */}
                {(detail.total_cases ?? detail.test_count) > (detail.page_size ?? 50) && (
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-muted-foreground">
                      Page {detail.page ?? casesPage} of {Math.ceil((detail.total_cases ?? detail.test_count) / (detail.page_size ?? 50))}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        disabled={casesPage <= 1}
                        onClick={() => setCasesPage((p) => Math.max(1, p - 1))}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        disabled={casesPage >= Math.ceil((detail.total_cases ?? detail.test_count) / (detail.page_size ?? 50))}
                        onClick={() => setCasesPage((p) => p + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
