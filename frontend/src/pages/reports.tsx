import { useState } from "react"
import { FileText, ExternalLink, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/layout/page-header"
import { formatBytes } from "@/lib/utils"
import { useReports } from "@/hooks/use-results"
import type { ReportInfo } from "@/types"

export default function ReportsPage() {
  const { data: reports, isLoading, refetch } = useReports()
  const [activeReport, setActiveReport] = useState<ReportInfo | null>(null)

  const sorted = [...(reports ?? [])].sort(
    (a, b) => new Date(b.created).getTime() - new Date(a.created).getTime(),
  )

  const iframeSrc = activeReport ? `/api/results/report/${encodeURIComponent(activeReport.filename)}` : null

  return (
    <div className="space-y-4 h-full flex flex-col">
      <PageHeader
        title="Reports"
        description="View generated HTML reports"
        actions={
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Refresh
          </Button>
        }
      />

      {isLoading && <p className="text-xs text-muted-foreground">Loading reports…</p>}

      {!isLoading && sorted.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <FileText className="h-12 w-12 text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground">No reports yet</p>
          <p className="text-xs text-muted-foreground">
            Select result files on the Results page and click "Generate Report"
          </p>
        </div>
      )}

      {sorted.length > 0 && (
        <div className="grid grid-cols-[280px_1fr] gap-4 flex-1 min-h-0">
          {/* Left panel — report list */}
          <div className="border rounded-md overflow-y-auto">
            {sorted.map((r) => (
              <button
                key={r.filename}
                onClick={() => setActiveReport(r)}
                className={`w-full text-left px-3 py-2.5 border-b last:border-b-0 hover:bg-muted/50 transition-colors ${
                  activeReport?.filename === r.filename ? "bg-muted" : ""
                }`}
              >
                <p className="text-xs font-medium truncate">{r.filename}</p>
                <p className="text-[10px] text-muted-foreground">
                  {new Date(r.created).toLocaleString()} · {formatBytes(r.size_bytes)}
                </p>
              </button>
            ))}
          </div>

          {/* Right panel — report iframe */}
          <div className="border rounded-md overflow-hidden flex flex-col">
            {iframeSrc ? (
              <>
                <div className="flex items-center justify-between px-3 py-1.5 border-b bg-muted/30">
                  <span className="text-xs text-muted-foreground truncate">{activeReport?.filename}</span>
                  <a href={iframeSrc} target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                      <ExternalLink className="mr-1 h-3 w-3" /> Open
                    </Button>
                  </a>
                </div>
                <iframe src={iframeSrc} className="flex-1 w-full bg-white" title="Report" />
              </>
            ) : (
              <div className="flex items-center justify-center flex-1 text-xs text-muted-foreground">
                Select a report from the left
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
