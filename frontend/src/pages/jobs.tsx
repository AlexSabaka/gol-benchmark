import { useNavigate } from "react-router"
import { type ColumnDef, type Table } from "@tanstack/react-table"
import { toast } from "sonner"
import { Ban, Eye, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { DataTable } from "@/components/data-table/data-table"
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter"
import { PageHeader } from "@/components/layout/page-header"
import { useJobs, useCancelJob } from "@/hooks/use-jobs"
import { formatDuration, formatTimestamp, basename } from "@/lib/utils"
import type { Job } from "@/types"

const STATE_OPTIONS = [
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
]

const stateBadge: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
  pending: { variant: "outline", label: "Pending" },
  running: { variant: "default", label: "Running" },
  completed: { variant: "secondary", label: "Completed" },
  failed: { variant: "destructive", label: "Failed" },
  cancelled: { variant: "outline", label: "Cancelled" },
}

export default function JobsPage() {
  const nav = useNavigate()
  const { data: jobs = [], isLoading } = useJobs(true)
  const cancelMut = useCancelJob()

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
        return <span className="font-medium truncate max-w-[200px] block">{name}</span>
      },
    },
    {
      accessorKey: "testset_path",
      header: "Test Set",
      cell: ({ row }) => <span className="text-muted-foreground truncate max-w-[200px] block">{basename(row.original.testset_path)}</span>,
      enableSorting: false,
    },
    {
      accessorKey: "state",
      header: "State",
      cell: ({ row }) => {
        const s = row.original.state
        const b = stateBadge[s] ?? stateBadge.pending
        return (
          <Badge variant={b.variant} className="gap-1">
            {s === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
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
        const { state, progress_current, progress_total } = row.original
        if (state !== "running" && state !== "pending") return <span className="text-muted-foreground">-</span>
        const pct = progress_total > 0 ? (progress_current / progress_total) * 100 : 0
        return (
          <div className="flex items-center gap-2 min-w-[120px]">
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
      id: "actions",
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => {
        const job = row.original
        return (
          <div className="flex items-center gap-1">
            {(job.state === "running" || job.state === "pending") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-destructive"
                onClick={() => cancelMut.mutate(job.id, {
                  onSuccess: () => toast.success(`Cancelled job for ${job.model_name}`),
                  onError: (err) => toast.error(`Cancel failed: ${err instanceof Error ? err.message : "Unknown error"}`),
                })}
                disabled={cancelMut.isPending}
              >
                <Ban className="h-3.5 w-3.5" />
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
      />
    </div>
  )
}
