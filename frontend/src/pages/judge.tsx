import { useMemo, useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { toast } from "sonner"
import {
  Scale,
  Loader2,
  ChevronDown,
  AlertTriangle,
  XCircle,
  Bug,
  Download,
  FileText,
  Trash2,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { IdentifierLabel } from "@/components/identifier-label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { DataTable } from "@/components/data-table/data-table"
import { PageHeader } from "@/components/layout/page-header"
import { useJudgeResult, useJudgeResults, useDeleteResult } from "@/hooks/use-results"
import { makeStorageKey, useLocalStorageState } from "@/lib/local-storage"
import type { JudgeSummary, JudgeResult, JudgmentEntry } from "@/types"

interface JudgeTableRow extends JudgmentEntry {
  rowId: string
}

// ── Verdict styling ──

const VERDICT_CONFIG: Record<string, { label: string; color: string; icon: typeof XCircle }> = {
  true_incorrect: { label: "True Incorrect", color: "text-red-500 bg-red-500/10 border-red-500/20", icon: XCircle },
  false_negative: { label: "False Negative", color: "text-amber-500 bg-amber-500/10 border-amber-500/20", icon: AlertTriangle },
  parser_failure: { label: "Parser Failure", color: "text-blue-500 bg-blue-500/10 border-blue-500/20", icon: Bug },
  error: { label: "Error", color: "text-muted-foreground bg-muted", icon: AlertTriangle },
  parse_error: { label: "Parse Error", color: "text-muted-foreground bg-muted", icon: AlertTriangle },
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const config = VERDICT_CONFIG[verdict] ?? VERDICT_CONFIG.error
  const Icon = config.icon
  return (
    <Badge variant="outline" className={`gap-1 text-[11px] ${config.color}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colors: Record<string, string> = {
    high: "text-green-600 bg-green-500/10",
    medium: "text-yellow-600 bg-yellow-500/10",
    low: "text-red-600 bg-red-500/10",
  }
  return (
    <Badge variant="outline" className={`text-[10px] ${colors[confidence] ?? ""}`}>
      {confidence}
    </Badge>
  )
}

function buildJudgmentRowId(judgment: JudgmentEntry, index: number) {
  return `${judgment.source_file}:${judgment.test_id}:${judgment.model}:${index}`
}

function JudgmentDetailContent({ judgment }: { judgment: JudgmentEntry }) {
  return (
    <div className="space-y-3 text-xs">
      <div>
        <h5 className="mb-1 font-medium text-muted-foreground">Expected Answer</h5>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2">{judgment.expected_answer}</pre>
      </div>
      <div>
        <h5 className="mb-1 font-medium text-muted-foreground">Parsed Answer</h5>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2">{judgment.parsed_answer}</pre>
      </div>
      <div>
        <h5 className="mb-1 font-medium text-muted-foreground">Model Response</h5>
        <pre className="max-h-50 overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2">{judgment.raw_response}</pre>
      </div>
      <div>
        <h5 className="mb-1 font-medium text-muted-foreground">Question</h5>
        <pre className="max-h-50 overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2">{judgment.user_prompt}</pre>
      </div>
    </div>
  )
}

// ── Summary cards ──

function SummaryCards({ result }: { result: JudgeResult }) {
  const s = result.summary
  const total = s.total_judged || 1
  const stats = [
    { label: "Total Judged", value: s.total_judged, pct: null, color: "text-foreground" },
    { label: "True Incorrect", value: s.true_incorrect ?? 0, pct: ((s.true_incorrect ?? 0) / total * 100).toFixed(1), color: "text-red-500" },
    { label: "False Negative", value: s.false_negative ?? 0, pct: ((s.false_negative ?? 0) / total * 100).toFixed(1), color: "text-amber-500" },
    { label: "Parser Failure", value: s.parser_failure ?? 0, pct: ((s.parser_failure ?? 0) / total * 100).toFixed(1), color: "text-blue-500" },
  ]

  return (
    <div className="grid gap-3 sm:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-muted-foreground">{s.label}</p>
            <p className={`text-2xl font-bold tabular-nums ${s.color}`}>
              {s.value}
              {s.pct !== null && <span className="text-xs font-normal text-muted-foreground ml-1">({s.pct}%)</span>}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Verdict distribution bar ──

function VerdictBar({ result }: { result: JudgeResult }) {
  const s = result.summary
  const total = s.total_judged || 1
  const segments = [
    { key: "true_incorrect", value: s.true_incorrect ?? 0, color: "bg-red-500" },
    { key: "false_negative", value: s.false_negative ?? 0, color: "bg-amber-500" },
    { key: "parser_failure", value: s.parser_failure ?? 0, color: "bg-blue-500" },
  ]

  return (
    <div className="space-y-2">
      <div className="flex h-5 w-full rounded-full overflow-hidden bg-muted">
        {segments.map((seg) => {
          const pct = (seg.value / total) * 100
          if (pct === 0) return null
          return (
            <div
              key={seg.key}
              className={`${seg.color} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${VERDICT_CONFIG[seg.key]?.label}: ${seg.value} (${pct.toFixed(1)}%)`}
            />
          )
        })}
      </div>
      <div className="flex gap-4 text-xs text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key} className="flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${seg.color}`} />
            {VERDICT_CONFIG[seg.key]?.label}: {seg.value}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Parser issues breakdown ──

function ParserIssuesCard({ issues }: { issues: Record<string, number> }) {
  const entries = Object.entries(issues).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Parser Issue Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          {entries.map(([issue, count]) => (
            <div key={issue} className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{issue.replace(/_/g, " ")}</span>
              <Badge variant="secondary" className="text-[10px]">{count}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// ── Export helpers ──

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function exportJsonl(result: JudgeResult, filename: string) {
  const lines = result.judgments.map((j) => JSON.stringify(j)).join("\n")
  downloadBlob(lines, filename.replace(".json.gz", ".jsonl"), "application/jsonl")
}

function exportMarkdown(result: JudgeResult, filename: string) {
  const meta = result.metadata as Record<string, string>
  const s = result.summary
  const total = s.total_judged || 1

  // Group by verdict
  const byVerdict: Record<string, typeof result.judgments> = {}
  for (const j of result.judgments) {
    ;(byVerdict[j.verdict] ??= []).push(j)
  }

  // Group parser failures by task_type then issue
  const parserFails = byVerdict["parser_failure"] ?? []
  const pfByTask: Record<string, typeof result.judgments> = {}
  for (const j of parserFails) {
    const task = j.task_type || j.test_id.replace(/_\d+$/, "").replace(/^multi_\d+_/, "") || "unknown"
    ;(pfByTask[task] ??= []).push(j)
  }
  const pfByIssue: Record<string, typeof result.judgments> = {}
  for (const j of parserFails) {
    ;(pfByIssue[j.parser_issue ?? "unknown"] ??= []).push(j)
  }

  // Group false negatives by task_type
  const falseNegs = byVerdict["false_negative"] ?? []
  const fnByTask: Record<string, typeof result.judgments> = {}
  for (const j of falseNegs) {
    const task = j.task_type || j.test_id.replace(/_\d+$/, "").replace(/^multi_\d+_/, "") || "unknown"
    ;(fnByTask[task] ??= []).push(j)
  }

  let md = `# LLM Judge Report

**Judge model:** ${meta.judge_model ?? "unknown"}
**Provider:** ${meta.judge_provider ?? "unknown"}
**Date:** ${meta.timestamp ?? "unknown"}
**Duration:** ${meta.duration_seconds ?? "?"}s
**Source files:** ${result.source_results.join(", ")}

## Summary

| Verdict | Count | % |
|---------|------:|--:|
| True Incorrect | ${s.true_incorrect ?? 0} | ${((s.true_incorrect ?? 0) / total * 100).toFixed(1)}% |
| False Negative | ${s.false_negative ?? 0} | ${((s.false_negative ?? 0) / total * 100).toFixed(1)}% |
| Parser Failure | ${s.parser_failure ?? 0} | ${((s.parser_failure ?? 0) / total * 100).toFixed(1)}% |
| **Total** | **${s.total_judged}** | |
`

  if (Object.keys(s.parser_issues).length > 0) {
    md += `\n### Parser Issue Breakdown\n\n| Issue Type | Count |\n|-----------|------:|\n`
    for (const [issue, count] of Object.entries(s.parser_issues).sort((a, b) => (b[1] as number) - (a[1] as number))) {
      md += `| ${issue.replace(/_/g, " ")} | ${count} |\n`
    }
  }

  // ── Key Findings (auto-generated actionable summary) ──
  const actionable = parserFails.length + falseNegs.length
  if (actionable > 0) {
    md += `\n### Key Findings\n\n`
    // Top task types with parser failures
    for (const [task, items] of Object.entries(pfByTask).sort((a, b) => b[1].length - a[1].length).slice(0, 5)) {
      const langs = [...new Set(items.map((j) => j.language || "?"))].join(", ")
      const issues = [...new Set(items.map((j) => j.parser_issue || "?"))].join(", ")
      md += `- **${items.length}/${parserFails.length} parser failures** are \`${task}\` (lang: ${langs}, issues: ${issues})\n`
    }
    for (const [task, items] of Object.entries(fnByTask).sort((a, b) => b[1].length - a[1].length).slice(0, 3)) {
      md += `- **${items.length} false negatives** in \`${task}\`\n`
    }
    md += "\n"
  }

  // ── Parser Failures by Task Type ──
  if (parserFails.length > 0) {
    md += `\n## Parser Failures (${parserFails.length})\n\nThe model gave a correct answer but the parser failed to extract it.\n\n`

    for (const [task, items] of Object.entries(pfByTask).sort((a, b) => b[1].length - a[1].length)) {
      md += `### Task: \`${task}\` (${items.length} failures)\n\n`
      md += `| Test ID | Model | Lang | Issue | Parsed | Expected | Notes |\n`
      md += `|---------|-------|------|-------|--------|----------|-------|\n`
      for (const j of items) {
        const parsed = j.parsed_answer === "None" || !j.parsed_answer ? "(no extraction)" : `\`${j.parsed_answer}\``
        md += `| ${j.test_id} | ${j.model} | ${j.language || "?"} | ${(j.parser_issue || "-").replace(/_/g, " ")} | ${parsed} | \`${j.expected_answer}\` | ${j.notes} |\n`
      }
      md += "\n"

      // Show response snippets for this task group
      md += `<details><summary>Response samples (${Math.min(items.length, 5)} of ${items.length})</summary>\n\n`
      for (const j of items.slice(0, 5)) {
        md += `**${j.test_id}** (${j.model}, ${j.language || "?"}):\n\`\`\`\n${j.raw_response.slice(0, 400)}${j.raw_response.length > 400 ? "\n..." : ""}\n\`\`\`\n\n`
      }
      md += `</details>\n\n`
    }
  }

  // ── False Negatives by Task Type ──
  if (falseNegs.length > 0) {
    md += `\n## False Negatives (${falseNegs.length})\n\nThese responses were marked incorrect but the judge determined them correct or defensible.\n\n`

    for (const [task, items] of Object.entries(fnByTask).sort((a, b) => b[1].length - a[1].length)) {
      md += `### Task: \`${task}\` (${items.length})\n\n`
      for (const j of items) {
        md += `- **${j.test_id}** (${j.model}, lang=${j.language || "?"}, confidence=${j.confidence})\n`
        md += `  - **Notes:** ${j.notes}\n`
        md += `  - Expected: \`${j.expected_answer}\` | Parsed: \`${j.parsed_answer || "(none)"}\`\n`
        md += `\n  <details><summary>Full response</summary>\n\n  \`\`\`\n  ${j.raw_response.slice(0, 800)}\n  \`\`\`\n  </details>\n\n`
      }
    }
  }

  // ── True Incorrect (compact table) ──
  const trueIncorrect = byVerdict["true_incorrect"] ?? []
  if (trueIncorrect.length > 0) {
    md += `\n## True Incorrect (${trueIncorrect.length})\n\nGenuinely wrong model responses — no parser fix needed.\n\n`
    md += `| Test ID | Model | Lang | Confidence | Notes |\n|---------|-------|------|-----------|-------|\n`
    for (const j of trueIncorrect.slice(0, 50)) {
      md += `| ${j.test_id} | ${j.model} | ${j.language || "?"} | ${j.confidence} | ${j.notes} |\n`
    }
    if (trueIncorrect.length > 50) {
      md += `\n*... and ${trueIncorrect.length - 50} more*\n`
    }
  }

  downloadBlob(md, filename.replace(".json.gz", "_report.md"), "text/markdown")
}

// ── Main page ──

export default function JudgePage() {
  const storageScope = "judge-page"
  const { data: judgeFiles, isLoading: filesLoading, refetch: refetchJudgeFiles } = useJudgeResults()
  const deleteMutation = useDeleteResult()
  const [selectedFile, setSelectedFile] = useLocalStorageState<string | null>(makeStorageKey(storageScope, "selected-file"), null)
  const [verdictFilter, setVerdictFilter] = useLocalStorageState<string>(makeStorageKey(storageScope, "verdict-filter"), "__all__")
  const [confidenceFilter, setConfidenceFilter] = useLocalStorageState<string>(makeStorageKey(storageScope, "confidence-filter"), "__all__")
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const { data: judgeResult, isLoading: resultLoading } = useJudgeResult(selectedFile)

  const toggleExpandedRow = (rowId: string) => {
    setExpandedRows((previous) => {
      const next = new Set(previous)
      if (next.has(rowId)) next.delete(rowId)
      else next.add(rowId)
      return next
    })
  }

  const handleDeleteJudge = async (filename: string) => {
    try {
      await deleteMutation.mutateAsync(filename)
      toast.success("Judge result deleted")
      if (selectedFile === filename) {
        setSelectedFile(null)
      }
      refetchJudgeFiles()
    } catch {
      toast.error("Delete failed")
    }
  }

  const judgmentRows = useMemo<JudgeTableRow[]>(() => (
    judgeResult
      ? judgeResult.judgments.map((judgment, index) => ({
          ...judgment,
          rowId: buildJudgmentRowId(judgment, index),
        }))
      : []
  ), [judgeResult])

  const filteredJudgments = useMemo(() => {
    let items = judgmentRows
    if (verdictFilter !== "__all__") {
      items = items.filter((j) => j.verdict === verdictFilter)
    }
    if (confidenceFilter !== "__all__") {
      items = items.filter((j) => j.confidence === confidenceFilter)
    }
    return items
  }, [confidenceFilter, judgmentRows, verdictFilter])

  const visibleExpandedRows = useMemo(() => {
    const visibleIds = new Set(filteredJudgments.map((judgment) => judgment.rowId))
    return new Set([...expandedRows].filter((rowId) => visibleIds.has(rowId)))
  }, [expandedRows, filteredJudgments])

  // Available verdicts and confidences for filters
  const verdictOptions = useMemo(() => {
    if (!judgeResult) return []
    return [...new Set(judgeResult.judgments.map((j) => j.verdict))].sort()
  }, [judgeResult])

  const confidenceOptions = useMemo(() => {
    if (!judgeResult) return []
    return [...new Set(judgeResult.judgments.map((j) => j.confidence))].sort()
  }, [judgeResult])

  // Table columns
  const columns: ColumnDef<JudgeTableRow>[] = [
    {
      id: "expand",
      header: "",
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => {
        const expanded = expandedRows.has(row.id)
        return (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => toggleExpandedRow(row.id)}
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
          </Button>
        )
      },
    },
    {
      accessorKey: "test_id",
      header: "Test ID",
      cell: ({ row }) => (
        <IdentifierLabel
          value={row.original.test_id}
          mono
          primaryMax={34}
          secondaryMax={20}
          primaryClassName="text-xs"
          secondaryClassName="text-[10px]"
        />
      ),
    },
    {
      accessorKey: "model",
      header: "Model",
      cell: ({ row }) => <span className="block max-w-30 truncate text-xs">{row.original.model}</span>,
    },
    {
      accessorKey: "verdict",
      header: "Verdict",
      cell: ({ row }) => <VerdictBadge verdict={row.original.verdict} />,
    },
    {
      accessorKey: "parser_issue",
      header: "Parser Issue",
      cell: ({ row }) => row.original.parser_issue
        ? <span className="text-xs text-muted-foreground">{row.original.parser_issue.replace(/_/g, " ")}</span>
        : <span className="text-xs text-muted-foreground/40">-</span>,
    },
    {
      accessorKey: "confidence",
      header: "Confidence",
      cell: ({ row }) => <ConfidenceBadge confidence={row.original.confidence} />,
    },
    {
      accessorKey: "notes",
      header: "Notes",
      cell: ({ row }) => {
        const notes = row.original.notes
        if (!notes) return <span className="text-xs text-muted-foreground/40">-</span>
        return (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="block max-w-70 cursor-help wrap-break-word text-xs leading-5 text-muted-foreground">
                {notes}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-sm text-xs">{notes}</TooltipContent>
          </Tooltip>
        )
      },
    },
  ]

  // Toolbar with filters
  const toolbar = () => (
    <div className="flex items-center gap-2">
      <Select value={verdictFilter} onValueChange={setVerdictFilter}>
        <SelectTrigger className="h-7 w-40 text-xs">
          <SelectValue placeholder="All verdicts" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All verdicts</SelectItem>
          {verdictOptions.map((v) => (
            <SelectItem key={v} value={v} className="text-xs">
              {VERDICT_CONFIG[v]?.label ?? v}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={confidenceFilter} onValueChange={setConfidenceFilter}>
        <SelectTrigger className="h-7 w-32.5 text-xs">
          <SelectValue placeholder="All confidence" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All confidence</SelectItem>
          {confidenceOptions.map((c) => (
            <SelectItem key={c} value={c} className="text-xs">{c}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <span className="text-xs text-muted-foreground ml-2">
        {filteredJudgments.length} judgment{filteredJudgments.length !== 1 ? "s" : ""}
      </span>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="LLM Judge"
        description="Audit model responses — classify incorrect results as true errors, false negatives, or parser failures"
        actions={
          judgeResult && selectedFile ? (
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => exportJsonl(judgeResult, selectedFile)}>
                <Download className="mr-1.5 h-3.5 w-3.5" /> Export JSONL
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportMarkdown(judgeResult, selectedFile)}>
                <FileText className="mr-1.5 h-3.5 w-3.5" /> Export Report
              </Button>
              <Button variant="destructive" size="sm" onClick={() => handleDeleteJudge(selectedFile!)}>
                <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Delete
              </Button>
            </div>
          ) : undefined
        }
      />

      {/* File selector */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Judge Results</CardTitle>
        </CardHeader>
        <CardContent>
          {filesLoading ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading judge results...
            </div>
          ) : !judgeFiles?.length ? (
            <div className="flex flex-col items-center py-8 text-muted-foreground">
              <Scale className="h-10 w-10 opacity-20 mb-3" />
              <p className="text-sm">No judge results yet</p>
              <p className="text-xs mt-1">Run LLM Judge from the Results page to get started</p>
            </div>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {judgeFiles.map((f: JudgeSummary) => (
                <button
                  key={f.filename}
                  onClick={() => setSelectedFile(f.filename)}
                  className={`flex w-full items-center justify-between rounded px-3 py-2 text-xs transition-colors ${
                    selectedFile === f.filename
                      ? "bg-primary/10 text-primary border border-primary/20"
                      : "hover:bg-accent border border-transparent"
                  }`}
                >
                  <div className="flex flex-col items-start gap-0.5 min-w-0">
                    <span className="max-w-75 truncate font-medium">{f.judge_model}</span>
                    <span className="text-muted-foreground">
                      {f.total_judged} judged | {f.source_results.length} source file{f.source_results.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex gap-1.5">
                      <span className="text-red-500">{f.true_incorrect}</span>
                      <span className="text-amber-500">{f.false_negative}</span>
                      <span className="text-blue-500">{f.parser_failure}</span>
                    </div>
                    <span className="text-muted-foreground/60 text-[10px]">
                      {f.created?.slice(4, 10)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Loading state */}
      {resultLoading && (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-12">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-muted-foreground">Loading judge results...</span>
          </CardContent>
        </Card>
      )}

      {/* Summary dashboard */}
      {judgeResult && !resultLoading && (
        <>
          <SummaryCards result={judgeResult} />

          <div className="grid gap-4 sm:grid-cols-[1fr_280px]">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Verdict Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <VerdictBar result={judgeResult} />
              </CardContent>
            </Card>
            <ParserIssuesCard issues={judgeResult.summary.parser_issues} />
          </div>

          {/* Judgments table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Individual Judgments</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={columns}
                data={filteredJudgments}
                searchKey="test_id"
                searchPlaceholder="Search by test ID..."
                toolbar={toolbar}
                persistKey="judge-table"
                getRowId={(row) => row.rowId}
                rowExpansion={{
                  expandedRowIds: visibleExpandedRows,
                  onToggleRow: toggleExpandedRow,
                  renderContent: (row) => <JudgmentDetailContent judgment={row.original} />,
                }}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
