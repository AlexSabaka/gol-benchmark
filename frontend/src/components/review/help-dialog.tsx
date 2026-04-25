import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ShortcutRow {
  keys: string[]
  description: string
}

function KbdRow({ keys, description }: ShortcutRow) {
  return (
    <div className="flex items-center justify-between gap-3 py-0.5">
      <span className="text-[12px] text-muted-foreground">{description}</span>
      <span className="flex shrink-0 items-center gap-0.5">
        {keys.map((k, i) => (
          <kbd
            key={i}
            className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px] leading-none text-foreground"
          >
            {k}
          </kbd>
        ))}
      </span>
    </div>
  )
}

function Section({ title, rows }: { title: string; rows: ShortcutRow[] }) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <div className="space-y-0.5 rounded-md border border-border/60 bg-muted/20 px-3 py-2">
        {rows.map((r, i) => (
          <KbdRow key={i} {...r} />
        ))}
      </div>
    </div>
  )
}

interface MarkTypeRow {
  preview: React.ReactNode
  name: string
  description: string
  keys: string[]
}

function MarkTypeSection({ rows }: { rows: MarkTypeRow[] }) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Mark types · hold modifier key + click or drag
      </p>
      <div className="rounded-md border border-border/60 bg-muted/20 overflow-hidden">
        {rows.map((row, i) => (
          <div
            key={i}
            className={`grid grid-cols-[28px_130px_1fr_auto] items-start gap-3 px-3 py-2 text-[12px] ${
              i < rows.length - 1 ? "border-b border-border/40" : ""
            }`}
          >
            {/* Preview swatch */}
            <span className="flex justify-center">{row.preview}</span>
            {/* Name */}
            <span className="font-medium text-foreground shrink-0">{row.name}</span>
            {/* Description */}
            <span className="text-muted-foreground leading-snug">{row.description}</span>
            {/* Key binding */}
            <span className="flex shrink-0 items-center gap-0.5 justify-end">
              {row.keys.map((k, j) => (
                <kbd
                  key={j}
                  className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] leading-none text-foreground whitespace-nowrap"
                >
                  {k}
                </kbd>
              ))}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** v4 (Phase 1): four mark types. Modifier keys are now held letters —
 *  A for anchor, D for keyword, Shift for negative. No keyboard gymnastics:
 *  plain drag commits an answer span immediately (no dock).
 */
const MARK_ROWS: MarkTypeRow[] = [
  {
    preview: (
      <span className="inline-block w-16 rounded-sm border-b-2 border-primary bg-primary/20 px-1 text-center font-mono text-[11px] text-foreground leading-5">
        Walk
      </span>
    ),
    name: "Answer span",
    description: "The text the model gave as its final answer. Plain click or drag.",
    keys: ["Click/Drag"],
  },
  {
    preview: (
      <span className="inline-block w-16 rounded-sm border-b border-dashed border-indigo-500 bg-indigo-400/15 px-1 text-center font-mono text-[11px] text-foreground leading-5">
        Rec:
      </span>
    ),
    name: "Context anchor",
    description: "Label or phrase introducing the answer (e.g. 'Recommendation:').",
    keys: ["Hold A", "Click/Drag"],
  },
  {
    preview: (
      <span className="inline-block w-16 rounded-sm border-b border-dotted border-violet-500 bg-violet-400/15 px-1 text-center font-mono text-[11px] text-foreground leading-5">
        walk
      </span>
    ),
    name: "Answer keyword",
    description: "Canonical answer word (e.g. 'walk') — feeds keyword taxonomies.",
    keys: ["Hold D", "Click/Drag"],
  },
  {
    preview: (
      <span className="inline-block w-16 rounded-sm border-b-2 border-rose-500 bg-rose-400/15 px-1 text-center font-mono text-[11px] text-foreground leading-5">
        drive
      </span>
    ),
    name: "Negative",
    description: "Text the parser wrongly matched — feeds anti-patterns in the report.",
    keys: ["Hold ⇧", "Click/Drag"],
  },
]

export function HelpDialog({ open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(95vw,64rem)] sm:!max-w-[64rem]">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts &amp; Annotation Guide</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-[240px_1fr] gap-5">
          {/* Left column: nav + classification + dock stacked */}
          <div className="space-y-4">
            <Section
              title="Navigation"
              rows={[
                { keys: ["Space"], description: "Save (if draft) & advance; else skip" },
                { keys: ["⌃/⌘", "Space"], description: "Discard draft & advance" },
                { keys: ["←"], description: "Previous case" },
                { keys: ["⌃/⌘", "Z"], description: "Undo (current case)" },
                { keys: ["⌃/⌘", "⇧", "Z"], description: "Redo" },
                { keys: ["?"], description: "Toggle this help dialog" },
              ]}
            />
            <Section
              title="Classification (toggle)"
              rows={[
                { keys: ["2", "E"], description: "Truncated" },
                { keys: ["3", "Q"], description: "Unrecoverable" },
                { keys: ["4", "F"], description: "False-positive" },
                { keys: ["5"], description: "Hedge" },
              ]}
            />
          </div>

          {/* Right column: mark types table, fills remaining width */}
          <MarkTypeSection rows={MARK_ROWS} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
