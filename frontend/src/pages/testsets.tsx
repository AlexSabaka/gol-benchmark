import { useState } from "react"
import { useNavigate } from "react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { toast } from "sonner"
import { Trash2, Play, Eye, MoreHorizontal } from "lucide-react"

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
import { DataTable } from "@/components/data-table/data-table"
import { PageHeader } from "@/components/layout/page-header"
import { TaskBadge } from "@/components/task-badge"
import { formatBytes } from "@/lib/utils"
import { useTestsets, useTestset, useDeleteTestset } from "@/hooks/use-testsets"
import type { TestsetSummary } from "@/types"

export default function TestSetsPage() {
  const nav = useNavigate()
  const { data: testsets, isLoading } = useTestsets()
  const deleteMutation = useDeleteTestset()
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [detailTarget, setDetailTarget] = useState<string | null>(null)
  const { data: detail } = useTestset(detailTarget)

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
      filterFn: (row, _col, value: string) =>
        row.original.task_types.some((t) => t.includes(value)),
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
            <DropdownMenuItem onClick={() => nav(`/execute?testset=${row.original.filename}`)}>
              <Play className="mr-2 h-3.5 w-3.5" /> Run Benchmark
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

      <DataTable columns={columns} data={testsets ?? []} loading={isLoading} searchPlaceholder="Search test sets…" />

      {/* Delete confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete test set?</DialogTitle>
            <DialogDescription>
              This will permanently delete <span className="font-mono text-xs">{deleteTarget}</span>.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteMutation.isPending}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail sheet */}
      <Sheet open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <SheetContent className="sm:max-w-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-sm truncate">{detailTarget}</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="mt-4 space-y-4 text-xs">
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
              {detail.sample_cases.length > 0 && (
                <section>
                  <h4 className="font-medium mb-1">Sample Cases ({detail.sample_cases.length})</h4>
                  <pre className="bg-muted p-2 rounded overflow-x-auto max-h-[400px]">
                    {JSON.stringify(detail.sample_cases, null, 2)}
                  </pre>
                </section>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
