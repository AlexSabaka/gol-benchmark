import { Eye, MoreHorizontal, Play, RotateCcw, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { TaskBadge } from "@/components/task-badge"
import { langFlags } from "@/lib/language-flags"
import { formatBytes, formatDate } from "@/lib/utils"
import type { TestsetSummary } from "@/types"

interface TestsetSummaryCardProps {
  summary: TestsetSummary
  onView: () => void
  onRun: () => void
  onRegenerate: () => void
  onDelete: () => void
}

export function TestsetSummaryCard({ summary, onView, onRun, onRegenerate, onDelete }: TestsetSummaryCardProps) {
  const title = summary.filename.replace(".json.gz", "")

  return (
    <Card className="gap-4 py-4">
      <CardHeader className="px-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <CardTitle className="truncate text-sm" title={title}>{title}</CardTitle>
            <div className="flex flex-wrap gap-1">
              {summary.task_types.map((task) => (
                <TaskBadge key={task} task={task} />
              ))}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onRun}>
                <Play className="mr-2 h-3.5 w-3.5" /> Run Benchmark
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onRegenerate}>
                <RotateCcw className="mr-2 h-3.5 w-3.5" /> Regenerate with Params
              </DropdownMenuItem>
              <DropdownMenuItem className="text-destructive" onClick={onDelete}>
                <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 px-4 text-xs">
        {summary.matrix_label && <p className="line-clamp-2 text-muted-foreground">{summary.matrix_label}</p>}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Languages</span>
          <span className="text-sm" title={(summary.languages ?? []).join(", ")}>{langFlags(summary.languages ?? [])}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">User / System</span>
          <span>{summary.user_styles.join(", ") || "-"} / {summary.system_styles.join(", ") || "-"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Tests / Size</span>
          <span>{summary.test_count} / {formatBytes(summary.size_bytes)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Created</span>
          <span>{formatDate(summary.created)}</span>
        </div>
        {summary.matrix_cell_id && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Matrix Cell</span>
            <Badge variant="outline">{summary.matrix_cell_id}</Badge>
          </div>
        )}
      </CardContent>
      <CardFooter className="px-4 pt-0">
        <Button variant="outline" size="sm" className="w-full text-xs" onClick={onView}>
          <Eye className="mr-1.5 h-3.5 w-3.5" /> View Details
        </Button>
      </CardFooter>
    </Card>
  )
}