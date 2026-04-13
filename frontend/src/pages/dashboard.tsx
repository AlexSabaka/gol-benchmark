import { Link } from "react-router"
import { Database, Play, BarChart3, Plus, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IdentifierLabel } from "@/components/identifier-label"
import { Progress } from "@/components/ui/progress"
import { PageHeader } from "@/components/layout/page-header"
import { TaskBadge } from "@/components/task-badge"
import { JobStateBadge } from "@/components/job-state-badge"
import { useTestsets } from "@/hooks/use-testsets"
import { useResults } from "@/hooks/use-results"
import { useJobs } from "@/hooks/use-jobs"
import { formatDuration, formatPercent } from "@/lib/utils"

export default function DashboardPage() {
  const { data: testsets } = useTestsets()
  const { data: results } = useResults()
  const { data: jobs } = useJobs(true)

  const activeJobs = jobs?.filter((j) => j.state === "running" || j.state === "pending") ?? []
  const recentTestsets = testsets?.slice(0, 5) ?? []
  const recentResults = results?.slice(0, 5) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your benchmark suite"
        actions={
          <Button asChild>
            <Link to="/configure">
              <Plus className="mr-2 h-4 w-4" /> New Test Set
            </Link>
          </Button>
        }
      />

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard title="Test Sets" value={testsets?.length ?? 0} icon={Database} to="/testsets" />
        <SummaryCard title="Results" value={results?.length ?? 0} icon={BarChart3} to="/results" />
        <SummaryCard
          title="Active Jobs"
          value={activeJobs.length}
          icon={activeJobs.length > 0 ? Loader2 : Play}
          to="/execute"
          iconClassName={activeJobs.length > 0 ? "animate-spin" : ""}
        />
      </div>

      {/* Active jobs */}
      {activeJobs.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Active Jobs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeJobs.map((job) => (
              <div key={job.id} className="flex items-center gap-4 text-sm">
                <JobStateBadge state={job.state} />
                <span className="font-medium truncate flex-1">{job.model_name}</span>
                <div className="w-32">
                  <Progress
                    value={job.progress_total > 0 ? (job.progress_current / job.progress_total) * 100 : 0}
                    className="h-2"
                  />
                </div>
                <span className="text-muted-foreground text-xs whitespace-nowrap">
                  {job.progress_current}/{job.progress_total}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent items */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent test sets */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">Recent Test Sets</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/testsets">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recentTestsets.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No test sets yet</p>
            ) : (
              <div className="space-y-2">
                {recentTestsets.map((ts) => (
                  <div key={ts.filename} className="flex items-center gap-3 text-sm">
                    <IdentifierLabel
                      value={ts.filename.replace(".json.gz", "")}
                      className="flex-1"
                      primaryMax={38}
                      secondaryMax={24}
                      primaryClassName="text-sm"
                    />
                    <div className="flex gap-1">
                      {ts.task_types?.slice(0, 2).map((t) => <TaskBadge key={t} task={t} />)}
                      {(ts.task_types?.length ?? 0) > 2 && (
                        <span className="text-xs text-muted-foreground">+{ts.task_types.length - 2}</span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{ts.test_count} tests</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent results */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">Recent Results</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/results">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {recentResults.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No results yet</p>
            ) : (
              <div className="space-y-2">
                {recentResults.map((r) => (
                  <div key={r.filename} className="flex items-center gap-3 text-sm">
                    <span className="font-medium truncate flex-1">{r.model_name}</span>
                    <span
                      className={`font-mono text-xs font-medium ${
                        r.accuracy >= 0.7
                          ? "text-green-600 dark:text-green-400"
                          : r.accuracy >= 0.4
                          ? "text-yellow-600 dark:text-yellow-400"
                          : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      {formatPercent(r.accuracy)}
                    </span>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{r.total_tests} tests</span>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{formatDuration(r.duration_seconds)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  )
}

function SummaryCard({
  title,
  value,
  icon: Icon,
  to,
  iconClassName = "",
}: {
  title: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  to: string
  iconClassName?: string
}) {
  return (
    <Link to={to}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardContent className="flex items-center gap-4 pt-6">
          <div className="rounded-lg bg-primary/10 p-3">
            <Icon className={`h-5 w-5 text-primary ${iconClassName}`} />
          </div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-sm text-muted-foreground">{title}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
