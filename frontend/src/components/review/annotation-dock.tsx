import { useEffect, useState } from "react"
import { Check, ChevronDown, Plus, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { SpanFormat, SpanPosition } from "@/types"

export interface PendingSpan {
  text: string
  char_start: number
  char_end: number
  position: SpanPosition
  format: SpanFormat
}

interface Props {
  pending: PendingSpan | null
  note: string
  onCommit: () => void
  onDismiss: () => void
  onChangePosition: (position: SpanPosition) => void
  onChangeFormat: (format: SpanFormat) => void
  onChangeNote: (note: string) => void
  /** Register an imperative commit handler for the Space/Enter keyboard shortcut. */
  onRegisterCommit?: (commit: (() => void) | null) => void
}

const POSITIONS: SpanPosition[] = ["start", "middle", "end"]
const FORMATS: SpanFormat[] = [
  "plain",
  "bold",
  "italic",
  "strikethrough",
  "header",
  "boxed",
  "label",
  "other",
]

/**
 * Persistent annotation dock — lives between the response text and the note
 * area. Replaces the v1 floating toolbar, which obscured the text it annotated
 * and dismissed on any misclick.
 *
 * Idle: shows a quiet "select text to annotate" hint.
 * Active: shows the selection preview + Mark button + collapsed metadata.
 */
export function AnnotationDock({
  pending,
  note,
  onCommit,
  onDismiss,
  onChangePosition,
  onChangeFormat,
  onChangeNote,
  onRegisterCommit,
}: Props) {
  const [metaOpen, setMetaOpen] = useState(false)
  const [noteOpen, setNoteOpen] = useState(note.trim().length > 0)

  // Register / un-register the commit handler for keyboard shortcuts so the
  // parent `ReviewPage` can bind Space/Enter without prop-drilling selection.
  useEffect(() => {
    if (!onRegisterCommit) return
    onRegisterCommit(pending ? onCommit : null)
    return () => onRegisterCommit(null)
  }, [pending, onCommit, onRegisterCommit])

  return (
    <div className="space-y-2 rounded-md border border-border/70 bg-muted/20 px-3 py-2.5">
      {pending ? (
        <ActiveDock
          pending={pending}
          metaOpen={metaOpen}
          onMetaToggle={() => setMetaOpen((v) => !v)}
          onCommit={onCommit}
          onDismiss={onDismiss}
          onChangePosition={onChangePosition}
          onChangeFormat={onChangeFormat}
        />
      ) : (
        <IdleDock />
      )}

      <div className="border-t border-border/40 pt-2">
        {noteOpen ? (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Note
              </label>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 text-muted-foreground"
                onClick={() => {
                  onChangeNote("")
                  setNoteOpen(false)
                }}
                title="Discard note"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
            <Textarea
              value={note}
              onChange={(e) => onChangeNote(e.target.value)}
              placeholder="Optional context for this annotation…"
              className="min-h-[44px] text-sm"
            />
          </div>
        ) : (
          <button
            onClick={() => setNoteOpen(true)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            <Plus className="h-3 w-3" />
            Add note
          </button>
        )}
      </div>
    </div>
  )
}

function IdleDock() {
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
      Select text in the response to mark an answer span, or pick a classification below.
      <span className="ml-auto hidden items-center gap-1 font-mono text-[10px] sm:flex">
        <kbd className="rounded border border-border bg-background px-1">Space</kbd>
        to commit when active
      </span>
    </div>
  )
}

function ActiveDock({
  pending,
  metaOpen,
  onMetaToggle,
  onCommit,
  onDismiss,
  onChangePosition,
  onChangeFormat,
}: {
  pending: PendingSpan
  metaOpen: boolean
  onMetaToggle: () => void
  onCommit: () => void
  onDismiss: () => void
  onChangePosition: (position: SpanPosition) => void
  onChangeFormat: (format: SpanFormat) => void
}) {
  const preview = pending.text.length > 80 ? `${pending.text.slice(0, 77)}…` : pending.text

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="max-w-[60vw] truncate border-primary/40 bg-primary/5 font-mono text-[11px] text-foreground">
          <span className="truncate">“{preview}”</span>
        </Badge>
        <div className="ml-auto flex items-center gap-1.5">
          <Button size="sm" onClick={onCommit} className="h-7 gap-1 px-2">
            <Check className="h-3.5 w-3.5" />
            Mark as Answer
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onMetaToggle}
            className="h-7 w-7 text-muted-foreground"
            title="Position / Format options"
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${metaOpen ? "rotate-180" : ""}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onDismiss}
            className="h-7 w-7 text-muted-foreground"
            title="Clear selection"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span>
          Auto: <span className="font-mono">{pending.position}</span> /{" "}
          <span className="font-mono">{pending.format}</span>
        </span>
        {metaOpen && (
          <>
            <label className="flex items-center gap-1">
              position
              <select
                className="h-6 rounded border border-input bg-background px-1 text-xs"
                value={pending.position}
                onChange={(e) => onChangePosition(e.target.value as SpanPosition)}
              >
                {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1">
              format
              <select
                className="h-6 rounded border border-input bg-background px-1 text-xs"
                value={pending.format}
                onChange={(e) => onChangeFormat(e.target.value as SpanFormat)}
              >
                {FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </label>
          </>
        )}
      </div>
    </div>
  )
}

/** Auto-detect annotation position from char offset in the response string. */
export function autoPosition(char_start: number, total_length: number): SpanPosition {
  if (total_length <= 0) return "middle"
  const ratio = char_start / total_length
  if (ratio < 0.33) return "start"
  if (ratio < 0.66) return "middle"
  return "end"
}

/** Auto-detect format by probing a small window around the selection. */
export function autoFormat(response: string, char_start: number, char_end: number): SpanFormat {
  const before = response.slice(Math.max(0, char_start - 16), char_start)
  const after = response.slice(char_end, char_end + 16)
  const inside = response.slice(char_start, char_end)
  const window = `${before}${inside}${after}`.toLowerCase()

  if (/\\boxed\s*\{/.test(window) || /\\boxed/.test(before)) return "boxed"
  // Bold — `**text**`. Check before/after separately.
  if (before.endsWith("**") || after.startsWith("**")) return "bold"
  // Strikethrough — `~~text~~`. Check before/after separately.
  if (before.endsWith("~~") || after.startsWith("~~")) return "strikethrough"
  // Italic — `*text*` (single, not part of **) or `_text_` (word-boundary `_`).
  // Underscore-italic: require a non-word char (or line-start) before the
  // opening `_`, to avoid misfiring on identifiers like `my_var`.
  if (/(^|[^*])\*$/.test(before) && /^\*(?!\*)/.test(after)) return "italic"
  if (/(^|[^\w])_$/.test(before) && /^_(?!\w)/.test(after)) return "italic"
  // Header — span sits on a line that begins with `#`. Walk `before` back to
  // the last newline and check.
  const lineStart = before.lastIndexOf("\n")
  const linePrefix = lineStart >= 0 ? before.slice(lineStart + 1) : before
  if (/^#{1,6}\s/.test(linePrefix)) return "header"
  // Labelled answer — the span follows a canonical label like "Answer:" or
  // its multilingual equivalent.
  if (
    /\b(answer|result|respuesta|resultado|antwort|réponse|答案|відповідь|recommendation|recomendación|recommandation|empfehlung|рекомендація|conclusion|conclusión|висновок|bottom line|in short|in summary|тldr|tl;dr)\s*[:：]\s*\**$/i.test(
      before,
    )
  ) {
    return "label"
  }
  return "plain"
}
