import { useNavigate } from "react-router"
import { type ColumnDef, type Table } from "@tanstack/react-table"
import { toast } from "sonner"
import { Ban, Eye, Loader2, PauseCircle, PlayCircle, StopCircle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { IdentifierLabel } from "@/components/identifier-label"
import { Progress } from "@/components/ui/progress"
import { DataTable } from "@/components/data-table/data-table"
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter"
import { PageHeader } from "@/components/layout/page-header"
import { useJobs, useCancelJob, usePauseJob, useResumeJob, useStopAndDumpJob } from "@/hooks/use-jobs"
import { formatDuration, formatTimestamp, basename } from "@/lib/utils"
import type { Job } from "@/types"

const STATE_OPTIONS = [
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Paused", value: "paused" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
]

const stateBadge: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string; className?: string }> = {
  pending: { variant: "outline", label: "Pending" },
  running: { variant: "default", label: "Running" },
  paused: { variant: "outline", label: "Paused", className: "border-amber-400 bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300" },
  completed: { variant: "secondary", label: "Completed" },
  failed: { variant: "destructive", label: "Failed" },
  cancelled: { variant: "outline", label: "Cancelled" },
}

export default function JobsPage() {
  const nav = useNavigate()
  const { data: jobs = [], isLoading } = useJobs(true)
  const cancelMut = useCancelJob()
  const pauseMut = usePauseJob()
  const resumeMut = useResumeJob()
  const stopDumpMut = useStopAndDumpJob()

  const columns: ColumnDef<Job>[] = [
    {
      id: "type",
      header: "Type",
      cell: ({ row }) => {
        const isJudge = row.original.model_name.startsWith("judge:")
        return (
          <Badge variant={isJudge ? "secondary" : "outline"} className="text-[10px]">
            {isJudge ? "judge" : "inference"}
          </Badge>
        )
      },
    },
    {
      accessorKey: "model_name",
      header: "Model",
      cell: ({ row }) => {
        const name = row.original.model_name.replace(/^judge:/, "")
        return <span className="block max-w-50 truncate font-medium">{name}</span>
      },
    },
    {
      accessorKey: "testset_path",
      header: "Test Set",
      cell: ({ row }) => (
        <IdentifierLabel
          value={basename(row.original.testset_path)}
          primaryMax={40}
          secondaryMax={28}
          primaryClassName="text-xs text-muted-foreground"
          secondaryClassName="text-[10px]"
        />
      ),
      enableSorting: false,
    },
    {
      accessorKey: "state",
      header: "State",
      cell: ({ row }) => {
        const s = row.original.state
        const jobId = row.original.id
        if (pauseMut.isPending && pauseMut.variables === jobId)
          return <Badge variant="outline" className="gap-1 border-amber-400 bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300"><Loader2 className="h-3 w-3 animate-spin" />Pausing</Badge>
        if (stopDumpMut.isPending && stopDumpMut.variables === jobId)
          return <Badge variant="outline" className="gap-1 border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"><Loader2 className="h-3 w-3 animate-spin" />Stopping</Badge>
        if (resumeMut.isPending && resumeMut.variables === jobId)
          return <Badge variant="outline" className="gap-1 border-green-400 bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"><Loader2 className="h-3 w-3 animate-spin" />Resuming</Badge>
        const b = stateBadge[s] ?? stateBadge.pending
        return (
          <Badge variant={b.variant} className={`gap-1 ${b.className ?? ""}`}>
            {s === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
            {s === "paused" && <PauseCircle className="h-3 w-3" />}
            {b.label}
          </Badge>
        )
      },
      filterFn: (row, id, value: string[]) => value.includes(row.getValue(id) as string),
    },
    {
      id: "progress",
      header: "Progress",
      cell: ({ row }) => {
        const { state, progress_current, progress_total, paused_at_index } = row.original
        if (state === "paused") {
          const idx = paused_at_index ?? progress_current
          const pct = progress_total > 0 ? (idx / progress_total) * 100 : 0
          return (
            <div className="flex min-w-30 items-center gap-2">
              <Progress value={pct} className="h-2 flex-1 [&>div]:bg-amber-400" />
              <span className="text-xs text-muted-foreground whitespace-nowrap">{idx}/{progress_total}</span>
            </div>
          )
        }
        if (state !== "running" && state !== "pending") return <span className="text-muted-foreground">-</span>
        const pct = progress_total > 0 ? (progress_current / progress_total) * 100 : 0
        return (
          <div className="flex min-w-30 items-center gap-2">
            <Progress value={pct} className="h-2 flex-1" />
            <span className="text-xs text-muted-foreground whitespace-nowrap">{progress_current}/{progress_total}</span>
          </div>
        )
      },
      enableSorting: false,
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => <span className="text-muted-foreground whitespace-nowrap">{formatTimestamp(row.original.created_at)}</span>,
    },
    {
      accessorKey: "elapsed_seconds",
      header: "Duration",
      cell: ({ row }) => <span className="text-muted-foreground">{formatDuration(row.original.elapsed_seconds)}</span>,
    },
    {
      id: "eta",
      header: "ETA",
      cell: ({ row }) => {
        const { state, eta_seconds } = row.original
        return (
          <span className="block min-w-16 text-muted-foreground">
            {state === "running" && eta_seconds != null ? formatDuration(eta_seconds) : "—"}
          </span>
        )
      },
      enableSorting: false,
    },
    {
      id: "actions",
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => {
        const job = row.original
        return (
          <div className="flex items-center gap-1">
            {job.state === "running" && !job.model_name.startsWith("judge:") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-amber-600 hover:text-amber-700"
                onClick={() => pauseMut.mutate(job.id, {
                  onSuccess: () => toast.success(`Pausing job for ${job.model_name}…`),
                  onError: (err) => toast.error(`Pause failed: ${err instanceof Error ? err.message : "Unknown error"}`),
                })}
                disabled={pauseMut.isPending && pauseMut.variables === job.id}
                title="Pause Job"
              >
                {pauseMut.isPending && pauseMut.variables === job.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <PauseCircle className="h-3.5 w-3.5" />
                )}
              </Button>
            )}
            {(job.state === "running" || job.state === "paused") && !job.model_name.startsWith("judge:") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-blue-600 hover:text-blue-700"
                onClick={() => stopDumpMut.mutate(job.id, {
                  onSuccess: () => toast.success(`Stopping and saving results for ${job.model_name}…`),
                  onError: (err) => toast.error(`Stop failed: ${err instanceof Error ? err.message : "Unknown error"}`),
                })}
                disabled={stopDumpMut.isPending && stopDumpMut.variables === job.id}
                title="Stop and save results"
              >
                {stopDumpMut.isPending && stopDumpMut.variables === job.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <StopCircle className="h-3.5 w-3.5" />
                )}
              </Button>
            )}
            {job.state === "paused" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-green-600 hover:text-green-700"
                onClick={() => resumeMut.mutate(job.id, {
                  onSuccess: () => toast.success(`Resuming job for ${job.model_name}`),
                  onError: (err) => toast.error(`Resume failed: ${err instanceof Error ? err.message : "Unknown error"}`),
                })}
                disabled={resumeMut.isPending && resumeMut.variables === job.id}
                title="Resume Job"
              >
                {resumeMut.isPending && resumeMut.variables === job.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <PlayCircle className="h-3.5 w-3.5" />
                )}
              </Button>
            )}
            {(job.state === "running" || job.state === "pending") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-destructive"
                onClick={() => cancelMut.mutate(job.id, {
                  onSuccess: () => toast.success(`Cancelled job for ${job.model_name}`),
                  onError: (err) => toast.error(`Cancel failed: ${err instanceof Error ? err.message : "Unknown error"}`),
                })}
                disabled={cancelMut.isPending && cancelMut.variables === job.id}
                title="Cancel Job"
              >
                {cancelMut.isPending && cancelMut.variables === job.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Ban className="h-3.5 w-3.5" />
                )}
              </Button>
            )}
            {job.state === "completed" && job.result_path && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                onClick={() => nav(job.model_name.startsWith("judge:") ? "/judge" : "/results")}
              >
                <Eye className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        )
      },
    },
  ]

  const toolbar = (table: Table<Job>) => (
    <>
      {table.getColumn("state") && (
        <DataTableFacetedFilter column={table.getColumn("state")} title="State" options={STATE_OPTIONS} />
      )}
    </>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Monitor benchmark execution jobs"
      />
      <DataTable
        columns={columns}
        data={jobs}
        searchKey="model_name"
        searchPlaceholder="Search by model..."
        toolbar={toolbar}
        loading={isLoading}
        persistKey="jobs-table"
        getRowId={(row) => row.id}
      />
    </div>
  )
}
