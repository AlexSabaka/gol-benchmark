import { useMemo, useState } from "react"
import { useNavigate } from "react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { toast } from "sonner"
import { Eye, MoreHorizontal, Play, RotateCcw, Search, Trash2 } from "lucide-react"

import { DataTable } from "@/components/data-table/data-table"
import { GroupedGridSection } from "@/components/grouped-grid-section"
import { IdentifierLabel } from "@/components/identifier-label"
import { PageHeader } from "@/components/layout/page-header"
import { PageFacetFilter } from "@/components/page-facet-filter"
import { ParamOverrideModal } from "@/components/param-override-modal"
import { TaskBadge } from "@/components/task-badge"
import { TestsetSummaryCard } from "@/components/testset-summary-card"
import { languageFilterOptions } from "@/components/language-filter-chip"
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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
import { useDeleteTestset, useTestset, useTestsets } from "@/hooks/use-testsets"
import { langFlags } from "@/lib/language-flags"
import { makeStorageKey, useLocalStorageState } from "@/lib/local-storage"
import { formatBytes, formatDate } from "@/lib/utils"
import type { TestsetSummary } from "@/types"

type ViewMode = "table" | "cards"
type GroupMode = "none" | "task_type" | "matrix_batch"

interface TestsetGroup {
  key: string
  title: string
  subtitle?: string
  countLabel: string
  items: TestsetSummary[]
  headerExtras?: React.ReactNode
}

function matchesAny(values: string[] | undefined, selected: string[]) {
  if (selected.length === 0) return true
  return selected.some((value) => (values ?? []).includes(value))
}

function matchesSearch(summary: TestsetSummary, query: string) {
  if (!query) return true

  const haystack = [
    summary.filename,
    summary.matrix_label ?? "",
    summary.matrix_plugin ?? "",
    summary.matrix_batch_id ?? "",
    summary.task_types.join(" "),
    summary.languages.join(" "),
    String((summary.metadata as Record<string, unknown>)?.name ?? ""),
    String((summary.metadata as Record<string, unknown>)?.description ?? ""),
  ].join(" ").toLowerCase()

  return haystack.includes(query)
}

function buildGroups(testsets: TestsetSummary[], groupBy: GroupMode): TestsetGroup[] {
  if (groupBy === "none") return []

  const grouped = new Map<string, TestsetSummary[]>()
  for (const summary of testsets) {
    let key = "all"
    if (groupBy === "task_type") {
      key = summary.task_types.length === 1 ? summary.task_types[0] : summary.task_types.join(", ") || "unknown"
    } else if (groupBy === "matrix_batch") {
      key = summary.matrix_batch_id ?? "__standalone__"
    }

    const items = grouped.get(key) ?? []
    items.push(summary)
    grouped.set(key, items)
  }

  return Array.from(grouped.entries()).map(([key, items]) => {
    const first = items[0]

    if (groupBy === "task_type") {
      return {
        key,
        title: key === "unknown" ? "Unknown Task" : key,
        subtitle: `${items.length} test set${items.length !== 1 ? "s" : ""}`,
        countLabel: `${items.length} items`,
        items,
      }
    }

    if (key === "__standalone__") {
      return {
        key,
        title: "Standalone Test Sets",
        subtitle: "Generated outside Matrix Execution",
        countLabel: `${items.length} items`,
        items,
      }
    }

    return {
      key,
      title: `Matrix Batch ${key}`,
      subtitle: `${first.matrix_plugin ?? first.task_types.join(", ")} • ${items.length} cell${items.length !== 1 ? "s" : ""}`,
      countLabel: `${items.length} cells`,
      items,
      headerExtras: first.matrix_plugin ? <Badge variant="outline">{first.matrix_plugin}</Badge> : null,
    }
  })
}

export default function TestSetsPage() {
  const storageScope = "testsets-page"
  const nav = useNavigate()
  const { data: testsets, isLoading } = useTestsets()
  const deleteMutation = useDeleteTestset()
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [detailTarget, setDetailTarget] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<string>("overview")
  const [regenTarget, setRegenTarget] = useState<string | null>(null)
  const [casesPage, setCasesPage] = useState(1)
  const [storedViewMode, setStoredViewMode] = useLocalStorageState<ViewMode>(makeStorageKey(storageScope, "view-mode"), "table")
  const [groupBy, setGroupBy] = useLocalStorageState<GroupMode>(makeStorageKey(storageScope, "group-by"), "none")
  const [searchTerm, setSearchTerm] = useLocalStorageState<string>(makeStorageKey(storageScope, "search"), "")
  const [taskFilter, setTaskFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "task-filter"), [])
  const [languageFilter, setLanguageFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "language-filter"), [])
  const [userStyleFilter, setUserStyleFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "user-style-filter"), [])
  const [systemStyleFilter, setSystemStyleFilter] = useLocalStorageState<string[]>(makeStorageKey(storageScope, "system-style-filter"), [])
  const { data: detail } = useTestset(detailTarget, casesPage)
  const viewMode: ViewMode = groupBy === "none" && storedViewMode === "cards" ? "table" : storedViewMode

  const taskOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((summary) => summary.task_types))].sort()
    return unique.map((task) => ({ label: task, value: task }))
  }, [testsets])

  const languageOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((summary) => summary.languages ?? []))].sort()
    return languageFilterOptions(unique)
  }, [testsets])

  const userStyleOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((summary) => summary.user_styles ?? []))].sort()
    return unique.map((style) => ({ label: style, value: style }))
  }, [testsets])

  const systemStyleOptions = useMemo(() => {
    const unique = [...new Set((testsets ?? []).flatMap((summary) => summary.system_styles ?? []))].sort()
    return unique.map((style) => ({ label: style, value: style }))
  }, [testsets])

  const filteredTestsets = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    return [...(testsets ?? [])]
      .filter((summary) => matchesSearch(summary, query))
      .filter((summary) => taskFilter.length === 0 || taskFilter.some((value) => summary.task_types.includes(value)))
      .filter((summary) => matchesAny(summary.languages, languageFilter))
      .filter((summary) => matchesAny(summary.user_styles, userStyleFilter))
      .filter((summary) => matchesAny(summary.system_styles, systemStyleFilter))
      .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())
  }, [languageFilter, searchTerm, systemStyleFilter, taskFilter, testsets, userStyleFilter])

  const groups = useMemo(() => buildGroups(filteredTestsets, groupBy), [filteredTestsets, groupBy])
  const showFlatOrGroupedTable = viewMode === "table" || groupBy === "none"

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

  const columns: ColumnDef<TestsetSummary>[] = [
    {
      accessorKey: "filename",
      header: "Name",
      cell: ({ row }) => (
        <IdentifierLabel
          value={row.original.filename.replace(".json.gz", "")}
          primaryMax={48}
          secondaryMax={30}
          primaryClassName="text-xs"
        />
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
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDate(row.original.created)}</span>,
    },
    {
      id: "view_details",
      header: "Details",
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={() => {
            setDetailTarget(row.original.filename)
            setCasesPage(1)
          }}
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

      <div className="space-y-3 rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-60 flex-1 sm:max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search test sets..."
              className="pl-8"
            />
          </div>
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
            ["matrix_batch", "Matrix Batch"],
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
          <Badge variant="secondary" className="ml-auto">{filteredTestsets.length} visible</Badge>
        </div>
      </div>

      {showFlatOrGroupedTable ? (
        <DataTable
          columns={columns}
          data={filteredTestsets}
          loading={isLoading}
          grouping={groupBy === "none" ? undefined : { buildGroups: (rows) => buildGroups(rows, groupBy) }}
          persistKey="testsets-table"
          getRowId={(row) => row.filename}
        />
      ) : groups.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          No test sets match the current filters.
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group, index) => (
            <GroupedGridSection
              key={group.key}
              title={group.title}
              subtitle={group.subtitle}
              countLabel={group.countLabel}
              headerExtras={group.headerExtras}
              defaultOpen={groups.length === 1 || index === 0}
            >
              <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {group.items.map((summary) => (
                  <TestsetSummaryCard
                    key={summary.filename}
                    summary={summary}
                    onView={() => {
                      setDetailTarget(summary.filename)
                      setCasesPage(1)
                    }}
                    onRun={() => nav(`/execute?testset=${summary.filename}`)}
                    onRegenerate={() => setRegenTarget(summary.filename)}
                    onDelete={() => setDeleteTarget(summary.filename)}
                  />
                ))}
              </div>
            </GroupedGridSection>
          ))}
        </div>
      )}

      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent className="max-w-lg sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Delete test set?</DialogTitle>
            <DialogDescription>
              This will permanently delete:
              <span className="mt-1 block truncate font-mono text-xs" title={deleteTarget ?? ""}>
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

      {regenTarget && (
        <ParamOverrideModal
          open={!!regenTarget}
          onOpenChange={(open) => { if (!open) setRegenTarget(null) }}
          testsetFilename={regenTarget}
          mode="regenerate"
        />
      )}

      <Sheet open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <SheetContent className="overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle className="truncate text-sm">{detailTarget}</SheetTitle>
          </SheetHeader>
          {detail && (
            <Tabs value={detailTab} onValueChange={setDetailTab} className="mt-4">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="cases">
                  Cases ({detail.total_cases ?? detail.test_count})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-3 space-y-4 text-xs">
                <section>
                  <h4 className="mb-1 font-medium">Metadata</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.metadata, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="mb-1 font-medium">Generation Params</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.generation_params, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="mb-1 font-medium">Sampling Params</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.sampling_params, null, 2)}</pre>
                </section>
                <section>
                  <h4 className="mb-1 font-medium">Statistics</h4>
                  <pre className="overflow-x-auto rounded bg-muted p-2">{JSON.stringify(detail.statistics, null, 2)}</pre>
                </section>
              </TabsContent>

              <TabsContent value="cases" className="mt-3 space-y-2 text-xs">
                {detail.sample_cases.map((testCase, index) => (
                  <details key={index} className="rounded border">
                    <summary className="flex cursor-pointer items-center justify-between p-2">
                      <span className="font-mono">
                        {((testCase as Record<string, unknown>).test_id as string) ?? `Case ${((detail.page ?? 1) - 1) * (detail.page_size ?? 50) + index + 1}`}
                      </span>
                      <Badge variant="secondary" className="text-[10px]">
                        {((testCase as Record<string, unknown>).task_type as string) ?? "unknown"}
                      </Badge>
                    </summary>
                    <pre className="overflow-x-auto bg-muted/50 p-2">
                      {JSON.stringify(testCase, null, 2)}
                    </pre>
                  </details>
                ))}

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
                        onClick={() => setCasesPage((page) => Math.max(1, page - 1))}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        disabled={casesPage >= Math.ceil((detail.total_cases ?? detail.test_count) / (detail.page_size ?? 50))}
                        onClick={() => setCasesPage((page) => page + 1)}
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