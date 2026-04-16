import { useMemo, useState } from "react"
import { AlertTriangle, Copy, Download, FileBarChart, Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useImprovementReport } from "@/hooks/use-review"
import { languageLabel } from "@/components/language-filter-chip"
import type {
  AnnotatorNote,
  AxisBucket,
  DataQuality,
  ExpectedDistractorPair,
  ImprovementReport,
  LabelTaxonomyRow,
  LongTailGroup,
  ModelAnswerBucket,
  ParserSpanAlignment,
  PrefixAnchor,
  RegexCaptureSample,
  RegexTestResult,
  SpanExample,
  SpanGroup,
  SpanRegexCandidate,
  StrategyBucket,
  StructuralRatios,
} from "@/types"

/** Narrow helper — v2 spans are objects, v1 spans are plain strings. */
function isSpanExampleObject(s: SpanExample | string): s is SpanExample {
  return typeof s === "object" && s !== null && "text" in s
}
function isRegexCandidateObject(r: SpanRegexCandidate | string): r is SpanRegexCandidate {
  return typeof r === "object" && r !== null && "pattern" in r
}
function fmtPct(value: number | undefined): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—"
  return `${(value * 100).toFixed(1)}%`
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  fileIds: string[]
}

export function ImprovementReportDialog({ open, onOpenChange, fileIds }: Props) {
  const query = useImprovementReport(fileIds, open)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-fit max-w-[min(95vw,1200px)] sm:max-w-[min(95vw,1200px)]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileBarChart className="h-4 w-4" />
            Improvement report
          </DialogTitle>
          <DialogDescription>
            Aggregated from annotations across {fileIds.length} result file{fileIds.length === 1 ? "" : "s"}.
          </DialogDescription>
        </DialogHeader>

        {query.isLoading && (
          <div className="flex min-h-50 items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Building report…
          </div>
        )}
        {query.isError && (
          <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-600">
            Failed to build report. {query.error instanceof Error ? query.error.message : ""}
          </div>
        )}
        {query.data && <ReportBody report={query.data} />}
      </DialogContent>
    </Dialog>
  )
}

function ReportBody({ report }: { report: ImprovementReport }) {
  const jsonText = useMemo(() => JSON.stringify(report, null, 2), [report])

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(jsonText)
      toast.success("Report JSON copied")
    } catch (err) {
      toast.error(`Copy failed: ${err instanceof Error ? err.message : "unknown"}`)
    }
  }

  const downloadAll = () => {
    const blob = new Blob([jsonText], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "gol-improvement-report.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      {report.data_quality && report.data_quality.warnings.length > 0 && (
        <DataQualityBanner dq={report.data_quality} />
      )}
      <Tabs defaultValue="summary">
        <TabsList className="flex-nowrap overflow-x-auto justify-start">
          <TabsTrigger value="summary" className="whitespace-nowrap shrink-0">Summary</TabsTrigger>
          <TabsTrigger value="spans" className="whitespace-nowrap shrink-0">
            Spans ({report.span_groups.length}
            {report.long_tail_groups && report.long_tail_groups.length > 0 ? ` + ${report.long_tail_groups.length}` : ""})
          </TabsTrigger>
          {report.strategy_breakdown && (
            <TabsTrigger value="strategy" className="whitespace-nowrap shrink-0">
              Strategy ({Object.keys(report.strategy_breakdown).length})
            </TabsTrigger>
          )}
          <TabsTrigger value="languages" className="whitespace-nowrap shrink-0">Languages</TabsTrigger>
          {report.answer_when_missed && (
            <TabsTrigger value="misses" className="whitespace-nowrap shrink-0">Misses</TabsTrigger>
          )}
          <TabsTrigger value="answers" className="whitespace-nowrap shrink-0">
            Answers ({Object.keys(report.model_answer_distribution ?? {}).length})
          </TabsTrigger>
          {report.ordering_hints && report.ordering_hints.length > 0 && (
            <TabsTrigger value="ordering" className="whitespace-nowrap shrink-0">
              Ordering ({report.ordering_hints.length})
            </TabsTrigger>
          )}
          {report.summary.response_class_counts &&
            Object.keys(report.summary.response_class_counts).length > 0 && (
            <TabsTrigger value="classes" className="whitespace-nowrap shrink-0">Classes</TabsTrigger>
          )}
          {report.annotator_notes && report.annotator_notes.length > 0 && (
            <TabsTrigger value="notes" className="whitespace-nowrap shrink-0">
              Notes ({report.annotator_notes.length})
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="summary" className="mt-3">
          <SummaryTab report={report} />
        </TabsContent>
        <TabsContent value="spans" className="mt-3">
          <SpansTab
            groups={report.span_groups}
            longTail={report.long_tail_groups ?? []}
          />
        </TabsContent>
        {report.strategy_breakdown && (
          <TabsContent value="strategy" className="mt-3">
            <StrategyTab strategies={report.strategy_breakdown} />
          </TabsContent>
        )}
        <TabsContent value="languages" className="mt-3">
          <BreakdownTab
            label="Language"
            buckets={report.language_breakdown ?? {}}
            keyFormatter={(k) => languageLabel(k)}
          />
          <div className="mt-4 space-y-3">
            <BreakdownTab
              label="System style"
              buckets={report.config_breakdown ?? {}}
              keyFormatter={(k) => k}
            />
            <BreakdownTab
              label="User style"
              buckets={report.user_style_breakdown ?? {}}
              keyFormatter={(k) => k}
            />
          </div>
        </TabsContent>
        {report.answer_when_missed && (
          <TabsContent value="misses" className="mt-3">
            <MissesTab data={report.answer_when_missed} />
          </TabsContent>
        )}
        <TabsContent value="answers" className="mt-3">
          <ModelAnswersTab
            distribution={report.model_answer_distribution ?? {}}
            variants={report.model_answer_variants}
          />
        </TabsContent>
        {report.ordering_hints && report.ordering_hints.length > 0 && (
          <TabsContent value="ordering" className="mt-3">
            <OrderingTab hints={report.ordering_hints} />
          </TabsContent>
        )}
        {report.summary.response_class_counts &&
          Object.keys(report.summary.response_class_counts).length > 0 && (
          <TabsContent value="classes" className="mt-3">
            <ClassesTab classes={report.summary.response_class_counts} />
          </TabsContent>
        )}
        {report.annotator_notes && report.annotator_notes.length > 0 && (
          <TabsContent value="notes" className="mt-3">
            <NotesTab notes={report.annotator_notes} />
          </TabsContent>
        )}
      </Tabs>

      <div className="flex justify-end gap-2 border-t pt-3">
        <Button variant="outline" size="sm" onClick={copyAll}>
          <Copy className="mr-1.5 h-3.5 w-3.5" />
          Copy JSON
        </Button>
        <Button variant="outline" size="sm" onClick={downloadAll}>
          <Download className="mr-1.5 h-3.5 w-3.5" />
          Download JSON
        </Button>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-md border border-border/70 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${tone ?? ""}`}>{value}</div>
    </div>
  )
}

/**
 * Parser-missed stat card with the v2.3 aligned/misaligned/no-output split
 * rendered as a compact sub-line under the headline number.
 */
function ParserMissedStat({
  total,
  aligned,
  misaligned,
  noOutput,
}: {
  total: number
  aligned?: number
  misaligned?: number
  noOutput?: number
}) {
  const hasSplit =
    aligned !== undefined || misaligned !== undefined || noOutput !== undefined
  return (
    <div className="rounded-md border border-border/70 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Parser missed
      </div>
      <div className="mt-1 text-2xl font-bold tabular-nums text-amber-600">{total}</div>
      {hasSplit && (
        <div className="mt-0.5 flex flex-wrap gap-x-2 gap-y-0 text-[10px] text-muted-foreground">
          {aligned !== undefined && aligned > 0 && (
            <span title="parser extracted correctly, annotator just used spans-only workflow">
              <span className="text-emerald-600">aligned</span> {aligned}
            </span>
          )}
          {misaligned !== undefined && misaligned > 0 && (
            <span title="true parser failure — extracted wrong token">
              <span className="text-rose-600">wrong</span> {misaligned}
            </span>
          )}
          {noOutput !== undefined && noOutput > 0 && (
            <span title="parser returned nothing; span has no competing extraction">
              <span className="text-muted-foreground/80">no-out</span> {noOutput}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/** Like Stat, but renders a percentage and auto-tones based on the value. */
function AccuracyStat({ label, value }: { label: string; value: number | undefined }) {
  const tone =
    value === undefined
      ? "text-muted-foreground"
      : value >= 0.9
        ? "text-emerald-600"
        : value >= 0.7
          ? "text-amber-600"
          : "text-rose-600"
  return (
    <div className="rounded-md border border-border/70 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${tone}`}>{fmtPct(value)}</div>
    </div>
  )
}

function SummaryTab({ report }: { report: ImprovementReport }) {
  const s = report.summary
  const fpr = report.false_positive_rate ?? s.false_positive_rate
  const fp = s.parser_false_positive ?? 0
  const parserClaimedCorrect = s.parser_was_correct + fp
  const parserAccuracy =
    parserClaimedCorrect > 0 ? s.parser_was_correct / parserClaimedCorrect : undefined
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Total cases" value={s.total_cases} />
        <Stat label="Annotated" value={s.annotated} />
        <Stat label="Skipped" value={s.skipped} />
        <AccuracyStat label="Parser accuracy" value={parserAccuracy} />
        <Stat label="Parser correct" value={s.parser_was_correct} tone="text-emerald-600" />
        <Stat
          label="Parser false-positive"
          value={fp}
          tone="text-fuchsia-600"
        />
        <ParserMissedStat
          total={s.parser_missed_extractable}
          aligned={s.parser_missed_aligned}
          misaligned={s.parser_missed_misaligned}
          noOutput={s.parser_missed_no_output}
        />
        <Stat label="True unparseable" value={s.true_unparseable} tone="text-rose-600" />
      </div>
      {report.parser_span_alignment && report.parser_span_alignment.total_comparable > 0 && (
        <ParserSpanAlignmentCallout alignment={report.parser_span_alignment} />
      )}
      {fpr !== undefined && fpr > 0 && (
        <div className="rounded-md border border-fuchsia-500/30 bg-fuchsia-500/5 p-3 text-sm">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Accuracy inflation estimate (false-positive rate)
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-bold tabular-nums text-fuchsia-700 dark:text-fuchsia-400">
              {fmtPct(fpr)}
            </span>
            <span className="text-[11px] text-muted-foreground">
              of cases the parser called correct were actually wrong
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function DataQualityBanner({ dq }: { dq: DataQuality }) {
  const [expanded, setExpanded] = useState(false)
  const headline =
    dq.warnings.length === 1
      ? dq.warnings[0].detail
      : `${dq.warnings.length} data-quality warnings — click to expand`
  return (
    <div className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 text-left"
      >
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
        <span className="flex-1 text-amber-900 dark:text-amber-200">{headline}</span>
        {dq.warnings.length > 1 && (
          <span className="text-[10px] text-muted-foreground">{expanded ? "hide" : "show"}</span>
        )}
      </button>
      {expanded && dq.warnings.length > 1 && (
        <ul className="mt-2 space-y-1 border-t border-amber-500/30 pt-2">
          {dq.warnings.map((w, i) => (
            <li key={i} className="flex gap-2">
              <code className="rounded bg-amber-500/10 px-1 py-0.5 font-mono text-[10px] text-amber-700 dark:text-amber-300">
                {w.code}
              </code>
              <span className="flex-1 text-amber-900 dark:text-amber-200/90">{w.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function ParserSpanAlignmentCallout({ alignment }: { alignment: ParserSpanAlignment }) {
  const { aligned_with_parser, misaligned_with_parser, no_parser_output, total_comparable, alignment_ratio } = alignment
  const ratioTone =
    alignment_ratio >= 0.8
      ? "text-emerald-700 dark:text-emerald-400"
      : alignment_ratio >= 0.5
        ? "text-amber-700 dark:text-amber-400"
        : "text-rose-700 dark:text-rose-400"
  return (
    <div className="rounded-md border border-sky-500/30 bg-sky-500/5 p-3 text-sm">
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Parser ↔ annotator alignment
        </div>
        <div className={`text-xs font-mono tabular-nums ${ratioTone}`}>
          {fmtPct(alignment_ratio)} aligned
        </div>
      </div>
      <div className="mt-2 flex h-4 w-full overflow-hidden rounded-full border border-border/60">
        {aligned_with_parser > 0 && (
          <div
            className="bg-emerald-500"
            style={{ width: `${(aligned_with_parser / total_comparable) * 100}%` }}
            title={`aligned: ${aligned_with_parser}`}
          />
        )}
        {misaligned_with_parser > 0 && (
          <div
            className="bg-rose-500"
            style={{ width: `${(misaligned_with_parser / total_comparable) * 100}%` }}
            title={`misaligned: ${misaligned_with_parser}`}
          />
        )}
        {no_parser_output > 0 && (
          <div
            className="bg-muted"
            style={{ width: `${(no_parser_output / total_comparable) * 100}%` }}
            title={`no parser output: ${no_parser_output}`}
          />
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          aligned <span className="font-mono text-foreground">{aligned_with_parser}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-rose-500" />
          misaligned <span className="font-mono text-foreground">{misaligned_with_parser}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-muted" />
          no output <span className="font-mono text-foreground">{no_parser_output}</span>
        </span>
      </div>
      {alignment.sample_misaligned.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Sample misaligned cases ({alignment.sample_misaligned.length})
          </summary>
          <ul className="mt-1 space-y-1 font-mono text-[11px]">
            {alignment.sample_misaligned.map((s, i) => (
              <li key={i} className="rounded bg-muted/40 px-2 py-1">
                <span className="text-muted-foreground">{s.case_id}</span>
                <span className="mx-2 text-rose-500">{String(s.parser_extracted ?? "—")}</span>
                <span className="text-muted-foreground/60">vs</span>
                <span className="ml-2 text-emerald-600 dark:text-emerald-400">
                  {s.annotated_spans.join(" | ")}
                </span>
                {s.parser_match_type && (
                  <span className="ml-2 text-[10px] text-muted-foreground/60">[{s.parser_match_type}]</span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

function SpansTab({
  groups,
  longTail,
}: {
  groups: SpanGroup[]
  longTail: LongTailGroup[]
}) {
  if (groups.length === 0 && longTail.length === 0) {
    return <div className="py-8 text-center text-sm text-muted-foreground">No annotated spans yet.</div>
  }
  return (
    <div className="max-h-[50vh] space-y-3 overflow-y-auto pr-1">
      {groups.map((g, i) => (
        <SpanGroupCard key={i} group={g} />
      ))}
      {longTail.length > 0 && <LongTailGroupsBlock groups={longTail} />}
    </div>
  )
}

// v2.5 — compact rendering of statistically-useless groups (count < 4). One
// row each, expandable to the single retained example span. Kept visually
// distinct (dimmed header + smaller typography) so the agent reads full
// groups first.
function LongTailGroupsBlock({ groups }: { groups: LongTailGroup[] }) {
  return (
    <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-2.5">
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Long-tail groups ({groups.length}) — count &lt; 4, low signal
      </div>
      <div className="space-y-1">
        {groups.map((g, i) => (
          <LongTailRow key={i} group={g} />
        ))}
      </div>
    </div>
  )
}

function LongTailRow({ group }: { group: LongTailGroup }) {
  const [open, setOpen] = useState(false)
  const hasExample = group.example !== null
  return (
    <div className="rounded border border-border/40 bg-background/50">
      <button
        type="button"
        onClick={() => hasExample && setOpen((v) => !v)}
        disabled={!hasExample}
        className="flex w-full items-center gap-2 px-2 py-1 text-left text-[11px] disabled:cursor-default"
      >
        {hasExample ? (
          <span className="w-3 text-muted-foreground">{open ? "▾" : "▸"}</span>
        ) : (
          <span className="w-3" />
        )}
        <Badge variant="outline" className="text-[10px] uppercase">
          {group.position} / {group.format}
        </Badge>
        <span className="font-mono tabular-nums text-muted-foreground">
          ×{group.count}
        </span>
      </button>
      {open && group.example && (
        <div className="border-t border-border/40 px-2 pb-1.5 pt-1 text-[11px]">
          <div className="font-mono text-foreground">
            "{group.example.text}"
          </div>
          <div className="mt-0.5 text-muted-foreground">
            <span className="opacity-60">{group.example.case_id}</span>
            {group.example.language && (
              <span className="ml-2 opacity-60">· {group.example.language}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const CONFIDENCE_TONE: Record<string, string> = {
  high: "bg-emerald-500/10 text-emerald-600 border-emerald-500/40",
  medium: "bg-amber-500/10 text-amber-600 border-amber-500/40",
  low: "bg-rose-500/10 text-rose-600 border-rose-500/40",
}

function SpanGroupCard({ group }: { group: SpanGroup }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-md border border-border/70">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 p-3 text-left"
      >
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="outline" className="text-[10px] uppercase">
            {group.position} / {group.format}
          </Badge>
          <span className="font-mono tabular-nums">{group.count}</span>
          <span className="text-muted-foreground">→ {group.suggested_strategy}</span>
          {group.confidence && (
            <Badge className={`text-[10px] ${CONFIDENCE_TONE[group.confidence] ?? ""}`}>
              {group.confidence} confidence
            </Badge>
          )}
          {group.missed_by_existing && (
            <Badge className="bg-amber-500/10 text-[10px] text-amber-600 border-amber-500/40">
              missed by parser
            </Badge>
          )}
          {group.languages && group.languages.length > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {group.languages.join(", ").toUpperCase()}
            </span>
          )}
        </div>
        <span className="text-[11px] text-muted-foreground">{open ? "Hide" : "Details"}</span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-border/60 p-3 text-xs">
          <div>
            <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Example spans (with surrounding context)
            </div>
            <ul className="space-y-1 font-mono">
              {group.example_spans.map((s, i) => (
                isSpanExampleObject(s) ? (
                  <li key={i} className="rounded bg-muted/50 px-2 py-1">
                    <div>
                      <span className="text-muted-foreground">{s.before}</span>
                      <span className="font-bold text-primary">{s.text}</span>
                      <span className="text-muted-foreground">{s.after}</span>
                      <span className="ml-2 text-[9px] text-muted-foreground/70">[{s.case_id}]</span>
                    </div>
                    {s.sentence && s.sentence !== `${s.before}${s.text}${s.after}`.trim() && (
                      <div className="mt-0.5 text-[10px] italic text-muted-foreground/80">
                        sentence: {s.sentence}
                      </div>
                    )}
                    {s.parser_extracted !== undefined && s.parser_extracted !== null && (
                      <div className="mt-0.5 flex items-center gap-2 text-[10px] text-muted-foreground/80">
                        <Badge variant="outline" className="text-[9px] uppercase">
                          parser
                        </Badge>
                        <span className="font-mono text-rose-500 dark:text-rose-400">
                          {String(s.parser_extracted)}
                        </span>
                        <span className="text-muted-foreground/60">→ annotator:</span>
                        <span className="font-mono text-emerald-600 dark:text-emerald-400">
                          {s.text}
                        </span>
                        {s.parser_match_type && (
                          <span className="ml-1 font-mono text-muted-foreground/60">
                            [{s.parser_match_type}]
                          </span>
                        )}
                      </div>
                    )}
                  </li>
                ) : (
                  <li key={i} className="rounded bg-muted/50 px-2 py-1">{s}</li>
                )
              ))}
            </ul>
          </div>
          {group.structural_ratios && (
            <StructuralSignalsRow ratios={group.structural_ratios} />
          )}
          {group.label_taxonomy && group.label_taxonomy.length > 0 && (
            <LabelTaxonomyBlock rows={group.label_taxonomy} />
          )}
          {group.prefix_anchors && group.prefix_anchors.length > 0 && (
            <PrefixAnchorsTable anchors={group.prefix_anchors} />
          )}
          {group.regex_test && group.regex_test.length > 0 ? (
            <div>
              <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Regex test results (run against every example)
              </div>
              <div className="space-y-1">
                {group.regex_test.map((r, i) => (
                  <RegexTestRow key={i} result={r} />
                ))}
              </div>
            </div>
          ) : (
            group.suggested_regex.length > 0 && (
              <div>
                <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Regex candidates (sorted by support)
                </div>
                {group.suggested_regex.map((r, i) => (
                  <RegexRow key={i} candidate={r} />
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}

function RegexRow({ candidate }: { candidate: SpanRegexCandidate | string }) {
  const pattern = isRegexCandidateObject(candidate) ? candidate.pattern : candidate
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(pattern)
      toast.success("Regex copied")
    } catch (err) {
      toast.error(`Copy failed: ${err instanceof Error ? err.message : "unknown"}`)
    }
  }
  return (
    <div className="flex items-center gap-2">
      {isRegexCandidateObject(candidate) && (
        <Badge variant="outline" className="text-[9px] uppercase">
          {candidate.kind}
          <span className="ml-1 text-muted-foreground">×{candidate.support}</span>
        </Badge>
      )}
      <pre className="flex-1 overflow-x-auto rounded bg-muted/50 px-2 py-1 font-mono text-[11px]">
        {pattern}
      </pre>
      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
        <Copy className="h-3 w-3" />
      </Button>
    </div>
  )
}

// Pretty label mapping for the seven structural signals.
const STRUCT_LABEL: Record<keyof StructuralRatios, string> = {
  line_start: "line-start",
  paragraph_start: "paragraph-start",
  list_marker: "list marker",
  label_colon: "`label:`",
  bold_wrap: "**bold-wrapped**",
  quote_wrap: "quote-wrapped",
  answer_label_match: "answer-label",
}

function StructuralSignalsRow({ ratios }: { ratios: StructuralRatios }) {
  const visible = (Object.keys(ratios) as Array<keyof StructuralRatios>)
    .filter((k) => ratios[k] > 0)
    .sort((a, b) => ratios[b] - ratios[a])
  if (visible.length === 0) return null
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Structural signals
      </div>
      <div className="flex flex-wrap gap-1.5">
        {visible.map((k) => {
          const v = ratios[k]
          const tone =
            v >= 0.8
              ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/40"
              : v >= 0.4
                ? "bg-amber-500/10 text-amber-600 border-amber-500/40"
                : "bg-muted text-muted-foreground border-border/60"
          return (
            <Badge key={k} variant="outline" className={`text-[10px] ${tone}`}>
              <span className="mr-1">{STRUCT_LABEL[k]}</span>
              <span className="font-mono tabular-nums">{fmtPct(v)}</span>
            </Badge>
          )
        })}
      </div>
    </div>
  )
}

const ANCHOR_TYPE_TONE: Record<string, string> = {
  label: "bg-emerald-500/10 text-emerald-600 border-emerald-500/40",
  format: "bg-amber-500/10 text-amber-600 border-amber-500/40",
  phrase: "bg-muted text-muted-foreground border-border/60",
}

function PrefixAnchorsTable({ anchors }: { anchors: PrefixAnchor[] }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Prefix anchors (trailing words of `before`)
      </div>
      <table className="w-full border-separate border-spacing-y-0.5">
        <tbody>
          {anchors.map((a, i) => (
            <tr key={i}>
              <td className="rounded-l bg-muted/40 px-2 py-1">
                {a.type && (
                  <Badge
                    variant="outline"
                    className={`mr-1.5 text-[9px] uppercase ${ANCHOR_TYPE_TONE[a.type] ?? ""}`}
                  >
                    {a.type}
                  </Badge>
                )}
                <span className="font-mono text-[11px]">{a.phrase}</span>
              </td>
              <td className="bg-muted/40 px-2 py-1 text-right font-mono tabular-nums text-[10px] text-muted-foreground">
                ×{a.count}
              </td>
              <td className="rounded-r bg-muted/40 px-2 py-1 text-right font-mono tabular-nums text-[10px] text-muted-foreground">
                {fmtPct(a.ratio)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MatchRatePill({ rate, matched, total }: { rate: number; matched: number; total: number }) {
  if (rate < 0) {
    return (
      <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-[9px]">
        compile error
      </Badge>
    )
  }
  const tone =
    rate >= 0.8
      ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/40"
      : rate >= 0.3
        ? "bg-amber-500/10 text-amber-600 border-amber-500/40"
        : "bg-rose-500/10 text-rose-600 border-rose-500/40"
  return (
    <Badge variant="outline" className={`text-[9px] ${tone}`}>
      <span className="font-mono tabular-nums">{fmtPct(rate)}</span>
      <span className="ml-1 text-muted-foreground">
        {matched}/{total}
      </span>
    </Badge>
  )
}

function RegexTestRow({ result }: { result: RegexTestResult }) {
  const [open, setOpen] = useState(false)
  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(result.pattern)
      toast.success("Regex copied")
    } catch (err) {
      toast.error(`Copy failed: ${err instanceof Error ? err.message : "unknown"}`)
    }
  }
  const kindLabel = result.kind.replace(/_/g, " ")
  // v2.4 — the merged disjunction is the highest-leverage candidate; tone it
  // distinctly so the agent notices it at a glance.
  const kindTone =
    result.kind === "merged_label_disjunction"
      ? "bg-sky-500/10 text-sky-600 border-sky-500/40"
      : ""
  const hasCaptureMetrics =
    result.capture_exact_rate !== undefined || result.capture_contains_rate !== undefined
  const samples = result.sample_captures ?? []
  const expandable = hasCaptureMetrics && (samples.length > 0 || result.match_rate > 0)
  return (
    <div className="rounded bg-muted/30">
      <div className="flex items-center gap-2 px-1 py-0.5">
        <Badge variant="outline" className={`text-[9px] uppercase whitespace-nowrap ${kindTone}`}>
          {kindLabel}
          <span className="ml-1 text-muted-foreground">×{result.support}</span>
        </Badge>
        <MatchRatePill rate={result.match_rate} matched={result.matched_count} total={result.total} />
        {hasCaptureMetrics && result.match_rate > 0 && (
          <CaptureQualityPill
            exactRate={result.capture_exact_rate ?? 0}
            containsRate={result.capture_contains_rate ?? 0}
          />
        )}
        <pre
          className="flex-1 cursor-pointer overflow-x-auto rounded bg-muted/50 px-2 py-1 font-mono text-[11px]"
          onClick={() => expandable && setOpen((v) => !v)}
          title={expandable ? "Click to see sample captures" : undefined}
        >
          {result.pattern}
        </pre>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
          <Copy className="h-3 w-3" />
        </Button>
      </div>
      {open && samples.length > 0 && (
        <div className="border-t border-border/40 px-3 pb-2 pt-1">
          <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
            Sample captures ({samples.length} shown)
          </div>
          <ul className="space-y-0.5 font-mono text-[10px]">
            {samples.map((s, i) => (
              <CaptureSampleRow key={i} sample={s} />
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function CaptureQualityPill({ exactRate, containsRate }: { exactRate: number; containsRate: number }) {
  // The more meaningful number is `capture_contains_rate` — "does the regex
  // produce an output that lines up with the annotated answer?" Tone the
  // badge on that, surface exact as a secondary number.
  const tone =
    containsRate >= 0.8
      ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/40"
      : containsRate >= 0.5
        ? "bg-amber-500/10 text-amber-600 border-amber-500/40"
        : "bg-rose-500/10 text-rose-600 border-rose-500/40"
  return (
    <Badge
      variant="outline"
      className={`text-[9px] uppercase whitespace-nowrap ${tone}`}
      title={`capture_contains_rate ${fmtPct(containsRate)} · capture_exact_rate ${fmtPct(exactRate)}`}
    >
      capture
      <span className="ml-1 font-mono tabular-nums">
        {fmtPct(containsRate)}
      </span>
      {exactRate !== containsRate && (
        <span className="ml-1 text-muted-foreground">(exact {fmtPct(exactRate)})</span>
      )}
    </Badge>
  )
}

function CaptureSampleRow({ sample }: { sample: RegexCaptureSample }) {
  const tone = sample.exact_match
    ? "text-emerald-600 dark:text-emerald-400"
    : sample.aligned
      ? "text-amber-600 dark:text-amber-400"
      : "text-rose-600 dark:text-rose-400"
  const icon = sample.exact_match ? "✓" : sample.aligned ? "~" : "✗"
  return (
    <li className="flex items-baseline gap-2">
      <span className={`font-mono ${tone}`} title={
        sample.exact_match
          ? "exact match"
          : sample.aligned
            ? "aligned (superset/subset of annotated)"
            : "misaligned"
      }>{icon}</span>
      <span className="text-muted-foreground/80">{sample.case_id}</span>
      <span className="max-w-[50%] truncate">
        captured: <span className={tone}>{sample.captured || "—"}</span>
      </span>
      <span className="text-muted-foreground/60">→</span>
      <span className="max-w-[30%] truncate text-muted-foreground">
        annotated: <span className="text-foreground">{sample.annotated || "—"}</span>
      </span>
    </li>
  )
}

function OrderingTab({ hints }: { hints: ImprovementReport["ordering_hints"] }) {
  const rows = hints ?? []
  if (rows.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No ordering hints — your parser seems to be scanning in the right direction.
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {rows.map((h, i) => (
        <div
          key={i}
          className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-sm"
        >
          <div className="text-amber-700 dark:text-amber-300">{h.observation}</div>
          <div className="mt-1 text-xs font-medium">→ {h.recommendation}</div>
        </div>
      ))}
    </div>
  )
}

const CLASS_TONE: Record<string, string> = {
  hedge: "bg-amber-500",
  gibberish: "bg-rose-500",
  refusal: "bg-red-500",
  language_error: "bg-orange-500",
  verbose_correct: "bg-sky-500",
  parser_ok: "bg-emerald-500",
  parser_false_positive: "bg-fuchsia-500",
  parser_missed: "bg-violet-500",
}

function ClassesTab({ classes }: { classes: Record<string, number> }) {
  const entries = Object.entries(classes).filter(([, v]) => v > 0)
  const total = entries.reduce((acc, [, v]) => acc + v, 0)
  if (total === 0) {
    return <div className="py-8 text-center text-sm text-muted-foreground">No response classes recorded.</div>
  }
  return (
    <div className="space-y-4">
      <div className="flex h-5 w-full overflow-hidden rounded-full border border-border/60">
        {entries.map(([k, v]) => (
          <div
            key={k}
            className={CLASS_TONE[k] || "bg-muted"}
            style={{ width: `${(v / total) * 100}%` }}
            title={`${k}: ${v}`}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 rounded border border-border/60 px-2 py-1.5 text-xs">
            <span className={`h-2 w-2 rounded-full ${CLASS_TONE[k] || "bg-muted"}`} />
            <span className="flex-1 capitalize">{k.replace(/_/g, " ")}</span>
            <span className="font-mono tabular-nums">{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── v2 tabs ────────────────────────────────────────────────────────────

function StrategyTab({ strategies }: { strategies: Record<string, StrategyBucket> }) {
  const rows = Object.entries(strategies).sort(
    (a, b) => (b[1].parser_false_positive ?? 0) - (a[1].parser_false_positive ?? 0),
  )
  if (rows.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No per-strategy data — re-run the testset so `parse_strategy` is captured per case.
      </div>
    )
  }
  return (
    <div className="max-h-[50vh] space-y-2 overflow-y-auto pr-1">
      {rows.map(([strategy, b]) => {
        const fpr = b.false_positive_rate
        const tone = fpr > 0.3 ? "text-rose-600" : fpr > 0.1 ? "text-amber-600" : "text-emerald-600"
        return (
          <div key={strategy} className="rounded-md border border-border/70 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-[10px]">{strategy}</Badge>
                <span className="text-[11px] text-muted-foreground">
                  fired ×{b.total_fired}
                </span>
              </div>
              <div className="text-xs">
                <span className={`font-mono tabular-nums ${tone}`}>{fmtPct(fpr)}</span>{" "}
                <span className="text-muted-foreground">false-positive rate</span>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
              <span>parser_ok: <span className="font-mono">{b.parser_ok}</span></span>
              <span className="text-fuchsia-600">false-positive: <span className="font-mono">{b.parser_false_positive}</span></span>
              <span>recoverable miss: <span className="font-mono">{b.recoverable_miss}</span></span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function BreakdownTab({
  label,
  buckets,
  keyFormatter,
}: {
  label: string
  buckets: Record<string, AxisBucket>
  keyFormatter: (k: string) => string
}) {
  const rows = Object.entries(buckets).sort((a, b) => b[1].miss_rate - a[1].miss_rate)
  if (rows.length === 0) {
    return (
      <div className="py-3 text-sm text-muted-foreground">{label}: no data.</div>
    )
  }
  return (
    <div>
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="overflow-x-auto rounded-md border border-border/70">
        <table className="w-full text-xs">
          <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-2 py-1.5 text-left">{label}</th>
              <th className="px-2 py-1.5 text-right">total</th>
              <th className="px-2 py-1.5 text-right text-emerald-600">ok</th>
              <th className="px-2 py-1.5 text-right text-fuchsia-600">false-pos</th>
              <th className="px-2 py-1.5 text-right text-amber-600">missed</th>
              <th className="px-2 py-1.5 text-right text-rose-600">unparseable</th>
              <th className="px-2 py-1.5 text-right">miss rate</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, b]) => (
              <tr key={k} className="border-t border-border/40 font-mono">
                <td className="px-2 py-1.5">{keyFormatter(k)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{b.total}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{b.parser_was_correct}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{b.parser_false_positive}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{b.parser_missed_extractable}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{b.true_unparseable}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{fmtPct(b.miss_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MissesTab({ data }: { data: ImprovementReport["answer_when_missed"] }) {
  if (!data) {
    return <div className="py-8 text-center text-sm text-muted-foreground">No miss data.</div>
  }
  const pairs = data.expected_distractor_pairs ?? []
  const expected = Object.entries(data.by_expected ?? {})
  const distractors = Object.entries(data.by_extracted_distractor ?? {})
  if (pairs.length === 0 && expected.length === 0 && distractors.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No annotated misses yet.
      </div>
    )
  }
  return (
    <div className="space-y-4">
      {pairs.length > 0 && (
        <div>
          <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Expected → parser-extracted distractor pairs
          </div>
          <div className="space-y-1">
            {pairs.map((p: ExpectedDistractorPair, i) => (
              <div key={i} className="flex items-center gap-2 rounded border border-border/60 px-2 py-1.5 text-xs">
                <span className="font-mono text-emerald-600">{p.expected}</span>
                <span className="text-muted-foreground">→</span>
                <span className="font-mono text-rose-600">{p.parser_extracted}</span>
                <span className="ml-auto font-mono tabular-nums text-muted-foreground">×{p.count}</span>
                <span className="text-[10px] text-muted-foreground/70">
                  {p.example_case_ids.slice(0, 2).join(", ")}
                  {p.example_case_ids.length > 2 ? "…" : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <FreqTable label="Correct answers the parser missed" entries={expected} tone="text-emerald-600" />
        <FreqTable label="Distractor tokens the parser grabbed" entries={distractors} tone="text-rose-600" />
      </div>
    </div>
  )
}

function FreqTable({ label, entries, tone }: { label: string; entries: [string, number][]; tone: string }) {
  if (entries.length === 0) {
    return (
      <div>
        <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="text-[11px] text-muted-foreground">none</div>
      </div>
    )
  }
  return (
    <div>
      <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="space-y-0.5">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between gap-2 rounded px-2 py-1 text-xs hover:bg-muted/40">
            <span className={`font-mono ${tone}`}>{k}</span>
            <span className="font-mono tabular-nums text-muted-foreground">×{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function NotesTab({ notes }: { notes: AnnotatorNote[] }) {
  if (notes.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No annotator notes — add notes during review to surface meta-pattern observations here.
      </div>
    )
  }
  return (
    <div className="max-h-[50vh] space-y-2 overflow-y-auto pr-1">
      {notes.map((n, i) => (
        <div key={i} className="rounded-md border border-border/70 p-3">
          <div className="mb-1 flex items-center gap-2 text-[11px]">
            <span className="font-mono text-muted-foreground">{n.case_id}</span>
            <Badge variant="outline" className="text-[10px]">
              {languageLabel(n.language)}
            </Badge>
            {n.verdict && (
              <Badge variant="outline" className="text-[10px]">
                {n.verdict.replace(/_/g, " ")}
              </Badge>
            )}
          </div>
          <p className="whitespace-pre-wrap text-sm">{n.note}</p>
        </div>
      ))}
    </div>
  )
}

// ── v2.2 tabs ──────────────────────────────────────────────────────────

function ModelAnswersTab({
  distribution,
  variants,
}: {
  distribution: Record<string, number>
  variants?: Record<string, ModelAnswerBucket>
}) {
  const entries = Object.entries(distribution).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        No model answers captured — spans aren't populated yet.
      </div>
    )
  }
  const total = entries.reduce((acc, [, v]) => acc + v, 0)
  return (
    <div className="max-h-[50vh] space-y-1 overflow-y-auto pr-1">
      <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
        What the model actually answered ({total} spans, normalized across markdown)
      </div>
      <div className="space-y-0.5">
        {entries.map(([answer, count]) => (
          <ModelAnswerRow
            key={answer}
            answer={answer}
            count={count}
            total={total}
            bucket={variants?.[answer]}
          />
        ))}
      </div>
    </div>
  )
}

function ModelAnswerRow({
  answer,
  count,
  total,
  bucket,
}: {
  answer: string
  count: number
  total: number
  bucket?: ModelAnswerBucket
}) {
  const [open, setOpen] = useState(false)
  const ratio = count / total
  // Only show the expansion affordance when there's more than one raw variant
  // under this normalized bucket — single-variant buckets gain nothing from
  // expansion and the extra chevron clutters the row.
  const expandable = (bucket?.variants.length ?? 0) > 1
  return (
    <div className="rounded bg-muted/40">
      <button
        type="button"
        disabled={!expandable}
        onClick={() => expandable && setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-2 py-1 text-left disabled:cursor-default"
      >
        {expandable ? (
          <span className="text-[9px] text-muted-foreground w-3">{open ? "▾" : "▸"}</span>
        ) : (
          <span className="w-3" />
        )}
        <span className="flex-1 font-mono text-[11px]">{answer}</span>
        {expandable && (
          <span className="text-[9px] text-muted-foreground/70">
            {bucket?.variants.length} variants
          </span>
        )}
        <span className="text-right font-mono tabular-nums text-[10px] text-muted-foreground w-10">
          ×{count}
        </span>
        <span className="text-right font-mono tabular-nums text-[10px] text-muted-foreground w-12">
          {fmtPct(ratio)}
        </span>
        <span className="w-24">
          <span className="block h-1.5 rounded-full bg-primary/20">
            <span
              className="block h-full rounded-full bg-primary"
              style={{ width: `${Math.max(4, ratio * 100)}%` }}
            />
          </span>
        </span>
      </button>
      {open && bucket && bucket.variants.length > 0 && (
        <div className="border-t border-border/40 px-3 pb-2 pt-1">
          <div className="mb-1 text-[9px] uppercase tracking-wider text-muted-foreground">
            Raw variants
          </div>
          <table className="w-full">
            <tbody>
              {bucket.variants.map((v, i) => (
                <tr key={i}>
                  <td className="py-0.5 font-mono text-[11px]">
                    <span className="rounded bg-background/60 px-1.5 py-0.5 border border-border/40">
                      {v.text}
                    </span>
                  </td>
                  <td className="py-0.5 text-right font-mono tabular-nums text-[10px] text-muted-foreground">
                    ×{v.count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function LabelTaxonomyBlock({ rows }: { rows: LabelTaxonomyRow[] }) {
  if (rows.length === 0) return null
  return (
    <div>
      <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Label taxonomy (answer-label words in `before`)
      </div>
      <div className="flex flex-wrap gap-1.5">
        {rows.map((r) => (
          <Badge key={r.label} variant="outline" className="text-[10px]">
            <span className="mr-1 font-mono">{r.label}:</span>
            <span className="font-mono tabular-nums">×{r.count}</span>
          </Badge>
        ))}
      </div>
    </div>
  )
}
