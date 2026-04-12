import { Eye, MoreHorizontal, RotateCcw, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { TaskBadge } from "@/components/task-badge"
import { langFlags } from "@/lib/language-flags"
import { formatDate, formatDuration, formatPercent } from "@/lib/utils"
import type { ResultSummary } from "@/types"

interface ResultSummaryCardProps {
  summary: ResultSummary
  selected: boolean
  onToggleSelect: () => void
  onView: () => void
  onRerun: () => void
  onDelete: () => void
}

export function ResultSummaryCard({
  summary,
  selected,
  onToggleSelect,
  onView,
  onRerun,
  onDelete,
}: ResultSummaryCardProps) {
  const accuracyClass = summary.accuracy >= 0.7 ? "text-green-600" : summary.accuracy >= 0.4 ? "text-yellow-600" : "text-red-600"

  return (
    <Card className="gap-4 py-4">
      <CardHeader className="px-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-start gap-2">
            <Checkbox checked={selected} onCheckedChange={onToggleSelect} className="mt-0.5" />
            <div className="min-w-0 flex-1 space-y-2">
              <CardTitle className="truncate text-sm" title={summary.model_name}>{summary.model_name}</CardTitle>
              <div className="flex flex-wrap gap-1">
                {summary.task_types.map((task) => (
                  <TaskBadge key={task} task={task} />
                ))}
              </div>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onView}>
                <Eye className="mr-2 h-3.5 w-3.5" /> View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onRerun}>
                <RotateCcw className="mr-2 h-3.5 w-3.5" /> Rerun with Params
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={onDelete}>
                <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 px-4 text-xs">
        {summary.matrix_label && <p className="line-clamp-2 text-muted-foreground">{summary.matrix_label}</p>}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Accuracy</span>
          <span className={`font-mono font-medium ${accuracyClass}`}>{formatPercent(summary.accuracy)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Tests</span>
          <Badge variant="secondary">{summary.correct}/{summary.total_tests}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Parse errors</span>
          <span>{formatPercent(summary.parse_error_rate)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Languages</span>
          <span className="text-sm" title={(summary.languages ?? []).join(", ")}>{langFlags(summary.languages ?? [])}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Test Set</span>
          <span className="truncate pl-4 text-right" title={summary.testset_name}>{summary.testset_name || "-"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Duration</span>
          <span>{formatDuration(summary.duration_seconds)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Created</span>
          <span>{formatDate(summary.created)}</span>
        </div>
      </CardContent>
      <CardFooter className="px-4 pt-0">
        <Button variant="outline" size="sm" className="w-full text-xs" onClick={onView}>
          <Eye className="mr-1.5 h-3.5 w-3.5" /> View Details
        </Button>
      </CardFooter>
    </Card>
  )
}